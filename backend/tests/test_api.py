import time

import pytest
from fastapi.testclient import TestClient

import main
from agents.orchestrator import Sources
from tests.helpers import FakeMarket, breakout_frame, news_for


@pytest.fixture
def client(monkeypatch):
    fake = lambda: Sources(
        market=FakeMarket({"BRK": breakout_frame()}, {"BRK": {"name": "Breakout Co", "float_shares": 5_000_000}}),
        news=news_for({"BRK": ["Breakout Co wins $40M Navy contract"]}),
    )
    monkeypatch.setattr(main.runner, "_sources_factory", fake)
    return TestClient(main.app)


def wait_for(client, scan_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        scan = client.get(f"/api/scans/{scan_id}").json()
        if scan["status"] != "running":
            return scan
        time.sleep(0.05)
    raise TimeoutError(scan_id)


def test_health_and_status(client):
    assert client.get("/health").json() == {"status": "ok"}
    status = client.get("/api/status").json()
    assert status["sources"]["yfinance"] is True
    assert status["llm_model"] is None


def test_strategies_crud(client):
    names = [s["name"] for s in client.get("/api/strategies").json()]
    assert "Small Cap Momentum" in names

    new = {"id": "9", "name": "Test", "criteria": {"price_min": 1, "price_max": 5}, "setup_preferences": ["breakout"]}
    assert client.put("/api/strategies", json=new).status_code == 200
    assert "Test" in [s["name"] for s in client.get("/api/strategies").json()]
    assert client.delete("/api/strategies/Test").status_code == 200
    assert client.delete("/api/strategies/Test").status_code == 404


def test_scan_round_trip(client):
    assert client.get("/api/scans/latest").status_code == 404

    res = client.post("/api/scans", json={"strategy": "Small Cap Momentum", "tickers": ["BRK"]})
    assert res.status_code == 202
    scan = wait_for(client, res.json()["id"])

    assert scan["status"] == "done"
    assert scan["final"][0]["ticker"] == "BRK"
    assert client.get("/api/scans/latest").json()["id"] == scan["id"]
    assert client.get("/api/scans").json()[0]["id"] == scan["id"]

    detail = client.get(f"/api/scans/{scan['id']}/tickers/brk").json()
    assert detail["candidate"]["ticker"] == "BRK"
    assert len(detail["trace"]) == 8


def test_bad_requests(client):
    assert client.post("/api/scans", json={"strategy": "Nope"}).status_code == 404
    assert client.get("/api/scans/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/scans/nope").status_code == 404
