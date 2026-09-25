# -*- coding: utf-8 -*-
"""Flatten parliamentary decisions ("Beschlussfassung") into a table.

Decisions are part of the procedure positions ('vorgangsposition') of the DIP
API. Each position can carry several decisions, e.g. the Bundestag adopting a
bill in the third reading or the Bundesrat giving its consent. This module
turns them into one flat row per decision, enriched with the context of the
procedure and the document in which the decision is recorded.

Important when interpreting the results: the decision text (``decision``,
e.g. "Annahme der Beschlussempfehlung") refers to the document named in
``decided_document_number``. Adopting a committee recommendation
("Beschlussempfehlung") can mean that the original motion was *rejected*,
if the committee recommended rejection. Always check which document was
decided on before reporting an outcome.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .vocabulary import VOTING_METHODS


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def flatten_decisions(positions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn procedure positions into one row per decision.

    Positions without decisions are skipped.

    Parameters
    ----------
    positions: iterable of dict
        Procedure positions ('vorgangsposition') as returned by the DIP API,
        e.g. from ``btaConnection.search_procedureposition()``.

    Returns
    -------
    list of dict
        One row per decision.
    """
    rows = []
    for position in positions:
        decisions = position.get("beschlussfassung") or []
        if not decisions:
            continue
        fundstelle = position.get("fundstelle") or {}
        is_protocol = fundstelle.get("dokumentart") == "Plenarprotokoll"
        top = fundstelle.get("top")
        agenda_item = f"{top}{fundstelle.get('top_zusatz') or ''}" if top is not None else None
        for index, decision in enumerate(decisions):
            voting_method = decision.get("abstimmungsart")
            rows.append({
                "procedure_id": _to_int(position.get("vorgang_id")),
                "procedure_title": position.get("titel"),
                "procedure_type": position.get("vorgangstyp"),
                "position_id": _to_int(position.get("id")),
                "position": position.get("vorgangsposition"),
                "institution": position.get("zuordnung"),
                "date": position.get("datum"),
                "document_type": fundstelle.get("dokumentart"),
                "document_number": fundstelle.get("dokumentnummer"),
                "protocol_id": _to_int(fundstelle.get("id")) if is_protocol else None,
                "agenda_item": agenda_item,
                "pdf_url": fundstelle.get("pdf_url"),
                "decision_index": index,
                "decision": decision.get("beschlusstenor"),
                "decided_document_number": decision.get("dokumentnummer"),
                "page": decision.get("seite"),
                "voting_method": voting_method,
                "recorded_vote": voting_method == "Namentliche Abstimmung",
                "majority": decision.get("mehrheit"),
                "result_remark": decision.get("abstimm_ergebnis_bemerkung"),
                "legal_basis": decision.get("grundlage"),
            })
    return rows
