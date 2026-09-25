# -*- coding: utf-8 -*-
"""
Python wrapper for the official Bundestag API
"""

from ._version import __version__
from .bta_wrapper import btaConnection
from .models import Person, Role, Drucksache, Aktivitaet, Vorgang, Vorgangsposition, Plenarprotokoll
from .speeches import ParsedProtocol, parse_protocol_xml, split_comment
from .decisions import flatten_decisions
from . import vocabulary
from .vocabulary import VOTING_METHODS, legislative_period_for, legislative_period_dates
from .sync import SyncResult
