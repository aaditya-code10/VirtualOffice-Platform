"""Test fixtures: an isolated SQLite database per test session."""
import os
import tempfile
from pathlib import Path

import pytest

# Configure the app for testing BEFORE importing anything that reads settings.
_TMP = Path(tempfile.mkdtemp(prefix="avo-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ["SECRET_KEY"] = "test-secret-key-of-at-least-32-bytes-for-hs256"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["RATE_LIMIT_DELAY_SECONDS"] = "0"
os.environ["DEBUG"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.seed import seed_demo_workspace  # noqa: E402

settings.rate_limit_delay_seconds = 0.0


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def registered(client):
    """A fresh company + owner, returning (client, auth headers, payload)."""
    import uuid

    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "full_name": "Test Owner",
            "company_name": f"Testco {uuid.uuid4().hex[:6]}",
            "industry": "Technology",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user": body["user"],
        "email": email,
        "password": "supersecret1",
    }


@pytest.fixture
def demo(client):
    """The seeded demo workspace with metrics, facts and an indexed document."""
    session = SessionLocal()
    try:
        company = seed_demo_workspace(session)
        session.commit()
        if company is None:
            from sqlalchemy import select

            from app.config import settings
            from app.models import Company, User

            user = session.execute(
                select(User).where(User.email == settings.demo_email)
            ).scalar_one()
            company = session.get(Company, user.company_id)
        company_id = company.id
    finally:
        session.close()

    from app.config import settings

    response = client.post(
        "/api/auth/login",
        json={"email": settings.demo_email, "password": settings.demo_password},
    )
    assert response.status_code == 200, response.text
    return {
        "headers": {"Authorization": f"Bearer {response.json()['access_token']}"},
        "company_id": company_id,
    }
