import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from .schemas import Analysis, HistoryItem, ReportRequest, Stats

class ScanRepository:
    def __init__(self, database_url: str | None = None):
        configured = database_url or os.getenv('DATABASE_URL', 'sqlite:///./data/scamshield.db')
        if not configured.startswith('sqlite:///'):
            raise ValueError('The starter repository supports sqlite:/// locally; swap this adapter for PostgreSQL in production.')
        self.path = Path(configured.removeprefix('sqlite:///'))
        if not self.path.is_absolute():
            self.path = Path.cwd() / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY, content TEXT NOT NULL, scan_type TEXT NOT NULL, score INTEGER NOT NULL, verdict TEXT NOT NULL, analysis_json TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, reason TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS scans_created_at_idx ON scans(created_at DESC);
            ''')

    def save_scan(self, content: str, analysis: Analysis) -> None:
        with self.lock, self._connection() as connection:
            connection.execute('INSERT INTO scans VALUES (?, ?, ?, ?, ?, ?, ?)', (analysis.id, content, analysis.scan_type, analysis.score, analysis.verdict, analysis.model_dump_json(), analysis.created_at.isoformat()))

    def history(self, limit: int = 20) -> list[HistoryItem]:
        with self._connection() as connection:
            rows = connection.execute('SELECT id, content, scan_type, score, verdict, created_at FROM scans ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
        return [HistoryItem(id=row['id'], preview=row['content'][:82], scan_type=row['scan_type'], score=row['score'], verdict=row['verdict'], created_at=datetime.fromisoformat(row['created_at'])) for row in rows]

    def stats(self) -> Stats:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) total, SUM(verdict = 'High risk') high_risk, SUM(verdict = 'Caution') caution, SUM(verdict = 'Safe') safe, COALESCE(AVG(score), 0) average_score FROM scans").fetchone()
        return Stats(total_scans=row['total'], high_risk=row['high_risk'] or 0, caution=row['caution'] or 0, safe=row['safe'] or 0, average_score=round(row['average_score'], 1))

    def save_report(self, report: ReportRequest) -> None:
        with self.lock, self._connection() as connection:
            connection.execute('INSERT INTO reports(content, reason, notes, created_at) VALUES (?, ?, ?, ?)', (report.content, report.reason, report.notes, datetime.now(timezone.utc).isoformat()))
