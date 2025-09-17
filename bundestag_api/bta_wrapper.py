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
            logger.error("You need to supply your own API key.")
        elif apikey is None and date_expiry.date() > today.date():
            self.apikey = GEN_APIKEY
            logger.info("General API key used. It is valid until 31.05.2026.")
        elif apikey is not None:
            if not isinstance(apikey, str):
                raise ValueError("API key needs to be a string.")
            elif len(apikey.strip()) < 16:  # minimal guard against obviously wrong keys
                raise ValueError("apikey looks malformed (too short).")
            else:
                self.apikey = apikey
                logger.debug("Personal API key is used.")
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
            try:
                # Attempt to convert all items to int
                return [int(item) for item in param_value]
            except (ValueError, TypeError) as e:
                raise ValueError(f"All items in {param_name} must be convertible to integers.") from e
        return param_value

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

        BASE_URL = "https://search.dip.bundestag.de/api/v1/"
        RESOURCETYPES = ["aktivitaet", "drucksache", "drucksache-text", "person",
                         "plenarprotokoll", "plenarprotokoll-text", "vorgang",
                         "vorgangsposition"]
        INSTITUTIONS = ["BT", "BR", "BV", "EK"]
        # Validate resource
        if resource not in Resource.__args__:
            raise ValueError("No or wrong resource")
        # Validate fid
        if fid is not None:
            if isinstance(fid, int):
                fid = [fid]
            if not isinstance(fid, list):
                raise Exception("fid must be int or a list of ints.")
            if all(isinstance(item, int) for item in fid) is False:
                try:
                    fid = [int(item) for item in fid]
                except ValueError as e:
                    raise Exception("IDs must be integers: {}".format(e)) from None
        # The 'fid' list will be handled correctly by the requests library.
        if return_format not in ["json", "xml", "object", "pandas"]:
            raise ValueError("return_format: Not a correct format!")
        if institution is not None and institution not in INSTITUTIONS:
            raise ValueError("Unknown institution")
        if resource not in ["aktivitaet", "vorgang", "vorgangsposition"]:
            if drucksacheID is not None:
                raise ValueError(
                    "drucksacheID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
            if plenaryprotocolID is not None:
                raise ValueError(
                    "plenaryprotocolID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
        elif resource in ["aktivitaet", "vorgang", "vorgangsposition"]:
            if drucksacheID is not None and not isinstance(drucksacheID, int):
                raise ValueError("drucksacheID must be an integer")
            if plenaryprotocolID is not None and not isinstance(plenaryprotocolID, int):
                raise ValueError("plenaryprotocolID must be an integer")
        if resource not in ["vorgangsposition"]:
            if processID is not None:
                raise ValueError(
                    "processID must be combined with resource 'vorgangsposition'")
        elif resource in ["vorgangsposition"]:
            if processID is not None and not isinstance(processID, int):
                raise ValueError("processID must be an integer")
        if resource in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            title = self._validate_str_list_param(title, "title")
            process_type = self._validate_str_list_param(process_type, "process_type")
            process_type_notation = self._validate_int_list_param(process_type_notation, "process_type_notation")
            if drucksache_type is not None:
                if not isinstance(drucksache_type, str):
                    raise ValueError("drucksache_type must be a string.")
        if resource not in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            if title is not None:
                raise ValueError("Title must be combined with a document or process")
            if drucksache_type is not None:
                raise ValueError("Drucksache type must be combined with a document or process")
        if activityID is not None:
            if resource != "vorgangsposition":
                raise ValueError("activityID must be combined with resource 'vorgangsposition'")
            if not isinstance(activityID, int):
                raise ValueError("activityID must be an integer")
        # Validate that only one of the possible IDs is given and raise an error otherwise
        non_none_count = sum(arg is not None for arg in [
                             plenaryprotocolID, drucksacheID, processID, activityID])
        if non_none_count > 1:
            raise ValueError(
                "Can't select more than one of drucksacheID, plenaryprotocolID, processID, and activityID")
        # Validate the limit parameter is an integer and positive
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be an integer larger than zero")
        # Validate updated_since and updated_until are both in ISO 8601 format
        if updated_since is not None:
            updated_since = to_iso8601(updated_since)
        if updated_until is not None:
            updated_until = to_iso8601(updated_until)
        # Validate descriptors
        descriptor = self._validate_str_list_param(descriptor, "descriptor")
        # Validate sachgebiet
        sachgebiet = self._validate_str_list_param(sachgebiet, "sachgebiet")
        # Validate new params
        legislative_period = self._validate_int_list_param(legislative_period, "legislative_period")
        legislative_period = self._validate_int_list_param(legislative_period, "legislative_period") # Applies to all resources
        person_name = self._validate_str_list_param(person_name, "person_name")
        personID = self._validate_int_list_param(personID, "personID")
        document_number = self._validate_str_list_param(document_number, "document_number")
        if document_art is not None and document_art not in ["Drucksache", "Plenarprotokoll"]:
            raise ValueError("document_art must be either 'Drucksache' or 'Plenarprotokoll'")
        question_number = self._validate_str_list_param(question_number, "question_number")
        gesta_id = self._validate_str_list_param(gesta_id, "gesta_id")
        procedure_positionID = self._validate_int_list_param(procedure_positionID, "procedure_positionID")
        consultation_status = self._validate_str_list_param(consultation_status, "consultation_status")
        publication_reference = self._validate_str_list_param(publication_reference, "publication_reference")
        initiative = self._validate_str_list_param(initiative, "initiative")
        lead_department = self._validate_str_list_param(lead_department, "lead_department")
        originator = self._validate_str_list_param(originator, "originator")

        # Resource-specific validation for parameters
        if person_name is not None and resource not in ["aktivitaet", "person"]:
            raise ValueError("person_name can only be used with resource 'aktivitaet' or 'person'")
        if personID is not None and resource not in ["aktivitaet"]:
            raise ValueError("personID can only be used with resource 'aktivitaet'")
        if document_number is not None and resource in ["person"]:
            raise ValueError("document_number cannot be used with resource 'person'")
        if document_art is not None and resource not in ["vorgang", "vorgangsposition", "aktivitaet"]:
            raise ValueError("document_art can only be used with resource 'vorgang', 'vorgangsposition', or 'aktivitaet'")
        if question_number is not None and resource not in ["vorgang", "vorgangsposition", "aktivitaet"]:
            raise ValueError("question_number can only be used with resource 'vorgang', 'vorgangsposition', or 'aktivitaet'")
        if gesta_id is not None and resource not in ["vorgang"]:
            raise ValueError("gesta_id can only be used with resource 'vorgang'")
        if procedure_positionID is not None and resource not in ["aktivitaet"]:
            raise ValueError("procedure_positionID can only be used with resource 'aktivitaet'")
        if consultation_status is not None and resource not in ["vorgang"]:
            raise ValueError("consultation_status can only be used with resource 'vorgang'")
        if publication_reference is not None and resource not in ["vorgang"]:
            raise ValueError("publication_reference can only be used with resource 'vorgang'")
        if initiative is not None and resource not in ["vorgang"]:
            raise ValueError("initiative can only be used with resource 'vorgang'")
        if lead_department is not None and resource not in ["vorgang", "vorgangsposition", "drucksache", "drucksache-text"]:
            raise ValueError("lead_department can only be used with 'vorgang', 'vorgangsposition', 'drucksache', or 'drucksache-text'")
        if originator is not None and resource not in ["vorgang", "vorgangsposition", "drucksache", "drucksache-text", "aktivitaet"]:
            raise ValueError("originator can only be used with 'vorgang', 'vorgangsposition', 'drucksache', 'drucksache-text', or 'aktivitaet'")

        if fulltext:
            if resource in ("drucksache", "plenarprotokoll"):
                resource = cast(Resource, resource + "-text")
            elif resource not in ("drucksache-text", "plenarprotokoll-text"):
                raise ValueError("fulltext is only supported for 'drucksache' and 'plenarprotokoll'")


        r_url = BASE_URL+resource
        return_object = False
        if return_format == "object":
            return_format = "json"
            return_object = True

        payload = {"apikey": self.apikey,
                   "format": return_format,
                   "f.id": fid,
                   "f.datum.start": date_start,
                   "f.datum.end": date_end,
                   "f.aktualisiert.start": updated_since,
                   "f.aktualisiert.end": updated_until,
                   "f.drucksache": drucksacheID,
                   "f.plenarprotokoll": plenaryprotocolID,
                   "f.vorgang": processID,
                   "f.zuordnung": institution,
                   "f.deskriptor": descriptor,
                   "f.sachgebiet": sachgebiet,
                   "f.drucksachetyp": drucksache_type,
                   "f.vorgangstyp": process_type,
                   "f.vorgangstyp_notation": process_type_notation,
                   "f.titel": title,
                   "f.aktivitaet": activityID,
                   "f.wahlperiode": legislative_period,
                   "f.person": person_name,
                   "f.person_id": personID,
                   "f.dokumentnummer": document_number,
                   "f.dokumentart": document_art,
                   "f.frage_nummer": question_number,
                   "f.gesta": gesta_id,
                   "f.vorgangsposition_id": procedure_positionID,
                   "f.beratungsstand": consultation_status,
                   "f.verkuendung_fundstelle": publication_reference,
                   "f.initiative": initiative,
                   "f.ressort_fdf": lead_department,
                   "f.urheber": originator,
                   "cursor": None}
        data = []
        prs = True
        while prs:
            r = self.session.get(r_url, params=payload, timeout=30)
            logger.debug(r.url)
            if r.status_code == requests.codes.ok:
                content = r.json()
                documents_on_page = content.get("documents", [])

                if content.get("numFound", 0) == 0:
                    logging.info("No data was returned.")
                    prs = False
                else:
                    data.extend(documents_on_page)
                    next_cursor = content.get("cursor")

                    # Stop paginating if the limit is reached, there's no next cursor,
                    # or the API signals the last page by returning the same cursor.
                    if len(data) >= limit:
                        data = data[0:limit]
                        prs = False
                    elif not next_cursor or payload["cursor"] == next_cursor:
                        prs = False
                    else:
                        payload["cursor"] = next_cursor
            elif r.status_code == 400:
                logger.error("A syntax error occurred. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
                prs = False
            elif r.status_code == 401:
                logger.error("An authorization error occurred. Likely an error with your API key. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
                prs = False
            elif r.status_code == 404:
                logger.error("The API is not reachable. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
                prs = False
            else:
                logger.error("An error occurred. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
                prs = False
        if return_object:
            model_map = {
                "aktivitaet": Aktivitaet, "drucksache": Drucksache, "drucksache-text": Drucksache, "person": Person, "plenarprotokoll": Plenarprotokoll, "plenarprotokoll-text": Plenarprotokoll, "vorgang": Vorgang, "vorgangsposition": Vorgangsposition,
            }
            model_class = model_map.get(resource)
            if model_class:
                data = [model_class(item) for item in data]
        if return_format == "pandas":
            return pd.json_normalize(data)
        if len(data) == 0:
            logger.info("No data was returned.")
        return data

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
