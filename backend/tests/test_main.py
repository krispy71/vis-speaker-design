# backend/tests/test_main.py
import pytest
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch
from fastapi.testclient import TestClient

import database

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    import database as db_mod
    db_mod.DB_PATH = tmp_path / "test.db"
    database.init_db()

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

def test_create_session(client):
    response = client.post("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "phase" in data

def test_get_session(client):
    create = client.post("/sessions")
    session_id = create.json()["session_id"]
    get = client.get(f"/sessions/{session_id}")
    assert get.status_code == 200
    assert get.json()["id"] == session_id

def test_get_session_404(client):
    response = client.get("/sessions/nonexistent")
    assert response.status_code == 404

def test_send_message_intake(client):
    create = client.post("/sessions")
    session_id = create.json()["session_id"]
    with patch("session_manager.run_claude", return_value="What music do you enjoy?"):
        response = client.post(
            f"/sessions/{session_id}/message",
            json={"content": "I want bookshelf speakers"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "What music do you enjoy?"
    assert data["phase"] == "intake"
    assert data["transition"] is None
