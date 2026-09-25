"""Tests for the procedure timeline. Step sequence modelled on a live procedure, fields per spec."""
import pytest

from bundestag_api import btaConnection, build_timeline

PROCEDURE = {
    "id": "310586", "titel": "Testforschungsgesetz", "beratungsstand": "Verkündet",
    "typ": "Vorgang", "vorgangstyp": "Gesetzgebung", "wahlperiode": 20,
    "verkuendung": [{
        "jahrgang": "2024", "seite": "1", "ausfertigungsdatum": "2024-10-23",
        "verkuendungsdatum": "2024-10-29", "einleitungstext": "Gesetz",
        "fundstelle": "BGBl I 2024, 324", "verkuendungsblatt_bezeichnung": "Bundesgesetzblatt Teil I",
        "pdf_url": "https://example.org/bgbl.pdf",
    }],
    "inkrafttreten": [{"datum": "2024-10-30"}, {"datum": "2025-01-01", "erlaeuterung": "Artikel 3"}],
}


def _pos(pid, datum, name, zuordnung, dokumentart, gang, **extra):
    p = {"id": str(pid), "vorgangsposition": name, "zuordnung": zuordnung, "gang": gang,
         "fortsetzung": False, "nachtrag": False, "vorgangstyp": "Gesetzgebung",
         "typ": "Vorgangsposition", "titel": "Testforschungsgesetz", "dokumentart": dokumentart,
         "vorgang_id": "310586", "datum": datum, "aktualisiert": "2024-11-01T10:00:00+01:00",
         "aktivitaet_anzahl": 0,
         "fundstelle": {"id": str(9000 + pid), "dokumentart": dokumentart, "dokumentnummer": f"20/{pid}",
                        "datum": datum, "herausgeber": zuordnung, "urheber": [],
                        "pdf_url": f"https://example.org/{pid}.pdf"}}
    p.update(extra)
    return p


POSITIONS = [
    # deliberately not in date order
    _pos(5, "2024-07-04", "3. Beratung", "BT", "Plenarprotokoll", True,
         beschlussfassung=[{"beschlusstenor": "Annahme in Ausschussfassung", "dokumentnummer": "20/11561, 20/12149",
                            "abstimmungsart": "Namentliche Abstimmung"}]),
    _pos(1, "2024-05-17", "Gesetzentwurf", "BR", "Drucksache", True,
         urheber=[{"bezeichnung": "BRg", "titel": "Bundesregierung"}]),
    _pos(3, "2024-06-06", "1. Beratung", "BT", "Plenarprotokoll", True,
         beschlussfassung=[{"beschlusstenor": "Überweisung", "dokumentnummer": "20/11561"}],
         ueberweisung=[
             {"ausschuss": "Ausschuss für Gesundheit", "ausschuss_kuerzel": "AfG", "federfuehrung": True},
             {"ausschuss": "Ausschuss für Bildung", "ausschuss_kuerzel": "AfB", "federfuehrung": False},
         ]),
    _pos(4, "2024-07-04", "2. Beratung", "BT", "Plenarprotokoll", True,
         beschlussfassung=[{"beschlusstenor": "Annahme in Ausschussfassung", "dokumentnummer": "20/11561, 20/12149"}]),
    _pos(2, "2024-06-01", "Empfehlungen der Ausschüsse", "BR", "Drucksache", False),
]


@pytest.fixture
def timeline():
    return build_timeline(PROCEDURE, POSITIONS)


def test_rows_sorted_by_date_with_stable_ties(timeline):
    dates = [r["date"] for r in timeline]
    assert dates == sorted(dates)
    same_day = [r["event"] for r in timeline if r["date"] == "2024-07-04"]
    assert same_day == ["3. Beratung", "2. Beratung"]  # API order kept for ties


def test_step_columns(timeline):
    first_reading = next(r for r in timeline if r["event"] == "1. Beratung")
    assert first_reading["event_type"] == "step"
    assert first_reading["institution"] == "BT"
    assert first_reading["lead_committee"] == "Ausschuss für Gesundheit"
    assert first_reading["committees"] == "Ausschuss für Gesundheit; Ausschuss für Bildung"
    assert first_reading["decisions"] == "Überweisung"
    assert first_reading["protocol_id"] == 9003
    assert first_reading["procedure_id"] == 310586
    assert first_reading["procedure_status"] == "Verkündet"

    bill = next(r for r in timeline if r["event"] == "Gesetzentwurf")
    assert bill["originator"] == "Bundesregierung"
    assert bill["protocol_id"] is None
    assert bill["document_number"] == "20/1"

    third = next(r for r in timeline if r["event"] == "3. Beratung")
    assert third["voting_methods"] == "Namentliche Abstimmung"
    assert third["decided_document_numbers"] == "20/11561, 20/12149"


def test_promulgation_and_entry_into_force(timeline):
    events = [(r["event_type"], r["date"]) for r in timeline if r["event_type"] != "step"]
    assert events == [("signing", "2024-10-23"), ("promulgation", "2024-10-29"),
                      ("entry_into_force", "2024-10-30"), ("entry_into_force", "2025-01-01")]
    promulgation = next(r for r in timeline if r["event_type"] == "promulgation")
    assert promulgation["document_number"] == "BGBl I 2024, 324"
    assert promulgation["pdf_url"] == "https://example.org/bgbl.pdf"
    assert timeline[-1]["details"] == "Artikel 3"


def test_only_important(timeline):
    important = build_timeline(PROCEDURE, POSITIONS, only_important=True)
    names = [r["event"] for r in important]
    assert "Empfehlungen der Ausschüsse" not in names
    assert "Verkündung" in names and "Inkrafttreten" in names
    assert len(important) == len(timeline) - 1


def test_procedure_without_promulgation():
    rows = build_timeline({"id": "1", "titel": "x"}, [])
    assert rows == []
    rows = build_timeline({"id": "1", "inkrafttreten": [{"erlaeuterung": "no date"}]}, [])
    assert rows == []


# ---- btaConnection integration (no network) ----

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
    def __init__(self):
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, headers=None):
        params = dict(params or {})
        self.calls.append((url, params))
        if params.get("cursor"):
            return _Response([])
        if url.endswith("/vorgang"):
            return _Response([PROCEDURE] if params.get("f.id") == [310586] else [])
        return _Response(POSITIONS)


@pytest.fixture
def conn():
    c = btaConnection(apikey="testapikey0123456789")
    c.session = _Session()
    return c


def test_procedure_timeline_requests(conn):
    rows = conn.procedure_timeline(310586)
    assert len(rows) == 9
    first_calls = [(url.rsplit("/", 1)[1], p) for url, p in conn.session.calls if p.get("cursor") is None]
    assert first_calls[0][0] == "vorgang" and first_calls[0][1]["f.id"] == [310586]
    assert first_calls[1][0] == "vorgangsposition" and first_calls[1][1]["f.vorgang"] == 310586


def test_procedure_timeline_pandas(conn):
    df = conn.procedure_timeline(310586, only_important=True, return_format="pandas")
    assert len(df) == 8
    assert {"date", "event", "lead_committee", "decisions"} <= set(df.columns)


def test_procedure_timeline_unknown_id(conn):
    with pytest.raises(ValueError, match="not found"):
        conn.procedure_timeline(1)


def test_procedure_timeline_validates_format(conn):
    with pytest.raises(ValueError, match="return_format"):
        conn.procedure_timeline(310586, return_format="object")
