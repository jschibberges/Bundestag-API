# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import logging
import time
import random
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union, Literal, cast
from ._version import __version__
from .models import Person, Aktivitaet, Vorgang, Vorgangsposition, Drucksache, Plenarprotokoll
from .utils import to_iso8601, to_date_string
from .speeches import ParsedProtocol, parse_protocol_xml
from .decisions import flatten_decisions
from .vocabulary import DOCUMENT_ARTS, INSTITUTIONS, VOTING_METHODS

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger("bundestag_api")
logger.addHandler(logging.NullHandler())

ReturnFormat = Literal["json", "object", "pandas"]
SpeechLevel = Literal["speech", "segment", "comment"]
Institution = Literal["BT", "BR", "BV", "EK"]
Resource = Literal["aktivitaet", "drucksache", "drucksache-text", "person", 
                   "plenarprotokoll", "plenarprotokoll-text", "vorgang", 
                   "vorgangsposition"]

# Maps the wrapper's parameter names to the DIP API filter names.
FILTER_PARAMS = {
    "fid": "f.id",
    "date_start": "f.datum.start",
    "date_end": "f.datum.end",
    "updated_since": "f.aktualisiert.start",
    "updated_until": "f.aktualisiert.end",
    "drucksacheID": "f.drucksache",
    "plenaryprotocolID": "f.plenarprotokoll",
    "processID": "f.vorgang",
    "institution": "f.zuordnung",
    "descriptor": "f.deskriptor",
    "sachgebiet": "f.sachgebiet",
    "drucksache_type": "f.drucksachetyp",
    "process_type": "f.vorgangstyp",
    "process_type_notation": "f.vorgangstyp_notation",
    "title": "f.titel",
    "activityID": "f.aktivitaet",
    "legislative_period": "f.wahlperiode",
    "person_name": "f.person",
    "personID": "f.person_id",
    "document_number": "f.dokumentnummer",
    "document_art": "f.dokumentart",
    "question_number": "f.frage_nummer",
    "gesta_id": "f.gesta",
    "procedure_positionID": "f.vorgangsposition_id",
    "consultation_status": "f.beratungsstand",
    "publication_reference": "f.verkuendung_fundstelle",
    "initiative": "f.initiative",
    "lead_department": "f.ressort_fdf",
    "originator": "f.urheber",
}

# Filters accepted by each endpoint, taken from the DIP OpenAPI specification (v1.5).
_COMMON_FILTERS = {"f.id", "f.datum.start", "f.datum.end", "f.aktualisiert.start",
                   "f.aktualisiert.end", "f.wahlperiode"}
_DRUCKSACHE_FILTERS = _COMMON_FILTERS | {
    "f.dokumentnummer", "f.drucksachetyp", "f.ressort_fdf", "f.titel", "f.urheber",
    "f.vorgangstyp", "f.vorgangstyp_notation", "f.zuordnung"}
_PLENARPROTOKOLL_FILTERS = _COMMON_FILTERS | {
    "f.dokumentnummer", "f.vorgangstyp", "f.vorgangstyp_notation", "f.zuordnung"}
SUPPORTED_FILTERS = {
    "vorgang": _COMMON_FILTERS | {
        "f.beratungsstand", "f.deskriptor", "f.dokumentart", "f.dokumentnummer",
        "f.drucksache", "f.drucksachetyp", "f.frage_nummer", "f.gesta", "f.initiative",
        "f.kom", "f.plenarprotokoll", "f.ratsdok", "f.ressort_fdf", "f.sachgebiet",
        "f.titel", "f.urheber", "f.verkuendung_fundstelle", "f.vorgangstyp",
        "f.vorgangstyp_notation"},
    "vorgangsposition": _COMMON_FILTERS | {
        "f.aktivitaet", "f.dokumentart", "f.dokumentnummer", "f.drucksache",
        "f.drucksachetyp", "f.frage_nummer", "f.kom", "f.plenarprotokoll", "f.ratsdok",
        "f.ressort_fdf", "f.titel", "f.urheber", "f.vorgang", "f.vorgangstyp",
        "f.vorgangstyp_notation", "f.zuordnung"},
    "drucksache": _DRUCKSACHE_FILTERS,
    "drucksache-text": _DRUCKSACHE_FILTERS,
    "plenarprotokoll": _PLENARPROTOKOLL_FILTERS,
    "plenarprotokoll-text": _PLENARPROTOKOLL_FILTERS,
    "aktivitaet": _COMMON_FILTERS | {
        "f.deskriptor", "f.dokumentart", "f.dokumentnummer", "f.drucksache",
        "f.drucksachetyp", "f.frage_nummer", "f.kom", "f.person", "f.person_id",
        "f.plenarprotokoll", "f.ratsdok", "f.sachgebiet", "f.urheber",
        "f.vorgangsposition_id", "f.vorgangstyp", "f.vorgangstyp_notation", "f.zuordnung"},
    "person": _COMMON_FILTERS | {"f.person"},
}

class btaConnection:
    """This class handles the API authentication and provides search functionality

    Methods
    -------
    query(...)
        A general search function for the official Bundestag API. See method docstring for all parameters.
    search_procedure(...)
        Searches procedures ('vorgang').
    search_procedureposition(...)
        Searches procedure positions ('vorgangsposition').
    search_document(...)
        Searches documents ('drucksache').
    search_person(...)
        Searches persons ('person').
    search_plenaryprotocol(...)
        Searches plenary protocols ('plenarprotokoll').
    search_activity(...)
        Searches activities ('aktivitaet').
    get_activity(...)
        Retrieves activities by ID.
    get_procedure(...)
        Retrieves procedures by ID.
    get_procedureposition(...)
        Retrieves procedure positions by ID.
    get_document(...)
        Retrieves documents by ID.
    get_person(...)
        Retrieves persons by ID.
    get_plenaryprotocol(...)
        Retrieves plenary protocols by ID.
    """

    def __init__(self, apikey=None, delay: float = 0.0, session: Optional[requests.Session] = None):
        GEN_APIKEY = "R2BZaee.DjdCyihKZMf8AOjtScubP2EVydegzjmBIQ"

        DATE_GEN_APIKEY = "31.05.2027"
        date_expiry = datetime.strptime(DATE_GEN_APIKEY, "%d.%m.%Y")

        today = datetime.now()
        if apikey is None and date_expiry.date() < today.date():
            raise ValueError("The general API key has expired. Please provide your own API key via btaConnection(apikey='your_key').")
        elif apikey is None and date_expiry.date() >= today.date():
            self.apikey = GEN_APIKEY
            logger.warning(
                "Using shared generic API key. This key is potentially used by many users. "
                "The API allows max 25 concurrent requests. When using parallel processing "
                "(ThreadPoolExecutor, multiprocessing, etc.), limit workers to avoid triggering "
                "bot protection. For better performance, get a personal API key at "
                "https://dip.bundestag.de/"
            )
        elif apikey is not None:
            if not isinstance(apikey, str):
                raise ValueError("API key needs to be a string.")
            elif len(apikey.strip()) < 16:  # minimal guard against obviously wrong keys
                raise ValueError("apikey looks malformed (too short).")
            else:
                self.apikey = apikey
                logger.info("Using personal API key. API allows max 25 concurrent requests.")
        if not isinstance(delay, (int, float)) or delay < 0:
            raise ValueError("delay must be a non-negative number of seconds.")
        self.delay = float(delay)
        if session is not None:
            if not isinstance(session, requests.Session):
                raise ValueError("session must be a requests.Session instance (or subclass).")
            self._apply_session_headers(session)
            self.session = session
        else:
            self.session = self._build_session()


    def _masked_apikey(self) -> str:
        return f"{self.apikey[:4]}...{self.apikey[-2:]}"

    def __str__(self):
        return "API key: " + self._masked_apikey()

    def __repr__(self):
        return f"btaConnection(apikey='{self._masked_apikey()}')"

    def _apply_session_headers(self, s: requests.Session) -> None:
        """Apply the standard request headers to a session."""
        s.headers.update({
            'User-Agent': f'bundestag_api/{__version__}',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        })

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        retry = Retry(
            total=3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(['GET']),
            backoff_factor=1.0,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount('https://', adapter)
        s.mount('http://', adapter)
        self._apply_session_headers(s)
        return s

    def _validate_str_list_param(self, param_value: Optional[Union[str, List[str]]], param_name: str) -> Optional[List[str]]:
        """Helper to validate parameters that can be a string or a list of strings."""
        if param_value is None:
            return None
        if isinstance(param_value, str):
            param_value = [param_value]
        if not isinstance(param_value, list):
            raise ValueError(f"{param_name} must be a string or a list of strings.")
        if not all(isinstance(item, str) for item in param_value):
            raise ValueError(f"All items in {param_name} must be strings.")
        if not all(len(item) < 100 for item in param_value):
            raise ValueError(f"Strings in {param_name} must be under 100 characters.")
        return param_value

    def _validate_int_list_param(self, param_value: Optional[Union[int, List[int]]], param_name: str) -> Optional[List[int]]:
        """Helper to validate parameters that can be an integer or a list of integers."""
        if param_value is None:
            return None
        if isinstance(param_value, int):
            param_value = [param_value]
        if not isinstance(param_value, list):
            raise ValueError(f"{param_name} must be an integer or a list of integers.")
        if not all(isinstance(item, int) for item in param_value):
            # Check for floats explicitly to avoid silent truncation
            if any(isinstance(item, float) for item in param_value):
                raise ValueError(f"All items in {param_name} must be convertible to integers. Floats are not allowed to prevent data loss.")
            try:
                # Attempt to convert all items to int (e.g., string integers like "123")
                return [int(item) for item in param_value]
            except (ValueError, TypeError) as e:
                raise ValueError(f"All items in {param_name} must be convertible to integers.") from e
        return param_value

    def _validate_basic_params(self, resource: Resource, return_format: str, limit: int,
                              institution: Optional[str], fulltext: bool) -> Resource:
        """Validate basic query parameters and adjust resource for fulltext if needed."""
        # Validate resource
        if resource not in Resource.__args__:
            raise ValueError("No or wrong resource")

        # Validate return format
        if return_format not in ["json", "object", "pandas"]:
            raise ValueError("return_format: Not a correct format!")

        # Validate institution
        if institution is not None and institution not in INSTITUTIONS:
            raise ValueError("Unknown institution. Use one of: "
                             + ", ".join(f"{k} ({v})" for k, v in INSTITUTIONS.items()))

        # Validate limit
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be an integer larger than zero")

        # Handle fulltext resource routing
        if fulltext:
            if resource in ("drucksache", "plenarprotokoll"):
                resource = cast(Resource, resource + "-text")
            elif resource not in ("drucksache-text", "plenarprotokoll-text"):
                raise ValueError("fulltext is only supported for 'drucksache' and 'plenarprotokoll'")

        return resource

    def _validate_reference_ids(self, resource: Resource, drucksacheID: Optional[int],
                                plenaryprotocolID: Optional[int], processID: Optional[int],
                                activityID: Optional[int]) -> dict:
        """Validate reference ID parameters (drucksacheID, plenaryprotocolID, etc.)"""

        # Check mutual exclusivity
        non_none_count = sum(arg is not None for arg in [
            plenaryprotocolID, drucksacheID, processID, activityID
        ])
        if non_none_count > 1:
            raise ValueError(
                "Can't select more than one of drucksacheID, plenaryprotocolID, processID, and activityID"
            )

        # Validate drucksacheID and plenaryprotocolID
        if resource not in ["aktivitaet", "vorgang", "vorgangsposition"]:
            if drucksacheID is not None:
                raise ValueError(
                    "drucksacheID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'"
                )
            if plenaryprotocolID is not None:
                raise ValueError(
                    "plenaryprotocolID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'"
                )
        else:
            if drucksacheID is not None and not isinstance(drucksacheID, int):
                raise ValueError("drucksacheID must be an integer")
            if plenaryprotocolID is not None and not isinstance(plenaryprotocolID, int):
                raise ValueError("plenaryprotocolID must be an integer")

        # Validate processID
        if resource != "vorgangsposition":
            if processID is not None:
                raise ValueError("processID must be combined with resource 'vorgangsposition'")
        else:
            if processID is not None and not isinstance(processID, int):
                raise ValueError("processID must be an integer")

        # Validate activityID
        if activityID is not None:
            if resource != "vorgangsposition":
                raise ValueError("activityID must be combined with resource 'vorgangsposition'")
            if not isinstance(activityID, int):
                raise ValueError("activityID must be an integer")

        return {
            'drucksacheID': drucksacheID,
            'plenaryprotocolID': plenaryprotocolID,
            'processID': processID,
            'activityID': activityID
        }

    def _validate_resource_specific_params(self, resource: Resource, params: dict):
        """Validate that parameters are only used with compatible resources.

        Uses the SUPPORTED_FILTERS table derived from the OpenAPI specification.
        Raises ValueError if a parameter is used with an incompatible resource,
        so that filters are never silently dropped or ignored by the API.
        """
        supported = SUPPORTED_FILTERS[resource]
        for param_name, value in params.items():
            if value is None:
                continue
            api_filter = FILTER_PARAMS.get(param_name)
            if api_filter is None or api_filter in supported:
                continue
            allowed = sorted(r for r, filters in SUPPORTED_FILTERS.items() if api_filter in filters)
            raise ValueError(
                f"{param_name} can only be used with resource "
                + ", ".join(f"'{r}'" for r in allowed)
                + f" (not with '{resource}')"
            )

    def _validate_and_normalize_params(self, resource: Resource, **params) -> dict:
        """Validate all filter parameters and normalize them to correct types.

        Returns a dictionary of validated parameters ready for API payload.
        """
        validated = {}

        # Validate ID parameters
        validated['fid'] = self._validate_int_list_param(params.get('fid'), "fid")

        # Validate datetime parameters
        validated['updated_since'] = to_iso8601(params.get('updated_since')) if params.get('updated_since') else None
        validated['updated_until'] = to_iso8601(params.get('updated_until')) if params.get('updated_until') else None

        # Validate list parameters
        validated['descriptor'] = self._validate_str_list_param(params.get('descriptor'), "descriptor")
        validated['sachgebiet'] = self._validate_str_list_param(params.get('sachgebiet'), "sachgebiet")
        validated['legislative_period'] = self._validate_int_list_param(params.get('legislative_period'), "legislative_period")
        validated['person_name'] = self._validate_str_list_param(params.get('person_name'), "person_name")
        validated['personID'] = self._validate_int_list_param(params.get('personID'), "personID")
        validated['document_number'] = self._validate_str_list_param(params.get('document_number'), "document_number")
        validated['question_number'] = self._validate_str_list_param(params.get('question_number'), "question_number")
        validated['gesta_id'] = self._validate_str_list_param(params.get('gesta_id'), "gesta_id")
        validated['procedure_positionID'] = self._validate_int_list_param(params.get('procedure_positionID'), "procedure_positionID")
        validated['consultation_status'] = self._validate_str_list_param(params.get('consultation_status'), "consultation_status")
        validated['publication_reference'] = self._validate_str_list_param(params.get('publication_reference'), "publication_reference")
        validated['initiative'] = self._validate_str_list_param(params.get('initiative'), "initiative")
        validated['lead_department'] = self._validate_str_list_param(params.get('lead_department'), "lead_department")
        validated['originator'] = self._validate_str_list_param(params.get('originator'), "originator")

        validated['title'] = self._validate_str_list_param(params.get('title'), "title")
        validated['process_type'] = self._validate_str_list_param(params.get('process_type'), "process_type")
        validated['process_type_notation'] = self._validate_int_list_param(params.get('process_type_notation'), "process_type_notation")

        drucksache_type = params.get('drucksache_type')
        if drucksache_type is not None and not isinstance(drucksache_type, str):
            raise ValueError("drucksache_type must be a string.")
        validated['drucksache_type'] = drucksache_type

        # Validate reference ID parameters and their resource compatibility
        validated.update(self._validate_reference_ids(
            resource=resource,
            drucksacheID=params.get('drucksacheID'),
            plenaryprotocolID=params.get('plenaryprotocolID'),
            processID=params.get('processID'),
            activityID=params.get('activityID')
        ))

        # Add simple passthrough params (before resource-specific validation)
        validated['date_start'] = to_date_string(params.get('date_start'), "date_start")
        validated['date_end'] = to_date_string(params.get('date_end'), "date_end")
        validated['institution'] = params.get('institution')
        validated['document_art'] = params.get('document_art')

        # Validate document_art value
        if validated['document_art'] is not None and validated['document_art'] not in DOCUMENT_ARTS:
            raise ValueError("document_art must be either 'Drucksache' or 'Plenarprotokoll'")

        # Validate resource-specific parameters
        self._validate_resource_specific_params(resource, validated)

        return validated

    def _build_api_payload(self, validated_params: dict) -> dict:
        """Build the API request payload from validated parameters."""
        # The API key is sent in the Authorization header (see _execute_paginated_query),
        # so it never shows up in URLs, logs or exception messages.
        payload: Dict[str, Any] = {"format": "json"}
        for param_name, api_filter in FILTER_PARAMS.items():
            payload[api_filter] = validated_params.get(param_name)
        payload["cursor"] = None
        return payload

    def _execute_paginated_query(self, resource: Resource, payload: dict, limit: int) -> List[dict]:
        """Execute the API query with automatic pagination."""
        BASE_URL = "https://search.dip.bundestag.de/api/v1/"
        r_url = BASE_URL + resource

        data = []
        continue_pagination = True

        while continue_pagination:
            r = self.session.get(r_url, params=payload, timeout=30,
                                 headers={"Authorization": f"ApiKey {self.apikey}"})
            logger.debug(r.url)

            if r.status_code == requests.codes.ok:
                content = r.json()
                documents_on_page = content.get("documents", [])

                if content.get("numFound", 0) == 0:
                    logger.info("No data was returned.")
                    continue_pagination = False
                else:
                    data.extend(documents_on_page)
                    next_cursor = content.get("cursor")

                    # Stop paginating if limit reached or no more pages
                    if len(data) >= limit:
                        data = data[0:limit]
                        continue_pagination = False
                    elif not next_cursor or payload["cursor"] == next_cursor:
                        continue_pagination = False
                    else:
                        payload["cursor"] = next_cursor
                        time.sleep(self.delay * random.uniform(0.8, 1.2) if self.delay > 0 else 0.0)

            elif r.status_code in (400, 403):
                try:
                    body = r.text.lower()
                except Exception:
                    body = ""
                bot_signals = (
                    '.enodia' in r.url
                    or '/challenge' in r.url
                    or any(kw in body for kw in ('enodia', 'captcha', 'bot protection', 'access denied'))
                )
                if bot_signals or r.status_code == 403:
                    msg = (
                        "Bot protection detected (Enodia challenge). The Bundestag API blocked this request.\n"
                        "Possible causes:\n"
                        "  • Too many parallel requests (API limit: 25 concurrent)\n"
                        "  • Too many requests per second (no delay between paginated calls)\n"
                        "  • Shared generic API key is being used by many scripts simultaneously\n"
                        "Solutions:\n"
                        "  1. Add a delay: btaConnection(delay=0.5)\n"
                        "  2. Reduce parallel workers to ≤5 in ThreadPoolExecutor\n"
                        "  3. Use a personal API key: https://dip.bundestag.de/\n"
                    )
                    logger.error(msg)
                    raise ConnectionError(msg)
                else:
                    msg = f"A syntax error occurred. Code {r.status_code}: {r.reason}"
                    logger.error(msg)
                    raise ValueError(f"Bad request to Bundestag API: {r.reason}")

            elif r.status_code == 401:
                msg = f"An authorization error occurred. Likely an error with your API key. Code {r.status_code}: {r.reason}"
                logger.error(msg)
                raise ValueError(f"Authorization failed. Check your API key: {r.reason}")

            elif r.status_code == 404:
                msg = f"The API is not reachable. Code {r.status_code}: {r.reason}"
                logger.error(msg)
                raise ConnectionError(f"Bundestag API not reachable: {r.reason}")

            else:
                msg = f"An error occurred. Code {r.status_code}: {r.reason}"
                logger.error(msg)
                raise requests.HTTPError(f"HTTP {r.status_code}: {r.reason}")

        self._sanitize_pdf_urls(data)
        if len(data) == 0:
            logger.info("No data was returned.")

        return data

    def _format_results(self, data: List[dict], return_format: str, resource: Resource) -> Union[List[Any], pd.DataFrame]:
        """Format the query results according to the requested return format."""

        # Handle object format
        if return_format == "object":
            model_map = {
                "aktivitaet": Aktivitaet,
                "drucksache": Drucksache,
                "drucksache-text": Drucksache,
                "person": Person,
                "plenarprotokoll": Plenarprotokoll,
                "plenarprotokoll-text": Plenarprotokoll,
                "vorgang": Vorgang,
                "vorgangsposition": Vorgangsposition,
            }
            model_class = model_map.get(resource)
            if model_class:
                return [model_class(item) for item in data]

        # Handle pandas format
        if return_format == "pandas":
            try:
                import pandas as pd
            except ImportError as e:
                raise ImportError(
                    "return_format='pandas' requires pandas. Install it with "
                    "'pip install bundestag_api[pandas]' or 'conda install pandas'."
                ) from e
            return pd.json_normalize(data)

        # Default: return JSON (list of dicts)
        return data

    def query(self,
              resource: Resource,
              return_format: ReturnFormat ="json",
              limit: int = 100,
              fid: Optional[Union[int, List[int]]] = None,
              date_start: Optional[Union[str, date]] = None,
              date_end: Optional[Union[str, date]] = None,
              updated_since: Optional[Union[str, datetime]] = None,
              updated_until: Optional[Union[str, datetime]] = None,
              institution: Optional[Institution] = None,
              drucksacheID: Optional[int] = None,
              plenaryprotocolID: Optional[int] = None,
              processID: Optional[int] = None,
              descriptor: Optional[Union[str, List[str]]] = None,
              sachgebiet: Optional[Union[str, List[str]]] = None,
              drucksache_type: Optional[str] = None,
              process_type: Optional[Union[str, List[str]]] = None,
              process_type_notation: Optional[Union[int, List[int]]] = None,
              title: Optional[Union[str, List[str]]] = None,
              activityID: Optional[int] = None,
              legislative_period: Optional[Union[int, List[int]]] = None,
              person_name: Optional[Union[str, List[str]]] = None,
              personID: Optional[Union[int, List[int]]] = None,
              document_number: Optional[Union[str, List[str]]] = None,
              document_art: Optional[Literal["Drucksache", "Plenarprotokoll"]] = None,
              question_number: Optional[Union[str, List[str]]] = None,
              gesta_id: Optional[Union[str, List[str]]] = None,
              procedure_positionID: Optional[Union[int, List[int]]] = None,
              consultation_status: Optional[Union[str, List[str]]] = None,
              publication_reference: Optional[Union[str, List[str]]] = None,
              initiative: Optional[Union[str, List[str]]] = None,
              lead_department: Optional[Union[str, List[str]]] = None,
              originator: Optional[Union[str, List[str]]] = None,
              fulltext: bool = False
              ) -> Union[List[Any], pd.DataFrame]:
        """A general search function for the official Bundestag API

        Parameters
            ----------
            resource: str
                The resource type to be queried. options are aktivitaet,
                drucksache, drucksache-text, person, plenarprotokoll,
                plenarprotokoll-text, vorgang or vorgangsposition
            return_format: str, optional
                Return format of the data. Defaults to "json" (list of dicts).
                "object" returns model class instances, "pandas" returns a
                DataFrame (requires pandas).
            limit: int, optional
                Number of maximal results to be returned. Defaults to 100
            fid: int/list, optional
                ID of an entity. Can be a list to retrieve more than one entity
            date_start: str/date, optional
                Earliest document date (inclusive). String "YYYY-MM-DD" or a
                datetime.date / datetime.datetime object
            date_end: str/date, optional
                Latest document date (inclusive). String "YYYY-MM-DD" or a
                datetime.date / datetime.datetime object
            updated_since: str, optional
                Date and time after which updated documents are to be retrieved
            updated_until: str, optional
                Date and time until which updated documents are to be retrieved
            institution: str, optional
                Filter results by institution BT, BR, BV or EK
            drucksacheID: int, optional
                Entity ID of a 'Drucksache'. Can be used to select activities,
                procedures and procedure positions that are connected to the
                'Drucksache'.
            plenaryprotocolID: int, optional
                Entity ID of a plenary protocol. Can be used to select activities,
                procedures and procedure positions that are connected to the
                protocol
            processID: int, optional
                Entity ID of a process. Can be used to select procedure positions
                that are connected to the process
            descriptor: str/list, optional
                Keyword that is connected to the entities. Multiple strings can
                be supplied as a list but they will be joined via AND. An OR-
                search is not possible
            sachgebiet: str/list, optional
                Political field that is connected to the entities. Multiple 
                strings can be supplied as a list but they will be joined via
                AND. An OR-search is not possible
            drucksache_type: str, optional
                The type of 'Drucksache' (e.g. "Antrag", "Gesetzentwurf") to be returned.
            process_type: str, optional
                The type of process ("Gesetzgebung") to be returned.
            process_type_notation: int, optional
                The type of process (100) to be returned.
            title: str/list, optional
                Keyword that can be found in the title of documents. Multiple 
                strings can be supplied as a list and will be joined via
                an OR-search.
            activityID: int, optional
                Entity ID of an activity. Can be used to select procedure positions.
            legislative_period: int/list, optional
                Number of the legislative period.
            person_name: str/list, optional
                Name of a person.
            personID: int/list, optional
                ID of a person.
            document_number: str/list, optional
                Number of a document.
            document_art: str, optional
                The "art" of a document, e.g. 'Drucksache' or 'Plenarprotokoll'.
            question_number: str/list, optional
                Number of a question within a document.
            gesta_id: str/list, optional
                GESTA-Ordnungsnummer.
            procedure_positionID: int/list, optional
                ID of a procedure position.
            consultation_status: str/list, optional
                The status of the consultation/process.
            publication_reference: str/list, optional
                Reference to the publication (Fundstelle der Verkündung).
            initiative: str/list, optional
                Filter by the initiator of a process.
            lead_department: str/list, optional
                Filter by the lead department (Ressort federführend).
            originator: str/list, optional
                Filter by the originator (Urheber).
            fulltext: boolean
                Whether the fulltext (if available) should be requested or not. Default is False

        """

        # 1. Validate basic parameters
        resource = self._validate_basic_params(resource, return_format, limit, institution, fulltext)

        # 2. Validate and normalize all filter parameters
        validated_params = self._validate_and_normalize_params(
            resource=resource,
            fid=fid,
            date_start=date_start,
            date_end=date_end,
            updated_since=updated_since,
            updated_until=updated_until,
            institution=institution,
            drucksacheID=drucksacheID,
            plenaryprotocolID=plenaryprotocolID,
            processID=processID,
            descriptor=descriptor,
            sachgebiet=sachgebiet,
            drucksache_type=drucksache_type,
            process_type=process_type,
            process_type_notation=process_type_notation,
            title=title,
            activityID=activityID,
            legislative_period=legislative_period,
            person_name=person_name,
            personID=personID,
            document_number=document_number,
            document_art=document_art,
            question_number=question_number,
            gesta_id=gesta_id,
            procedure_positionID=procedure_positionID,
            consultation_status=consultation_status,
            publication_reference=publication_reference,
            initiative=initiative,
            lead_department=lead_department,
            originator=originator
        )

        # 3. Build API payload
        payload = self._build_api_payload(validated_params)

        # 4. Execute paginated query
        data = self._execute_paginated_query(resource, payload, limit)

        # 5. Format and return results
        return self._format_results(data, return_format, resource)

    # The following two methods are used to construct the specific search and get methods
    def _search(self, resource: Resource, **filters):
        """Generic search: forwards to .query(resource, **filters)."""
        return self.query(resource=resource, **filters)

    def _get(self, resource: Resource, btid: Union[int, List[int]], **filters):
        """Generic get: forwards to .query(resource, fid=btid, **filters)."""
        return self.query(resource=resource, fid=btid, **filters)

    def _sanitize_pdf_urls(self, node: Union[dict, List[Any]]) -> None:
        """
        Ensure fundstelle.pdf_url values are only returned when all components are present.

        The Bundestag API sometimes returns placeholder strings like 'null' when a PDF
        reference is incomplete. Those should surface as None for downstream consumers.
        """
        if isinstance(node, dict):
            fundstelle = node.get("fundstelle")
            if isinstance(fundstelle, dict):
                pdf_url = fundstelle.get("pdf_url")
                if self._should_clear_pdf_url(pdf_url):
                    fundstelle["pdf_url"] = None

            for value in node.values():
                if isinstance(value, (dict, list)):
                    self._sanitize_pdf_urls(value)

        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    self._sanitize_pdf_urls(item)

    @staticmethod
    def _should_clear_pdf_url(pdf_url: Any) -> bool:
        """Return True when a pdf_url contains placeholder markers instead of real values."""
        if not isinstance(pdf_url, str):
            return False

        stripped = pdf_url.strip()
        if not stripped:
            return True

        placeholders = {"null", "none", "undefined"}
        segments = [segment.lower() for segment in stripped.split("/") if segment]
        return any(segment in placeholders for segment in segments)

    # procedures
    def search_procedure(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches procedures specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'vorgang' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("vorgang", **filters)

    def get_procedure(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more procedures ('vorgang') by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the procedure(s) to retrieve.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("vorgang", btid, **filters)

    # procedure positions
    def search_procedureposition(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches procedure positions specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'vorgangsposition' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("vorgangsposition", **filters)

    def get_procedureposition(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more procedure positions ('vorgangsposition') by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the procedure position(s) to retrieve.
        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("vorgangsposition", btid, **filters)

    # documents
    def search_document(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches documents specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'drucksache' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("drucksache", **filters)

    def get_document(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more documents ('drucksache') by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the document(s) to retrieve.
        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("drucksache", btid, **filters)

    # persons
    def search_person(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches persons specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'person' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("person", **filters)

    def get_person(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more persons by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the person(s) to retrieve.
        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("person", btid, **filters)

    # plenary protocols
    def search_plenaryprotocol(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches plenary protocols specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'plenarprotokoll' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("plenarprotokoll", **filters)

    def get_plenaryprotocol(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more plenary protocols by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the plenary protocol(s) to retrieve.
        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("plenarprotokoll", btid, **filters)

    # activities
    def search_activity(self, **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Searches activities specified by the parameters
        
        This is a convenience wrapper around the main `query` method for the 'aktivitaet' resource.
        For a full list of available filters, see `btaConnection.query`.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._search("aktivitaet", **filters)

    def get_activity(self, btid: Union[int, List[int]], **filters) -> Union[List[Any], pd.DataFrame]:
        """
        Retrieves one or more activities by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The ID or IDs of the activity/activities to retrieve.

        Returns
        -------
        Union[List[Any], pd.DataFrame]
            A list of dictionaries or model objects, or a pandas DataFrame if `return_format="pandas"`.
        """
        return self._get("aktivitaet", btid, **filters)
    
    # speeches (structured XML plenary protocols)
    def _download_protocol_xml(self, xml_url: str) -> bytes:
        """Download a structured XML plenary protocol from the Bundestag document server."""
        if not isinstance(xml_url, str) or not xml_url.startswith("https://"):
            raise ValueError(f"Invalid XML URL: {xml_url!r}")
        # No Authorization header: the document server does not need the API key.
        r = self.session.get(xml_url, timeout=60, headers={"Accept": "application/xml"})
        logger.debug(xml_url)
        if r.status_code != requests.codes.ok:
            msg = f"Could not download {xml_url}. Code {r.status_code}: {r.reason}"
            logger.error(msg)
            raise requests.HTTPError(msg)
        return r.content

    def _protocol_record(self, protocol: Union[int, dict]) -> dict:
        """Return the DIP metadata of a plenary protocol given its ID or a search result."""
        if isinstance(protocol, dict):
            return protocol
        records = self.get_plenaryprotocol(protocol)
        if not records:
            raise ValueError(f"Plenary protocol with ID {protocol} not found.")
        return records[0]

    def parse_protocol(self, protocol: Union[int, dict]) -> ParsedProtocol:
        """
        Downloads and parses the structured XML version of a plenary protocol.

        Structured XML is available for Bundestag protocols from the 18th
        legislative period onwards (not for Bundesrat protocols).

        Parameters
        ----------
        protocol: int or dict
            The DIP ID of a plenary protocol ('plenarprotokoll'), or a protocol
            record as returned by `search_plenaryprotocol`.

        Returns
        -------
        ParsedProtocol
            Object with the attributes `metadata`, `speeches`, `segments` and
            `comments` (lists of dicts) and a `to_dataframes()` method.
        """
        record = self._protocol_record(protocol)
        xml_url = (record.get("fundstelle") or {}).get("xml_url")
        if not xml_url:
            raise ValueError(
                f"No structured XML available for plenary protocol "
                f"{record.get('dokumentnummer', record.get('id'))} ({record.get('herausgeber')}). "
                "XML protocols exist for the Bundestag from the 18th legislative period onwards."
            )
        content = self._download_protocol_xml(xml_url)
        return parse_protocol_xml(content, extra_metadata={
            "protocol_id": int(record["id"]),
            "document_number": record.get("dokumentnummer"),
        })

    @staticmethod
    def _collect_speech_rows(parsed: List[ParsedProtocol], level: str,
                             speaker: Optional[str], faction: Optional[str]) -> List[dict]:
        """Combine rows of the requested level and apply speaker/faction filters."""
        rows: List[dict] = []
        for protocol in parsed:
            speech_ids = None
            if speaker is not None or faction is not None:
                speech_ids = {
                    s["speech_id"] for s in protocol.speeches
                    if (speaker is None or speaker.lower() in (s["speaker_name"] or "").lower())
                    and (faction is None or faction.lower() in (s["faction"] or "").lower())
                }
            table = {"speech": protocol.speeches, "segment": protocol.segments,
                     "comment": protocol.comments}[level]
            rows.extend(r for r in table if speech_ids is None or r["speech_id"] in speech_ids)
        return rows

    @staticmethod
    def _validate_speech_args(level: str, return_format: str) -> None:
        if level not in ("speech", "segment", "comment"):
            raise ValueError("level must be 'speech', 'segment' or 'comment'.")
        if return_format not in ("json", "pandas"):
            raise ValueError("return_format must be 'json' or 'pandas' for speeches.")

    def _format_rows(self, rows: List[dict], return_format: str):
        """Return flat rows as list of dicts or pandas DataFrame."""
        if return_format == "pandas":
            try:
                import pandas as pd
            except ImportError as e:
                raise ImportError(
                    "return_format='pandas' requires pandas. Install it with "
                    "'pip install bundestag_api[pandas]' or 'conda install pandas'."
                ) from e
            return pd.DataFrame(rows)
        return rows

    def get_speeches(self,
                     btid: Union[int, List[int]],
                     level: SpeechLevel = "speech",
                     return_format: Literal["json", "pandas"] = "json",
                     speaker: Optional[str] = None,
                     faction: Optional[str] = None) -> Union[List[dict], pd.DataFrame]:
        """
        Retrieves the speeches of one or more plenary protocols by their ID(s).

        Parameters
        ----------
        btid: int or list of int
            The DIP ID or IDs of the plenary protocol(s).
        level: str, optional
            "speech" (default): one row per speech, text of the main speaker only.
            "segment": one row per passage of one speaker, including the presiding
            officer and interposed questions.
            "comment": one row per interjection (applause, heckling, laughter, ...).
        return_format: str, optional
            "json" (list of dicts, default) or "pandas" (DataFrame).
        speaker: str, optional
            Only speeches whose speaker name contains this string (case-insensitive).
        faction: str, optional
            Only speeches of speakers whose faction contains this string
            (case-insensitive), e.g. "SPD" or "GRÜNE".

        Returns
        -------
        Union[List[dict], pd.DataFrame]
        """
        self._validate_speech_args(level, return_format)
        ids = self._validate_int_list_param(btid, "btid") or []
        parsed = []
        for i, protocol_id in enumerate(ids):
            if i > 0 and self.delay > 0:
                time.sleep(self.delay * random.uniform(0.8, 1.2))
            parsed.append(self.parse_protocol(protocol_id))
        rows = self._collect_speech_rows(parsed, level, speaker, faction)
        return self._format_rows(rows, return_format)

    def search_speeches(self,
                        level: SpeechLevel = "speech",
                        return_format: Literal["json", "pandas"] = "json",
                        speaker: Optional[str] = None,
                        faction: Optional[str] = None,
                        max_protocols: int = 10,
                        **filters) -> Union[List[dict], pd.DataFrame]:
        """
        Searches plenary protocols and returns the speeches they contain.

        Protocols are selected with the same filters as `search_plenaryprotocol`
        (e.g. `date_start`, `date_end`, `legislative_period`, `document_number`).
        Only Bundestag protocols have structured XML, so `institution` defaults
        to "BT". Protocols without XML are skipped.

        Every protocol is a separate download of several megabytes, so the number
        of protocols is capped by `max_protocols` (default 10).

        Parameters
        ----------
        level, return_format, speaker, faction:
            See `get_speeches`.
        max_protocols: int, optional
            Maximum number of protocols to download. Defaults to 10.
        **filters:
            Filters passed to `search_plenaryprotocol`.

        Returns
        -------
        Union[List[dict], pd.DataFrame]
        """
        self._validate_speech_args(level, return_format)
        if "limit" in filters:
            raise ValueError("Use max_protocols instead of limit to cap the number of protocols.")
        if "return_format" in filters or "fulltext" in filters:
            raise ValueError("return_format and fulltext cannot be passed as protocol filters.")
        filters.setdefault("institution", "BT")
        records = self.search_plenaryprotocol(limit=max_protocols, **filters)
        parsed = []
        for record in records:
            if not (record.get("fundstelle") or {}).get("xml_url"):
                logger.info("Skipping plenary protocol %s: no structured XML available.",
                            record.get("dokumentnummer"))
                continue
            if parsed and self.delay > 0:
                time.sleep(self.delay * random.uniform(0.8, 1.2))
            parsed.append(self.parse_protocol(record))
        rows = self._collect_speech_rows(parsed, level, speaker, faction)
        return self._format_rows(rows, return_format)

    # decisions (Beschlussfassung)
    @staticmethod
    def _validate_decision_args(return_format: str, voting_method: Optional[str]) -> None:
        if return_format not in ("json", "pandas"):
            raise ValueError("return_format must be 'json' or 'pandas' for decisions.")
        if voting_method is not None and voting_method not in VOTING_METHODS:
            raise ValueError("voting_method must be one of: " + ", ".join(VOTING_METHODS))

    @staticmethod
    def _filter_decisions(rows: List[dict], voting_method: Optional[str]) -> List[dict]:
        if voting_method is None:
            return rows
        return [r for r in rows if r["voting_method"] == voting_method]

    def get_decisions(self,
                      procedure_id: Union[int, List[int]],
                      return_format: Literal["json", "pandas"] = "json",
                      voting_method: Optional[str] = None) -> Union[List[dict], pd.DataFrame]:
        """
        Retrieves all decisions ('Beschlussfassung') of one or more procedures.

        Collects the procedure positions of each procedure ('vorgang') and returns
        one row per decision, e.g. the adoption of a bill by the Bundestag or the
        consent of the Bundesrat.

        Note: `decision` refers to the document in `decided_document_number`.
        "Annahme der Beschlussempfehlung" can mean that a motion was rejected if
        the committee recommended rejection.

        Parameters
        ----------
        procedure_id: int or list of int
            The DIP ID or IDs of the procedure(s) ('vorgang').
        return_format: str, optional
            "json" (list of dicts, default) or "pandas" (DataFrame).
        voting_method: str, optional
            Only decisions with this voting method, e.g. "Namentliche Abstimmung"
            (recorded vote). See `bundestag_api.decisions.VOTING_METHODS`.

        Returns
        -------
        Union[List[dict], pd.DataFrame]
        """
        self._validate_decision_args(return_format, voting_method)
        ids = self._validate_int_list_param(procedure_id, "procedure_id") or []
        rows: List[dict] = []
        for i, pid in enumerate(ids):
            if i > 0 and self.delay > 0:
                time.sleep(self.delay * random.uniform(0.8, 1.2))
            positions = self.search_procedureposition(processID=pid, limit=1000)
            rows.extend(flatten_decisions(positions))
        rows = self._filter_decisions(rows, voting_method)
        return self._format_rows(rows, return_format)

    def search_decisions(self,
                         limit: int = 100,
                         return_format: Literal["json", "pandas"] = "json",
                         voting_method: Optional[str] = None,
                         **filters) -> Union[List[dict], pd.DataFrame]:
        """
        Searches procedure positions and returns the decisions they contain.

        Positions are selected with the same filters as `search_procedureposition`
        (e.g. `date_start`, `date_end`, `legislative_period`, `process_type`,
        `institution`, `title`). Positions without a decision are skipped.

        Parameters
        ----------
        limit: int, optional
            Maximum number of procedure positions to scan (not decisions).
            Defaults to 100.
        return_format: str, optional
            "json" (list of dicts, default) or "pandas" (DataFrame).
        voting_method: str, optional
            Only decisions with this voting method, e.g. "Namentliche Abstimmung".
        **filters:
            Filters passed to `search_procedureposition`.

        Returns
        -------
        Union[List[dict], pd.DataFrame]
        """
        self._validate_decision_args(return_format, voting_method)
        if "return_format" in filters or "fulltext" in filters:
            raise ValueError("return_format and fulltext cannot be passed as filters.")
        positions = self.search_procedureposition(limit=limit, **filters)
        rows = self._filter_decisions(flatten_decisions(positions), voting_method)
        return self._format_rows(rows, return_format)

    # vocabularies
    def discover_values(self,
                        resource: Resource,
                        field: str,
                        limit: int = 1000,
                        return_format: Literal["json", "pandas"] = "json",
                        **filters) -> Union[List[dict], pd.DataFrame]:
        """
        Counts which values of a field actually occur in the data.

        Useful for open vocabularies that are not fixed in the API
        specification, e.g. subject areas, document types or consultation
        states. The result shows the exact spelling to use in filters.

        Parameters
        ----------
        resource: str
            The resource to sample, e.g. "vorgang" or "drucksache".
        field: str
            The field to count. Use dots for nested fields, e.g. "sachgebiet",
            "beratungsstand", "drucksachetyp", "urheber.titel",
            "deskriptor.name" or "ressort.titel". Lists are counted per element.
        limit: int, optional
            Number of records to sample. Defaults to 1000. Rare values may be
            missing from a small sample.
        return_format: str, optional
            "json" (list of {"value", "count"} dicts, default) or "pandas".
        **filters:
            Filters to restrict the sample, e.g. legislative_period=20.

        Returns
        -------
        Union[List[dict], pd.DataFrame]
            Values sorted by frequency, most frequent first.

        Examples
        --------
        >>> bt.discover_values("vorgang", "sachgebiet", legislative_period=20)
        >>> bt.discover_values("drucksache", "drucksachetyp", institution="BT")
        """
        if return_format not in ("json", "pandas"):
            raise ValueError("return_format must be 'json' or 'pandas'.")
        if not isinstance(field, str) or not field:
            raise ValueError("field must be a non-empty string, e.g. 'sachgebiet'.")
        records = self.query(resource=resource, limit=limit, **filters)
        counts: Dict[str, int] = {}
        for record in records:
            for value in self._values_at_path(record, field.split(".")):
                counts[value] = counts.get(value, 0) + 1
        rows = [{"value": v, "count": c}
                for v, c in sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))]
        return self._format_rows(rows, return_format)

    @classmethod
    def _values_at_path(cls, node: Any, path: List[str]) -> List[Any]:
        """Return all scalar values at a dotted path, flattening lists."""
        if isinstance(node, list):
            return [v for item in node for v in cls._values_at_path(item, path)]
        if not path:
            return [] if node is None or isinstance(node, dict) else [node]
        if not isinstance(node, dict):
            return []
        return cls._values_at_path(node.get(path[0]), path[1:])

    # utility
    def list_methods(self):
        """
        list all methods offered by btaConnection

        Returns
        -------
        list_of_methods: list
            A list of strings

        """
        list_of_methods = dir(btaConnection)
        list_of_methods = [item for item in list_of_methods if "__" not in item]
        return list_of_methods
