"""Administrative commands.

    python -m app.cli seed        # create the demo workspace
    python -m app.cli reset       # drop every table, recreate, re-seed
    python -m app.cli status      # what this instance is configured with
    python -m app.cli create-user # add a user to an existing company
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal, engine
from app.models import Base, Company, User, UserRole
from app.services import llm
from app.services.seed import ensure_agents, seed_demo_workspace, unique_slug


def cmd_seed(_: argparse.Namespace) -> int:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        company = seed_demo_workspace(db)
        db.commit()

    if company is None:
        print(f"Demo workspace already exists ({settings.demo_email}). Nothing to do.")
        return 0

    print(f"Seeded '{company.name}'")
    print(f"  sign in: {settings.demo_email} / {settings.demo_password}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    if not args.yes:
        target = engine.url.render_as_string(hide_password=True)
        answer = input(f"This DROPS every table in {target}. Type 'yes' to continue: ")
        if answer.strip().lower() != "yes":
            print("Aborted.")
            return 1

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Schema recreated.")
    return cmd_seed(args)


def cmd_reindex(_: argparse.Namespace) -> int:
    """Rebuild every document's search index from its stored original.

    Required after any change to `rag.tokenize` (stopwords, stemming), because
    chunk term-frequencies are computed at index time and would otherwise keep
    the vocabulary of the old tokenizer.
    """
    from pathlib import Path

    from app.models import Document, DocumentStatus
    from app.services import rag

    rebuilt = skipped = 0
    with SessionLocal() as db:
        for document in db.execute(select(Document)).scalars().all():
            if not document.storage_path or not Path(document.storage_path).exists():
                print(f"  skip     {document.filename}: original is no longer on disk")
                skipped += 1
                continue
            try:
                raw = Path(document.storage_path).read_bytes()
                text = rag.extract_text(document.filename, document.content_type, raw)
            except Exception as exc:  # noqa: BLE001 - report and carry on
                print(f"  skip     {document.filename}: {exc}")
                skipped += 1
                continue

            document.chunk_count = rag.index_document(db, document, text)
            document.status = DocumentStatus.INDEXED
            rebuilt += 1
            print(f"  reindex  {document.filename}: {document.chunk_count} chunks")
        db.commit()

    print(f"Reindexed {rebuilt} document(s); {skipped} skipped.")
    if skipped:
        print("Skipped documents keep their old index and may not match new queries.")
    return 0 if not skipped else 1


def cmd_status(_: argparse.Namespace) -> int:
    print(f"environment : {settings.environment}")
    print(f"database    : {engine.url.render_as_string(hide_password=True)}")
    print(f"engine      : {'anthropic:' + settings.llm_model if llm.is_available() else 'deterministic'}")
    print(f"storage     : {settings.storage_dir}")

    with SessionLocal() as db:
        companies = db.execute(select(Company)).scalars().all()
        print(f"companies   : {len(companies)}")
        for company in companies:
            users = db.execute(select(User).where(User.company_id == company.id)).scalars().all()
            print(f"  - {company.name} ({company.slug}) · {len(users)} user(s)")
    return 0


def cmd_create_user(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        if db.execute(select(User).where(User.email == args.email)).scalar_one_or_none():
            print(f"A user with email {args.email} already exists.", file=sys.stderr)
            return 1

        if args.company:
            company = db.execute(
                select(Company).where(Company.slug == args.company)
            ).scalar_one_or_none()
            if company is None:
                print(f"No company with slug '{args.company}'.", file=sys.stderr)
                return 1
        else:
            company = Company(name=args.company_name or "New Company",
                              slug=unique_slug(db, args.company_name or "New Company"))
            db.add(company)
            db.flush()
            ensure_agents(db, company)

        user = User(
            company_id=company.id,
            email=args.email,
            full_name=args.name,
            hashed_password=hash_password(args.password),
            role=UserRole(args.role),
        )
        db.add(user)
        db.commit()

    print(f"Created {args.email} ({args.role}) in {company.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="create the demo workspace").set_defaults(func=cmd_seed)

    reset = sub.add_parser("reset", help="drop every table, recreate, re-seed")
    reset.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    reset.set_defaults(func=cmd_reset)

    sub.add_parser("status", help="show configuration and contents").set_defaults(func=cmd_status)

    sub.add_parser(
        "reindex",
        help="rebuild document search indexes (required after a tokenizer change)",
    ).set_defaults(func=cmd_reindex)

    create = sub.add_parser("create-user", help="add a user")
    create.add_argument("--email", required=True)
    create.add_argument("--password", required=True)
    create.add_argument("--name", default="New User")
    create.add_argument("--role", default="MEMBER", choices=[r.value for r in UserRole])
    create.add_argument("--company", help="slug of an existing company")
    create.add_argument("--company-name", help="name for a new company (if --company is omitted)")
    create.set_defaults(func=cmd_create_user)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
