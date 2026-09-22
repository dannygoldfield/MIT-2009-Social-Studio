"""Small SQLite boundary. Each operation owns its connection and transaction."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

JSON_FIELDS = {"analysis", "settings", "context", "sources", "artifacts", "request", "snapshot", "detail"}


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid4().hex


def packed(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def unpack(row):
    if row is None:
        return None
    return {k: json.loads(v) if k in JSON_FIELDS else v for k, v in dict(row).items()}


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "studio.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RuntimeError(f"Unsupported database version {version}. Back up before upgrading.")
            db.executescript(Path(__file__).with_name("schema.sql").read_text())

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def all(self, sql, args=()):
        with self.connect() as db:
            return [unpack(r) for r in db.execute(sql, args)]

    def one(self, sql, args=()):
        rows = self.all(sql, args)
        if not rows:
            raise ValueError("That record was not found.")
        return rows[0]

    def path(self, relative):
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Media must remain within this studio's data folder.")
        return target

    def relative(self, path):
        return str(Path(path).resolve().relative_to(self.root))

    @staticmethod
    def event(db, project_id, user_id, action, detail):
        db.execute(
            "INSERT INTO events(project_id,user_id,action,detail,created_at) VALUES(?,?,?,?,?)",
            (project_id, user_id, action, packed(detail), now()),
        )
