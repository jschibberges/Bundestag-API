# tests/test_bta_wrapper_improved.py
"""
Improved, self-contained pytest suite for bta_wrapper.

Key improvements:
- Autouse fixture to block real network calls.
- Robust FakeResponse/FakeSession mirroring requests.Response & Session behavior.
- Reusable fixtures for connection setup.
- Parametrized tests for wrapper → resource mapping.
- Focused tests for datetime coercion, list params, fulltext routing, error handling, and timeouts.
"""

from __future__ import annotations

import types
import inspect
from datetime import datetime
from typing import Iterable, List, Optional

import pytest
import requests

# ---- Auto-block all real network in tests (fail fast) ----
@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    def _blocked(*a, **k):
        raise AssertionError("Network call blocked in tests")
    monkeypatch.setattr(requests, "get", _blocked, raising=True)
    monkeypatch.setattr(requests.sessions.Session, "get", _blocked, raising=True)


# ---- Robust fakes ------------------------------------------------------------

class FakeResponse:
    """A lightweight, requests.Response-like object for tests."""
    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[dict] = None,
        reason: str = "OK",
        text: str = "",
        url: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {"numFound": 0, "documents": [], "cursor": None}
        self.reason = reason
        self.text = text or reason or ""
        self.url = url or "https://search.dip.bundestag.de/api/v1/test"
        # mimic requests.Response.request structure
        self.request = types.SimpleNamespace(url=self.url, method="GET")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if not self.ok:
            msg = f"{self.status_code} {self.reason} for url: {getattr(self, 'url', 'unknown')}"
            raise requests.HTTPError(msg)


class FakeSession:
    """A minimal Session that records the last call & returns preloaded responses."""
    def __init__(self, responses: Optional[List[FakeResponse]] = None) -> None:
        self.responses = responses or [FakeResponse(200, {"numFound": 0, "documents": []})]
        self.call_count = 0
        self.max_calls = 10  # Prevent infinite loops in tests
        self.last_url = None
        self.last_params = None
        self.last_timeout = None
        self.headers = {}

    def mount(self, *args, **kwargs):
        # bta_wrapper may call session.mount; we accept & ignore.
        return None

    def get(self, url, params=None, timeout=None):
        if self.call_count >= self.max_calls:
            # Prevent infinite loops in tests
            raise RuntimeError(f"Too many API calls in test ({self.call_count})")
       
        self.last_url = url
        self.last_params = params or {}
        self.last_timeout = timeout
        # pick response (support multiple sequential responses)
        idx = min(self.call_count, len(self.responses) - 1)
        resp = self.responses[idx]
        self.call_count += 1
        # keep url/request up to date
        resp.url = url
        resp.request = types.SimpleNamespace(url=url, method="GET")
        return resp


# ---- Fixtures ----------------------------------------------------------------

@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def conn(monkeypatch, fake_session):
    # Import here to avoid import errors if package layout changes.
    try:
        from bundestag_api.bta_wrapper import btaConnection
    except ImportError:
        from bta_wrapper import btaConnection  # fallback for non-packaged layout

    # Ensure our connection uses the fake session
    c = btaConnection(apikey="testapikey0123456789")
    c.session = fake_session
    return c


# ---- Tests -------------------------------------------------------------------

@pytest.mark.parametrize(
    "wrapper, expected_resource",
    [
        ("search_document", "drucksache"),
        ("search_procedure", "vorgang"),
        ("search_plenaryprotocol", "plenarprotokoll"),
        ("search_activity", "aktivitaet"),
        ("search_person", "person"),
        ("search_procedureposition", "vorgangsposition"),
    ],
)
def test_wrappers_delegate_to_query_with_correct_resource(conn, wrapper, expected_resource):
    called = {}

    def fake_query(*, resource, **kw):
        called["resource"] = resource
        return [] # Return a list as expected by the wrapper

    # Monkeypatch the instance method
    conn.query = fake_query  # type: ignore[assignment]
    getattr(conn, wrapper)(limit=1)
    assert called["resource"] == expected_resource

@pytest.mark.parametrize(
    "wrapper, expected_resource",
    [
        ("get_document", "drucksache"),
        ("get_procedure", "vorgang"),
        ("get_plenaryprotocol", "plenarprotokoll"),
        ("get_activity", "aktivitaet"),
        ("get_person", "person"),
        ("get_procedureposition", "vorgangsposition"),
    ],
)
def test_get_wrappers_delegate_to_query_with_correct_resource_and_fid(conn, wrapper, expected_resource):
    called = {}

    def fake_query(*, resource, fid, **kw):
        called["resource"] = resource
        called["fid"] = fid
        return [] # Return a list as expected by the wrapper

    conn.query = fake_query
    getattr(conn, wrapper)(btid=12345)
    assert called["resource"] == expected_resource
    assert called["fid"] == 12345


# ---- Input Validation & Parameter Handling ----
 
def test_query_coerces_updated_since_datetime_if_supported(conn):
    sig = inspect.signature(conn.query)
    if "updated_since" in sig.parameters:
        conn.query(resource="aktivitaet", updated_since=datetime(2025, 1, 2, 3, 4, 5), limit=1)
        assert conn.session.last_params.get("f.aktualisiert.start") == "2025-01-02T03:04:05"
    else:
        pytest.skip("query(updated_since=...) not implemented")


def test_list_params_are_left_as_lists_for_requests_expansion(conn):
    conn.query(resource="drucksache", title=["Haushalt", "Bund"], descriptor=["Finanzen", "Steuern"], limit=5)
    assert conn.session.last_params.get("f.titel") == ["Haushalt", "Bund"]
    assert conn.session.last_params.get("f.deskriptor") == ["Finanzen", "Steuern"]


def test_fulltext_switches_endpoint_and_raises_for_unsupported(conn):
    sig = inspect.signature(conn.query)
    if "fulltext" not in sig.parameters:
        pytest.skip("fulltext routing not implemented in this version")

    # supported → endpoint should contain '-text'
    conn.query(resource="drucksache", fulltext=True, limit=1)
    assert "-text" in (conn.session.last_url or "")

    # unsupported → raise
    with pytest.raises(ValueError):
        conn.query(resource="person", fulltext=True, limit=1)


def test_invalid_resource_raises_error(conn):
    with pytest.raises(ValueError, match="No or wrong resource"):
        conn.query(resource="invalid_resource")


def test_invalid_limit_raises_error(conn):
    with pytest.raises(ValueError, match="limit must be an integer larger than zero"):
        conn.query(resource="drucksache", limit=0)
    with pytest.raises(ValueError, match="limit must be an integer larger than zero"):
        conn.query(resource="drucksache", limit=-10)


def test_mutually_exclusive_ids_raise_value_error(conn):
    with pytest.raises(ValueError):
        conn.query(resource="vorgangsposition", drucksacheID=1, processID=2, limit=1)


@pytest.mark.parametrize(
    "param, value, valid_resource, invalid_resource, match_str",
    [
        ("person_name", "Scholz", "person", "drucksache", "person_name"),
        ("personID", 123, "aktivitaet", "person", "personID"),
        ("document_number", "20/1234", "drucksache", "person", "document_number"),
        ("document_art", "Drucksache", "vorgang", "person", "document_art"),
        ("question_number", "C.4", "aktivitaet", "person", "question_number"),
        ("gesta_id", "B101", "vorgang", "drucksache", "gesta_id"),
        ("procedure_positionID", 987, "aktivitaet", "vorgang", "procedure_positionID"),
        ("consultation_status", "Abgeschlossen", "vorgang", "drucksache", "consultation_status"),
        ("publication_reference", "BGBl I", "vorgang", "drucksache", "publication_reference"),
        ("initiative", "Bundesregierung", "vorgang", "drucksache", "initiative"),
        ("lead_department", "BMG", "drucksache", "person", "lead_department"),
        ("originator", "Bundesregierung", "drucksache", "person", "originator"),
        # Also check some existing ones for completeness
        ("drucksacheID", 1, "vorgang", "drucksache", "drucksacheID"),
        ("plenaryprotocolID", 1, "vorgang", "drucksache", "plenaryprotocolID"),
        ("processID", 1, "vorgangsposition", "vorgang", "processID"),
        ("activityID", 1, "vorgangsposition", "vorgang", "activityID"),
        ("title", "Test", "drucksache", "person", "Title"),
        ("drucksache_type", "Antrag", "vorgang", "person", "Drucksache type"),
    ],
)
def test_resource_specific_parameter_validation(conn, param, value, valid_resource, invalid_resource, match_str):
    """
    Tests that parameters raise ValueError when used with an unsupported resource,
    and do not raise an error when used with a supported one.
    """
    # Test with invalid resource - should raise ValueError
    with pytest.raises(ValueError, match=match_str):
        conn.query(resource=invalid_resource, **{param: value})

    # Test with valid resource - should not raise an error
    conn.query(resource=valid_resource, **{param: value})


# ---- Pagination & Return Formats ----

def test_query_paginates_correctly(conn):
    # Simulate a two-page response
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 15,
            "documents": [{"id": i} for i in range(10)],
            "cursor": "cursor_for_page_2"
        }),
        FakeResponse(200, {
            "numFound": 15,
            "documents": [{"id": i} for i in range(10, 15)],
            "cursor": "cursor_for_page_2" # API returns same cursor on last page
        })
    ]
    
    results = conn.query(resource="drucksache", limit=20)
    
    assert conn.session.call_count == 2
    assert len(results) == 15
    assert results[14]["id"] == 14


def test_query_respects_limit_during_pagination(conn):
    # Simulate a multi-page response where the limit is hit on the second page
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 30,
            "documents": [{"id": i} for i in range(10)],
            "cursor": "cursor_for_page_2"
        }),
        FakeResponse(200, {
            "numFound": 30,
            "documents": [{"id": i} for i in range(10, 20)],
            "cursor": "cursor_for_page_3"
        })
    ]
    
    results = conn.query(resource="drucksache", limit=15)
    
    assert conn.session.call_count == 2
    assert len(results) == 15 # Truncated to the limit
    assert results[-1]["id"] == 14


def test_query_handles_empty_response(conn):
    conn.session.responses = [FakeResponse(200, {"numFound": 0, "documents": []})]
    results = conn.query(resource="drucksache", limit=10)
    assert len(results) == 0
    assert conn.session.call_count == 1


def test_query_returns_objects(conn):
    from bundestag_api.models import Drucksache
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 1,
            "documents": [{"id": 123, "typ": "drucksache"}]
        })
    ]
    
    results = conn.query(resource="drucksache", return_format="object", limit=1)
    
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], Drucksache)
    assert results[0].btid == 123


@pytest.mark.skipif(
    not pytest.importorskip("pandas", minversion=None),
    reason="pandas not available"
)
def test_query_returns_pandas_dataframe(conn):
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 2,
            "documents": [{"id": 1}, {"id": 2}]
        })
    ]
    
    df = conn.query(resource="drucksache", return_format="pandas", limit=2)
    
    import pandas as pd
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 1)
    assert list(df['id']) == [1, 2]


# ---- Error Handling & Session ----

def test_timeout_is_set_on_requests(conn):
    conn.query(resource="drucksache", limit=1)
    assert conn.session.last_timeout is not None


@pytest.mark.parametrize(
    "status_code, reason, expected_log_part",
    [
        (400, "Bad Request", "syntax error"),
        (401, "Unauthorized", "authorization error"),
        (404, "Not Found", "not reachable"),
    ]
)
def test_http_error_codes_are_logged(conn, monkeypatch, status_code, reason, expected_log_part):
    # Swap in a response with the specified error
    conn.session.responses = [FakeResponse(status_code=status_code, reason=reason)]
    
    # Mock the logger to capture its output
    mock_logger = types.SimpleNamespace(error=lambda msg: setattr(mock_logger, 'last_message', msg))
    monkeypatch.setattr("bundestag_api.bta_wrapper.logger", mock_logger)
    
    results = conn.query(resource="drucksache", limit=1)
    
    assert len(results) == 0
    assert hasattr(mock_logger, 'last_message')
    assert expected_log_part in mock_logger.last_message.lower()
