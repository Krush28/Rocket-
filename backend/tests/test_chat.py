from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def sid(): return f"test-{uuid4()}"

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_chat_asks_for_missing_details():
    response = client.post("/api/chat", json={"session_id": sid(), "message": "tomatoes"})
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["crop"] == "Tomatoes"
    assert body["ready_for_confirmation"] is False
    assert body["missing_fields"][0] == "quantity_kg"

def test_quantity_units_are_normalized_and_confirmation_is_gated():
    session = sid()
    for message in ["tomatoes", "2 quintals", "near Ponda Goa", "ready now"]:
        response = client.post("/api/chat", json={"session_id": session, "message": message})
        assert response.status_code == 200
    body = response.json()
    assert body["profile"]["quantity_kg"] == 200
    assert body["profile"]["quantity_original"] == "2 quintals"
    assert body["ready_for_confirmation"] is True
    assert body["confirmed"] is False
    confirmed = client.post("/api/profile/confirm", json={"session_id": session, "confirmed": True})
    assert confirmed.json()["confirmed"] is True

def test_session_survives_manager_reload():
    session = sid()
    client.post("/api/chat", json={"session_id": session, "message": "potatoes"})
    loaded = client.get(f"/api/profile/{session}")
    assert loaded.status_code == 200
    assert loaded.json()["profile"]["crop"] == "Potatoes"

def test_hindi_prompt_and_language_detection():
    response = client.post("/api/chat", json={"session_id": sid(), "message": "टमाटर"})
    assert response.status_code == 200
    assert response.json()["profile"]["preferred_language"] == "hi"
    assert "कितनी उपज" in response.json()["reply"]

def test_combined_farmer_message_and_thousand_separator():
    session = sid()
    response = client.post("/api/chat", json={
        "session_id": session,
        "message": "tomatoes, 1,000 kg, near Ponda Goa, ready now"
    })
    body = response.json()
    assert body["profile"]["crop"] == "Tomatoes"
    assert body["profile"]["quantity_kg"] == 1000
    assert body["profile"]["location"] == "Ponda Goa"
    assert body["profile"]["ready_when"] == "Now"
    assert body["ready_for_confirmation"] is True
