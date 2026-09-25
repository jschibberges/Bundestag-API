"""Tests for decisions ('Beschlussfassung') using payloads shaped like the DIP OpenAPI spec."""
import pytest

from bundestag_api import btaConnection, flatten_decisions
from bundestag_api.models import Vorgangsposition


def _position(pid, decisions, dokumentart="Plenarprotokoll", zuordnung="BT", **extra):
    position = {
        "id": str(pid), "vorgangsposition": "2. Beratung", "zuordnung": zuordnung,
        "gang": True, "fortsetzung": False, "nachtrag": False,
        "vorgangstyp": "Gesetzgebung", "typ": "Vorgangsposition",
        "titel": "Gesetz zur Erprobung von Tests", "dokumentart": dokumentart,
        "vorgang_id": "300001", "datum": "2024-06-06", "aktualisiert": "2024-06-07T10:00:00+02:00",
        "fundstelle": {
            "id": "5678", "dokumentart": dokumentart, "dokumentnummer": "20/999",
            "datum": "2024-06-06", "herausgeber": zuordnung, "urheber": [],
            "pdf_url": "https://dserver.bundestag.de/btp/20/20999.pdf#P.123",
            "top": 7, "top_zusatz": "a",
        },
        "aktivitaet_anzahl": 0,
    }
    if decisions is not None:
        position["beschlussfassung"] = decisions
    position.update(extra)
    return position


POSITIONS = [
    _position(1, [
        {"beschlusstenor": "Annahme in Ausschussfassung", "seite": "123C",
         "abstimmungsart": "Namentliche Abstimmung", "dokumentnummer": "20/1000"},
        {"beschlusstenor": "Ablehnung", "seite": "124A", "dokumentnummer": "20/1001",
         "abstimm_ergebnis_bemerkung": "einstimmig"},
    ]),
    _position(2, None),  # no decision
    _position(3, [{"beschlusstenor": "Zustimmung", "grundlage": "Art. 80 Abs. 2 GG",
                   "mehrheit": "Absolute Mehrheit"}],
              dokumentart="Plenarprotokoll", zuordnung="BR", vorgangsposition="BR-Plenum"),
]


def test_flatten_decisions_one_row_per_decision():
    rows = flatten_decisions(POSITIONS)
    assert len(rows) == 3
    first = rows[0]
    assert first["procedure_id"] == 300001
    assert first["position_id"] == 1
    assert first["position"] == "2. Beratung"
    assert first["institution"] == "BT"
    assert first["decision"] == "Annahme in Ausschussfassung"
    assert first["decided_document_number"] == "20/1000"
    assert first["voting_method"] == "Namentliche Abstimmung"
    assert first["recorded_vote"] is True
    assert first["protocol_id"] == 5678
    assert first["agenda_item"] == "7a"
    assert first["page"] == "123C"
    assert rows[1]["decision_index"] == 1
    assert rows[1]["recorded_vote"] is False
    assert rows[1]["result_remark"] == "einstimmig"
    assert rows[2]["institution"] == "BR"
    assert rows[2]["legal_basis"] == "Art. 80 Abs. 2 GG"
    assert rows[2]["majority"] == "Absolute Mehrheit"


def test_protocol_id_only_for_plenary_protocols():
    rows = flatten_decisions([_position(9, [{"beschlusstenor": "Annahme"}], dokumentart="Drucksache")])
    assert rows[0]["protocol_id"] is None
    assert rows[0]["document_type"] == "Drucksache"


def test_vorgangsposition_model_exposes_decisions():
    vp = Vorgangsposition(POSITIONS[0])
    assert len(vp.decisions) == 2
    assert Vorgangsposition(POSITIONS[1]).decisions == []


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
    def __init__(self, documents):
        self.documents = documents
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, dict(params or {})))
        # First page returns the documents, a follow-up page with the same cursor none
        return _Response(self.documents if (params or {}).get("cursor") is None else [])


@pytest.fixture
def conn():
    c = btaConnection(apikey="testapikey0123456789")
    c.session = _Session(POSITIONS)
    return c


def test_get_decisions_queries_positions_of_procedure(conn):
    rows = conn.get_decisions(300001)
    url, params = conn.session.calls[0]
    assert url.endswith("/vorgangsposition")
    assert params["f.vorgang"] == 300001
    assert len(rows) == 3


def test_get_decisions_multiple_procedures(conn):
    conn.get_decisions([1, 2])
    assert [c[1]["f.vorgang"] for c in conn.session.calls if c[1]["cursor"] is None] == [1, 2]


def test_get_decisions_filters_voting_method(conn):
    rows = conn.get_decisions(300001, voting_method="Namentliche Abstimmung")
    assert len(rows) == 1
    assert rows[0]["recorded_vote"] is True


def test_get_decisions_pandas(conn):
    df = conn.get_decisions(300001, return_format="pandas")
    assert len(df) == 3
    assert {"decision", "voting_method", "procedure_title"} <= set(df.columns)


def test_search_decisions_passes_filters(conn):
    rows = conn.search_decisions(legislative_period=20, institution="BR", limit=50)
    params = conn.session.calls[0][1]
    assert params["f.wahlperiode"] == [20]
    assert params["f.zuordnung"] == "BR"
    assert len(rows) == 3


def test_search_decisions_scans_plenary_positions_by_default(conn):
    conn.search_decisions(legislative_period=20)
    assert conn.session.calls[0][1]["f.dokumentart"] == "Plenarprotokoll"
    conn.search_decisions(legislative_period=20, document_art=None)
    assert conn.session.calls[-1][1]["f.dokumentart"] is None


def test_decision_argument_validation(conn):
    with pytest.raises(ValueError, match="voting_method"):
        conn.get_decisions(1, voting_method="Handzeichen")
    with pytest.raises(ValueError, match="return_format"):
        conn.search_decisions(return_format="object")
