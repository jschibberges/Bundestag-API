"""Tests for iter_query, count, limit=None, fetch_updates and sync."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from bundestag_api import btaConnection, SyncResult
from bundestag_api.models import Drucksache
from bundestag_api.sync import latest_update
from bundestag_api.utils import to_iso8601


class _Response:
    status_code = 200
    reason = "OK"
    text = ""
    url = ""

    def __init__(self, content):
        self._content = content

    def json(self):
        return self._content


class _PagedSession:
    """Serves `docs` in pages of `page_size`, using the page index as cursor."""
    def __init__(self, docs, page_size=3):
        self.docs = docs
        self.page_size = page_size
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, headers=None):
        params = dict(params or {})
        self.calls.append((url, params))
        page = int(params.get("cursor") or 0)
        chunk = self.docs[page * self.page_size:(page + 1) * self.page_size]
        next_cursor = str(page + 1) if chunk else str(page)
        return _Response({"numFound": len(self.docs), "cursor": next_cursor, "documents": chunk})


def _docs(n, updated=None):
    return [{"id": str(i), "titel": f"Dok {i}",
             "aktualisiert": (updated or {}).get(i, "2024-06-01T10:00:00+02:00")} for i in range(n)]


@pytest.fixture
def make_conn():
    def factory(docs, page_size=3):
        c = btaConnection(apikey="testapikey0123456789")
        c.session = _PagedSession(docs, page_size)
        return c
    return factory


# ---- limit=None ----

def test_query_limit_none_fetches_all(make_conn):
    conn = make_conn(_docs(10))
    assert len(conn.query("drucksache", limit=None)) == 10


def test_query_logs_truncation(make_conn, caplog):
    conn = make_conn(_docs(10))
    with caplog.at_level("INFO", logger="bundestag_api"):
        conn.query("drucksache", limit=4)
    assert "Returned 4 of 10" in caplog.text


@pytest.mark.parametrize("bad", [0, -1, True, 2.5])
def test_invalid_limit(make_conn, bad):
    with pytest.raises(ValueError, match="limit"):
        make_conn([]).query("drucksache", limit=bad)


# ---- iter_query ----

def test_iter_query_is_lazy(make_conn):
    conn = make_conn(_docs(10))
    it = conn.iter_query("drucksache", legislative_period=20)
    assert conn.session.calls == []  # nothing requested before iterating
    first = next(it)
    assert first["id"] == "0"
    assert len(conn.session.calls) == 1
    assert conn.session.calls[0][1]["f.wahlperiode"] == [20]


def test_iter_query_yields_all_pages(make_conn):
    conn = make_conn(_docs(10))
    assert [d["id"] for d in conn.iter_query("drucksache")] == [str(i) for i in range(10)]


def test_iter_query_respects_limit_and_stops_requesting(make_conn):
    conn = make_conn(_docs(10))
    assert len(list(conn.iter_query("drucksache", limit=4))) == 4
    assert len(conn.session.calls) == 2


def test_iter_query_objects(make_conn):
    conn = make_conn(_docs(2))
    items = list(conn.iter_query("drucksache", return_format="object"))
    assert all(isinstance(i, Drucksache) for i in items)


def test_iter_query_validates_eagerly(make_conn):
    conn = make_conn([])
    with pytest.raises(TypeError, match="Unknown filter"):
        conn.iter_query("drucksache", legislativ_period=20)  # typo
    with pytest.raises(ValueError, match="descriptor"):
        conn.iter_query("drucksache", descriptor="Klimaschutz")
    with pytest.raises(ValueError, match="return_format"):
        conn.iter_query("drucksache", return_format="pandas")


# ---- count ----

def test_count_uses_single_request(make_conn):
    conn = make_conn(_docs(42))
    assert conn.count("drucksache", institution="BT") == 42
    assert len(conn.session.calls) == 1
    assert conn.session.calls[0][1]["f.zuordnung"] == "BT"


def test_count_fulltext_endpoint(make_conn):
    conn = make_conn(_docs(1))
    conn.count("drucksache", fulltext=True)
    assert conn.session.calls[0][0].endswith("/drucksache-text")


def test_count_rejects_unknown_filters(make_conn):
    with pytest.raises(TypeError):
        make_conn([]).count("drucksache", foo=1)


# ---- timestamps ----

def test_to_iso8601_keeps_timezone():
    aware = datetime(2024, 6, 1, 10, 0, 0, 123, tzinfo=timezone(timedelta(hours=2)))
    assert to_iso8601(aware) == "2024-06-01T10:00:00+02:00"


def test_latest_update_compares_timezones():
    records = [{"aktualisiert": "2024-06-01T10:00:00+02:00"},   # 08:00 UTC
               {"aktualisiert": "2024-06-01T09:00:00+00:00"},   # 09:00 UTC -> latest
               {"aktualisiert": None}, {}]
    assert latest_update(records) == "2024-06-01T09:00:00+00:00"
    assert latest_update([]) is None


# ---- fetch_updates ----

def test_fetch_updates_sets_filter_and_checkpoint(make_conn):
    docs = _docs(4, {2: "2024-06-03T08:00:00+02:00"})
    conn = make_conn(docs)
    result = conn.fetch_updates("drucksache", since="2024-06-01T00:00:00", institution="BT")
    assert isinstance(result, SyncResult)
    assert len(result) == 4
    params = conn.session.calls[0][1]
    assert params["f.aktualisiert.start"] == "2024-06-01T00:00:00"
    assert params["f.zuordnung"] == "BT"
    assert result.since == "2024-06-01T00:00:00"
    assert result.checkpoint == "2024-06-03T08:00:00+02:00"
    assert result.ids_at_checkpoint == ["2"]


def test_fetch_updates_without_results_keeps_since(make_conn):
    result = make_conn([]).fetch_updates("vorgang", since=datetime(2024, 6, 1))
    assert len(result) == 0
    assert result.checkpoint == "2024-06-01T00:00:00"


def test_fetch_updates_pandas(make_conn):
    result = make_conn(_docs(3)).fetch_updates("drucksache", since="2024-06-01T00:00:00",
                                               return_format="pandas")
    assert len(result.records) == 3


def test_fetch_updates_rejects_reserved_filters(make_conn):
    with pytest.raises(ValueError, match="limit"):
        make_conn([]).fetch_updates("drucksache", since="2024-06-01T00:00:00", limit=5)


# ---- sync ----

def test_sync_requires_since_on_first_run(make_conn, tmp_path):
    with pytest.raises(ValueError, match="since"):
        make_conn([]).sync("drucksache", state_file=str(tmp_path / "state.json"))


def test_sync_stores_checkpoint_and_skips_duplicates(make_conn, tmp_path):
    state_file = str(tmp_path / "state.json")
    docs = _docs(3, {0: "2024-06-01T10:00:00+02:00", 1: "2024-06-02T10:00:00+02:00",
                     2: "2024-06-02T10:00:00+02:00"})
    conn = make_conn(docs)

    first = conn.sync("drucksache", state_file=state_file, since="2024-06-01T00:00:00", institution="BT")
    assert len(first) == 3
    assert first.checkpoint == "2024-06-02T10:00:00+02:00"

    # Second run: the API returns the boundary records again (inclusive filter) plus a new one
    conn.session.docs = [docs[1], docs[2], {"id": "3", "aktualisiert": "2024-06-03T09:00:00+02:00"}]
    second = conn.sync("drucksache", state_file=state_file, since="2000-01-01T00:00:00", institution="BT")
    assert [r["id"] for r in second.records] == ["3"]
    # the stored checkpoint wins over `since`
    assert conn.session.calls[-1][1]["f.aktualisiert.start"] == "2024-06-02T10:00:00+02:00"

    state = json.loads(open(state_file, encoding="utf-8").read())
    (entry,) = state.values()
    assert entry["checkpoint"] == "2024-06-03T09:00:00+02:00"
    assert entry["ids_at_checkpoint"] == ["3"]


def test_sync_without_changes_returns_nothing_twice(make_conn, tmp_path):
    state_file = str(tmp_path / "state.json")
    docs = _docs(2, {0: "2024-06-02T10:00:00+02:00", 1: "2024-06-02T10:00:00+02:00"})
    conn = make_conn(docs)
    assert len(conn.sync("vorgang", state_file=state_file, since="2024-06-01T00:00:00")) == 2
    assert len(conn.sync("vorgang", state_file=state_file)) == 0
    assert len(conn.sync("vorgang", state_file=state_file)) == 0


def test_sync_keeps_separate_checkpoints_per_query(make_conn, tmp_path):
    state_file = str(tmp_path / "state.json")
    conn = make_conn(_docs(1))
    conn.sync("drucksache", state_file=state_file, since="2024-06-01T00:00:00", institution="BT")
    conn.sync("drucksache", state_file=state_file, since="2024-06-01T00:00:00", institution="BR")
    conn.sync("vorgang", state_file=state_file, since="2024-06-01T00:00:00")
    assert len(json.loads(open(state_file, encoding="utf-8").read())) == 3


def test_sync_does_not_write_state_on_error(make_conn, tmp_path):
    state_file = tmp_path / "state.json"
    conn = make_conn([])

    def failing_get(*args, **kwargs):
        raise ConnectionError("network down")
    conn.session.get = failing_get
    with pytest.raises(ConnectionError):
        conn.sync("drucksache", state_file=str(state_file), since="2024-06-01T00:00:00")
    assert not state_file.exists()


def test_latest_update_handles_mixed_naive_and_aware():
    assert latest_update([{"aktualisiert": "2024-06-01T10:00:00"},
                          {"aktualisiert": "2030-01-01T00:00:00+00:00"}]) == "2030-01-01T00:00:00+00:00"


def test_sync_does_not_advance_checkpoint_when_formatting_fails(make_conn, tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    docs = _docs(2, {0: "2024-06-02T10:00:00+02:00", 1: "2024-06-03T10:00:00+02:00"})
    conn = make_conn(docs)

    original_format = conn._format_results

    def no_pandas(data, return_format, resource):
        if return_format == "pandas":
            raise ImportError("return_format='pandas' requires pandas")
        return original_format(data, return_format, resource)
    monkeypatch.setattr(conn, "_format_results", no_pandas)
    with pytest.raises(ImportError):
        conn.sync("drucksache", state_file=str(state_file), since="2024-06-01T00:00:00",
                  return_format="pandas")
    assert not state_file.exists()

    # the next run still gets all records
    monkeypatch.undo()
    result = conn.sync("drucksache", state_file=str(state_file), since="2024-06-01T00:00:00")
    assert len(result) == 2


@pytest.mark.parametrize("method", ["sync", "fetch_updates"])
def test_invalid_return_format_rejected_before_request(make_conn, tmp_path, method):
    conn = make_conn(_docs(1))
    kwargs = {"state_file": str(tmp_path / "s.json")} if method == "sync" else {}
    with pytest.raises(ValueError, match="return_format"):
        getattr(conn, method)("drucksache", since="2024-06-01T00:00:00", return_format="xml", **kwargs)
    assert conn.session.calls == []


def test_parallel_sync_runs_do_not_overwrite_each_other(make_conn, tmp_path, monkeypatch):
    """Run B saves while run A is between reading and saving; A must keep B's entry."""
    import bundestag_api.bta_wrapper as wrapper
    state_file = str(tmp_path / "state.json")
    conn_a = make_conn(_docs(1, {0: "2024-06-02T10:00:00+02:00"}))
    conn_b = make_conn(_docs(1, {0: "2024-06-05T10:00:00+02:00"}))

    original_raw = btaConnection._fetch_updates_raw

    def fetch_then_let_b_run(self, *args, **kwargs):
        result = original_raw(self, *args, **kwargs)
        if self is conn_a:
            conn_b.sync("vorgang", state_file=state_file, since="2024-06-01T00:00:00")
        return result
    monkeypatch.setattr(wrapper.btaConnection, "_fetch_updates_raw", fetch_then_let_b_run)

    conn_a.sync("drucksache", state_file=state_file, since="2024-06-01T00:00:00")
    state = json.loads(open(state_file, encoding="utf-8").read())
    checkpoints = sorted(e["checkpoint"] for e in state.values())
    assert checkpoints == ["2024-06-02T10:00:00+02:00", "2024-06-05T10:00:00+02:00"]


def test_state_lock_removes_stale_lock_and_times_out(tmp_path):
    import os
    import time
    from bundestag_api.sync import _state_lock, update_state_entry
    path = str(tmp_path / "state.json")
    lock = path + ".lock"

    open(lock, "w").close()
    old = time.time() - 3600
    os.utime(lock, (old, old))
    update_state_entry(path, "k", {"checkpoint": "x"})  # stale lock is removed
    assert not os.path.exists(lock)

    open(lock, "w").close()  # fresh lock held by "another process"
    with pytest.raises(TimeoutError, match="delete"):
        with _state_lock(path, timeout=0.2):
            pass
    os.remove(lock)


def test_get_decisions_fetches_all_positions(tmp_path):
    from tests.test_decisions import _position
    positions = [_position(i, [{"beschlusstenor": "Annahme"}]) for i in range(1205)]
    c = btaConnection(apikey="testapikey0123456789")
    c.session = _PagedSession(positions, page_size=100)
    assert len(c.get_decisions(300001)) == 1205
