import sys
from datetime import datetime

sys.path.insert(0, '/mnt/data')

import pytest

# If utils.py doesn't exist in this environment, skip — you'll run these in your repo.
utils = pytest.importorskip("utils")

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