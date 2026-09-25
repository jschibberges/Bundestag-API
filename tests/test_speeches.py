"""Tests for the speech parser using a synthetic protocol in the Bundestag XML structure."""
from pathlib import Path

import pytest
import requests

from bundestag_api import btaConnection, parse_protocol_xml, split_comment

FIXTURE = Path(__file__).parent / "fixtures" / "plenarprotokoll_sample.xml"
XML_URL = "https://dserver.bundestag.de/btp/20/20999.xml"


@pytest.fixture
def parsed():
    return parse_protocol_xml(FIXTURE, extra_metadata={"protocol_id": 5})


def _speech(parsed, speech_id):
    return next(s for s in parsed.speeches if s["speech_id"] == speech_id)


def test_metadata(parsed):
    assert parsed.metadata["legislative_period"] == 20
    assert parsed.metadata["session"] == 999
    assert parsed.metadata["document_number"] == "20/999"
    assert parsed.metadata["date"] == "2024-06-06"
    assert parsed.metadata["protocol_id"] == 5


def test_speeches_contain_only_main_speaker_text(parsed):
    speech = _speech(parsed, "ID209990100")
    assert speech["speaker_name"] == "Dr. Anna Muster"
    assert speech["speaker_id"] == "11001234"
    assert speech["faction"] == "SPD"
    assert speech["agenda_item"] == "Tagesordnungspunkt 1"
    assert "Klimaschutz" in speech["text"]
    assert "Weniger als Nichtstun." in speech["text"]
    # chair, interposed question and interjections are not part of the speech text
    assert "Zwischenfrage" not in speech["text"]
    assert "Was kostet das?" not in speech["text"]
    assert "Beifall" not in speech["text"]
    assert speech["n_comments"] == 2
    assert speech["n_interventions"] == 1
    assert speech["protocol_id"] == 5
    assert speech["date"] == "2024-06-06"


def test_minister_role_and_quotes(parsed):
    speech = _speech(parsed, "ID209990200")
    assert speech["speaker_name"] == "Carl von Probe"
    assert speech["role"] == "Bundesminister für Testwesen"
    assert speech["faction"] is None
    assert "Ein Zitat im Text." in speech["text"]


def test_annex_speech_is_flagged(parsed):
    speech = _speech(parsed, "ID209990300")
    assert speech["in_annex"] is True
    assert speech["agenda_item"] is None
    assert speech["federal_state"] == "Niedersachsen"


def test_segments_follow_speaker_changes(parsed):
    segments = [s for s in parsed.segments if s["speech_id"] == "ID209990100"]
    assert [s["speaker_role"] for s in segments] == ["main", "chair", "main", "other", "main"]
    assert segments[1]["speaker_name"] == "Präsidentin Erika Beispiel"
    assert segments[3]["speaker_name"] == "Bernd Beispiel"
    assert segments[3]["speaker_place"] == "(Musterstadt)"
    assert segments[3]["text"] == "Was kostet das?"


def test_page_anchors_do_not_break_segments(parsed):
    texts = " ".join(s["text"] for s in parsed.segments)
    assert "S2" not in texts


def test_comments_are_split_and_classified(parsed):
    comments = [c for c in parsed.comments if c["speech_id"] == "ID209990100"]
    assert [c["kind"] for c in comments] == ["Beifall", "Zuruf", "Heiterkeit"]
    heckle = comments[1]
    assert heckle["actor"] == "Bernd Beispiel"
    assert heckle["actor_faction"] == "AfD"
    assert heckle["quote"] == "Das glauben Sie doch selbst nicht!"
    assert heckle["speaker_name"] == "Dr. Anna Muster"
    assert heckle["segment_index"] == 0
    assert comments[2]["segment_index"] == 4


def test_split_comment_handles_multiple_heckles():
    parts = split_comment("(Zurufe von der CDU/CSU – Gegenruf der Abg. Eva Test [DIE LINKE]: Hört, hört!)")
    assert [p["kind"] for p in parts] == ["Zuruf", "Gegenruf"]
    assert parts[1]["actor"] == "Eva Test"
    assert parts[1]["actor_faction"] == "DIE LINKE"
    assert parts[1]["quote"] == "Hört, hört!"


def test_parse_accepts_bytes_and_str():
    data = FIXTURE.read_bytes()
    assert len(parse_protocol_xml(data).speeches) == 3
    assert len(parse_protocol_xml(data.decode("utf-8")).speeches) == 3


def test_parse_rejects_other_xml():
    with pytest.raises(ValueError, match="Not a Bundestag plenary protocol"):
        parse_protocol_xml("<foo/>")
    with pytest.raises(ValueError, match="Could not parse"):
        parse_protocol_xml("<dbtplenarprotokoll>")


def test_to_dataframes(parsed):
    frames = parsed.to_dataframes()
    assert set(frames) == {"speeches", "segments", "comments"}
    assert len(frames["speeches"]) == 3
    assert "text" in frames["speeches"].columns


# ---- btaConnection integration (no network) ----

class _Response:
    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json = json_data
        self.content = content
        self.status_code = status_code
        self.reason = "OK" if status_code == 200 else "Not Found"
        self.text = ""
        self.url = ""

    def json(self):
        return self._json


class _Session:
    """Returns protocol metadata for API calls and the fixture for XML downloads."""
    def __init__(self, records):
        self.records = records
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params, headers))
        if url.endswith(".xml"):
            return _Response(content=FIXTURE.read_bytes())
        return _Response({"numFound": len(self.records), "cursor": "c", "documents": self.records})


def _record(pid=5, xml_url=XML_URL):
    fundstelle = {"id": str(pid), "dokumentnummer": "20/999", "pdf_url": "https://x/20999.pdf"}
    if xml_url:
        fundstelle["xml_url"] = xml_url
    return {"id": str(pid), "dokumentnummer": "20/999", "herausgeber": "BT", "fundstelle": fundstelle}


@pytest.fixture
def conn():
    c = btaConnection(apikey="testapikey0123456789")
    return c


def test_get_speeches_downloads_and_parses(conn):
    conn.session = _Session([_record()])
    speeches = conn.get_speeches(5)
    assert len(speeches) == 3
    assert speeches[0]["protocol_id"] == 5
    xml_call = conn.session.calls[-1]
    assert xml_call[0] == XML_URL
    # the API key must not be sent to the document server
    assert "Authorization" not in (xml_call[2] or {})


def test_get_speeches_filters_by_faction_and_speaker(conn):
    conn.session = _Session([_record()])
    assert [s["speech_id"] for s in conn.get_speeches(5, faction="spd")] == ["ID209990100"]
    assert [s["speech_id"] for s in conn.get_speeches(5, speaker="probe")] == ["ID209990200"]
    comments = conn.get_speeches(5, level="comment", faction="SPD")
    assert {c["speech_id"] for c in comments} == {"ID209990100"}


def test_get_speeches_pandas(conn):
    conn.session = _Session([_record()])
    df = conn.get_speeches(5, level="segment", return_format="pandas")
    assert len(df) == 7
    assert "speaker_role" in df.columns


def test_get_speeches_without_xml_raises(conn):
    conn.session = _Session([_record(xml_url=None)])
    with pytest.raises(ValueError, match="No structured XML"):
        conn.get_speeches(5)


def test_get_speeches_validates_arguments(conn):
    with pytest.raises(ValueError, match="level"):
        conn.get_speeches(5, level="words")
    with pytest.raises(ValueError, match="return_format"):
        conn.get_speeches(5, return_format="object")


def test_search_speeches_defaults_to_bundestag_and_skips_missing_xml(conn):
    conn.session = _Session([_record(5), _record(6, xml_url=None)])
    speeches = conn.search_speeches(legislative_period=20, max_protocols=2)
    api_params = conn.session.calls[0][1]
    assert api_params["f.zuordnung"] == "BT"
    assert api_params["f.wahlperiode"] == [20]
    assert len(speeches) == 3  # only the protocol with XML was parsed
    assert sum(1 for c in conn.session.calls if c[0].endswith(".xml")) == 1


def test_search_speeches_rejects_limit(conn):
    with pytest.raises(ValueError, match="max_protocols"):
        conn.search_speeches(limit=5)


def test_download_error_raises(conn):
    class _Failing(_Session):
        def get(self, url, params=None, timeout=None, headers=None):
            if url.endswith(".xml"):
                return _Response(status_code=404)
            return super().get(url, params, timeout, headers)
    conn.session = _Failing([_record()])
    with pytest.raises(requests.HTTPError, match="Could not download"):
        conn.get_speeches(5)


def test_missing_extra_metadata_does_not_overwrite_xml_values():
    parsed = parse_protocol_xml(FIXTURE, extra_metadata={"protocol_id": 5, "document_number": None})
    assert parsed.metadata["document_number"] == "20/999"
    assert parsed.speeches[0]["document_number"] == "20/999"


@pytest.mark.parametrize("text, kind, actor, faction, quote", [
    ("(Lebhafter Beifall bei der SPD)", "Beifall", None, None, None),
    ("(Anhaltender Beifall)", "Beifall", None, None, None),
    ("(Dr. Max Muster [AfD]: Das ist doch Unsinn!)", "Zuruf", "Dr. Max Muster", "AfD", "Das ist doch Unsinn!"),
    ("(Zuruf von der AfD: Unsinn!)", "Zuruf", None, None, "Unsinn!"),
    ("(Zurufe von der CDU/CSU)", "Zuruf", None, None, None),
    ("(Heiterkeit und Beifall bei der SPD)", "Heiterkeit", None, None, None),
    ("(Eva Test [DIE LINKE] meldet sich zu einer Zwischenfrage)", "Sonstiges", None, None, None),
])
def test_comment_classification_variants(text, kind, actor, faction, quote):
    (part,) = split_comment(text)
    assert (part["kind"], part["actor"], part["actor_faction"], part["quote"]) == (kind, actor, faction, quote)
