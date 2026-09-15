# app/storage/db.py
import sys
from pathlib import Path
import sqlite3

# Ensure project root is in sys.path when executed directly as a script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config import settings


def get_db_path() -> Path:
    """Resolve database file path relative to project root"""
    raw_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if raw_path.startswith("./"):
        return project_root / raw_path[2:]
    return Path(raw_path)


def get_db_connection() -> sqlite3.Connection:
    """Return SQLite connection with foreign keys and dict-like row access"""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: Raw requests (for audit trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY,
        raw_text TEXT NOT NULL,
        source TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table 2: Pending intakes (for analysis + human review)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intakes (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        extracted_json TEXT,
        team_recommendation_json TEXT,
        checklist_json TEXT,
        requires_manual_review BOOLEAN DEFAULT 0,
        review_notes TEXT,
        issues_marked TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests (id)
    )
    """)

    # Table 3: Approved intakes (final record)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approved_intakes (
        id TEXT PRIMARY KEY,
        intake_id TEXT NOT NULL,
        request_id TEXT NOT NULL,
        final_data_json TEXT,
        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_by TEXT,
        status TEXT,
        FOREIGN KEY (intake_id) REFERENCES intakes (id),
        FOREIGN KEY (request_id) REFERENCES requests (id)
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", get_db_path())