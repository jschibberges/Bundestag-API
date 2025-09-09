# -*- coding: utf-8 -*-
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import logging
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
    query(resource, return_format="json", limit=100, fid=None, date_start=None, date_end=None,
          institution=None, documentID=None, plenaryprotocolID=None, processID=None)
        A general search function for the official Bundestag API
    search_procedure(return_format="json",limit=100,fid=None,date_start=None,date_end=None):
        Searches procedures specified by the parameters
    search_procedureposition(return_format="json", limit=100, fid=None, date_start=None, date_end=None, processID=None):
        Searches procedure positions specified by the parameters
    search_document(return_format="json", limit=100, fid=None, date_start=None, date_end=None,institution=None):
        Searches documents specified by the parameters
    search_person(return_format="json", limit=100, fid=None):
        Searches persons specified by the parameters
    search_plenaryprotocol(return_format="json", limit=100, fid=None, date_start=None, date_end=None, institution=None):
        Searches plenary protocols specified by the parameters
    search_activity(return_format="json", limit=100, fid=None, date_start=None, date_end=None, documentID=None, plenaryprotocolID=None, institution=None):
        Searches activities specified by the parameters
    get_activity(btid, return_format="json"):
        Retrieves activities specified by IDs
    get_procedure(btid, return_format="json"):
        Retrieves procedures specified by IDs
    get_procedureposition(btid, return_format="json"):
        Retrieves procedure positions specified by IDs
    get_document(btid, return_format="json"):
        Retrieves documents specified by IDs
    get_person(btid, return_format="json"):
        Retrieves persons specified by IDs
    get_plenaryprotocol(btid, return_format="json"):
        Retrieves plenary protocols specified by IDs
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

    def query(self,
              resource: Resource,
              return_format: ReturnFormat ="json",
              limit: int = 100,
              fid: Optional[Union[int, List[int]]] = None,
              date_start: Optional[str] = None,
              date_end: Optional[str] = None,
              updated_since: Optional[str] = None,
              updated_until: Optional[str] = None,
              institution: Optional[Institution] = None,
              documentID: Optional[int] = None,
              plenaryprotocolID: Optional[int] = None,
              processID: Optional[int] = None,
              descriptor: Optional[Union[str, List[str]]] = None,
              sachgebiet: Optional[Union[str, List[str]]] = None,
              document_type: Optional[str] = None,
              process_type: Optional[str] = None,
              process_type_notation: Optional[int] = None,
              title: Optional[Union[str, List[str]]] = None,):
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
            documentID: int, optional
                Entity ID of a document. Can be used to select activities,
                procedures and procedure positions that are connected to the
                document
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
            document_type: str, optional
                The type of document to be returned.
            process_type: str, optional
                The type of process ("Gesetzgebung") to be returned.
            process_type_notation: int, optional
                The type of process (100) to be returned.
            title: str/list, optional
                Keyword that can be found in the title of documents. Multiple 
                strings can be supplied as a list and will be joined via
                an OR-search.
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
            fid_str = ''.join(f'&f.id={str(item)}' for item in fid)
        else:
            fid_str = None
        if return_format not in ["json", "xml", "object", "pandas"]:
            raise ValueError("return_format: Not a correct format!")
        if institution is not None and institution not in INSTITUTIONS:
            raise ValueError("Unknown institution")
        if resource not in ["aktivitaet", "vorgang", "vorgangsposition"]:
            if documentID is not None:
                raise ValueError(
                    "documentID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
            if plenaryprotocolID is not None:
                raise ValueError(
                    "plenaryprotocolID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
        elif resource in ["aktivitaet", "vorgang", "vorgangsposition"]:
            if documentID is not None and not isinstance(documentID, int):
                raise ValueError("documentID must be an integer")
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
            if title is not None:
                if isinstance(title, str):
                    title = [title]
                if not isinstance(title, list):
                    raise ValueError("title must be string or a list of strings.")
                if all(isinstance(item, str) for item in title) is False:
                    try:
                        title = [str(item) for item in title]
                    except ValueError as e:
                        raise ValueError("All title items need to be of type string.")
                if all(len(item) < 100 for item in title) is False:
                        raise ValueError("Strings are over 100 characters in length.")
                title = ''.join(f'&f.titel={str(item)}' for item in title)
            if document_type is not None:
                if isinstance(document_type, str) is False:
                    raise ValueError("document_type must be a string.")
            if process_type is not None:
                if isinstance(process_type, str) is False:
                    raise ValueError("process_type must be a string.")
            if process_type_notation is not None:
                if isinstance(process_type_notation, int) is False:
                    raise ValueError("process_type_notation must be an integer.")
        if resource not in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            if title is not None:
                raise ValueError("Title must be combined with a document or process")
            if document_type is not None:
                raise ValueError("Document type must be combined with a document")
        # Validate that only one of the possible IDs is given and raise an error otherwise
        non_none_count = sum(arg is not None for arg in [
                             plenaryprotocolID, documentID, processID])
        if non_none_count > 1:
            raise ValueError(
                "Can't select more than one of documentID, plenaryprotocolID and processID")
        # Validate the limit parameter is an integer and positive
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be an integer larger than zero")
        # Validate updated_since and updated_until are both in ISO 8601 format
        if updated_since is not None:
            updated_since = to_iso8601(updated_since)
        if updated_until is not None:
            updated_until = to_iso8601(updated_until)
        # Validate descriptors
        if descriptor is not None:
            if isinstance(descriptor, str):
                descriptor = [descriptor]
            if not isinstance(descriptor, list):
                raise ValueError("Descriptor must be string or a list of strings.")

            if all(isinstance(item, str) for item in descriptor) is False:
                try:
                    descriptor = [str(item) for item in descriptor]
                except ValueError as e:
                    raise ValueError("All descriptor items need to be of type string.")
            if all(len(item) < 100 for item in descriptor) is False:
                raise ValueError("There are descriptor strings that are over 100 characters in length.")
            descriptor = ''.join(f'&f.deskriptor={str(item)}' for item in descriptor)
        # Validate sachgebiet
        if sachgebiet is not None:
            if isinstance(sachgebiet, str):
                sachgebiet = [sachgebiet]
            if not isinstance(sachgebiet, list):
                raise ValueError("Sachgebiet must be string or a list of strings.")
            if all(isinstance(item, str) for item in sachgebiet) is False:
                try:
                    sachgebiet = [str(item) for item in sachgebiet]
                except ValueError as e:
                    raise ValueError("All sachgebiet items need to be of type string.")
            if all(len(item) < 100 for item in sachgebiet) is False:
                raise ValueError("There are sachgebiet strings that are over 100 characters in length.")
            sachgebiet = ''.join(f'&f.sachgebiet={str(item)}' for item in sachgebiet)
            

        r_url = BASE_URL+resource
        return_object = False
        if return_format == "object":
            return_format = "json"
            return_object = True

        payload = {"apikey": self.apikey,
                   "format": return_format,
                   "f.id": fid_str,
                   "f.datum.start": date_start,
                   "f.datum.end": date_end,
                   "f.aktualisiert.start": updated_since,
                   "f.aktualisiert.end": updated_until,
                   "f.drucksache": documentID,
                   "f.plenarprotokoll": plenaryprotocolID,
                   "f.vorgang": processID,
                   "f.zuordnung": institution,
                   "f.deskriptor": descriptor,
                   "f.sachgebiet": sachgebiet,
                   "f.drucksachetyp": document_type,
                   "f.vorgangstyp": process_type,
                   "f.vorgangstyp_notation": process_type_notation,
                   "f.titel": title,
                   "cursor": None}
        data = []
        prs = True
        while prs is True:
            r = self.session.get(r_url, params=payload, timeout=30)
            logger.debug(r.url)
            if r.status_code == requests.codes.ok:
                content = r.json()
                if content["numFound"] == 0:
                    logging.info("No data was returned.")
                    prs = False
                elif content["numFound"] > 0 and content["numFound"] <= limit:
                    data.extend(content["documents"])
                    prs = False
                elif content["numFound"] > limit:
                    if payload["cursor"] == content["cursor"]:
                        prs = False
                    data.extend(content["documents"])
                    if limit is not None and len(data) >= limit:
                        data = data[0:limit]
                        prs = False
                    payload["cursor"] = content["cursor"]
            elif r.status_code == 400:
                logger.error("A syntax error occured. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
            elif r.status_code == 401:
                logger.error("An authorization error occured. Likely an error with you API key. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
            elif r.status_code == 404:
                logger.error("The API is not reachable. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
            else:
                logger.error("An error occured. Code {code}: {message}".format(
                    code=r.status_code, message=r.reason))
        if return_object is True:
            if resource == "aktivitaet":
                data = {name["id"]: Aktivitaet(name) for name in data}
            elif resource == "drucksache":
                data = {name["id"]: Drucksache(name) for name in data}
            elif resource == "drucksache-text":
                data = {name["id"]: Drucksache(name) for name in data}
            elif resource == "person":
                data = {name["id"]: Person(name) for name in data}
            elif resource == "plenarprotokoll":
                data = {name["id"]: Plenarprotokoll(name) for name in data}
            elif resource == "plenarprotokoll-text":
                data = {name["id"]: Plenarprotokoll(name) for name in data}
            elif resource == "vorgang":
                data = {name["id"]: Vorgang(name) for name in data}
            elif resource == "vorgangsposition":
                data = {name["id"]: Vorgangsposition(name) for name in data}
        if return_format == "pandas":
            import pandas as pd
            data = pd.json_normalize(data)
        # Always return a list, even if it is just one element
        if not isinstance(data, list):
            data = [data]
        return data

    # The following two methods are used to construct the specific search and get methods
    def _search(self, resource: Resource, **filters):
        """Generic search: forwards to .query(resource, **filters)."""
        return self.query(resource=resource, **filters)

    def _get(self, resource: Resource, btid, **filters):
        """Generic get: forwards to .query(resource, fid=btid, **filters)."""
        return self.query(resource=resource, fid=btid, **filters)

    # procedures
    def search_procedure(self, **filters) -> list:
        """
        Searches procedures specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a procedure entity. Can be a list to retrieve more than
            one entity
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
        descriptor: str/list, optional
            Keyword that is connected to the entities. Multiple strings can
            be supplied as a list but they will be joined via AND. An OR-
            search is not possible         
        sachgebiet: str/list, optional
            Political field that is connected to the entities. Multiple 
            strings can be supplied as a list but they will be joined via
            AND. An OR-search is not possible
        document_type: str, optional
            The type of document to be returned.
        process_type: str, optional
            The type of process ("Gesetzgebung") to be returned.
        title: str/list, optional
            Keyword that can be found in the title of documents. Multiple 
            strings can be supplied as a list and will be joined via
            an OR-search.

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedures

        """
        return self._search("vorgang", **filters)

    def get_procedure(self, btid=None, **filters) -> list:
        """
        Retrieves procedure positions specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a procedure position entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        documentID: int, optional
            Returns procedure positions related to that documentID
        processID: int, optional
            Returns procedure positions related to that procedure
        plenaryprotocolID: int, optional
            Entity ID of a plenary protocol. Can be used to select activities,
            procedures and procedure positions that are connected to the
            protocol

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedure positions
        """
        return self._get("vorgang", btid, **filters)

    # procedure positions
    def search_procedureposition(self, **filters) -> list:
        """
        Searches procedure positions specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of an procedure position entity. Can be a list to retrieve more
            than one entity
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
        document_type: str, optional
            The type of document to be returned.
        title: str/list, optional
            Keyword that can be found in the title of documents. Multiple 
            strings can be supplied as a list and will be joined via
            an OR-search.

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedure positions
        """

        return self._search("vorgangsposition", **filters)

    def get_procedureposition(self, btid=None, **filters) -> list:
        """
        Retrieves procedure positions specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a procedure position entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        documentID: int, optional
            Returns procedure positions related to that documentID
        processID: int, optional
            Returns procedure positions related to that procedure
        plenaryprotocolID: int, optional
            Entity ID of a plenary protocol. Can be used to select activities,
            procedures and procedure positions that are connected to the
            protocol

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedure positions
        """
        return self._get("vorgangsposition", btid, **filters)

    # documents
    def search_document(self, **filters) -> list:
        """
        Searches documents specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a document entity. Can be a list to retrieve more than one entity
        date_start: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        date_end: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        institution: str, optional
            Filter results by institution BT, BR, BV or EK
        fulltext: boolean
            Whether the fulltext (if available) should be requested or not. Default is false
        updated_since: str, optional
            Date and time after which updated documents are to be retrieved
        updated_until: str, optional
            Date and time until which updated documents are to be retrieved
        document_type: str, optional
            The type of document to be returned.
        title: str/list, optional
            Keyword that can be found in the title of documents. Multiple 
            strings can be supplied as a list and will be joined via
            an OR-search.

        Returns
        -------
        data: list
            a list of dictionaries or class objects of documents
        """
        return self._search("drucksache", **filters)

    def get_document(self, btid=None, **filters) -> list:
        """
        Retrieves documents specified by IDs

        Parameters
        ----------
        btid: int/list
            ID of a document entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        fulltext: boolean
            Whether the fulltext (if available) should be requested or not. Default is False    

        Returns
        -------
        data: list
            a list of dictionaries or class objects of documents
        """
        return self._get("drucksache", btid, **filters)

    # persons
    def search_person(self, **filters) -> list:
        """
        Searches persons specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        updated_since: str, optional
            Date and time after which updated documents are to be retrieved
        updated_until: str, optional
            Date and time until which updated documents are to be retrieved

        Returns
        -------
        data: list
            a list of dictionaries or class objects of persons
        """
        return self._search("person", **filters)

    def get_person(self, btid=None, **filters) -> list:
        """
        Retrieves persons specified by IDs

        Parameters
        ----------
        btid: int/list
            ID of a person entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of persons
        """

        return self._get("person", btid, **filters)

    # plenary protocols
    def search_plenaryprotocol(self, **filters) -> list:
        """
        Searches plenary protocols specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        date_start: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        date_end: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        institution: str, optional
            Filter results by institution BT, BR, BV or EK
        fulltext: boolean
            Whether the fulltext (if available) should be requested or not. Default is false
        updated_since: str, optional
            Date and time after which updated documents are to be retrieved
        updated_until: str, optional
            Date and time until which updated documents are to be retrieved

        Returns
        -------
        data: list
            a list of dictionaries or class objects of plenary protocols
        """
        return self._search("plenarprotokoll", **filters)

    def get_plenaryprotocol(self, btid=None, **filters) -> list:
        """
        Retrieves plenary protocols specified by IDs

        Parameters
        ----------
        btid: int/list
            ID of a plenary protocol entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        fulltext: boolean
            Whether the fulltext (if available) should be requested or not. Default is false

        Returns
        -------
        data: list
            a list of dictionaries or class objects of plenary protocols
        """
        return self._get("plenarprotokoll", btid, **filters)

    # activities
    def search_activity(self, **filters) -> list:
        """
        Searches activities specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        limit: int, optional
            Number of maximal results to be returned. Defaults to 100
        date_start: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        date_end: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        institution: str, optional
            Filter results by institution BT, BR, BV or EK
        updated_since: str, optional
            Date and time after which updated documents are to be retrieved
        updated_until: str, optional
            Date and time until which updated documents are to be retrieved
        descriptor: str/list, optional
            Keyword that is connected to the entities. Multiple strings can
            be supplied as a list but they will be joined via AND. An OR-
            search is not possible         

        Returns
        -------
        data: list
            a list of dictionaries or class objects of activities
        """
        return self._search("aktivitaet", **filters)

    def get_activity(self, btid=None, **filters) -> list:
        """
        Retrieves activities specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of an activity entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        documentID: int, optional
            Entity ID of a document. Can be used to select activities,
            procedures and procedure positions that are connected to the
            document
        plenaryprotocolID: int, optional
            Entity ID of a plenary protocol. Can be used to select activities,
            procedures and procedure positions that are connected to the
            protocol
        Returns
        -------
        data: list
            a list of dictionaries or class objects of activities
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

if __name__ == "__main__":
    import sys
    from .utils import parse_args_to_dict
    # very small demo CLI
    if len(sys.argv) < 3:
        print("Usage: python -m bundestag_api <resource> <search|get> key=val ...")
        sys.exit(1)
    resource = cast(Resource, sys.argv[1])
    action = sys.argv[2]
    kwargs = parse_args_to_dict(sys.argv[3:])
    conn = btaConnection(apikey=kwargs.pop("apikey", None))
    if action == "search":
        print(conn.query(resource=resource, **kwargs))
    elif action == "get":
        fid = kwargs.pop("fid", None)
        print(conn.query(resource=resource, fid=fid, **kwargs))
    else:
        print("action must be 'search' or 'get'")
