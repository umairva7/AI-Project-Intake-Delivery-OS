import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_brief_returns_pending_intake():
    response = client.post(
        "/briefs",
        params={"brief_text": "We need a React frontend with Python backend..."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["status"] == "pending_review"

def test_get_brief_returns_intake():
    # First create
    create_response = client.post(
        "/briefs",
        params={"brief_text": "We need..."}
    )
    brief_id = create_response.json()["id"]
    
    # Then retrieve
    get_response = client.get(f"/briefs/{brief_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == brief_id

def test_approve_brief_transitions_status():
    # Create
    create_response = client.post("/briefs", params={"brief_text": "We need..."})
    brief_id = create_response.json()["id"]
    
    # Approve
    approve_response = client.post(f"/briefs/{brief_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

def test_get_nonexistent_brief_returns_404():
    response = client.get("/briefs/doesnotexist")
    assert response.status_code == 404

def test_mark_issues_flags_problems():
    # Create
    create_response = client.post(
        "/briefs",
        params={"brief_text": "We need a portal for tracking employee hours."}
    )
    brief_id = create_response.json()["id"]

    # Mark issues
    issues = ["Database technology not specified", "Timeline is unclear"]
    flag_response = client.post(
        f"/briefs/{brief_id}/mark-issues",
        json=issues
    )
    assert flag_response.status_code == 200
    assert flag_response.json()["status"] == "flagged"
    assert flag_response.json()["id"] == brief_id