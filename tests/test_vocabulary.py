from datetime import date, datetime

import pytest

from bundestag_api import btaConnection, vocabulary as voc
from bundestag_api import legislative_period_for, legislative_period_dates


def test_spec_enums():
    assert set(voc.INSTITUTIONS) == {"BT", "BR", "BV", "EK"}
    assert len(voc.FEDERAL_STATES) == 16
    assert "Namentliche Abstimmung" in voc.VOTING_METHODS
    assert voc.QUADRANTS == ("A", "B", "C", "D")


def test_legislative_periods_are_contiguous():
    periods = sorted(voc.LEGISLATIVE_PERIODS)
    assert periods == list(range(1, voc.CURRENT_LEGISLATIVE_PERIOD + 1))
    for p in periods[:-1]:
        _, end = voc.LEGISLATIVE_PERIODS[p]
        next_start, _ = voc.LEGISLATIVE_PERIODS[p + 1]
        assert (next_start - end).days == 1
    assert voc.LEGISLATIVE_PERIODS[voc.CURRENT_LEGISLATIVE_PERIOD][1] is None


@pytest.mark.parametrize("day, expected", [
    ("1949-09-07", 1),
    ("1949-09-06", None),
    (date(2019, 5, 1), 19),
    (datetime(2021, 10, 25, 23, 59), 19),
    ("2021-10-26", 20),
    ("2025-03-25", 21),
])
def test_legislative_period_for(day, expected):
    assert legislative_period_for(day) == expected


def test_legislative_period_dates():
    assert legislative_period_dates(19) == ("2017-10-24", "2021-10-25")
    start, end = legislative_period_dates(voc.CURRENT_LEGISLATIVE_PERIOD)
    assert end is None
    with pytest.raises(ValueError, match="Unknown legislative period"):
        legislative_period_dates(99)


def test_invalid_date_raises():
    with pytest.raises(ValueError):
        legislative_period_for("01.01.2020")


def test_unknown_institution_error_lists_options():
    c = btaConnection(apikey="testapikey0123456789")
    with pytest.raises(ValueError, match="BR \\(Bundesrat\\)"):
        c.query(resource="drucksache", institution="XX")


# ---- discover_values ----

class _Response:
    status_code = 200
    reason = "OK"
    text = ""
    url = ""

    def __init__(self, documents):
        self._documents = documents

    def json(self):
        return {"numFound": len(self._documents), "cursor": "c", "documents": self._documents}


class _Session:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, dict(params or {})))
        return _Response(self.documents if (params or {}).get("cursor") is None else [])


DOCS = [
    {"id": "1", "sachgebiet": ["Umwelt", "Energie"], "beratungsstand": "Abgeschlossen",
     "urheber": [{"titel": "Bundesregierung"}], "deskriptor": [{"name": "Klimaschutz", "typ": "Sachbegriffe"}]},
    {"id": "2", "sachgebiet": ["Umwelt"], "beratungsstand": "Noch nicht beraten",
     "urheber": [{"titel": "Fraktion der SPD"}, {"titel": "Bundesregierung"}]},
    {"id": "3", "beratungsstand": None},
]


@pytest.fixture
def conn():
    c = btaConnection(apikey="testapikey0123456789")
    c.session = _Session(DOCS)
    return c


def test_discover_values_counts_list_fields(conn):
    result = conn.discover_values("vorgang", "sachgebiet", legislative_period=20)
    assert result == [{"value": "Umwelt", "count": 2}, {"value": "Energie", "count": 1}]
    assert conn.session.calls[0][1]["f.wahlperiode"] == [20]


def test_discover_values_nested_paths(conn):
    assert conn.discover_values("vorgang", "urheber.titel")[0] == {"value": "Bundesregierung", "count": 2}
    assert conn.discover_values("vorgang", "deskriptor.name") == [{"value": "Klimaschutz", "count": 1}]


def test_discover_values_skips_missing_and_dicts(conn):
    assert len(conn.discover_values("vorgang", "beratungsstand")) == 2
    assert conn.discover_values("vorgang", "urheber") == []


def test_discover_values_pandas_and_validation(conn):
    df = conn.discover_values("vorgang", "sachgebiet", return_format="pandas")
    assert list(df.columns) == ["value", "count"]
    with pytest.raises(ValueError, match="field"):
        conn.discover_values("vorgang", "")
