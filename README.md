# Bundestag API

[![Upload Python Package](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jschibberges/Bundestag-API/actions/workflows/python-publish.yml)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

A beginner-friendly Python wrapper for accessing German Federal Parliament (Bundestag) data. This package simplifies querying parliamentary documents, procedures, plenary protocols, and member information through the official Bundestag API.

Perfect for data scientists, researchers, and political analysts who want to analyze German parliamentary data without dealing with complex API calls.

## What You Can Do

- **Analyze Parliamentary Documents**: Access bills, reports, and official documents
- **Track Legislative Processes**: Follow how laws move through parliament
- **Study Voting Patterns**: Examine plenary protocols and activities
- **Research Politicians**: Get information about current and former members of parliament
- **Time Series Analysis**: Filter data by date ranges for trend analysis

## Quick Start

### Installation

```bash
pip install bundestag_api
```

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
| **Activities** (`aktivitaet`) | Parliamentary actions | Voting behavior analysis |
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
# Find procedures by topic
procedures = bt.search_procedure(
    descriptor=["Climate", "Energy"],  # AND search
    limit=50
)

# Get detailed procedure information
procedure_details = bt.get_procedure(btid=12345)
```

### 3. Analyzing Parliamentary Speeches

```python
# Get plenary protocols with full text
protocols = bt.search_plenaryprotocol(
    date_start="2024-01-01",
    fulltext=True,
    limit=10
)
```

### 4. Member Analysis

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
    date_start="2024-01-01",      # Start date (YYYY-MM-DD)
    date_end="2024-12-31",        # End date (YYYY-MM-DD)  
    institution="BT",             # BT=Bundestag, BR=Bundesrat
    drucksache_type="Antrag",     # Specific 'Drucksache' types
    title=["Climate", "Energy"],  # Keywords in title (OR search)
    limit=100                     # Maximum results
)
```

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

### Document Structure
```python
{
    "id": 264030,
    "titel": "Climate Protection Act Amendment",
    "drucksachetyp": "Gesetzentwurf",
    "datum": "2024-01-15",
    "urheber": ["Federal Government"],
    "fundstelle": {
        "pdf_url": "https://...",
        "dokumentnummer": "20/1234"
    }
}
```

### Person Structure
```python
{
    "id": 12345,
    "vorname": "Angela",
    "nachname": "Merkel", 
    "titel": "Dr.",
    "person_roles": [{
        "funktion": "MdB",
        "fraktion": "CDU/CSU"
    }]
}
```

## API Authentication

The package includes a public API key that's valid until May 31, 2026. For production use or higher rate limits, request your personal API key from [parlamentsdokumentation@bundestag.de](mailto:parlamentsdokumentation@bundestag.de).

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
- Use `return_format="pandas"` for better memory efficiency

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