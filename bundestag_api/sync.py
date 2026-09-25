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
import time
from contextlib import contextmanager
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


@contextmanager
def _state_lock(path: str, timeout: float = 30.0, stale_after: float = 120.0):
    """Cross-platform lock for the state file, based on an exclusively created lock file.

    A lock file older than `stale_after` seconds (left behind by a crashed process)
    is removed.
    """
    lock_path = path + ".lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock_path) > stale_after:
                    os.remove(lock_path)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Could not lock state file {path} within {timeout:.0f} seconds. "
                    f"If no other sync is running, delete {lock_path}."
                ) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass


def update_state_entry(path: str, key: str, entry: Dict[str, Any]) -> None:
    """Store the checkpoint entry of one query without touching the others.

    The file is re-read under a lock right before writing, so parallel sync
    runs sharing one state file do not overwrite each other's checkpoints.
    """
    with _state_lock(path):
        state = load_state(path)
        state[key] = entry
        save_state(path, state)
