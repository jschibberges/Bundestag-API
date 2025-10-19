# tests/conftest.py
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest, requests
@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _blocked(*a, **k): raise AssertionError("Network call blocked in tests")
    monkeypatch.setattr(requests, "get", _blocked, raising=True)
    monkeypatch.setattr(requests.sessions.Session, "get", _blocked, raising=True)