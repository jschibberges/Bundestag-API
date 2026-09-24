# -*- coding: utf-8 -*-
"""Helpers for incremental synchronisation via the 'aktualisiert' timestamp.

Every entity of the DIP API carries an ``aktualisiert`` timestamp (last update).
The API can filter on it (``f.aktualisiert.start``), which allows fetching only
what changed since the last run instead of downloading everything again.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class SyncResult:
    """Result of ``btaConnection.fetch_updates()`` and ``btaConnection.sync()``.

    Attributes
    ----------
    records:
        The new or updated records (list of dicts, model objects or a DataFrame,
        depending on ``return_format``).
    since:
        The timestamp the query started from.
    checkpoint:
        The latest ``aktualisiert`` timestamp among the records (or ``since`` if
        nothing changed). Pass it as ``since`` in the next run.
    """
    records: Any
    since: Optional[str]
    checkpoint: Optional[str]
    ids_at_checkpoint: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.records)

    def __repr__(self) -> str:
        return f"SyncResult(records={len(self)}, since={self.since!r}, checkpoint={self.checkpoint!r})"


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp as delivered by the API (e.g. 2022-08-01T15:30:16+02:00)."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _sort_key(value: str) -> float:
    # The API delivers timestamps with UTC offset. Naive values are interpreted in the
    # local time zone, so that all values stay comparable.
    return parse_timestamp(value).timestamp()


def latest_update(records: Iterable[Dict[str, Any]]) -> Optional[str]:
    """Return the latest 'aktualisiert' value of the records (as delivered by the API)."""
    latest, latest_key = None, None
    for record in records:
        value = record.get("aktualisiert")
        if not value:
            continue
        try:
            key = _sort_key(value)
        except ValueError:
            continue
        if latest_key is None or key > latest_key:
            latest, latest_key = value, key
    return latest


def state_key(resource: str, filters: Dict[str, Any]) -> str:
    """Key under which the checkpoint of a query is stored in the state file."""
    return resource + "|" + json.dumps(filters, sort_keys=True, default=str, ensure_ascii=False)


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: Dict[str, Any]) -> None:
    """Write the state file atomically, so an interrupted run cannot corrupt it."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".bundestag_api_state_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
