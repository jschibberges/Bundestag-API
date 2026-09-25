from datetime import date, datetime

import pytest

from bundestag_api import utils


def test_to_iso8601_converts_datetime():
    dt = datetime(2025, 1, 2, 3, 4, 5)
    s = utils.to_iso8601(dt)
    assert s == "2025-01-02T03:04:05"

def test_to_iso8601_passthrough_string():
    s = utils.to_iso8601("2025-01-02T03:04:05")
    assert s == "2025-01-02T03:04:05"

def test_to_iso8601_none():
    assert utils.to_iso8601(None) is None

def test_to_iso8601_raises_for_wrong_type():
    with pytest.raises(ValueError):
        utils.to_iso8601(123)  # type: ignore[arg-type]

def test_to_date_string():
    assert utils.to_date_string(None) is None
    assert utils.to_date_string(date(2024, 3, 1)) == "2024-03-01"
    assert utils.to_date_string("2024-03-01") == "2024-03-01"
    with pytest.raises(ValueError):
        utils.to_date_string("01.03.2024")

def test_parse_args_to_dict_collects_repeated_keys():
    result = utils.parse_args_to_dict(["title=Klima", "--title=Energie", "limit=5"])
    assert result == {"title": ["Klima", "Energie"], "limit": "5"}

@pytest.mark.parametrize("value, expected", [("True", True), ("false", False), ("0", False), ("ja", True)])
def test_parse_bool(value, expected):
    assert utils.parse_bool(value) is expected

def test_parse_bool_rejects_garbage():
    with pytest.raises(ValueError):
        utils.parse_bool("maybe")
