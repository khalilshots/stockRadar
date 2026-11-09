from types import SimpleNamespace

import litellm
from pydantic import BaseModel

from config.settings import settings
from utils import llm


class Verdict(BaseModel):
    passed: bool
    reason: str


def reply(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_extract_json_handles_fences_and_prose():
    assert llm.extract_json('Sure! ```json\n{"passed": true, "reason": "ok"}\n```') == {"passed": True, "reason": "ok"}
    assert llm.extract_json("no json here") is None
    assert llm.extract_json('{"broken": ') is None


def test_ask_returns_none_when_llm_is_off():
    assert llm.ask("sys", "user", Verdict) is None


def test_ask_validates_against_schema(monkeypatch):
    monkeypatch.setattr(settings, "llm_model", "ollama/llama3.2:3b")
    monkeypatch.setattr(litellm, "completion", lambda **kw: reply('{"passed": true, "reason": "in range"}'))
    assert llm.ask("sys", "user", Verdict) == Verdict(passed=True, reason="in range")

    monkeypatch.setattr(litellm, "completion", lambda **kw: reply('{"passed": "maybe"}'))
    assert llm.ask("sys", "user", Verdict) is None


def test_ask_stops_calling_after_a_failure(monkeypatch):
    calls = []

    def broken(**kw):
        calls.append(1)
        raise ConnectionError("ollama not running")

    monkeypatch.setattr(settings, "llm_model", "ollama/llama3.2:3b")
    monkeypatch.setattr(litellm, "completion", broken)
    assert llm.ask("sys", "user", Verdict) is None
    assert llm.ask("sys", "user", Verdict) is None
    assert len(calls) == 1
