# -*- coding: utf-8 -*-
"""Parser for the structured XML plenary protocols of the German Bundestag.

Since the 18th legislative period the Bundestag publishes its plenary protocols
as structured XML (DTD "dbtplenarprotokoll"). The DIP API links these files in
``fundstelle.xml_url`` of a plenary protocol. This module turns such a file into
three flat tables that are easy to analyse:

speeches
    One row per speech (``<rede>``). ``text`` only contains what the main
    speaker said, without remarks of the presiding officer, interposed questions
    or interjections.
segments
    One row per contiguous passage of one speaker within a speech: the main
    speaker, the presiding officer (``speaker_role="chair"``) and other members
    asking interposed questions (``speaker_role="other"``).
comments
    One row per interjection recorded in the protocol, e.g. applause, heckling
    or laughter. A comment such as "(Beifall bei der SPD – Zuruf des Abg. Max
    Muster [AfD]: Unsinn!)" is split into its parts.

Note: ``speaker_id`` is the ID of the Bundestag's "MdB-Stammdaten", which is
*not* the same as the DIP ``person_id``.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Leading keywords of comment parts, used to classify interjections.
COMMENT_KINDS = (
    "Beifall", "Zuruf", "Zurufe", "Heiterkeit", "Lachen", "Widerspruch",
    "Zustimmung", "Unruhe", "Zwischenruf", "Gegenruf", "Glocke", "Buhrufe",
)

_ACTOR_PATTERN = re.compile(
    r"(?:Abg\.|Abgeordneten)\s+(?P<actor>[^\[\]:]+?)\s*\[(?P<faction>[^\]]+)\]"
)


@dataclass
class ParsedProtocol:
    """Result of :func:`parse_protocol_xml`.

    Each attribute is a list of flat dictionaries, which can be turned into
    pandas DataFrames with :meth:`to_dataframes` or ``pd.DataFrame(...)``.
    """
    metadata: Dict[str, Any]
    speeches: List[Dict[str, Any]] = field(default_factory=list)
    segments: List[Dict[str, Any]] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dataframes(self):
        """Return the tables as a dict of pandas DataFrames (requires pandas)."""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "to_dataframes() requires pandas. Install it with "
                "'pip install bundestag_api[pandas]' or 'conda install pandas'."
            ) from e
        return {
            "speeches": pd.DataFrame(self.speeches),
            "segments": pd.DataFrame(self.segments),
            "comments": pd.DataFrame(self.comments),
        }

    def __repr__(self):
        return (f"ParsedProtocol({self.metadata.get('document_number')}, "
                f"speeches={len(self.speeches)}, segments={len(self.segments)}, "
                f"comments={len(self.comments)})")


def _clean(text: Optional[str]) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text or "").strip()


def _child_text(element: Optional[ET.Element], tag: str) -> Optional[str]:
    if element is None:
        return None
    child = element.find(tag)
    if child is None:
        return None
    return _clean("".join(child.itertext())) or None


def _german_date_to_iso(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _to_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _parse_speaker(redner: ET.Element) -> Dict[str, Any]:
    """Extract speaker information from a <redner> element."""
    name = redner.find("name")
    rolle = name.find("rolle") if name is not None else None
    firstname = _child_text(name, "vorname")
    lastname = _child_text(name, "nachname")
    parts = [_child_text(name, "titel"), firstname, _child_text(name, "namenszusatz"), lastname]
    return {
        "speaker_id": redner.get("id"),
        "speaker_title": _child_text(name, "titel"),
        "speaker_firstname": firstname,
        "speaker_lastname": lastname,
        "speaker_name": " ".join(p for p in parts if p) or None,
        "speaker_place": _child_text(name, "ortszusatz"),
        "faction": _child_text(name, "fraktion"),
        "role": _child_text(rolle, "rolle_lang"),
        "role_short": _child_text(rolle, "rolle_kurz"),
        "federal_state": _child_text(name, "bdland"),
    }


def _empty_speaker(label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "speaker_id": None, "speaker_title": None, "speaker_firstname": None,
        "speaker_lastname": None, "speaker_name": label, "speaker_place": None,
        "faction": None, "role": None, "role_short": None, "federal_state": None,
    }


def split_comment(text: str) -> List[Dict[str, Optional[str]]]:
    """Split a protocol comment into its parts and classify them.

    Example::

        >>> split_comment("(Beifall bei der SPD – Zuruf des Abg. Max Muster [AfD]: Unsinn!)")
        [{'kind': 'Beifall', 'text': 'Beifall bei der SPD', 'actor': None, 'actor_faction': None, 'quote': None},
         {'kind': 'Zuruf', 'text': 'Zuruf des Abg. Max Muster [AfD]: Unsinn!', 'actor': 'Max Muster',
          'actor_faction': 'AfD', 'quote': 'Unsinn!'}]
    """
    body = _clean(text)
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1].strip()
    parts = [p.strip() for p in re.split(r"\s+[–—]\s+", body) if p.strip()]
    result = []
    for part in parts:
        first_word = re.split(r"[\s:,]", part, maxsplit=1)[0]
        kind = first_word if first_word in COMMENT_KINDS else "Sonstiges"
        if kind == "Zurufe":
            kind = "Zuruf"
        actor = actor_faction = quote = None
        match = _ACTOR_PATTERN.search(part)
        if match:
            actor = _clean(match.group("actor"))
            actor_faction = _clean(match.group("faction"))
            rest = part[match.end():]
            if rest.lstrip().startswith(":"):
                quote = rest.lstrip()[1:].strip() or None
        result.append({"kind": kind, "text": part, "actor": actor,
                       "actor_faction": actor_faction, "quote": quote})
    return result


def _load_root(source: Union[str, bytes, os.PathLike]) -> ET.Element:
    if isinstance(source, os.PathLike) or (
        isinstance(source, str) and not source.lstrip().startswith("<") and os.path.exists(source)
    ):
        data = Path(source).read_bytes()
    elif isinstance(source, str):
        data = source.encode("utf-8")
    elif isinstance(source, bytes):
        data = source
    else:
        raise TypeError("source must be XML content (str/bytes) or a path to an XML file.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse plenary protocol XML: {e}") from e


def _parse_metadata(root: ET.Element) -> Dict[str, Any]:
    period = root.get("wahlperiode") or root.findtext(".//kopfdaten//wahlperiode")
    session = root.get("sitzung-nr") or root.findtext(".//kopfdaten//sitzungsnr")
    date = root.get("sitzung-datum")
    if not date:
        datum = root.find(".//kopfdaten//datum")
        date = datum.get("date") if datum is not None else None
    period_i, session_i = _to_int(_clean(period)), _to_int(_clean(session))
    return {
        "legislative_period": period_i,
        "session": session_i,
        "document_number": f"{period_i}/{session_i}" if period_i and session_i else None,
        "date": _german_date_to_iso(date),
        "start_time": root.get("sitzung-start-uhrzeit"),
        "end_time": root.get("sitzung-ende-uhrzeit"),
    }


def parse_protocol_xml(source: Union[str, bytes, os.PathLike],
                       extra_metadata: Optional[Dict[str, Any]] = None) -> ParsedProtocol:
    """Parse a structured XML plenary protocol of the Bundestag.

    Parameters
    ----------
    source: str, bytes or path
        The XML content or the path to a downloaded XML file.
    extra_metadata: dict, optional
        Additional columns added to every row (e.g. the DIP protocol ID).

    Returns
    -------
    ParsedProtocol
        With the attributes ``metadata``, ``speeches``, ``segments`` and ``comments``.
    """
    root = _load_root(source)
    if root.tag != "dbtplenarprotokoll":
        raise ValueError(f"Not a Bundestag plenary protocol (root element '{root.tag}').")

    metadata = _parse_metadata(root)
    if extra_metadata:
        metadata.update(extra_metadata)
    base = dict(metadata)
    base.pop("start_time", None)
    base.pop("end_time", None)

    parent = {child: p for p in root.iter() for child in p}

    def context(rede: ET.Element) -> Dict[str, Any]:
        agenda_item, in_annex = None, False
        node = parent.get(rede)
        while node is not None:
            if node.tag == "tagesordnungspunkt" and agenda_item is None:
                agenda_item = node.get("top-id")
            if node.tag == "anlagen":
                in_annex = True
            node = parent.get(node)
        return {"agenda_item": agenda_item, "in_annex": in_annex}

    protocol = ParsedProtocol(metadata=metadata)

    for rede in root.iter("rede"):
        speech_id = rede.get("id")
        ctx = context(rede)
        segments: List[Dict[str, Any]] = []
        comments: List[Dict[str, Any]] = []
        main_speaker: Optional[Dict[str, Any]] = None
        current: Optional[Dict[str, Any]] = None

        def start_segment(speaker: Dict[str, Any], role: str) -> Dict[str, Any]:
            segment = {"speaker": speaker, "speaker_role": role, "paragraphs": []}
            segments.append(segment)
            return segment

        for child in rede:
            if child.tag == "p" and child.get("klasse") == "redner":
                redner = child.find("redner")
                if redner is None:
                    continue
                speaker = _parse_speaker(redner)
                if main_speaker is None:
                    main_speaker = speaker
                is_main = speaker["speaker_id"] == main_speaker["speaker_id"]
                current = start_segment(speaker, "main" if is_main else "other")
            elif child.tag == "name":
                label = _clean("".join(child.itertext())).rstrip(":").strip()
                current = start_segment(_empty_speaker(label), "chair")
            elif child.tag == "kommentar":
                comments.append({"segment_index": len(segments) - 1,
                                 "text": _clean("".join(child.itertext()))})
            elif child.tag in ("p", "zitat"):
                text = _clean("".join(child.itertext()))
                if not text:
                    continue
                if current is None:
                    current = start_segment(_empty_speaker(), "unknown")
                current["paragraphs"].append(text)
            # <a> (page anchors), <fussnote> and other elements are skipped

        if main_speaker is None:
            main_speaker = _empty_speaker()

        main_text = "\n\n".join(p for s in segments if s["speaker_role"] == "main"
                                for p in s["paragraphs"])
        protocol.speeches.append({
            **base,
            "speech_id": speech_id,
            **ctx,
            **main_speaker,
            "text": main_text,
            "word_count": len(main_text.split()),
            "n_comments": len(comments),
            "n_interventions": sum(1 for s in segments if s["speaker_role"] == "other"),
        })

        for index, segment in enumerate(segments):
            text = "\n\n".join(segment["paragraphs"])
            protocol.segments.append({
                **base,
                "speech_id": speech_id,
                "agenda_item": ctx["agenda_item"],
                "segment_index": index,
                "speaker_role": segment["speaker_role"],
                **segment["speaker"],
                "text": text,
                "word_count": len(text.split()),
            })

        for index, comment in enumerate(comments):
            for part_index, part in enumerate(split_comment(comment["text"])):
                protocol.comments.append({
                    **base,
                    "speech_id": speech_id,
                    "agenda_item": ctx["agenda_item"],
                    "speaker_name": main_speaker["speaker_name"],
                    "speaker_faction": main_speaker["faction"],
                    "segment_index": comment["segment_index"],
                    "comment_index": index,
                    "part_index": part_index,
                    **part,
                    "comment_text": comment["text"],
                })

    return protocol
