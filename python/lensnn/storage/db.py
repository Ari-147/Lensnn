import os
import sqlite3

from .. import config


def default_db_path(runs_dir=None):
    if runs_dir is None:
        return config.DB_PATH
    return os.path.join(runs_dir, config.DB_FILENAME)


def get_connection(db_path):
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            framework TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS captures (
            capture_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            step INTEGER,
            timestamp TEXT NOT NULL,
            npz_path TEXT NOT NULL,
            model_summary TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
        """
    )
    conn.commit()
    conn.close()


def insert_run(db_path, run_id, name, framework, created_at):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO runs (run_id, name, framework, created_at) VALUES (?, ?, ?, ?)",
        (run_id, name, framework, created_at),
    )
    conn.commit()
    conn.close()


def update_run_framework(db_path, run_id, framework):
    conn = get_connection(db_path)
    conn.execute("UPDATE runs SET framework = ? WHERE run_id = ?", (framework, run_id))
    conn.commit()
    conn.close()


def insert_capture(db_path, capture_id, run_id, step, timestamp, npz_path, model_summary):
    conn = get_connection(db_path)
    conn.execute(
        """
        INSERT INTO captures (capture_id, run_id, step, timestamp, npz_path, model_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (capture_id, run_id, step, timestamp, npz_path, model_summary),
    )
    conn.commit()
    conn.close()


def list_runs(db_path):
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM runs ORDER BY created_at").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_captures(db_path, run_id):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM captures WHERE run_id = ? ORDER BY timestamp", (run_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_capture(db_path, capture_id):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
