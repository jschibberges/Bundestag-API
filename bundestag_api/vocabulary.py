# -*- coding: utf-8 -*-
"""Controlled vocabularies of the DIP API and the German Bundestag.

The values below are either defined as enums in the DIP OpenAPI specification
(v1.5) or are fixed historical facts (legislative periods). They can be used
for autocompletion, validation and lookups::

    >>> from bundestag_api import vocabulary as voc
    >>> voc.INSTITUTIONS["BR"]
    'Bundesrat'
    >>> voc.legislative_period_for("2019-05-01")
    19

Open-ended vocabularies such as subject areas ("Sachgebiete"), document types
("Drucksachetypen"), procedure types or consultation states change over time and
are not part of the specification. Use ``btaConnection.discover_values()`` to
see which values actually occur in the data.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional, Tuple, Union

# Zuordnung: institution a document or procedure step belongs to (f.zuordnung / institution=...)
INSTITUTIONS: Dict[str, str] = {
    "BT": "Bundestag",
    "BR": "Bundesrat",
    "BV": "Bundesversammlung",
    "EK": "Europakammer des Bundesrates",
}

# Dokumentart of linked documents (document_art=...)
DOCUMENT_ARTS = ("Drucksache", "Plenarprotokoll")

# Bundesland, used for members of the Bundesrat
FEDERAL_STATES = (
    "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg",
    "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen",
    "Rheinland-Pfalz", "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein",
    "Thüringen",
)

# Beschlussfassung.abstimmungsart (voting_method=... in get_decisions/search_decisions)
VOTING_METHODS = (
    "Abstimmung durch Aufruf der Länder",
    "Geheime Wahl",
    "Hammelsprung",
    "Namentliche Abstimmung",
    "Verhältniswahl",
)

# Beschlussfassung.mehrheit: qualified majorities
MAJORITIES = ("Absolute Mehrheit", "Zweidrittelmehrheit")

# Deskriptor.typ: categories of the parliamentary thesaurus (ANTHES/PARTHES)
DESCRIPTOR_TYPES = (
    "Freier Deskriptor", "Geograph. Begriffe", "Institutionen", "Personen",
    "Rechtsmaterialien", "Sachbegriffe",
)

# Quadrant: each page of a plenary protocol is divided into four parts A-D
QUADRANTS = ("A", "B", "C", "D")

# Legislative periods (Wahlperioden) of the German Bundestag:
# from the constituent session to the day before the next constituent session.
# The end of the current period is None.
LEGISLATIVE_PERIODS: Dict[int, Tuple[date, Optional[date]]] = {
    1: (date(1949, 9, 7), date(1953, 10, 5)),
    2: (date(1953, 10, 6), date(1957, 10, 14)),
    3: (date(1957, 10, 15), date(1961, 10, 16)),
    4: (date(1961, 10, 17), date(1965, 10, 18)),
    5: (date(1965, 10, 19), date(1969, 10, 19)),
    6: (date(1969, 10, 20), date(1972, 12, 12)),
    7: (date(1972, 12, 13), date(1976, 12, 13)),
    8: (date(1976, 12, 14), date(1980, 11, 3)),
    9: (date(1980, 11, 4), date(1983, 3, 28)),
    10: (date(1983, 3, 29), date(1987, 2, 17)),
    11: (date(1987, 2, 18), date(1990, 12, 19)),
    12: (date(1990, 12, 20), date(1994, 11, 9)),
    13: (date(1994, 11, 10), date(1998, 10, 25)),
    14: (date(1998, 10, 26), date(2002, 10, 16)),
    15: (date(2002, 10, 17), date(2005, 10, 17)),
    16: (date(2005, 10, 18), date(2009, 10, 26)),
    17: (date(2009, 10, 27), date(2013, 10, 21)),
    18: (date(2013, 10, 22), date(2017, 10, 23)),
    19: (date(2017, 10, 24), date(2021, 10, 25)),
    20: (date(2021, 10, 26), date(2025, 3, 24)),
    21: (date(2025, 3, 25), None),
}

CURRENT_LEGISLATIVE_PERIOD = max(LEGISLATIVE_PERIODS)

# First legislative period with structured XML plenary protocols (see get_speeches)
FIRST_PERIOD_WITH_XML_PROTOCOLS = 18


def _to_date(value: Union[str, date, datetime]) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Expected a date in the format YYYY-MM-DD, got '{value}'.") from None
    raise ValueError("Expected a 'YYYY-MM-DD' string or a date/datetime object.")


def legislative_period_for(day: Union[str, date, datetime]) -> Optional[int]:
    """Return the legislative period (Wahlperiode) in which a given day falls.

    Returns None for days before the first Bundestag met (7 September 1949).
    """
    d = _to_date(day)
    for period, (start, end) in LEGISLATIVE_PERIODS.items():
        if start <= d and (end is None or d <= end):
            return period
    return None


def legislative_period_dates(period: int) -> Tuple[str, Optional[str]]:
    """Return start and end date ("YYYY-MM-DD") of a legislative period.

    The end of the current period is None. The result can be passed directly
    as ``date_start``/``date_end``::

        start, end = legislative_period_dates(19)
        bt.search_document(date_start=start, date_end=end)
    """
    if period not in LEGISLATIVE_PERIODS:
        raise ValueError(
            f"Unknown legislative period {period}. Known: 1-{CURRENT_LEGISLATIVE_PERIOD}."
        )
    start, end = LEGISLATIVE_PERIODS[period]
    return start.isoformat(), end.isoformat() if end else None
