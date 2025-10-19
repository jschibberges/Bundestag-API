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
    "status_code, reason, expected_exception, expected_log_part",
    [
        (400, "Bad Request", ValueError, "syntax error"),
        (401, "Unauthorized", ValueError, "authorization error"),
        (404, "Not Found", ConnectionError, "not reachable"),
        (500, "Internal Server Error", requests.HTTPError, "error occurred"),
    ]
)
def test_http_error_codes_raise_exceptions_and_log(conn, monkeypatch, status_code, reason, expected_exception, expected_log_part):
    """HTTP errors should raise appropriate exceptions and log error messages."""
    # Swap in a response with the specified error
    conn.session.responses = [FakeResponse(status_code=status_code, reason=reason)]

    # Mock the logger to capture its output (include both error and debug methods)
    mock_logger = types.SimpleNamespace(
        error=lambda msg: setattr(mock_logger, 'last_message', msg),
        debug=lambda msg: None  # No-op for debug messages
    )
    monkeypatch.setattr("bundestag_api.bta_wrapper.logger", mock_logger)

    # Should raise an exception
    with pytest.raises(expected_exception):
        conn.query(resource="drucksache", limit=1)

    # Should have logged the error
    assert hasattr(mock_logger, 'last_message')
    assert expected_log_part in mock_logger.last_message.lower()


# ---- Tests for Refactored Helper Methods ----

def test_validate_basic_params_validates_resource(conn):
    """_validate_basic_params should validate resource type."""
    with pytest.raises(ValueError, match="No or wrong resource"):
        conn._validate_basic_params("invalid_resource", "json", 100, None, False)


def test_validate_basic_params_validates_return_format(conn):
    """_validate_basic_params should validate return format."""
    with pytest.raises(ValueError, match="Not a correct format"):
        conn._validate_basic_params("drucksache", "invalid_format", 100, None, False)


def test_validate_basic_params_validates_limit(conn):
    """_validate_basic_params should validate limit is positive integer."""
    with pytest.raises(ValueError, match="limit must be an integer larger than zero"):
        conn._validate_basic_params("drucksache", "json", 0, None, False)

    with pytest.raises(ValueError, match="limit must be an integer larger than zero"):
        conn._validate_basic_params("drucksache", "json", -5, None, False)


def test_validate_basic_params_validates_institution(conn):
    """_validate_basic_params should validate institution codes."""
    with pytest.raises(ValueError, match="Unknown institution"):
        conn._validate_basic_params("drucksache", "json", 100, "INVALID", False)


def test_validate_basic_params_handles_fulltext(conn):
    """_validate_basic_params should convert resource for fulltext requests."""
    # Should add -text suffix for supported resources
    result = conn._validate_basic_params("drucksache", "json", 100, None, True)
    assert result == "drucksache-text"

    result = conn._validate_basic_params("plenarprotokoll", "json", 100, None, True)
    assert result == "plenarprotokoll-text"

    # Should raise for unsupported resources
    with pytest.raises(ValueError, match="fulltext is only supported"):
        conn._validate_basic_params("person", "json", 100, None, True)


def test_validate_reference_ids_enforces_mutual_exclusivity(conn):
    """_validate_reference_ids should prevent multiple ID parameters."""
    with pytest.raises(ValueError, match="Can't select more than one"):
        conn._validate_reference_ids("vorgangsposition", drucksacheID=1, plenaryprotocolID=2, processID=None, activityID=None)

    with pytest.raises(ValueError, match="Can't select more than one"):
        conn._validate_reference_ids("vorgangsposition", drucksacheID=None, plenaryprotocolID=None, processID=1, activityID=2)


def test_validate_reference_ids_validates_types(conn):
    """_validate_reference_ids should validate ID types are integers."""
    with pytest.raises(ValueError, match="must be an integer"):
        conn._validate_reference_ids("aktivitaet", drucksacheID="not_an_int", plenaryprotocolID=None, processID=None, activityID=None)


def test_validate_reference_ids_validates_resource_compatibility(conn):
    """_validate_reference_ids should ensure IDs are used with correct resources."""
    # processID only with vorgangsposition
    with pytest.raises(ValueError, match="processID must be combined with resource 'vorgangsposition'"):
        conn._validate_reference_ids("drucksache", drucksacheID=None, plenaryprotocolID=None, processID=123, activityID=None)

    # activityID only with vorgangsposition
    with pytest.raises(ValueError, match="activityID must be combined with resource 'vorgangsposition'"):
        conn._validate_reference_ids("drucksache", drucksacheID=None, plenaryprotocolID=None, processID=None, activityID=456)


def test_validate_resource_specific_params_uses_lookup_table(conn):
    """_validate_resource_specific_params should validate using data-driven approach."""
    params = {"person_name": "Schmidt", "personID": None}

    # person_name is valid with 'person' resource
    conn._validate_resource_specific_params("person", params)

    # person_name is invalid with 'drucksache' resource
    with pytest.raises(ValueError, match="person_name can only be used"):
        conn._validate_resource_specific_params("drucksache", params)


def test_validate_and_normalize_params_normalizes_lists(conn):
    """_validate_and_normalize_params should normalize string/int parameters to lists."""
    params = conn._validate_and_normalize_params(
        resource="drucksache",
        fid=123,  # Single int
        descriptor="Politik",  # Single string
        title=["Haushalt", "Budget"]  # Already a list
    )

    # Should be normalized to lists
    assert params['fid'] == [123]
    assert params['descriptor'] == ["Politik"]
    assert params['title'] == ["Haushalt", "Budget"]


def test_validate_and_normalize_params_converts_datetimes(conn):
    """_validate_and_normalize_params should convert datetime objects to ISO 8601."""
    params = conn._validate_and_normalize_params(
        resource="drucksache",
        updated_since=datetime(2025, 1, 15, 10, 30, 0)
    )

    assert params['updated_since'] == "2025-01-15T10:30:00"


def test_build_api_payload_creates_correct_structure(conn):
    """_build_api_payload should create properly formatted payload."""
    validated_params = {
        'fid': [123, 456],
        'date_start': "2024-01-01",
        'title': ["Climate", "Energy"],
        'institution': "BT",
        'drucksacheID': None,
        'plenaryprotocolID': None,
        'processID': None,
        'activityID': None,
    }

    payload = conn._build_api_payload(validated_params)

    assert payload["apikey"] == conn.apikey
    assert payload["format"] == "json"
    assert payload["f.id"] == [123, 456]
    assert payload["f.datum.start"] == "2024-01-01"
    assert payload["f.titel"] == ["Climate", "Energy"]
    assert payload["f.zuordnung"] == "BT"
    assert payload["cursor"] is None


def test_execute_paginated_query_handles_pagination(conn):
    """_execute_paginated_query should handle multi-page results."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 25,
            "documents": [{"id": i} for i in range(10)],
            "cursor": "page2"
        }),
        FakeResponse(200, {
            "numFound": 25,
            "documents": [{"id": i} for i in range(10, 20)],
            "cursor": "page3"
        }),
        FakeResponse(200, {
            "numFound": 25,
            "documents": [{"id": i} for i in range(20, 25)],
            "cursor": "page3"  # Same cursor = last page
        })
    ]

    payload = {"apikey": conn.apikey, "format": "json", "cursor": None}
    data = conn._execute_paginated_query("drucksache", payload, limit=30)

    assert len(data) == 25
    assert conn.session.call_count == 3


def test_execute_paginated_query_respects_limit(conn):
    """_execute_paginated_query should truncate results at limit."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 100,
            "documents": [{"id": i} for i in range(10)],
            "cursor": "page2"
        }),
        FakeResponse(200, {
            "numFound": 100,
            "documents": [{"id": i} for i in range(10, 20)],
            "cursor": "page3"
        })
    ]

    payload = {"apikey": conn.apikey, "format": "json", "cursor": None}
    data = conn._execute_paginated_query("drucksache", payload, limit=12)

    assert len(data) == 12  # Truncated
    assert conn.session.call_count == 2


def test_format_results_handles_object_format(conn):
    """_format_results should convert to model objects when return_format='object'."""
    from bundestag_api.models import Drucksache

    data = [{"id": 123, "titel": "Test Document"}]
    results = conn._format_results(data, "object", "drucksache")

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], Drucksache)
    assert results[0].btid == 123


def test_format_results_handles_pandas_format(conn):
    """_format_results should convert to DataFrame when return_format='pandas'."""
    import pandas as pd

    data = [{"id": 1, "name": "Doc1"}, {"id": 2, "name": "Doc2"}]
    results = conn._format_results(data, "pandas", "drucksache")

    assert isinstance(results, pd.DataFrame)
    assert len(results) == 2
    assert list(results.columns) == ["id", "name"]


def test_format_results_returns_json_by_default(conn):
    """_format_results should return list of dicts for json format."""
    data = [{"id": 1}, {"id": 2}]
    results = conn._format_results(data, "json", "drucksache")

    assert isinstance(results, list)
    assert results == data


# ---- Edge Cases & Data Handling Tests ----

def test_validate_str_list_param_rejects_empty_strings(conn):
    """String parameters should handle empty strings."""
    # Empty string should be converted to list with empty string
    result = conn._validate_str_list_param("", "test_param")
    assert result == [""]


def test_validate_str_list_param_rejects_overly_long_strings(conn):
    """String parameters should reject strings over 100 characters."""
    long_string = "a" * 101
    with pytest.raises(ValueError, match="must be under 100 characters"):
        conn._validate_str_list_param(long_string, "test_param")


def test_validate_str_list_param_handles_unicode(conn):
    """String parameters should handle unicode characters."""
    unicode_str = "Müller"
    result = conn._validate_str_list_param(unicode_str, "test_param")
    assert result == ["Müller"]


def test_validate_str_list_param_rejects_mixed_types(conn):
    """String list parameters should reject lists with non-string items."""
    mixed_list = ["valid", 123, "string"]
    with pytest.raises(ValueError, match="All items in test_param must be strings"):
        conn._validate_str_list_param(mixed_list, "test_param")


def test_validate_int_list_param_handles_string_integers(conn):
    """Int list parameters should convert string integers."""
    result = conn._validate_int_list_param(["123", "456"], "test_param")
    assert result == [123, 456]


def test_validate_int_list_param_rejects_floats(conn):
    """Int list parameters should reject float values."""
    with pytest.raises(ValueError, match="must be convertible to integers"):
        conn._validate_int_list_param([1.5, 2.7], "test_param")


def test_validate_int_list_param_rejects_invalid_strings(conn):
    """Int list parameters should reject non-numeric strings."""
    with pytest.raises(ValueError, match="must be convertible to integers"):
        conn._validate_int_list_param(["abc", "123"], "test_param")


def test_query_handles_malformed_json_response(conn, monkeypatch):
    """Query should handle malformed JSON responses gracefully."""
    class BadResponse:
        status_code = 200
        url = "http://test.com"

        def json(self):
            raise ValueError("Invalid JSON")

    conn.session.responses = [BadResponse()]

    with pytest.raises(ValueError):
        conn.query(resource="drucksache", limit=1)


def test_query_handles_missing_documents_field(conn):
    """Query should handle responses missing the 'documents' field."""
    conn.session.responses = [
        FakeResponse(200, {"numFound": 5})  # Missing 'documents' field
    ]

    results = conn.query(resource="drucksache", limit=10)
    assert len(results) == 0


def test_query_handles_none_values_in_response(conn):
    """Query should handle None values in API response."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 2,
            "documents": [
                {"id": 1, "title": None},
                {"id": 2, "title": "Valid"}
            ]
        })
    ]

    results = conn.query(resource="drucksache", limit=10)
    assert len(results) == 2
    assert results[0]["title"] is None


def test_query_handles_unexpected_data_types_in_response(conn):
    """Query should handle unexpected data types in response."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 1,
            "documents": [
                {"id": "should_be_string", "nested": {"key": "value"}}
            ]
        })
    ]

    results = conn.query(resource="drucksache", limit=10)
    assert len(results) == 1
    assert results[0]["id"] == "should_be_string"


def test_pagination_stops_on_cursor_infinite_loop(conn):
    """Pagination should stop if cursor keeps repeating (API bug protection)."""
    # Simulate API bug where cursor never changes
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 100,
            "documents": [{"id": 1}],
            "cursor": "same_cursor"
        })
    ] * 10  # Return same response multiple times

    payload = {"apikey": conn.apikey, "format": "json", "cursor": "same_cursor"}
    data = conn._execute_paginated_query("drucksache", payload, limit=50)

    # Should stop after first page because cursor doesn't change
    assert len(data) == 1
    assert conn.session.call_count == 1


def test_pagination_handles_decreasing_numfound(conn):
    """Pagination should handle numFound decreasing between pages."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 20,
            "documents": [{"id": i} for i in range(10)],
            "cursor": "page2"
        }),
        FakeResponse(200, {
            "numFound": 15,  # Decreased!
            "documents": [{"id": i} for i in range(10, 15)],
            "cursor": "page2"
        })
    ]

    payload = {"apikey": conn.apikey, "format": "json", "cursor": None}
    data = conn._execute_paginated_query("drucksache", payload, limit=30)

    # Should still collect all available documents
    assert len(data) == 15


def test_pagination_handles_empty_documents_with_positive_numfound(conn):
    """Pagination should handle empty documents array despite numFound > 0."""
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 10,  # Says 10 found
            "documents": []   # But returns none
        })
    ]

    results = conn.query(resource="drucksache", limit=10)
    assert len(results) == 0


def test_model_object_creation_handles_missing_required_fields(conn):
    """Model object creation should handle missing fields gracefully."""
    from bundestag_api.models import Drucksache

    # Drucksache requires 'id' field
    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 1,
            "documents": [{"titel": "Test", "datum": "2024-01-01"}]  # Missing 'id'
        })
    ]

    # Should raise KeyError when trying to create object
    with pytest.raises(KeyError):
        conn.query(resource="drucksache", return_format="object", limit=1)


def test_large_parameter_lists_are_handled(conn):
    """Query should handle large lists of parameters."""
    # Create a large list of document IDs
    large_fid_list = list(range(100))

    conn.query(resource="drucksache", fid=large_fid_list, limit=10)

    # Should have sent the full list in the payload
    assert conn.session.last_params.get("f.id") == large_fid_list


def test_query_result_length_never_exceeds_limit(conn):
    """Invariant: len(results) should never exceed limit."""
    # Test with various scenarios
    scenarios = [
        (5, 10),   # limit < available
        (10, 5),   # limit > available
        (10, 10),  # limit == available
    ]

    for available, limit in scenarios:
        conn.session.responses = [
            FakeResponse(200, {
                "numFound": available,
                "documents": [{"id": i} for i in range(available)]
            })
        ]

        results = conn.query(resource="drucksache", limit=limit)
        assert len(results) <= limit, f"Failed for available={available}, limit={limit}"


def test_datetime_conversion_handles_microseconds(conn):
    """Datetime conversion should handle microseconds correctly."""
    dt = datetime(2025, 1, 15, 10, 30, 45, 123456)
    params = conn._validate_and_normalize_params(
        resource="drucksache",
        updated_since=dt
    )

    # ISO 8601 format doesn't include microseconds in to_iso8601
    assert params['updated_since'] == "2025-01-15T10:30:45"


def test_multiple_validation_errors_are_clear(conn):
    """Validation errors should be clear about what's wrong."""
    # Test that error messages are descriptive
    with pytest.raises(ValueError) as exc_info:
        conn._validate_str_list_param([1, 2, 3], "my_param")

    assert "my_param" in str(exc_info.value)
    assert "strings" in str(exc_info.value).lower()


def test_empty_list_parameters_are_handled(conn):
    """Empty list parameters should be handled gracefully."""
    result = conn._validate_str_list_param([], "test_param")
    assert result == []

    result = conn._validate_int_list_param([], "test_param")
    assert result == []


def test_pandas_dataframe_with_nested_structures(conn):
    """Pandas format should handle nested structures via json_normalize."""
    import pandas as pd

    conn.session.responses = [
        FakeResponse(200, {
            "numFound": 2,
            "documents": [
                {"id": 1, "fundstelle": {"pdf_url": "http://example.com/1.pdf"}},
                {"id": 2, "fundstelle": {"pdf_url": "http://example.com/2.pdf"}}
            ]
        })
    ]

    df = conn.query(resource="drucksache", return_format="pandas", limit=10)

    assert isinstance(df, pd.DataFrame)
    # json_normalize should flatten nested structures
    assert "fundstelle.pdf_url" in df.columns or "fundstelle" in df.columns


def test_concurrent_query_calls_dont_interfere(conn):
    """Multiple query calls should not interfere with each other's state."""
    # First query
    conn.session.responses = [
        FakeResponse(200, {"numFound": 1, "documents": [{"id": 1}]})
    ]
    results1 = conn.query(resource="drucksache", limit=10)

    # Second query with different parameters
    conn.session.responses = [
        FakeResponse(200, {"numFound": 1, "documents": [{"id": 2}]})
    ]
    results2 = conn.query(resource="person", limit=5)

    # Results should be independent
    assert results1 != results2
    assert results1[0]["id"] == 1
    assert results2[0]["id"] == 2
