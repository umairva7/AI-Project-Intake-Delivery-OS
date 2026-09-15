import sqlite3
import pytest
from app.storage.db import get_db_connection, init_db, get_db_path


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure tables exist before tests run"""
    init_db()


def test_tables_exist():
    conn = get_db_connection()
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    table_names = [t["name"] for t in tables]
    assert "requests" in table_names
    assert "intakes" in table_names
    assert "approved_intakes" in table_names
    conn.close()


def test_insert_request_and_read():
    conn = get_db_connection()
    cursor = conn.cursor()

    req_id = "REQ-test001"
    cursor.execute(
        "INSERT INTO requests (id, raw_text, source, status) VALUES (?, ?, ?, ?)",
        (req_id, "We need a dashboard for tracking hours.", "web_form", "processing"),
    )
    conn.commit()

    row = cursor.execute("SELECT * FROM requests WHERE id = ?", (req_id,)).fetchone()
    assert row is not None
    assert row["id"] == req_id
    assert row["raw_text"] == "We need a dashboard for tracking hours."
    assert row["source"] == "web_form"
    assert row["status"] == "processing"
    assert row["created_at"] is not None

    # Cleanup
    cursor.execute("DELETE FROM requests WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()


def test_foreign_key_enforcement():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Attempting to insert an intake referencing a non-existent request_id
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO intakes (id, request_id, status) VALUES (?, ?, ?)",
            ("INT-invalid", "REQ-nonexistent", "pending_review"),
        )
        conn.commit()

    conn.close()


def test_intake_lifecycle_insert_and_approval():
    conn = get_db_connection()
    cursor = conn.cursor()

    req_id = "REQ-lifecycle-1"
    intake_id = "INT-lifecycle-1"
    approved_id = "APPROVED-lifecycle-1"

    # Step 1: Insert request
    cursor.execute(
        "INSERT INTO requests (id, raw_text, source, status) VALUES (?, ?, ?, ?)",
        (req_id, "Build a customer portal.", "email", "processing"),
    )

    # Step 2: Insert intake referencing request
    cursor.execute(
        """
        INSERT INTO intakes (
            id, request_id, extracted_json, team_recommendation_json, checklist_json,
            requires_manual_review, review_notes, issues_marked, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intake_id,
            req_id,
            '{"project_name": "Customer Portal"}',
            '{"team": "Web Development"}',
            '{"items": []}',
            1,
            "Needs manual check on timeline.",
            '["Timeline unclear"]',
            "pending_review",
        ),
    )

    # Step 3: Insert approved intake referencing intake and request
    cursor.execute(
        """
        INSERT INTO approved_intakes (id, intake_id, request_id, final_data_json, approved_by, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            approved_id,
            intake_id,
            req_id,
            '{"final": "data"}',
            "pm_user",
            "approved",
        ),
    )
    conn.commit()

    # Query back and verify row factory access
    intake_row = cursor.execute("SELECT * FROM intakes WHERE id = ?", (intake_id,)).fetchone()
    assert intake_row["requires_manual_review"] == 1
    assert intake_row["review_notes"] == "Needs manual check on timeline."
    assert intake_row["issues_marked"] == '["Timeline unclear"]'

    approved_row = cursor.execute("SELECT * FROM approved_intakes WHERE id = ?", (approved_id,)).fetchone()
    assert approved_row["approved_by"] == "pm_user"
    assert approved_row["status"] == "approved"

    # Cleanup
    cursor.execute("DELETE FROM approved_intakes WHERE id = ?", (approved_id,))
    cursor.execute("DELETE FROM intakes WHERE id = ?", (intake_id,))
    cursor.execute("DELETE FROM requests WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()
