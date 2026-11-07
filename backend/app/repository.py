import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .schemas import Analysis, HistoryItem, ReportRequest, Stats


def _database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


class ScanRepository:
    """SQLAlchemy repository with provider identities and per-user data isolation."""

    def __init__(self, database_url: str | None = None):
        configured = _database_url(database_url or os.getenv("DATABASE_URL", "sqlite:///./data/scamshield.db"))
        if configured.startswith("sqlite:///"):
            raw_path = configured.removeprefix("sqlite:///")
            if raw_path != ":memory:":
                path = Path(raw_path)
                if not path.is_absolute():
                    path = Path.cwd() / path
                path.parent.mkdir(parents=True, exist_ok=True)
                configured = f"sqlite:///{path}"
        elif not configured.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use SQLite or PostgreSQL.")

        connect_args = {"check_same_thread": False} if configured.startswith("sqlite:") else {}
        self.engine: Engine = create_engine(configured, pool_pre_ping=True, connect_args=connect_args)
        self._initialize()

    def _initialize(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS identity_links (
                    provider TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    email TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (provider, subject)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    scan_type TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    user_id TEXT REFERENCES users(id)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    user_id TEXT REFERENCES users(id)
                )
            """))
            scan_columns = {column["name"] for column in inspect(connection).get_columns("scans")}
            report_columns = {column["name"] for column in inspect(connection).get_columns("reports")}
            if "user_id" not in scan_columns:
                connection.execute(text("ALTER TABLE scans ADD COLUMN user_id TEXT REFERENCES users(id)"))
            if "user_id" not in report_columns:
                connection.execute(text("ALTER TABLE reports ADD COLUMN user_id TEXT REFERENCES users(id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS scans_user_created_idx ON scans(user_id, created_at DESC)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS reports_user_created_idx ON reports(user_id, created_at DESC)"))

    def get_or_create_user(self, provider: str, subject: str, email: str | None = None) -> str:
        with self.engine.begin() as connection:
            existing = connection.execute(
                text("SELECT user_id FROM identity_links WHERE provider = :provider AND subject = :subject"),
                {"provider": provider, "subject": subject},
            ).first()
            if existing:
                return str(existing[0])
            user_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(text("INSERT INTO users (id, created_at) VALUES (:id, :created_at)"), {"id": user_id, "created_at": now})
            connection.execute(text("""
                INSERT INTO identity_links (provider, subject, user_id, email, created_at)
                VALUES (:provider, :subject, :user_id, :email, :created_at)
            """), {"provider": provider, "subject": subject, "user_id": user_id, "email": email, "created_at": now})
            return user_id

    def link_identity(self, user_id: str, provider: str, subject: str, email: str | None = None) -> None:
        with self.engine.begin() as connection:
            existing = connection.execute(
                text("SELECT user_id FROM identity_links WHERE provider = :provider AND subject = :subject"),
                {"provider": provider, "subject": subject},
            ).first()
            if existing:
                if existing[0] != user_id:
                    raise ValueError("This provider account is already linked to a different ScamShield account.")
                return
            connection.execute(text("""
                INSERT INTO identity_links (provider, subject, user_id, email, created_at)
                VALUES (:provider, :subject, :user_id, :email, :created_at)
            """), {
                "provider": provider, "subject": subject, "user_id": user_id,
                "email": email, "created_at": datetime.now(timezone.utc).isoformat(),
            })

    def save_scan(self, content: str, analysis: Analysis, user_id: str | None = None) -> None:
        if not user_id:
            return
        with self.engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO scans (id, content, scan_type, score, verdict, analysis_json, created_at, user_id)
                VALUES (:id, :content, :scan_type, :score, :verdict, :analysis_json, :created_at, :user_id)
            """), {
                "id": analysis.id, "content": content, "scan_type": analysis.scan_type,
                "score": analysis.score, "verdict": analysis.verdict,
                "analysis_json": analysis.model_dump_json(), "created_at": analysis.created_at.isoformat(),
                "user_id": user_id,
            })

    def history(self, user_id: str, limit: int = 20) -> list[HistoryItem]:
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT id, content, scan_type, score, verdict, created_at
                FROM scans WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit
            """), {"user_id": user_id, "limit": limit}).mappings().all()
        return [
            HistoryItem(
                id=row["id"], preview=row["content"][:82], scan_type=row["scan_type"],
                score=row["score"], verdict=row["verdict"],
                created_at=datetime.fromisoformat(row["created_at"]),
            ) for row in rows
        ]

    def stats(self, user_id: str) -> Stats:
        with self.engine.connect() as connection:
            row = connection.execute(text("""
                SELECT COUNT(*) AS total,
                    SUM(CASE WHEN verdict = 'High risk' THEN 1 ELSE 0 END) AS high_risk,
                    SUM(CASE WHEN verdict = 'Caution' THEN 1 ELSE 0 END) AS caution,
                    SUM(CASE WHEN verdict = 'Safe' THEN 1 ELSE 0 END) AS safe,
                    COALESCE(AVG(score), 0) AS average_score
                FROM scans WHERE user_id = :user_id
            """), {"user_id": user_id}).mappings().one()
        return Stats(
            total_scans=row["total"], high_risk=row["high_risk"] or 0,
            caution=row["caution"] or 0, safe=row["safe"] or 0,
            average_score=round(float(row["average_score"]), 1),
        )

    def save_report(self, report: ReportRequest, user_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO reports (id, content, reason, notes, created_at, user_id)
                VALUES (:id, :content, :reason, :notes, :created_at, :user_id)
            """), {
                "id": str(uuid4()), "content": report.content, "reason": report.reason,
                "notes": report.notes, "created_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
            })

    def close(self) -> None:
        self.engine.dispose()
