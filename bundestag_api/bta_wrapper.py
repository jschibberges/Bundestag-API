# -*- coding: utf-8 -*-
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import logging
import pandas as pd
from typing import Any, Dict, Iterable, List, Optional, Union, Literal, cast
from .models import Person, Aktivitaet, Vorgang, Vorgangsposition, Drucksache, Plenarprotokoll
from .utils import to_iso8601

logger = logging.getLogger("bundestag_api")
logger.addHandler(logging.NullHandler())

ReturnFormat = Literal["json", "object", "pandas"]
Institution = Literal["BT", "BR", "BV", "EK"]
Resource = Literal["aktivitaet", "drucksache", "drucksache-text", "person", 
                   "plenarprotokoll", "plenarprotokoll-text", "vorgang", 
                   "vorgangsposition"]

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

    def __init__(self, apikey=None):
        GEN_APIKEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

        DATE_GEN_APIKEY = "31.05.2026"
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
        self.session = self._build_session()


    def __str__(self):
        return "API key: "+str(self.apikey)

    def __repr__(self):
        return "API key: "+str(self.apikey)

    def _build_session(self):
        s = requests.Session()
        retry = Retry(total=3,
                       status_forcelist=(429,500,502,503,504),
                       allowed_methods=frozenset(['GET']), 
                       backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        s.mount('https://', adapter)
        s.mount('http://', adapter)
        s.headers['User-Agent'] = 'bundestag_api (python)'
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
        INSTITUTIONS = ["BT", "BR", "BV", "EK"]

        # Validate resource
        if resource not in Resource.__args__:
            raise ValueError("No or wrong resource")

        # Validate return format
        if return_format not in ["json", "xml", "object", "pandas"]:
            raise ValueError("return_format: Not a correct format!")

        # Validate institution
        if institution is not None and institution not in INSTITUTIONS:
            raise ValueError("Unknown institution")

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

        Raises ValueError if a parameter is used with an incompatible resource.
        """
        validations = [
            ('person_name', ["aktivitaet", "person"],
             "person_name can only be used with resource 'aktivitaet' or 'person'"),
            ('personID', ["aktivitaet"],
             "personID can only be used with resource 'aktivitaet'"),
            ('gesta_id', ["vorgang"],
             "gesta_id can only be used with resource 'vorgang'"),
            ('procedure_positionID', ["aktivitaet"],
             "procedure_positionID can only be used with resource 'aktivitaet'"),
            ('consultation_status', ["vorgang"],
             "consultation_status can only be used with resource 'vorgang'"),
            ('publication_reference', ["vorgang"],
             "publication_reference can only be used with resource 'vorgang'"),
            ('initiative', ["vorgang"],
             "initiative can only be used with resource 'vorgang'"),
        ]

        for param_name, allowed_resources, error_msg in validations:
            if params.get(param_name) is not None and resource not in allowed_resources:
                raise ValueError(error_msg)

        # Special case: document_number cannot be used with person
        if params.get('document_number') is not None and resource == "person":
            raise ValueError("document_number cannot be used with resource 'person'")

        # Special case: document_art
        if params.get('document_art') is not None and resource not in ["vorgang", "vorgangsposition", "aktivitaet"]:
            raise ValueError("document_art can only be used with resource 'vorgang', 'vorgangsposition', or 'aktivitaet'")

        # Special case: question_number
        if params.get('question_number') is not None and resource not in ["vorgang", "vorgangsposition", "aktivitaet"]:
            raise ValueError("question_number can only be used with resource 'vorgang', 'vorgangsposition', or 'aktivitaet'")

        # Special case: lead_department
        if params.get('lead_department') is not None and resource not in ["vorgang", "vorgangsposition", "drucksache", "drucksache-text"]:
            raise ValueError("lead_department can only be used with 'vorgang', 'vorgangsposition', 'drucksache', or 'drucksache-text'")

        # Special case: originator
        if params.get('originator') is not None and resource not in ["vorgang", "vorgangsposition", "drucksache", "drucksache-text", "aktivitaet"]:
            raise ValueError("originator can only be used with 'vorgang', 'vorgangsposition', 'drucksache', 'drucksache-text', or 'aktivitaet'")

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

        # Resource-specific validation for title and process_type
        if resource in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            validated['title'] = self._validate_str_list_param(params.get('title'), "title")
            validated['process_type'] = self._validate_str_list_param(params.get('process_type'), "process_type")
            validated['process_type_notation'] = self._validate_int_list_param(params.get('process_type_notation'), "process_type_notation")

            drucksache_type = params.get('drucksache_type')
            if drucksache_type is not None and not isinstance(drucksache_type, str):
                raise ValueError("drucksache_type must be a string.")
            validated['drucksache_type'] = drucksache_type
        else:
            # Ensure these params aren't used with wrong resources
            if params.get('title') is not None:
                raise ValueError("Title must be combined with a document or process")
            if params.get('drucksache_type') is not None:
                raise ValueError("Drucksache type must be combined with a document or process")
            validated['title'] = None
            validated['process_type'] = None
            validated['process_type_notation'] = None
            validated['drucksache_type'] = None

        # Validate reference ID parameters and their resource compatibility
        validated.update(self._validate_reference_ids(
            resource=resource,
            drucksacheID=params.get('drucksacheID'),
            plenaryprotocolID=params.get('plenaryprotocolID'),
            processID=params.get('processID'),
            activityID=params.get('activityID')
        ))

        # Add simple passthrough params (before resource-specific validation)
        validated['date_start'] = params.get('date_start')
        validated['date_end'] = params.get('date_end')
        validated['institution'] = params.get('institution')
        validated['document_art'] = params.get('document_art')

        # Validate document_art value
        if validated['document_art'] is not None and validated['document_art'] not in ["Drucksache", "Plenarprotokoll"]:
            raise ValueError("document_art must be either 'Drucksache' or 'Plenarprotokoll'")

        # Validate resource-specific parameters
        self._validate_resource_specific_params(resource, validated)

        return validated

    def _build_api_payload(self, validated_params: dict) -> dict:
        """Build the API request payload from validated parameters."""
        return {
            "apikey": self.apikey,
            "format": "json",  # Will be handled separately for object/pandas formats
            "f.id": validated_params.get('fid'),
            "f.datum.start": validated_params.get('date_start'),
            "f.datum.end": validated_params.get('date_end'),
            "f.aktualisiert.start": validated_params.get('updated_since'),
            "f.aktualisiert.end": validated_params.get('updated_until'),
            "f.drucksache": validated_params.get('drucksacheID'),
            "f.plenarprotokoll": validated_params.get('plenaryprotocolID'),
            "f.vorgang": validated_params.get('processID'),
            "f.zuordnung": validated_params.get('institution'),
            "f.deskriptor": validated_params.get('descriptor'),
            "f.sachgebiet": validated_params.get('sachgebiet'),
            "f.drucksachetyp": validated_params.get('drucksache_type'),
            "f.vorgangstyp": validated_params.get('process_type'),
            "f.vorgangstyp_notation": validated_params.get('process_type_notation'),
            "f.titel": validated_params.get('title'),
            "f.aktivitaet": validated_params.get('activityID'),
            "f.wahlperiode": validated_params.get('legislative_period'),
            "f.person": validated_params.get('person_name'),
            "f.person_id": validated_params.get('personID'),
            "f.dokumentnummer": validated_params.get('document_number'),
            "f.dokumentart": validated_params.get('document_art'),
            "f.frage_nummer": validated_params.get('question_number'),
            "f.gesta": validated_params.get('gesta_id'),
            "f.vorgangsposition_id": validated_params.get('procedure_positionID'),
            "f.beratungsstand": validated_params.get('consultation_status'),
            "f.verkuendung_fundstelle": validated_params.get('publication_reference'),
            "f.initiative": validated_params.get('initiative'),
            "f.ressort_fdf": validated_params.get('lead_department'),
            "f.urheber": validated_params.get('originator'),
            "cursor": None
        }

    def _execute_paginated_query(self, resource: Resource, payload: dict, limit: int) -> List[dict]:
        """Execute the API query with automatic pagination."""
        BASE_URL = "https://search.dip.bundestag.de/api/v1/"
        r_url = BASE_URL + resource

        data = []
        continue_pagination = True

        while continue_pagination:
            r = self.session.get(r_url, params=payload, timeout=30)
            logger.debug(r.url)

            if r.status_code == requests.codes.ok:
                content = r.json()
                documents_on_page = content.get("documents", [])

                if content.get("numFound", 0) == 0:
                    logging.info("No data was returned.")
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

            elif r.status_code == 400:
                # Check if this is an Enodia challenge/bot protection issue
                if '.enodia' in r.url or '/challenge' in r.url:
                    msg = (
                        "Bot protection detected (Enodia challenge). The Bundestag API blocked this request. "
                        "Possible causes:\n"
                        "  • Too many parallel requests (API limit: 25 concurrent)\n"
                        "  • Too many requests per second\n"
                        "  • Shared generic API key is being used by too many people/scripts\n"
                        "Solutions:\n"
                        "  1. Reduce parallel workers (e.g., max_workers=5 in ThreadPoolExecutor)\n"
                        "  2. Add delays between requests (e.g., time.sleep(0.1))\n"
                        "  3. Get a personal API key at https://dip.bundestag.de/\n"
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
            return pd.json_normalize(data)

        # Default: return JSON (list of dicts)
        return data

    def query(self,
              resource: Resource,
              return_format: ReturnFormat ="json",
              limit: int = 100,
              fid: Optional[Union[int, List[int]]] = None,
              date_start: Optional[str] = None,
              date_end: Optional[str] = None,
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
                Return format of the data. Defaults to json. XML not implemented
                yet. Other option is "object" which will return results as class
                objects
            limit: int, optional
                Number of maximal results to be returned. Defaults to 100
            fid: int/list, optional
                ID of an entity. Can be a list to retrieve more than one entity
            date_start: str, optional
                Date after which entities should be retrieved. Format
                is "YYYY-MM-DD"
            date_end: str, optional
                Date before which entities should be retrieved. Format
                is "YYYY-MM-DD"
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
            fulltext: boolean
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
