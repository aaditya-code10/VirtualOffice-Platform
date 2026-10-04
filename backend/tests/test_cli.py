"""Administrative CLI."""
from app.cli import main
from app.config import settings
from app.database import SessionLocal
from app.models import Company, User


def test_seed_is_idempotent(capsys):
    assert main(["seed"]) == 0
    first = capsys.readouterr().out

    assert main(["seed"]) == 0
    second = capsys.readouterr().out

    assert "Seeded" in first or "already exists" in first
    assert "already exists" in second

    with SessionLocal() as db:
        from sqlalchemy import func, select

        count = db.execute(
            select(func.count(User.id)).where(User.email == settings.demo_email)
        ).scalar_one()
    assert count == 1


def test_status_reports_configuration(capsys):
    assert main(["status"]) == 0
    output = capsys.readouterr().out
    assert "environment" in output
    assert "database" in output
    assert "engine" in output


def test_create_user_rejects_duplicates(capsys):
    args = [
        "create-user", "--email", "cli-user@example.com", "--password", "supersecret1",
        "--name", "CLI User", "--role", "ADMIN", "--company-name", "CLI Test Co",
    ]
    assert main(args) == 0
    assert main(args) == 1  # second attempt is rejected

    with SessionLocal() as db:
        from sqlalchemy import select

        user = db.execute(
            select(User).where(User.email == "cli-user@example.com")
        ).scalar_one()
        company = db.get(Company, user.company_id)

    assert user.role.value == "ADMIN"
    assert company is not None


def test_create_user_in_an_existing_company(capsys):
    with SessionLocal() as db:
        from sqlalchemy import select

        slug = db.execute(select(Company.slug)).scalars().first()

    assert main([
        "create-user", "--email", "second@example.com", "--password", "supersecret1",
        "--name", "Second Seat", "--role", "VIEWER", "--company", slug,
    ]) == 0

    assert main([
        "create-user", "--email", "third@example.com", "--password", "supersecret1",
        "--company", "no-such-company",
    ]) == 1
