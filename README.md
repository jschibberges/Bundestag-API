# Bundestag API

[![Upload Python Package](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A beginner-friendly Python wrapper for accessing German Federal Parliament (Bundestag) data. This package simplifies querying parliamentary documents, procedures, plenary protocols, and member information through the official Bundestag API.

Perfect for data scientists, researchers, and political analysts who want to analyze German parliamentary data without dealing with complex API calls.

## What You Can Do

- **Analyze Parliamentary Documents**: Access bills, reports, and official documents
- **Track Legislative Processes**: Follow how laws move through parliament and how they were decided
- **Follow Parliamentary Debates**: Examine plenary protocols, speeches and other activities
- **Research Politicians**: Get information about current and former members of parliament
- **Time Series Analysis**: Filter data by date ranges for trend analysis

## Quick Start

### Installation

```bash
pip install bundestag_api            # core package
pip install "bundestag_api[pandas]"  # with pandas support for return_format="pandas"
```

Python 3.8 or newer is required.

### Your First Query

```python
import bundestag_api

# Create a connection (uses free public API key)
bt = bundestag_api.btaConnection()

# Get recent documents
documents = bt.search_document(limit=5, date_start="2024-01-01")

# Print document titles
for doc in documents:
    print(f"{doc['drucksachetyp']}: {doc['titel']}")
```

## Core Concepts

The Bundestag API provides access to 6 main data types:

| Data Type | Description | Use Cases |
|-----------|-------------|-----------|
| **Documents** (`drucksache`) | Bills, reports, proposals | Policy analysis, text mining |
| **Procedures** (`vorgang`) | Legislative processes | Tracking law development |
| **Activities** (`aktivitaet`) | Speeches, questions, other actions of individual persons | Who speaks or asks about what |
| **Persons** (`person`) | MPs and officials | Political network analysis |
| **Plenary Protocols** (`plenarprotokoll`) | Session transcripts | Speech analysis, debate tracking |
| **Procedure Positions** (`vorgangsposition`) | Steps in processes | Process flow analysis |

## Common Use Cases for Data Scientists

### 1. Document Analysis

```python
# Get all documents from a specific time period
documents = bt.search_document(
    date_start="2024-01-01",
    date_end="2024-03-31",
    limit=100
)

# Get full text for analysis
doc_with_text = bt.search_document(
    fid=[12345],  # specific document ID
    fulltext=True
)
```

### 2. Tracking Legislative Processes

```python
# Find procedures by topic. Descriptors are German keywords from the
# Bundestag thesaurus; multiple descriptors are combined with AND.
procedures = bt.search_procedure(
    descriptor=["Klimaschutz", "Windenergieanlage"],
    limit=50
)

# Get detailed procedure information
procedure_details = bt.get_procedure(btid=12345)
```

### 3. Full Text of Plenary Protocols

```python
# Get plenary protocols with their full text as one string (all periods, BT and BR).
# For individual speeches, see "Speech Analysis" below.
protocols = bt.search_plenaryprotocol(
    date_start="2024-01-01",
    fulltext=True,
    limit=10
)
```

### 4. Speech Analysis (Who Said What)

Since the 18th legislative period (2013), the Bundestag publishes its plenary
protocols as structured XML. The package downloads and parses these files into
flat tables, so you can analyse speeches without writing any XML code.

```python
# All speeches of one plenary session (DIP ID of the 'plenarprotokoll')
speeches = bt.get_speeches(5678, return_format="pandas")
speeches[["speaker_name", "faction", "agenda_item", "word_count"]].head()

# Speeches from several sessions, filtered by faction (case-insensitive substring)
greens = bt.search_speeches(
    date_start="2024-06-01",
    date_end="2024-06-30",
    faction="GRÜNE",
    max_protocols=5,          # each protocol is a separate download
    return_format="pandas",
)

# Words spoken per faction
greens.groupby("faction")["word_count"].sum()
```

Three levels of detail are available via `level=`:

| `level` | One row per | Typical use |
|---------|-------------|-------------|
| `"speech"` (default) | speech; `text` contains only the main speaker | text mining, speaking time, topics |
| `"segment"` | passage of one speaker, incl. presiding officer (`speaker_role="chair"`) and interposed questions (`"other"`) | debate dynamics, interventions |
| `"comment"` | part of an interjection recorded in the protocol | applause and heckling analysis |

```python
# Who heckles whom?
comments = bt.get_speeches(5678, level="comment", return_format="pandas")
heckles = comments[comments["kind"] == "Zuruf"]
heckles.groupby(["actor_faction", "speaker_faction"]).size()

# Applause, also when combined with other reactions ("Heiterkeit und Beifall ...")
applause = comments[comments["text"].str.contains("Beifall")]
```

Already downloaded an XML file? Parse it directly:

```python
from bundestag_api import parse_protocol_xml

protocol = parse_protocol_xml("20177.xml")
frames = protocol.to_dataframes()   # {"speeches": ..., "segments": ..., "comments": ...}
```

Good to know:
- Structured XML exists only for Bundestag protocols from 2013 onwards (18th legislative
  period), not for the Bundesrat. `search_speeches` therefore filters on `institution="BT"`
  by default and skips protocols without XML.
- `speaker_id` is the ID of the Bundestag's member master data (MdB-Stammdaten), which
  differs from the DIP `person_id`.
- Speeches submitted in writing ("zu Protokoll gegebene Reden") are marked with `in_annex=True`.
- Comments are classified by their leading keyword (`kind`: Beifall, Zuruf, Heiterkeit,
  Lachen, Widerspruch, ...). The original wording is always kept in `text` and `comment_text`.

### 5. Decisions and Votes

Every step of a procedure (`vorgangsposition`) can contain decisions ("Beschlussfassung"):
the Bundestag adopting a bill, the Bundesrat giving its consent, a motion being rejected.
The package turns them into one flat row per decision.

```python
# All decisions on one legislative procedure (DIP ID of the 'vorgang')
decisions = bt.get_decisions(300001, return_format="pandas")
decisions[["date", "institution", "position", "decision", "decided_document_number", "voting_method"]]

# All recorded votes ("namentliche Abstimmungen") in June 2024
votes = bt.search_decisions(
    date_start="2024-06-01",
    date_end="2024-06-30",
    institution="BT",
    voting_method="Namentliche Abstimmung",
    limit=500,                 # number of procedure steps to scan
    return_format="pandas",
)
```

Each row contains the procedure (`procedure_id`, `procedure_title`, `procedure_type`), the step
(`position`, e.g. "2. Beratung", `institution`, `date`), the decision (`decision`, `decided_document_number`,
`voting_method`, `recorded_vote`, `majority`, `result_remark`, `legal_basis`) and where it is recorded
(`document_number`, `page`, `pdf_url`). For decisions taken in a plenary session, `protocol_id` links
to the protocol, so you can fetch the debate: `bt.get_speeches(row["protocol_id"])`.

⚠️ **Read decisions carefully.** `decision` refers to the document in `decided_document_number`.
"Annahme der Beschlussempfehlung" (adoption of the committee recommendation) can mean that the
original motion was *rejected*, if the committee recommended rejection. Check that document before
reporting an outcome. The API does not contain how individual members voted.

Available voting methods: `bundestag_api.VOTING_METHODS`.

### 6. Member Analysis

```python
# Search for members of the Bundestag
members = bt.search_person(limit=100)

# Get detailed information about a specific person
member_details = bt.get_person(btid=12345)
```

## Working with Data

### Return Formats

The package supports multiple return formats to fit your workflow:

```python
# JSON format (default) - good for general analysis
data_json = bt.search_document(return_format="json")

# Python objects - good for object-oriented programming
data_objects = bt.search_document(return_format="object")

# Pandas DataFrame - perfect for data analysis
data_df = bt.search_document(return_format="pandas")
```

### Filtering Data

All search functions support common filters:

```python
documents = bt.search_document(
    date_start="2024-01-01",      # Start date (YYYY-MM-DD string or datetime.date)
    date_end="2024-12-31",        # End date (YYYY-MM-DD string or datetime.date)
    institution="BT",             # BT=Bundestag, BR=Bundesrat
    drucksache_type="Antrag",     # Specific 'Drucksache' types
    title=["Klima", "Energie"],   # Keywords in title (OR search, German terms)
    limit=100                     # Maximum results
)
```

Not every filter is available for every data type. If you pass a filter that the
API does not support for a resource (e.g. `descriptor` for documents), the package
raises a `ValueError` naming the resources where the filter can be used, instead
of silently returning unfiltered data.

### Handling Large Datasets

```python
# Get all documents (automatically handles pagination)
all_documents = bt.search_document(
    date_start="2024-01-01",
    limit=1000  # Will make multiple API calls as needed
)

# Process data in chunks for memory efficiency
for i in range(0, len(all_documents), 100):
    chunk = all_documents[i:i+100]
    # Process your chunk here
    process_documents(chunk)
```

### Parallel Processing

⚠️ **Important Rate Limit Information**

The Bundestag API has a **maximum of 25 concurrent requests** limit. When using parallel processing (threading, multiprocessing, asyncio), you must respect this limit to avoid triggering bot protection.

#### API Key Considerations

**Generic API Key (default)**
- Shared potentially by all users globally
- More likely to hit rate limits

**Personal API Key** (recommended for production)
- Dedicated quota for your application
- Better performance and reliability
- Get your key at [dip.bundestag.de](https://dip.bundestag.de/)

#### Bot Protection Errors

If you encounter `ConnectionError: Bot protection detected (Enodia challenge)`, this means:
- Too many concurrent requests (>25)
- Too many requests per second
- The shared generic API key is overloaded

**Solutions:**
1. Reduce `max_workers` (try 5 or less)
2. Add `time.sleep()` delays between requests
3. Use a personal API key
4. Process data in smaller batches

## Data Structure Examples

Abbreviated examples; see the [official API documentation](https://dip.bundestag.de/über-dip/hilfe/api) for all fields.

### Document Structure
```python
{
    "id": "68852",
    "typ": "Dokument",
    "dokumentart": "Drucksache",
    "drucksachetyp": "Antrag",
    "dokumentnummer": "19/1",
    "wahlperiode": 19,
    "herausgeber": "BT",
    "datum": "2017-10-24",
    "titel": "Weitergeltung von Geschäftsordnungsrecht",
    "urheber": [{"bezeichnung": "CDU/CSU", "titel": "Fraktion der CDU/CSU"}],
    "fundstelle": {
        "dokumentnummer": "19/1",
        "pdf_url": "https://dserver.bundestag.de/btd/19/000/1900001.pdf"
    }
}
```

### Person Structure
```python
{
    "id": "1728",
    "vorname": "Ursula",
    "nachname": "Leyen",
    "namenszusatz": "von der",
    "titel": "Dr.  Ursula von der Leyen, Bundesmin., Bundesministerium der Verteidigung",
    "wahlperiode": [17, 18, 19],
    "person_roles": [{
        "funktion": "LMin Soz u. Frauen",
        "nachname": "Leyen",
        "vorname": "Ursula"
    }]
}
```

Note that IDs are delivered as strings in the raw JSON. With `return_format="object"`,
all IDs are converted to integers.

## API Authentication

The package includes a public API key that's valid until May 31, 2027. The key is sent in the
HTTP `Authorization` header, so it does not appear in URLs, logs or error messages. For production use or higher rate limits, request your personal API key from [parlamentsdokumentation@bundestag.de](mailto:parlamentsdokumentation@bundestag.de).

```python
# Using personal API key
bt = bundestag_api.btaConnection(apikey="your_api_key_here")
```

## Best Practices for Data Scientists

### 1. Start Small
```python
# Test with small datasets first
test_data = bt.search_document(limit=10)
print(f"Retrieved {len(test_data)} documents")
```

### 2. Use Appropriate Limits
```python
# Default limit is 100, increase for larger analyses
large_dataset = bt.search_document(limit=1000)
```

### 3. Handle Errors Gracefully
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bundestag_api")

# The package will log warnings and errors automatically
```

### 4. Combine with Data Analysis Libraries
```python
import pandas as pd
import numpy as np
from collections import Counter

# Get data as pandas DataFrame
df = bt.search_document(return_format="pandas", limit=500)

# Analyze document types
doc_types = Counter(df['drucksachetyp'])
print(doc_types.most_common(5))

# Time series analysis
df['datum'] = pd.to_datetime(df['datum'])
monthly_counts = df.groupby(df['datum'].dt.to_period('M')).size()
```

## Complete API Reference

### Search Functions
- `search_document(**filters)` - Find documents
- `search_procedure(**filters)` - Find legislative procedures  
- `search_activity(**filters)` - Find parliamentary activities
- `search_person(**filters)` - Find parliamentarians
- `search_plenaryprotocol(**filters)` - Find session protocols
- `search_procedureposition(**filters)` - Find procedure steps

### Speech Functions
- `get_speeches(btid, level="speech", **options)` - Speeches of specific plenary protocols
- `search_speeches(max_protocols=10, **filters)` - Speeches of protocols matching the filters
- `parse_protocol(btid)` - Download and parse a protocol into speeches, segments and comments
- `bundestag_api.parse_protocol_xml(path_or_xml)` - Parse a local XML protocol file

### Decision Functions
- `get_decisions(procedure_id, **options)` - Decisions of specific procedures
- `search_decisions(limit=100, voting_method=None, **filters)` - Decisions in procedure steps matching the filters
- `bundestag_api.flatten_decisions(positions)` - Turn procedure positions you already have into decision rows

### Get Functions (by ID)
- `get_document(btid, **options)` - Get specific documents
- `get_procedure(btid, **options)` - Get specific procedures
- `get_activity(btid, **options)` - Get specific activities  
- `get_person(btid, **options)` - Get specific persons
- `get_plenaryprotocol(btid, **options)` - Get specific protocols
- `get_procedureposition(btid, **options)` - Get specific procedure steps

## Common Issues & Solutions

**Memory issues with large datasets?**
- Use smaller `limit` values and process in chunks
- Filter by `legislative_period` or date range to reduce the result size

**Getting empty results?**
- Check date formats (YYYY-MM-DD)
- Verify institution codes (BT, BR, BV, EK)
- Start with broader searches, then add filters

**Need full document text?**
- Set `fulltext=True` for documents and protocols
- Note: Full text significantly increases response size

## Contributing

Contributions are welcome! Please check the [GitHub repository](https://github.com/jschibberges/Bundestag-API) for current issues and development guidelines.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/jschibberges/Bundestag-API/issues)
- Official API Documentation: [Bundestag.de API](https://dip.bundestag.de/über-dip/hilfe/api)
- Email for API keys: [parlamentsdokumentation@bundestag.de](mailto:parlamentsdokumentation@bundestag.de)

---

*Made for data scientists who want to analyze German parliamentary data without the complexity of raw API calls.*