# -*- coding: utf-8 -*-
"""Smoke test of bundestag_api against the live DIP API.

Checks the features that the unit tests can only cover with sample data:
authentication, filters, models, pagination, counting, incremental updates,
the speech parser, decisions, vocabularies and the legislative period dates.

Usage:
    python scripts/live_check.py                      # shared API key
    python scripts/live_check.py --apikey YOUR_KEY    # or env BUNDESTAG_API_KEY
    python scripts/live_check.py --skip-periods       # faster, skips period dates

Each check prints OK, WARN (plausibility issue, please look at it) or FAIL.
The exit code is 1 if any check failed.
"""
import argparse
import json
import os
import sys
import traceback
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

# Use the package from this repository, not an installed version
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bundestag_api  # noqa: E402
from bundestag_api import vocabulary as voc  # noqa: E402

RESULTS = []


def report(status, name, detail=""):
    RESULTS.append(status)
    print(f"[{status:4}] {name}" + (f": {detail}" if detail else ""))


def check(name):
    """Decorator: run a check, report exceptions as FAIL."""
    def decorator(func):
        def wrapper(bt, ctx):
            try:
                func(bt, ctx)
            except Exception as e:  # noqa: BLE001
                report("FAIL", name, f"{type(e).__name__}: {e}")
                traceback.print_exc(limit=2)
        wrapper.check_name = name
        return wrapper
    return decorator


@check("Authentication (API key in Authorization header)")
def check_auth(bt, ctx):
    n = bt.count("drucksache", legislative_period=voc.CURRENT_LEGISLATIVE_PERIOD)
    if n > 0:
        report("OK", "Authentication", f"{n} documents in legislative period {voc.CURRENT_LEGISLATIVE_PERIOD}")
    else:
        report("FAIL", "Authentication", "count() returned 0 documents")


@check("Filter institution")
def check_institution(bt, ctx):
    wp = voc.CURRENT_LEGISLATIVE_PERIOD
    total = bt.count("drucksache", legislative_period=wp)
    bt_n = bt.count("drucksache", legislative_period=wp, institution="BT")
    br_n = bt.count("drucksache", legislative_period=wp, institution="BR")
    sample = bt.search_document(legislative_period=wp, institution="BR", limit=20)
    wrong = [d["id"] for d in sample if d.get("herausgeber") != "BR"]
    detail = f"total={total}, BT={bt_n}, BR={br_n}"
    if wrong or bt_n == total or br_n == total:
        report("FAIL", "Filter institution", detail + f", records not from BR: {wrong[:5]}")
    else:
        report("OK", "Filter institution", detail)


@check("Models (return_format='object') for all resources")
def check_models(bt, ctx):
    wp = voc.CURRENT_LEGISLATIVE_PERIOD
    searches = {
        "drucksache": bt.search_document, "vorgang": bt.search_procedure,
        "vorgangsposition": bt.search_procedureposition, "aktivitaet": bt.search_activity,
        "plenarprotokoll": bt.search_plenaryprotocol, "person": bt.search_person,
    }
    counts = {}
    for resource, search in searches.items():
        objs = search(legislative_period=wp, limit=50, return_format="object")
        for o in objs:
            str(o), repr(o)
        counts[resource] = len(objs)
    report("OK", "Models", ", ".join(f"{k}={v}" for k, v in counts.items()))


@check("Pagination (iter_query)")
def check_pagination(bt, ctx):
    ids = [d["id"] for d in bt.iter_query("drucksache", legislative_period=20, limit=250)]
    if len(ids) == 250 and len(set(ids)) == 250:
        report("OK", "Pagination", "250 distinct records over 3 pages")
    else:
        report("FAIL", "Pagination", f"{len(ids)} records, {len(set(ids))} distinct")


@check("count() matches limit=None")
def check_count(bt, ctx):
    wp = voc.CURRENT_LEGISLATIVE_PERIOD
    n = bt.count("plenarprotokoll", legislative_period=wp, institution="BT")
    records = bt.search_plenaryprotocol(legislative_period=wp, institution="BT", limit=None)
    status = "OK" if n == len(records) and n > 0 else "FAIL"
    report(status, "count() vs. limit=None", f"count={n}, fetched={len(records)}")


@check("fetch_updates (f.aktualisiert.start)")
def check_updates(bt, ctx):
    since = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    total = bt.count("vorgang")
    result = bt.fetch_updates("vorgang", since=since)
    too_old = [r for r in result.records
               if r.get("aktualisiert") and r["aktualisiert"][:10] < since[:10]]
    detail = f"{len(result)} of {total} procedures updated since {since}, checkpoint={result.checkpoint}"
    if len(result) >= total or too_old:
        report("FAIL", "fetch_updates", detail + f", records older than since: {len(too_old)}")
    else:
        report("OK", "fetch_updates", detail)


@check("Speech parser (XML protocol)")
def check_speeches(bt, ctx):
    protocols = bt.search_plenaryprotocol(institution="BT", legislative_period=voc.CURRENT_LEGISLATIVE_PERIOD, limit=5)
    protocol = next(p for p in protocols if (p.get("fundstelle") or {}).get("xml_url"))
    parsed = bt.parse_protocol(protocol)
    speeches, segments, comments = parsed.speeches, parsed.segments, parsed.comments
    print(f"       {parsed}  ({protocol['fundstelle']['xml_url']})")

    no_name = sum(1 for s in speeches if not s["speaker_name"])
    no_text = sum(1 for s in speeches if not s["text"])
    no_affiliation = sum(1 for s in speeches if not s["faction"] and not s["role"] and not s["federal_state"])
    roles = Counter(s["speaker_role"] for s in segments)
    kinds = Counter(c["kind"] for c in comments)
    other_share = kinds.get("Sonstiges", 0) / max(len(comments), 1)
    print(f"       segment roles: {dict(roles)}")
    print(f"       comment kinds: {dict(kinds.most_common(8))}")
    print(f"       factions: {dict(Counter(s['faction'] for s in speeches).most_common(10))}")
    for s in speeches[:3]:
        print(f"       - {s['speaker_name']} ({s['faction'] or s['role']}), {s['word_count']} words: "
              f"{s['text'][:100]!r}")

    problems = []
    if not speeches:
        problems.append("no speeches")
    if no_name:
        problems.append(f"{no_name} speeches without speaker name")
    if no_text:
        problems.append(f"{no_text} speeches without text")
    if no_affiliation > 0.2 * len(speeches):
        problems.append(f"{no_affiliation} speeches without faction/role/state")
    if roles.get("chair", 0) == 0:
        problems.append("no chair segments")
    if roles.get("unknown", 0):
        problems.append(f"{roles['unknown']} segments with unknown speaker")
    unclassified = Counter(c["text"] for c in comments if c["kind"] == "Sonstiges")
    if unclassified:
        print("       most common unclassified comment parts:")
        for text, n in unclassified.most_common(15):
            print(f"         {n:3}x {text[:110]!r}")
    if other_share > 0.3:
        problems.append(f"{other_share:.0%} of comments not classified")
    report("WARN" if problems else "OK", "Speech parser", "; ".join(problems) or
           f"{len(speeches)} speeches, {len(comments)} comment parts")
    ctx["protocol_id"] = int(protocol["id"])


@check("Decisions")
def check_decisions(bt, ctx):
    rows = bt.search_decisions(legislative_period=20, process_type="Gesetzgebung", limit=300)
    if not rows:
        report("WARN", "Decisions", "no decisions in 300 procedure positions")
        diagnose_decisions(bt)
        return
    methods = Counter(r["voting_method"] for r in rows)
    print(f"       voting methods: {dict(methods)}")
    print(f"       decisions: {dict(Counter(r['decision'] for r in rows).most_common(6))}")
    unknown = set(methods) - set(voc.VOTING_METHODS) - {None}
    procedure_id = rows[0]["procedure_id"]
    per_procedure = bt.get_decisions(procedure_id)
    detail = f"{len(rows)} decisions, procedure {procedure_id} has {len(per_procedure)}"
    if unknown or not per_procedure:
        report("WARN", "Decisions", detail + f", unknown voting methods: {unknown}")
    else:
        report("OK", "Decisions", detail)


def diagnose_decisions(bt):
    """Show where decisions are delivered: list responses vs. single-entity endpoint."""
    positions = bt.search_procedureposition(legislative_period=20, process_type="Gesetzgebung", limit=300)
    keys = Counter(k for p in positions for k in p)
    print(f"       keys in {len(positions)} list results: {dict(keys.most_common())}")
    names = Counter(p.get("vorgangsposition") for p in positions)
    print(f"       most common positions: {dict(names.most_common(10))}")
    candidates = [p for p in positions if "Beratung" in (p.get("vorgangsposition") or "")
                  or "Durchgang" in (p.get("vorgangsposition") or "")][:3]
    for p in candidates:
        detail = bt._request_page(bt.BASE_URL + f"vorgangsposition/{p['id']}", {"format": "json"})
        in_detail = sorted(set(detail) - set(p))
        print(f"       position {p['id']} ({p.get('vorgangsposition')}): "
              f"fields only in single request: {in_detail}; "
              f"beschlussfassung={json.dumps(detail.get('beschlussfassung'), ensure_ascii=False)[:300]}")


@check("discover_values")
def check_vocabulary(bt, ctx):
    for resource, field in [("vorgang", "sachgebiet"), ("drucksache", "drucksachetyp"),
                            ("vorgang", "beratungsstand")]:
        values = bt.discover_values(resource, field, limit=300, legislative_period=20)
        print(f"       {resource}.{field}: " + ", ".join(f"{v['value']} ({v['count']})" for v in values[:8]))
        if not values:
            report("FAIL", "discover_values", f"no values for {resource}.{field}")
            return
    report("OK", "discover_values")


@check("Legislative period dates")
def check_periods(bt, ctx):
    problems = []
    for period, (start, end) in voc.LEGISLATIVE_PERIODS.items():
        protocols = bt.search_plenaryprotocol(legislative_period=period, institution="BT", limit=None)
        dates = sorted(p["datum"] for p in protocols if p.get("datum"))
        if not dates:
            problems.append(f"WP {period}: no protocols")
            continue
        first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
        if first != start:
            problems.append(f"WP {period}: first session {first}, expected start {start}")
        if end and last > end:
            problems.append(f"WP {period}: session on {last} after expected end {end}")
    report("WARN" if problems else "OK", "Legislative period dates",
           "; ".join(problems) or f"{len(voc.LEGISLATIVE_PERIODS)} periods match the plenary sessions")


CHECKS = [check_auth, check_institution, check_models, check_pagination, check_count,
          check_updates, check_speeches, check_decisions, check_vocabulary, check_periods]


def run_checks(bt, skip_periods=False):
    ctx = {}
    for c in CHECKS:
        if skip_periods and c is check_periods:
            continue
        print(f"\n--- {c.check_name}")
        c(bt, ctx)
    print("\nSummary: " + ", ".join(f"{s}={RESULTS.count(s)}" for s in ("OK", "WARN", "FAIL")))
    return 1 if "FAIL" in RESULTS else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apikey", default=os.environ.get("BUNDESTAG_API_KEY"))
    parser.add_argument("--delay", type=float, default=0.3, help="seconds between paginated requests")
    parser.add_argument("--skip-periods", action="store_true", help="skip the legislative period check")
    args = parser.parse_args()
    print(f"bundestag_api {bundestag_api.__version__}")
    bt = bundestag_api.btaConnection(apikey=args.apikey, delay=args.delay)
    sys.exit(run_checks(bt, skip_periods=args.skip_periods))


if __name__ == "__main__":
    main()
