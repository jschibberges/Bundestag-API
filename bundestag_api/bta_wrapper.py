# -*- coding: utf-8 -*-
from datetime import datetime
import requests
import sys
import logging
from models import Person, Aktivitaet, Vorgang, Vorgangsposition, Drucksache, Plenarprotokoll
from utils import is_iso8601, parse_args_to_dict

logger = logging.getLogger("bundestag_api")
logger.addHandler(logging.NullHandler())


class btaConnection:
    """This class handles the API authentication and provides search functionality

    Methods
    -------
    query(resource, return_format="json", num=100, fid=None, date_start=None, date_end=None,
          institution=None, documentID=None, plenaryprotocolID=None, procedureID=None)
        A general search function for the official Bundestag API
    search_procedure(return_format="json",num=100,fid=None,date_start=None,date_end=None):
        Searches procedures specified by the parameters
    search_procedureposition(return_format="json", num=100, fid=None, date_start=None, date_end=None, procedureID=None):
        Searches procedure positions specified by the parameters
    search_document(return_format="json", num=100, fid=None, date_start=None, date_end=None,institution=None):
        Searches documents specified by the parameters
    search_person(return_format="json", num=100, fid=None):
        Searches persons specified by the parameters
    search_plenaryprotocol(return_format="json", num=100, fid=None, date_start=None, date_end=None, institution=None):
        Searches plenary protocols specified by the parameters
    search_activity(return_format="json", num=100, fid=None, date_start=None, date_end=None, documentID=None, plenaryprotocolID=None, institution=None):
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
        GEN_APIKEY = "I9FKdCn.hbfefNWCY336dL6x62vfwNKpoN2RZ1gp21"

        DATE_GEN_APIKEY = "31.05.2025"
        date_expiry = datetime.strptime(DATE_GEN_APIKEY, "%d.%m.%Y")

        today = datetime.now()
        if apikey is None and date_expiry.date() < today.date():
            logger.error("You need to supply your own API key.")
        elif apikey is None and date_expiry.date() > today.date():
            self.apikey = GEN_APIKEY
            logger.info("General API key used. It is valid until 31.05.2024.")
        elif apikey is not None:
            if not isinstance(apikey, str) and len(apikey) == 42:
                raise ValueError("No (correct) API key provided")
            else:
                self.apikey = apikey
                logger.debug("Personal API key is used.")

    def __str__(self):
        return "API key: "+str(self.apikey)

    def __repr__(self):
        return "API key: "+str(self.apikey)

    def query(self,
              resource,
              return_format="json",
              num=100,
              fid=None,
              date_start=None,
              date_end=None,
              updated_since=None,
              updated_until=None,
              institution=None,
              documentID=None,
              plenaryprotocolID=None,
              procedureID=None,
              descriptor=None,
              sachgebiet=None,
              document_type=None,
              title=None,):
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
            num: int, optional
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
            procedureID: int, optional
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
        if isinstance(resource, str) is True:
            resource = resource.lower()
        if resource not in RESOURCETYPES:
            raise ValueError("No or wrong resource")
        # Validate fid
        if isinstance(fid, list) is True:
            if all(isinstance(item, int) for item in fid) is False:
                try:
                    fid = [int(item) for item in fid]
                except ValueError as e:
                    raise Exception("IDs must be integers: {}".format(e)) from None
            else:
                fid = '&f.id='.join(map(str, fid))
        elif fid is not None:
            if not isinstance(fid, int):
                try:
                    fid = int(fid)
                except ValueError as e:
                    raise Exception("IDs must be integers: {}".format(e)) from None
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
            if procedureID is not None:
                raise ValueError(
                    "procedureID must be combined with resource 'vorgangsposition'")
        elif resource in ["vorgangsposition"]:
            if procedureID is not None and not isinstance(procedureID, int):
                raise ValueError("procedureID must be an integer")
        if resource in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            if title is not None:
                if isinstance(title, list) is True:
                    if all(isinstance(item, str) for item in title) is False:
                        raise ValueError("All sachgebiet items need to be of type string.")
                    elif all(len(item) < 100 for item in title) is False:
                        raise ValueError("Strings are over 100 characters in length.")
                    else:
                        title = '&f.sachgebiet='.join(map(str, title))
                elif isinstance(title, str) is True:
                    if len(title) < 100:
                        raise ValueError("String is over 100 characters in length.")
                else:
                    raise ValueError("Sachgebiet must be string or a list of strings.")
            if document_type is not None:
                if isinstance(document_type, str) is False:
                    raise ValueError("document_type must be a string.")
        if resource not in ["drucksache", "drucksache-text", "vorgang", "vorgangsposition"]:
            if title is not None:
                raise ValueError("Title must be combined with a document of process")
            if document_type is not None:
                raise ValueError("Document type must be combined with a document")
        # Validate that only one of the possible IDs is given and raise an error otherwise
        non_none_count = sum(arg is not None for arg in [
                             plenaryprotocolID, documentID, procedureID])
        if non_none_count > 1:
            raise ValueError(
                "Can't select more than one of documentID, plenaryprotocolID and procedureID")
        # Validate the num parameter is an integer and positive
        if not isinstance(num, int) or num <= 0:
            raise ValueError("num must be an integer larger than zero")
        # Validate updated_since and updated_until are both in ISO 8601 format
        if updated_since is not None:
            if is_iso8601(updated_since) != True:
                raise ValueError(
                    "updated_since must be a string in the following format '2022-06-24T09:45:00'")
        if updated_until is not None:
            if is_iso8601(updated_until) != True:
                raise ValueError(
                    "updated_until must be a string in the following format '2022-06-24T09:45:00'")
        # Validate descriptors
        if descriptor is not None:
            if isinstance(descriptor, list) is True:
                if all(isinstance(item, str) for item in descriptor) is False:
                    raise ValueError("All descriptor items need to be of type string.")
                elif all(len(item) < 100 for item in descriptor) is False:
                    raise ValueError("Strings are over 100 characters in length.")
                else:
                    descriptor = '&f.deskriptor='.join(map(str, descriptor))
            elif isinstance(descriptor, str) is True:
                if len(descriptor) < 100:
                    raise ValueError("String is over 100 characters in length.")
            else:
                raise ValueError("Descriptor must be string or a list of strings.")
        # Validate sachgebiet
        if sachgebiet is not None:
            if isinstance(sachgebiet, list) is True:
                if all(isinstance(item, str) for item in sachgebiet) is False:
                    raise ValueError("All sachgebiet items need to be of type string.")
                elif all(len(item) < 100 for item in sachgebiet) is False:
                    raise ValueError("Strings are over 100 characters in length.")
                else:
                    sachgebiet = '&f.sachgebiet='.join(map(str, sachgebiet))
            elif isinstance(sachgebiet, str) is True:
                if len(sachgebiet) < 100:
                    raise ValueError("String is over 100 characters in length.")
            else:
                raise ValueError("Sachgebiet must be string or a list of strings.")

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
                   "f.drucksache": documentID,
                   "f.plenarprotokoll": plenaryprotocolID,
                   "f.vorgang": procedureID,
                   "f.zuordnung": institution,
                   "f.deskriptor": descriptor,
                   "f.sachgebiet": sachgebiet,
                   "f.drucksachetyp": document_type,
                   "f.titel": title,
                   "cursor": None}
        data = []
        prs = True
        while prs is True:
            r = requests.get(r_url, params=payload)
            logger.debug(r.url)
            if r.status_code == requests.codes.ok:
                content = r.json()
                if content["numFound"] == 0:
                    # print("No data was returned.")
                    data = "No data was returned."
                    prs = False
                elif content["numFound"] > 0 and content["numFound"] <= 50:
                    data.extend(content["documents"])
                    prs = False
                elif content["numFound"] > 50:
                    if payload["cursor"] == content["cursor"]:
                        prs = False
                    data.extend(content["documents"])
                    if num is not None and len(data) >= num:
                        data = data[0:num]
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
        if len(data) == 1 and isinstance(data, dict):
            tl = list(data.keys())
            data = data[tl[0]]
        elif len(data) == 1 and isinstance(data, list):
            data = data[0]
        return data

    def search_procedure(self,
                         return_format="json",
                         num=100,
                         fid=None,
                         date_start=None,
                         date_end=None,
                         updated_since=None,
                         updated_until=None,
                         descriptor=None,
                         sachgebiet=None,
                         document_type=None,
                         title=None,):
        """
        Searches procedures specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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
        title: str/list, optional
            Keyword that can be found in the title of documents. Multiple 
            strings can be supplied as a list and will be joined via
            an OR-search.

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedures

        """
        data = self.query(resource="vorgang",
                          return_format=return_format,
                          fid=fid,
                          date_start=date_start,
                          date_end=date_end,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,
                          descriptor=descriptor,
                          sachgebiet=sachgebiet,)
        return data

    def get_procedure(self,
                      btid=None,
                      return_format="json",
                      documentID=None,
                      plenaryprotocolID=None):
        """
        Retrieves procedures specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a procedure entity. Can be a list to retrieve more than
            one entity
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        documentID: int, optional
            Returns procedure related to that documentID
        plenaryprotocolID: int, optional
            Entity ID of a plenary protocol. Can be used to select activities,
            procedures and procedure positions that are connected to the
            protocol

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedures
        """
        if btid is None and documentID is None and plenaryprotocolID is None:
            raise ValueError(
                "Either an procedure ID, document ID or plenary protocol ID must be supplied")
        else:
            data = self.query(resource="vorgang",
                              fid=btid,
                              return_format=return_format,
                              documentID=documentID,
                              plenaryprotocolID=plenaryprotocolID)
            return data

    def search_procedureposition(self,
                                 return_format="json",
                                 num=100,
                                 fid=None,
                                 date_start=None,
                                 date_end=None,
                                 updated_since=None,
                                 updated_until=None,
                                 document_type=None,
                                 title=None,):
        """
        Searches procedure positions specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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

        data = self.query(resource="vorgangsposition",
                          return_format=return_format,
                          fid=fid,
                          date_start=date_start,
                          date_end=date_end,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,)
        return data

    def get_procedureposition(self,
                              btid,
                              return_format="json",
                              documentID=None,
                              procedureID=None,
                              plenaryprotocolID=None):
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
        procedureID: int, optional
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
        if btid is None and documentID is None and procedureID is None:
            raise ValueError(
                "Either an procedure ID, document ID or procedure ID must be supplied")
        else:
            data = self.query(resource="vorgangsposition",
                              fid=btid,
                              return_format=return_format,
                              documentID=documentID,
                              procedureID=procedureID,
                              plenaryprotocolID=plenaryprotocolID)
            return data

    def search_document(self,
                        return_format="json",
                        num=100,
                        fid=None,
                        date_start=None,
                        date_end=None,
                        institution=None,
                        fulltext=False,
                        updated_since=None,
                        updated_until=None,
                        document_type=None,
                        title=None,):
        """
        Searches documents specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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

        if fulltext == False:
            resource = "drucksache"
        elif fulltext == True:
            resource = "drucksache-text"
        else:
            resource = "drucksache"

        data = self.query(resource=resource,
                          return_format=return_format,
                          fid=fid,
                          date_start=date_start,
                          date_end=date_end,
                          institution=institution,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,)
        return data

    def get_document(self,
                     btid,
                     return_format="json",
                     fulltext=False):
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

        if fulltext == False:
            resource = "drucksache"
        elif fulltext == True:
            resource = "drucksache-text"
        else:
            resource = "drucksache"

        data = self.query(resource=resource,
                          fid=btid,
                          return_format=return_format)
        return data

    def search_person(self,
                      return_format="json",
                      num=100,
                      updated_since=None,
                      updated_until=None,):
        """
        Searches persons specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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

        data = self.query(resource="person",
                          return_format=return_format,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,)
        return data

    def get_person(self,
                   btid,
                   return_format="json"):
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

        data = self.query(resource="person",
                          fid=btid,
                          return_format=return_format)
        return data

    def search_plenaryprotocol(self,
                               return_format="json",
                               num=100,
                               **kwargs):
        """
        Searches plenary protocols specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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

        date_start = kwargs.get("date_start")
        date_end = kwargs.get("date_end")
        institution = kwargs.get("institution")
        fulltext = kwargs.get("fulltext")
        updated_since = kwargs.get("updated_since")
        updated_until = kwargs.get("updated_until")

        if fulltext == False:
            resource = "plenarprotokoll"
        elif fulltext == True:
            resource = "plenarprotokoll-text"
        else:
            resource = "plenarprotokoll"

        data = self.query(resource=resource,
                          return_format=return_format,
                          date_start=date_start,
                          date_end=date_end,
                          institution=institution,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,)

        return data

    def get_plenaryprotocol(self,
                            btid,
                            return_format="json",
                            fulltext=False):
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

        if fulltext == False:
            resource = "plenarprotokoll"
        elif fulltext == True:
            resource = "plenarprotokoll-text"
        else:
            resource = "plenarprotokoll"

        data = self.query(resource=resource,
                          fid=btid,
                          return_format=return_format)
        return data

    def search_activity(self,
                        return_format="json",
                        num=100,
                        date_start=None,
                        date_end=None,
                        institution=None,
                        updated_since=None,
                        updated_until=None,
                        descriptor=None,):
        """
        Searches activities specified by the parameters

        Parameters
        ----------
        return_format: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
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

        data = self.query(resource="aktivitaet",
                          return_format=return_format,
                          date_start=date_start,
                          date_end=date_end,
                          institution=institution,
                          num=num,
                          updated_since=updated_since,
                          updated_until=updated_until,
                          descriptor=descriptor)

        return data

    def get_activity(self,
                     btid=None,
                     return_format="json",
                     documentID=None,
                     plenaryprotocolID=None):
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
        if btid is None and documentID is None and plenaryprotocolID is None:
            raise ValueError(
                "Either an activity ID, document ID or plenary protocol ID must be supplied")
        else:
            data = self.query(resource="aktivitaet",
                              fid=btid,
                              return_format=return_format,
                              documentID=documentID,
                              plenaryprotocolID=plenaryprotocolID)
            return data

    def list_methods(self):
        """
        list all methods offered by btaConnection

        Returns
        -------
        data: list
            A list of strings

        """
        list_of_methods = dir(btaConnection)
        list_of_methods = [item for item in list_of_methods if "__" not in item]
        """
        list_of_methods = ["get_activity","search_activity","get_person",
                           "search_person", "get_plenaryprotocol",
                           "search_plenaryprotocol", "get_document",
                           "search_document", "get_procedureposition",
                           "search_procedureposition", "get_procedure",
                           "search_procedure", "query"] 
        """
        return list_of_methods


def main_function():
    arguments = parse_args_to_dict(sys.argv[1:])
    if arguments.get("o") is not None:
        output_format = arguments.get("o")
        output_defined = True
        arguments.pop("o")
        if arguments.get("n") is not None:
            file_name = arguments.get("n")
            if output_format not in file_name:
                file_name = file_name+"."+output_format
            arguments.pop("n")
        else:
            raise ValueError("Output defined but no filename given.")
    if arguments.get("apikey") is not None:
        bta = btaConnection(apikey=arguments.get("apikey"))
        arguments.pop("apikey")
    else:
        bta = btaConnection()
    if arguments.get("method") is not None:
        if arguments.get("method") in bta.list_methods():
            method = arguments.get("method")
            arguments.pop("method")
            if method == "searchProcedure":
                data = bta.search_procedure(arguments)
        else:
            raise ValueError("No valid method supplied.")
    else:
        raise ValueError("No method supplied")
    if output_defined == True:
        if output_format == "xlsx" or output_format == "xls":
            import pandas as pd
            data = pd.json_normalize(data)
            data.to_excel(file_name, index=False)
        elif output_format == "csv":
            import pandas as pd
            data = pd.json_normalize(data)
            data.to_csv(file_name, index=False)
        elif output_format == "json":
            import json
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    else:
        return data


if __name__ == "__main__":
    main_function()
