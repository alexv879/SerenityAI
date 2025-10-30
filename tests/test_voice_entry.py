from fastapi import FastAPI
from fastapi.testclient import TestClient
from endpoints.voice_entry import router as voice_router


def make_app():
    app = FastAPI()
    app.include_router(voice_router)
    return app


def test_voice_entry_returns_xml_with_gather():
    app = make_app()
    client = TestClient(app)
    resp = client.post("/voice/entry")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    body = resp.text
    assert "<Gather" in body
    assert "/voice/route" in body


def test_voice_route_news_keyword():
    app = make_app()
    client = TestClient(app)
    resp = client.post("/voice/route", data={"SpeechResult": "news today"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "update" in resp.text.lower()
