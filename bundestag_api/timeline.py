# -*- coding: utf-8 -*-
"""Timeline of a procedure: all steps, committees, decisions, promulgation and entry into force.

Combines two sources of the DIP API:

- the procedure steps ('vorgangsposition') with committee referrals
  ('ueberweisung') and decisions ('beschlussfassung')
- the procedure itself ('vorgang') with signing and promulgation
  ('verkuendung') and entry into force ('inkrafttreten')

The result is one row per event, sorted by date.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

EVENT_STEP = "step"
EVENT_SIGNING = "signing"
EVENT_PROMULGATION = "promulgation"
EVENT_ENTRY_INTO_FORCE = "entry_into_force"


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _join(values: Iterable[Optional[str]]) -> Optional[str]:
    """Join non-empty values with '; ', keeping order and dropping duplicates."""
    seen: List[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return "; ".join(seen) or None


def _empty_row(procedure: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "procedure_id": _to_int(procedure.get("id")),
        "procedure_title": procedure.get("titel"),
        "procedure_status": procedure.get("beratungsstand"),
        "date": None,
        "event_type": None,
        "event": None,
        "institution": None,
        "important": None,
        "position_id": None,
        "originator": None,
        "document_type": None,
        "document_number": None,
        "protocol_id": None,
        "pdf_url": None,
        "lead_committee": None,
        "committees": None,
        "decisions": None,
        "decided_document_numbers": None,
        "voting_methods": None,
        "details": None,
    }


def _step_row(procedure: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
    fundstelle = position.get("fundstelle") or {}
    referrals = position.get("ueberweisung") or []
    decisions = position.get("beschlussfassung") or []
    is_protocol = fundstelle.get("dokumentart") == "Plenarprotokoll"
    row = _empty_row(procedure)
    row.update({
        "date": position.get("datum"),
        "event_type": EVENT_STEP,
        "event": position.get("vorgangsposition"),
        "institution": position.get("zuordnung"),
        "important": position.get("gang"),
        "position_id": _to_int(position.get("id")),
        "originator": _join(u.get("titel") for u in position.get("urheber") or []),
        "document_type": fundstelle.get("dokumentart"),
        "document_number": fundstelle.get("dokumentnummer"),
        "protocol_id": _to_int(fundstelle.get("id")) if is_protocol else None,
        "pdf_url": fundstelle.get("pdf_url"),
        "lead_committee": _join(r.get("ausschuss") for r in referrals if r.get("federfuehrung")),
        "committees": _join(r.get("ausschuss") for r in referrals),
        "decisions": _join(d.get("beschlusstenor") for d in decisions),
        "decided_document_numbers": _join(d.get("dokumentnummer") for d in decisions),
        "voting_methods": _join(d.get("abstimmungsart") for d in decisions),
    })
    return row


def _promulgation_rows(procedure: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for entry in procedure.get("verkuendung") or []:
        reference = entry.get("fundstelle")
        if entry.get("ausfertigungsdatum"):
            row = _empty_row(procedure)
            row.update({
                "date": entry["ausfertigungsdatum"],
                "event_type": EVENT_SIGNING,
                "event": "Ausfertigung",
                "important": True,
                "details": reference,
            })
            rows.append(row)
        if entry.get("verkuendungsdatum"):
            row = _empty_row(procedure)
            row.update({
                "date": entry["verkuendungsdatum"],
                "event_type": EVENT_PROMULGATION,
                "event": "Verkündung",
                "important": True,
                "document_number": reference,
                "pdf_url": entry.get("pdf_url"),
                "details": _join([entry.get("verkuendungsblatt_bezeichnung"), entry.get("titel")]),
            })
            rows.append(row)
    return rows


def _entry_into_force_rows(procedure: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for entry in procedure.get("inkrafttreten") or []:
        if not entry.get("datum"):
            continue
        row = _empty_row(procedure)
        row.update({
            "date": entry["datum"],
            "event_type": EVENT_ENTRY_INTO_FORCE,
            "event": "Inkrafttreten",
            "important": True,
            "details": entry.get("erlaeuterung"),
        })
        rows.append(row)
    return rows


def build_timeline(procedure: Dict[str, Any], positions: Iterable[Dict[str, Any]],
                   only_important: bool = False) -> List[Dict[str, Any]]:
    """Build the timeline of a procedure.

    Parameters
    ----------
    procedure: dict
        The procedure ('vorgang') as returned by the DIP API.
    positions: iterable of dict
        Its procedure steps ('vorgangsposition').
    only_important: bool, optional
        Only keep steps the Bundestag marks as important for the course of the
        procedure ('gang'), plus signing, promulgation and entry into force.

    Returns
    -------
    list of dict
        One row per event, sorted by date. Rows with the same date keep the
        order of the API.
    """
    rows = [_step_row(procedure, p) for p in positions]
    rows += _promulgation_rows(procedure) + _entry_into_force_rows(procedure)
    if only_important:
        rows = [r for r in rows if r["important"]]
    # Stable sort: events without date go last, ties keep the API order
    rows.sort(key=lambda r: (r["date"] is None, r["date"] or ""))
    return rows
