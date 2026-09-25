# Bundestag API

[![Tests](https://github.com/jschibberges/Bundestag-API/actions/workflows/tests.yml/badge.svg)](https://github.com/jschibberges/Bundestag-API/actions/workflows/tests.yml)
[![Upload Python Package](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Python wrapper for the official API of the German Bundestag's documentation system
([DIP](https://dip.bundestag.de/)). It gives you documents, legislative procedures, plenary
protocols, speeches, decisions and information on members of parliament as lists, Python
objects or pandas DataFrames.

Made for **data scientists, journalists and civic coders** who want to work with German
parliamentary data without dealing with raw API calls.

## What You Can Do

- **Find documents**: bills, motions, written questions and the government's answers
- **Follow laws**: every step of a procedure and every decision, from the first draft to promulgation
- **Analyse debates**: speeches, applause and heckling from the plenary protocols
- **Research politicians**: what a member of parliament said, asked and submitted
- **Monitor parliament**: fetch only what changed since your last run

## Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Key Concepts](#key-concepts)
- [Recipes](#recipes)
- [Working with Data](#working-with-data)
- [Speeches in Detail](#speeches-in-detail)
- [Decisions in Detail](#decisions-in-detail)
- [API Key and Rate Limits](#api-key-and-rate-limits)
- [Upgrading to 1.4](#upgrading-to-14)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Data Source and Terms of Use](#data-source-and-terms-of-use)

## Installation

```bash
pip install bundestag_api            # core package
pip install "bundestag_api[pandas]"  # with pandas for return_format="pandas"
```

Python 3.8 or newer is required. In a conda environment, install pandas with conda first
(`conda install pandas`) and then the package with pip.

## Quick Start

```python
import bundestag_api

# Connect with the shared public API key (see "API Key and Rate Limits" for your own key)
bt = bundestag_api.btaConnection()

# The five most recent bills of the current legislative period
bills = bt.search_document(drucksache_type="Gesetzentwurf", legislative_period=21, limit=5)
for bill in bills:
    print(bill["datum"], bill["dokumentnummer"], bill["titel"])

# The same as a pandas DataFrame
df = bt.search_document(drucksache_type="Gesetzentwurf", legislative_period=21,
                        limit=100, return_format="pandas")
```

## Key Concepts

The data is organised in six types. The API uses German names, which you will also find in
the field names of the results.

| Data type | API name | What it is | Search / get |
|-----------|----------|------------|--------------|
| Documents | `drucksache` | Printed papers: bills, motions, written questions, answers, reports | `search_document`, `get_document` |
| Procedures | `vorgang` | Everything that belongs to one matter, e.g. a bill from draft to promulgation | `search_procedure`, `get_procedure` |
| Procedure steps | `vorgangsposition` | A single step of a procedure, e.g. "1. Beratung" (first reading) | `search_procedureposition`, `get_procedureposition` |
| Plenary protocols | `plenarprotokoll` | Verbatim records of the plenary sessions | `search_plenaryprotocol`, `get_plenaryprotocol` |
| Activities | `aktivitaet` | What one person did: a speech, a question, co-signing a motion | `search_activity`, `get_activity` |
| Persons | `person` | Members of parliament and other persons appearing in the documents | `search_person`, `get_person` |

### Glossary

| German term | Meaning |
|-------------|---------|
| Wahlperiode | Legislative period, usually four years. The 21st began on 25 March 2025. |
| Drucksache | Printed paper of the Bundestag or Bundesrat, numbered e.g. `21/1234` (period/number) |
| Drucksachetyp | Type of printed paper, e.g. Gesetzentwurf (bill), Antrag (motion), Kleine Anfrage (written question), Antwort (answer), Beschlussempfehlung und Bericht (committee report) |
| Plenarprotokoll | Verbatim record of a plenary session, numbered e.g. `21/95` (period/session) |
| Vorgang | Procedure: all documents and steps on one matter |
| Vorgangstyp | Type of procedure, e.g. Gesetzgebung (legislation) |
| Beratungsstand | Status of a procedure, e.g. Verkündet (promulgated), Abgelehnt (rejected), Beantwortet (answered) |
| Beschlussfassung | Decision taken in a procedure step, e.g. adoption of a bill |
| Urheber | Originator: the body that submitted a document, e.g. a parliamentary group or the federal government |
| Initiative | Who initiated a procedure |
| Fraktion | Parliamentary group, e.g. `CDU/CSU`, `SPD`, `AfD`, `BÜNDNIS 90/DIE GRÜNEN`, `Die Linke` |
| Sachgebiet | Subject area, e.g. Gesundheit (health) |
| Deskriptor | Keyword from the parliamentary thesaurus, e.g. Klimaschutz |
| Ressort (federführend) | Federal ministry in charge |
| Zuordnung | Institution: BT (Bundestag), BR (Bundesrat), BV (Federal Convention), EK (European Chamber of the Bundesrat) |

All search terms (types, statuses, subject areas, keywords) are German. See
[Finding the Right Filter Values](#finding-the-right-filter-values) for their exact spelling.

## Recipes

All recipes run as they are. They assume `bt = bundestag_api.btaConnection()` and pandas.

### Find documents on a topic

```python
docs = bt.search_document(
    title=["Wärmepumpe", "Heizungsgesetz"],   # words in the title, OR search
    date_start="2023-01-01",
    date_end="2023-12-31",
    limit=None,                               # all matches
    return_format="pandas",
)
docs[["datum", "dokumentnummer", "drucksachetyp", "titel"]]
```

### Follow a law

```python
# Find the procedure
laws = bt.search_procedure(title="Medizinforschungsgesetz", process_type="Gesetzgebung")
law = laws[0]
print(law["id"], law["titel"], law.get("beratungsstand"))

# All steps, in order
steps = bt.search_procedureposition(processID=int(law["id"]), limit=None, return_format="pandas")
steps[["datum", "zuordnung", "vorgangsposition", "dokumentart"]].sort_values("datum")

# All decisions, from the Bundesrat's opinion to the final vote
decisions = bt.get_decisions(int(law["id"]), return_format="pandas")
decisions[["date", "institution", "position", "decision", "decided_document_number"]]
```

### What did a member of parliament do?

```python
# Common names match several people: list them and pick the right one
people = bt.search_person(person_name="Müller", legislative_period=21)
for i, p in enumerate(people):
    print(i, p["id"], p["vorname"], p["nachname"], p.get("fraktion"))

person_id = int(people[0]["id"])   # use the index of the person you mean
activities = bt.search_activity(personID=person_id, legislative_period=21,
                                limit=None, return_format="pandas")
activities["aktivitaetsart"].value_counts()   # speeches, questions, ...
```

### Written questions of a parliamentary group and the answers

```python
# Check the exact spelling of the originators first
bt.discover_values("drucksache", "urheber.titel", drucksache_type="Kleine Anfrage",
                   legislative_period=21)

questions = bt.search_document(drucksache_type="Kleine Anfrage", originator="Fraktion der SPD",
                               legislative_period=21, limit=None, return_format="pandas")
answers = bt.search_document(drucksache_type="Antwort", legislative_period=21,
                             limit=None, return_format="pandas")
```

Questions and answers belong to the same procedure (`vorgangsbezug` in the results), which you
can use to match them.

### Speeches of a plenary session

```python
protocol = bt.search_plenaryprotocol(document_number="21/95", institution="BT")[0]
speeches = bt.get_speeches(int(protocol["id"]), return_format="pandas")

speeches.groupby("faction")["word_count"].sum()          # words spoken per group

comments = bt.get_speeches(int(protocol["id"]), level="comment", return_format="pandas")
comments[comments["kind"] == "Zuruf"].groupby(["actor_faction", "speaker_faction"]).size()
```

See [Speeches in Detail](#speeches-in-detail) for all columns and caveats.

### Recorded votes

```python
votes = bt.search_decisions(
    institution="BT",
    date_start="2024-01-01",
    date_end="2024-12-31",
    voting_method="Namentliche Abstimmung",   # recorded vote
    limit=None,                               # scan all plenary steps in the period
    return_format="pandas",
)
votes[["date", "procedure_title", "decision", "decided_document_number"]]
```

The API does not contain how individual members voted.

### What's new since yesterday?

```python
# Run this daily, e.g. with cron or a scheduled GitHub Action
result = bt.sync("drucksache", state_file="dip_state.json",
                 since="2025-01-01T00:00:00",     # only used on the first run
                 institution="BT", drucksache_type="Gesetzentwurf")
for doc in result.records:
    print(doc["dokumentnummer"], doc["titel"])
```

## Working with Data

### Return Formats

| `return_format` | Result | Available for |
|-----------------|--------|---------------|
| `"json"` (default) | list of dicts, as delivered by the API | all functions returning records |
| `"pandas"` | pandas DataFrame, nested fields flattened with dots (`fundstelle.pdf_url`) | all functions except `iter_query` |
| `"object"` | list of Python objects (`Drucksache`, `Vorgang`, `Person`, ...) | search/get functions, `iter_query`, `fetch_updates`, `sync` |

In the raw JSON, IDs are strings (`"id": "68852"`). Convert them with `int(...)` before
passing them on, as in the recipes. Objects already use integer IDs.

`get_*` functions accept one ID or a list of IDs and always return a list.

### Filtering

All search functions accept the same filter parameters. Each filter is only available for some
data types, following the official API specification.
If you use a filter with a data type that does not support it, you get a `ValueError` naming the
data types where it works. Filters are never silently ignored.

| Parameter | Meaning | Available for | Several values |
|-----------|---------|---------------|----------------|
| `fid` | ID(s) of the entity | all | OR |
| `date_start`, `date_end` | Document date, `"YYYY-MM-DD"` or `datetime.date` | all | – |
| `updated_since`, `updated_until` | Time of last update, ISO 8601 or `datetime` | all | – |
| `legislative_period` | Wahlperiode, e.g. `21` | all | OR |
| `title` | Words or phrase in the title | documents, procedures, steps | OR |
| `drucksache_type` | Drucksachetyp, e.g. `"Antrag"` | documents, procedures, steps, activities | – |
| `document_number` | Document number, e.g. `"21/1234"` | all except persons | OR |
| `institution` | `"BT"`, `"BR"`, `"BV"` or `"EK"` | documents, steps, protocols, activities | – |
| `originator` | Urheber, e.g. `"Bundesregierung"` | documents, procedures, steps, activities | AND |
| `lead_department` | Ministry in charge | documents, procedures, steps | AND |
| `process_type` | Vorgangstyp, e.g. `"Gesetzgebung"` | all except persons | OR |
| `process_type_notation` | Numeric procedure type, e.g. `100` | all except persons | OR |
| `descriptor` | Thesaurus keyword, e.g. `"Klimaschutz"` | procedures, activities | AND |
| `sachgebiet` | Subject area, e.g. `"Gesundheit"` | procedures, activities | AND |
| `consultation_status` | Beratungsstand, e.g. `"Verkündet"` | procedures | OR |
| `initiative` | Initiator of a procedure | procedures | AND |
| `publication_reference` | Federal Law Gazette reference, e.g. `"BGBl I 2023, 71"` | procedures | OR |
| `gesta_id` | GESTA number | procedures | OR |
| `document_art` | `"Drucksache"` or `"Plenarprotokoll"` | procedures, steps, activities | – |
| `question_number` | Number of a question within a document | procedures, steps, activities | OR |
| `person_name` | First or last name | activities, persons | OR |
| `personID` | DIP person ID | activities | OR |
| `procedure_positionID` | ID of a procedure step | activities | OR |
| `drucksacheID` | Linked document | procedures, steps, activities | – |
| `plenaryprotocolID` | Linked plenary protocol | procedures, steps, activities | – |
| `processID` | Linked procedure | steps | – |
| `activityID` | Linked activity | steps | – |

"Several values" means you can pass a list. OR finds entities matching any value, AND only
entities matching all values. An OR search over an AND filter needs one query per value.
Only one of `drucksacheID`, `plenaryprotocolID`, `processID` and `activityID` can be used at a time.

`fulltext=True` (documents and protocols only) adds the full text to each result.

### Finding the Right Filter Values

Fixed values are available as constants:

```python
from bundestag_api import vocabulary as voc

voc.INSTITUTIONS              # {"BT": "Bundestag", "BR": "Bundesrat", ...}
voc.VOTING_METHODS            # ("Namentliche Abstimmung", "Hammelsprung", ...)
voc.FEDERAL_STATES            # the 16 Länder
voc.LEGISLATIVE_PERIODS       # {19: (date(2017, 10, 24), date(2021, 10, 25)), ...}
voc.CURRENT_LEGISLATIVE_PERIOD

bundestag_api.legislative_period_for("2019-05-01")    # 19
bundestag_api.legislative_period_dates(19)            # ("2017-10-24", "2021-10-25")
```

Open vocabularies such as subject areas, document types or statuses change over time.
`discover_values` counts which values actually occur in the data, with their exact spelling:

```python
bt.discover_values("vorgang", "sachgebiet", legislative_period=21)
bt.discover_values("drucksache", "drucksachetyp", institution="BT", return_format="pandas")
bt.discover_values("vorgang", "beratungsstand")
bt.discover_values("drucksache", "urheber.titel")      # nested fields with dots
```

It samples the most recent 1000 records by default (`limit=`), so very rare values may be missing.

### Large Datasets

```python
# How many? One request, nothing downloaded
bt.count("drucksache", legislative_period=20, drucksache_type="Kleine Anfrage")

# Everything (searches return at most 100 results by default)
all_questions = bt.search_document(legislative_period=20, drucksache_type="Kleine Anfrage",
                                   limit=None)

# Stream page by page: constant memory, stop whenever you like
import csv
with open("documents.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    for doc in bt.iter_query("drucksache", legislative_period=20):
        writer.writerow([doc["id"], doc["datum"], doc["drucksachetyp"], doc["titel"]])
```

If a result was cut off by `limit`, the package logs how many records matched in total. Turn on
logging to see it:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Keeping Your Data Up to Date

Every record has an `aktualisiert` timestamp. `fetch_updates` returns everything created or
changed since a point in time; `sync` also remembers where it stopped:

```python
result = bt.fetch_updates("drucksache", since="2025-06-01T00:00:00", institution="BT")
result.records      # the changed records
result.checkpoint   # latest 'aktualisiert' value, use it as `since` next time

result = bt.sync("drucksache", state_file="dip_state.json", since="2025-06-01T00:00:00")
```

- `sync` stores one checkpoint per data type and filter combination in the state file and does not
  return the same record twice. Several jobs can share one state file, even at the same time.
- The state file is only written after a successful run, so a failed run is simply repeated.
- Times without UTC offset are interpreted by the API as local time in Berlin.
- "Updated" includes corrections, so a sync can also return older documents whose metadata changed.

## Speeches in Detail

Since the 18th legislative period (2013), the Bundestag publishes its plenary protocols as
structured XML. `get_speeches` and `search_speeches` download and parse them into flat tables.

```python
# Speeches of several sessions, only one parliamentary group
greens = bt.search_speeches(date_start="2025-06-01", date_end="2025-06-30",
                            faction="GRÜNE", max_protocols=10, return_format="pandas")
```

| `level` | One row per | Main columns |
|---------|-------------|--------------|
| `"speech"` (default) | speech | `speaker_name`, `faction`, `role`, `agenda_item`, `text` (main speaker only), `word_count`, `n_comments`, `n_interventions` |
| `"segment"` | passage of one speaker | `speaker_role` (`main`, `chair` for the presiding officer, `other` for interposed questions), `speaker_name`, `text` |
| `"comment"` | part of an interjection | `kind` (Beifall, Zuruf, Lachen, ...), `actor`, `actor_faction`, `quote`, `speaker_name`, `speaker_faction` |

Every row also has `protocol_id`, `document_number`, `date`, `legislative_period` and `speech_id`.

- `speaker` and `faction` filter by a case-insensitive part of the name, e.g. `faction="GRÜNE"`.
- Each protocol is a separate download of several megabytes, so `search_speeches` stops after
  `max_protocols` (default 10).
- XML exists only for Bundestag protocols from 2013 on, not for the Bundesrat.
- `speaker_id` is the ID of the Bundestag's member master data, which differs from the DIP person ID.
- Speeches submitted in writing ("zu Protokoll gegebene Reden") have `in_annex=True`.
- Comments are classified by keyword. Named heckling such as "Max Muster [AfD]: Unsinn!" counts
  as `Zuruf`. Applause combined with other reactions ("Heiterkeit und Beifall") is classified by
  the first keyword, so use `comments["text"].str.contains("Beifall")` to count all applause.
- A downloaded XML file can be parsed directly: `bundestag_api.parse_protocol_xml("21095.xml")`.

For the full text of a protocol as one string (all periods, Bundestag and Bundesrat), use
`bt.search_plenaryprotocol(..., fulltext=True)` instead.

## Decisions in Detail

Decisions ("Beschlussfassung") are part of the procedure steps. `get_decisions` (for procedures)
and `search_decisions` (with filters) return one row per decision:

| Column | Content |
|--------|---------|
| `procedure_id`, `procedure_title`, `procedure_type` | The procedure |
| `position`, `institution`, `date` | The step, e.g. "3. Beratung" in the Bundestag |
| `decision` | Wording of the decision, e.g. "Annahme in Ausschussfassung" |
| `decided_document_number` | Document(s) the decision refers to, e.g. `"20/11561, 20/12149"` |
| `voting_method`, `recorded_vote` | Special voting procedure, e.g. "Namentliche Abstimmung"; empty for ordinary votes |
| `majority`, `result_remark`, `legal_basis` | Qualified majority, remarks such as "einstimmig", legal basis |
| `document_number`, `page`, `pdf_url`, `protocol_id` | Where the decision is recorded. `protocol_id` leads to the debate: `bt.get_speeches(protocol_id)` |

⚠️ **Read decisions carefully.** `decision` refers to the documents in `decided_document_number`.
"Annahme der Beschlussempfehlung" (adoption of the committee recommendation) means the motion was
*rejected* if the committee recommended rejection. Check the document before reporting an outcome.

`search_decisions` only scans steps recorded in plenary protocols, where decisions are taken.
`limit` counts these steps, not decisions. Pass `document_art=None` to scan all steps.

## API Key and Rate Limits

The package includes a shared public API key, valid until 31 May 2027. It is shared by all users,
so for regular or heavy use request a personal key from
[parlamentsdokumentation@bundestag.de](mailto:parlamentsdokumentation@bundestag.de)
(see [API help](https://dip.bundestag.de/über-dip/hilfe/api)).

```python
bt = bundestag_api.btaConnection(apikey="your_api_key")
```

The key is sent in the HTTP `Authorization` header, so it does not appear in URLs, logs or error
messages.

The API allows at most 25 concurrent requests and blocks clients that send too many requests
(`ConnectionError: Bot protection detected`). To stay below the limits:

```python
# Pause between the pages of a query (seconds, with small random variation)
bt = bundestag_api.btaConnection(delay=0.5)

# Limit parallel requests
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(lambda wp: bt.count("drucksache", legislative_period=wp), range(18, 22)))
```

## Upgrading to 1.4

Version 1.4 fixes filters that silently did nothing and adds speeches, decisions, streaming and
sync. A few changes can affect existing code:

- **Unsupported filters raise a `ValueError`** instead of being ignored, e.g. `descriptor` with
  `search_document`. Before, such queries returned unfiltered data.
- **`institution` now works.** Before 1.4 it was never sent, so results contained both Bundestag
  and Bundesrat data.
- With `return_format="object"`, **all IDs are integers**.
- `Vorgang.approvalnecessaryBool` is `True`, `False` or `None` instead of a string.
- `return_format="xml"` is no longer accepted. Python 3.8 or newer is required.

See [CHANGELOG.md](CHANGELOG.md) for all changes.

## API Reference

All functions have docstrings with every parameter: `help(bt.search_document)`.

**Search and get** (all accept the filters above, `limit` (default 100, `None` for all) and `return_format`)
- `search_document`, `search_procedure`, `search_procedureposition`, `search_plenaryprotocol`,
  `search_activity`, `search_person`
- `get_document`, `get_procedure`, `get_procedureposition`, `get_plenaryprotocol`, `get_activity`,
  `get_person`: by ID or list of IDs
- `query(resource, **filters)`: generic search for any data type

**Large datasets and updates**
- `count(resource, **filters)`: number of matches, one request
- `iter_query(resource, **filters)`: iterate page by page
- `fetch_updates(resource, since, **filters)`: records created or changed since a point in time
- `sync(resource, state_file, **filters)`: like `fetch_updates`, remembers the checkpoint

**Speeches**
- `get_speeches(btid, level="speech", speaker=None, faction=None)`: `btid` is the DIP ID of a plenary protocol (or a list)
- `search_speeches(max_protocols=10, level="speech", speaker=None, faction=None, **filters)`
- `parse_protocol(protocol)`: speeches, segments and comments of one protocol (ID or search result)
- `bundestag_api.parse_protocol_xml(path_or_xml)`: parse a local XML file

**Decisions**
- `get_decisions(procedure_id, voting_method=None)`
- `search_decisions(limit=100, voting_method=None, **filters)`
- `bundestag_api.flatten_decisions(positions)`: decision rows from procedure steps you already have

**Vocabularies**
- `discover_values(resource, field, limit=1000, **filters)`
- `bundestag_api.vocabulary`, `legislative_period_for(date)`, `legislative_period_dates(period)`

### Data structure examples

Abbreviated; the [API documentation](https://dip.bundestag.de/über-dip/hilfe/api) lists all fields.

```python
# Document (drucksache)
{
    "id": "68852",
    "dokumentart": "Drucksache",
    "drucksachetyp": "Antrag",
    "dokumentnummer": "19/1",
    "wahlperiode": 19,
    "herausgeber": "BT",
    "datum": "2017-10-24",
    "titel": "Weitergeltung von Geschäftsordnungsrecht",
    "urheber": [{"bezeichnung": "CDU/CSU", "titel": "Fraktion der CDU/CSU"}],
    "fundstelle": {"dokumentnummer": "19/1",
                   "pdf_url": "https://dserver.bundestag.de/btd/19/000/1900001.pdf"},
    "aktualisiert": "2022-08-01T15:30:16+02:00"
}

# Person
{
    "id": "1728",
    "vorname": "Ursula",
    "nachname": "Leyen",
    "namenszusatz": "von der",
    "titel": "Dr.  Ursula von der Leyen, Bundesmin., Bundesministerium der Verteidigung",
    "wahlperiode": [17, 18, 19],
    "person_roles": [{"funktion": "LMin Soz u. Frauen", "nachname": "Leyen", "vorname": "Ursula"}]
}
```

## Troubleshooting

**Empty results?**
- Search terms are German and must be spelled exactly: check them with `bt.discover_values(...)`.
- Filters with AND logic (`originator`, `descriptor`, `sachgebiet`, ...) only match entities that
  have *all* given values.
- Dates must be `"YYYY-MM-DD"`.
- Start broad and add filters one by one.

**Only 100 results?** That is the default `limit`. Use `limit=None` or `iter_query`.

**`ValueError: ... can only be used with resource ...`?** The filter does not exist for this data
type; the message names the data types where it works. See the [filter table](#filtering).

**`ConnectionError: Bot protection detected`?** Too many requests. Use `delay=`, fewer parallel
workers or a personal API key, see [API Key and Rate Limits](#api-key-and-rate-limits).

**Memory issues?** Check the size with `count`, stream with `iter_query`, or narrow the query by
legislative period or date.

## Data Source and Terms of Use

The data comes from DIP, the documentation and information system for parliamentary materials of
the German Bundestag. Please check its [terms of use](https://dip.bundestag.de/%C3%BCber-dip/nutzungsbedingungen)
and name the source when you publish results.

## Contributing

Contributions are welcome, see the [issues](https://github.com/jschibberges/Bundestag-API/issues).

Run the unit tests with `pytest`; they use sample data and need no network access. Before a
release, run the smoke test against the live API:

```bash
python scripts/live_check.py              # add --apikey YOUR_KEY or set BUNDESTAG_API_KEY
python scripts/live_check.py --skip-periods   # faster
```

## License

MIT License, see [LICENSE](LICENSE).
