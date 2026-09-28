from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import services
from app.storage import LocalStore, get_store
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    store = LocalStore(tmp_path / "database.json")
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_data_crud_and_summary(client):
    assert client.get("/api/data/summary").json()["count"] == 0
    created = client.post(
        "/api/data", json={"date": "2026-09-01", "value": 60, "memo": "FastAPI"}
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert client.get("/api/data/summary").json()["metrics"]["average"] == 60
    assert client.put(
        f"/api/data/{item_id}", json={"date": "2026-09-02", "value": 90}
    ).status_code == 200
    assert client.delete(f"/api/data/{item_id}").status_code == 204


def test_validation(client):
    assert client.post(
        "/api/data", json={"date": "잘못된 날짜", "value": -1}
    ).status_code == 422


def test_mock_chat_autosaves_without_tokens(client):
    client.post("/api/data", json={"date": "2026-09-01", "value": 60})
    result = client.post("/api/chat", json={"message": "평균을 알려줘"})
    assert result.status_code == 200
    assert result.json()["usage"]["total_tokens"] == 0
    item_id = result.json()["conversation_id"]
    assert len(client.get(f"/api/conversations/{item_id}").json()["messages"]) == 2
    assert "messages" not in client.get("/api/conversations").json()[0]


def test_openai_request_is_small(client, monkeypatch):
    seen = []
    clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            clients.append(kwargs)
            self.chat = self
            self.completions = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def create(self, **kwargs):
            seen.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="평균은 60분입니다.")
                    )
                ],
                usage=None,
            )

    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")
    monkeypatch.setattr(services, "OpenAI", FakeOpenAI)
    client.post("/api/data", json={"date": "2026-09-01", "value": 60})
    response = client.post("/api/chat", json={"message": "평균은?"})
    assert response.status_code == 200
    assert clients[0]["base_url"] == "https://example.test/v1"
    assert seen[0]["max_completion_tokens"] == 220
    assert len(seen[0]["messages"]) == 2
    assert seen[0]["messages"][0]["role"] == "system"


def test_conversation_manual_save_and_delete(client):
    created = client.post(
        "/api/conversations",
        json={
            "title": "테스트 대화",
            "messages": [{"role": "user", "content": "안녕"}],
        },
    )
    item_id = created.json()["id"]
    assert client.delete(f"/api/conversations/{item_id}").status_code == 204
    assert client.get(f"/api/conversations/{item_id}").status_code == 404


def test_docs(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
