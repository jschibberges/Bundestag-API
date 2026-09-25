# Changelog

All notable changes to this project are documented in this file.

## [1.4.0] - unreleased

### Breaking changes

- **Unsupported filters raise an error.** Filters are now validated against the DIP API
  specification for each resource. A filter the API does not support for a resource
  (e.g. `descriptor` for documents, `institution` for procedures) raises a `ValueError`
  that names the resources where it can be used. Previously such filters were silently
  dropped or ignored by the API, so results were not filtered.
- **IDs are integers in object mode.** With `return_format="object"`, all IDs
  (`btid`, `procedureID`, references) are `int`. Previously only `Drucksache.btid` was.
- **`Vorgang.approvalnecessaryBool` is a boolean** (`True`, `False` or `None`) instead of
  a string such as `"Nein"`.
- **`return_format="xml"` is rejected.** It was accepted before but returned JSON.
- **Python 3.8 or newer is required.** The package did not work on 3.7 before either
  (`typing.Literal`).

### Added

- **Speeches** from the structured XML plenary protocols (Bundestag, from 2013):
  `get_speeches()`, `search_speeches()`, `parse_protocol()` and `parse_protocol_xml()`.
  Three levels: speeches (text of the main speaker only), segments (speaker changes incl.
  presiding officer and interposed questions) and comments (applause, heckling with name,
  faction and wording). Optional filters by speaker and faction.
- **Decisions** ("Beschlussfassung") as a flat table: `get_decisions()` for procedures and
  `search_decisions()` with the usual filters and an optional `voting_method`, e.g.
  `"Namentliche Abstimmung"`. `protocol_id` links a decision to the debate.
  `Vorgangsposition.decisions` exposes the raw decisions.
- **Large datasets:** `count()` returns the number of matches with one request,
  `iter_query()` streams results page by page, and `limit=None` fetches all results.
  Truncated results are logged ("Returned 100 of 3456 matching records").
- **Incremental sync:** `fetch_updates(since=...)` returns records updated since a point in
  time with a checkpoint; `sync(state_file=...)` stores checkpoints between runs, skips
  duplicates and can be used by several jobs sharing one state file.
- **Vocabularies:** `bundestag_api.vocabulary` with the enums of the API specification and
  the dates of all legislative periods (`legislative_period_for()`,
  `legislative_period_dates()`). `discover_values()` counts which values of open
  vocabularies (subject areas, document types, ...) occur in the data.
- `date_start` and `date_end` accept `datetime.date` objects and are validated.
- The command line interface accepts repeated keys as lists (`title=Klima title=Energie`).
- `scripts/live_check.py`: smoke test against the live API.
- `py.typed` marker, CI workflow running the tests on Python 3.8 to 3.13.

### Fixed

- `institution` was never sent to the API, so results were not filtered by Bundestag or
  Bundesrat.
- `process_type` and `process_type_notation` were silently dropped for plenary protocols and
  activities; `drucksache_type` was rejected for activities although the API supports it.
- `return_format="object"` crashed for documents with authors, activities without linked
  procedures, persons with roles without `funktion`, and `str()` of activities.
- `import bundestag_api` failed without pandas, although pandas is an optional dependency.
- Timezone-aware `datetime` values lost their UTC offset in `updated_since`/`updated_until`.
- The command line option `fulltext=False` was interpreted as true.
- Log messages went to the root logger instead of the `bundestag_api` logger.
- `tests/test_utils.py` was always skipped.

### Security

- The API key is sent in the `Authorization` header instead of the URL, so it no longer
  appears in logs and error messages. `repr()` and `str()` of a connection mask the key.

### Changed

- Package metadata is defined in `pyproject.toml` only; the version lives in
  `bundestag_api/_version.py`.
- The README was corrected (API key expiry date, German search terms, data examples) and
  extended with sections on speeches, decisions, filter values, large datasets and sync.
