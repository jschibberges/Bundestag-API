# -*- coding: utf-8 -*-
from datetime import datetime
import requests


class btaConnection:
    """This class handles the API authentication and provides search functionality

    Methods
    -------
    query(resource, rformat="json", num=100, fid=None, datestart=None, dateend=None, institution=None, documentID=None, plenaryprotocolID=None, processID=None)
        A general search function for the official Bundestag API
    search_procedure(rformat="json",num=100,fid=None,datestart=None,dateend=None):
        Searches procedures specified by the parameters
    search_procedureposition(rformat="json", num=100, fid=None, datestart=None, dateend=None, processID=None):
        Searches procedure positions specified by the parameters
    search_document(rformat="json", num=100, fid=None, datestart=None, dateend=None,institution=None):
        Searches documents specified by the parameters
    search_person(rformat="json", num=100, fid=None):
        Searches persons specified by the parameters
    search_plenaryprotocol(rformat="json", num=100, fid=None, datestart=None, dateend=None, institution=None):
        Searches plenary protocols specified by the parameters
    search_activity(rformat="json", num=100, fid=None, datestart=None, dateend=None, documentID=None, plenaryprotocolID=None, institution=None):
        Searches activities specified by the parameters
    get_activity(btid, rformat="json"):
        Retrieves activities specified by IDs
    get_procedure(btid, rformat="json"):
        Retrieves procedures specified by IDs
    get_procedureposition(btid, rformat="json"):
        Retrieves procedure positions specified by IDs
    get_document(btid, rformat="json"):
        Retrieves documents specified by IDs
    get_person(btid, rformat="json"):
        Retrieves persons specified by IDs
    get_plenaryprotocol(btid, rformat="json"):
        Retrieves plenary protocols specified by IDs
    """

    def __init__(self, apikey=None):
        GEN_APIKEY = "GmEPb1B.bfqJLIhcGAsH9fTJevTglhFpCoZyAAAdhp"

        DATE_GEN_APIKEY = "31.05.2023"
        date_expiry = datetime.strptime(DATE_GEN_APIKEY, "%d.%m.%Y")

        today = datetime.now()
        if apikey is None and date_expiry.date() < today.date():
            print("You need to supply your own API key.")
        elif apikey is None and date_expiry.date() > today.date():
            self.apikey = GEN_APIKEY
            print("General API key used. It is valid until 31.05.2023.")
        elif apikey is not None:
            if not isinstance(apikey, str) and len(apikey) == 42:
                raise ValueError("No (correct) API key provided")
            else:
                self.apikey = apikey

    def __str__(self):
        return "API key: "+str(self.apikey)

    def __repr__(self):
        return "API key: "+str(self.apikey)

    def query(self,
              resource,
              rformat="json",
              num=100,
              fid=None,
              datestart=None,
              dateend=None,
              institution=None,
              documentID=None,
              plenaryprotocolID=None,
              processID=None):
        """A general search function for the official Bundestag API

        Parameters
            ----------
            resource: str
                The resource type to be queried. options are aktivitaet,
                drucksache, drucksache-text, person, plenarprotokoll,
                plenarprotokoll-text, vorgang or vorgangsposition
            rformat: str, optional
                Return format of the data. Defaults to json. XML not implemented
                yet. Other option is "object" which will return results as class
                objects
            num: int, optional
                Number of maximal results to be returned. Defaults to 100
            fid: int/list, optional
                ID of an entity. Can be a list to retrieve more than one entity
            datestart: str, optional
                Date after which entities should be retrieved. Format
                is "YYYY-MM-DD"
            dateend: str, optional
                Date before which entities should be retrieved. Format
                is "YYYY-MM-DD"
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
        if isinstance(fid, list):
            for i in fid:
                if not isinstance(i, int):
                    raise TypeError("IDs must be integers")
        elif fid is not None:
            if not isinstance(fid, int):
                raise TypeError("IDs must be integers")
        if rformat not in ["json", "xml", "object"]:
            raise ValueError("rformat: Not a correct format!")
        if institution is not None and institution not in INSTITUTIONS:
            raise ValueError("Unknown institution")
        if resource not in ["aktivitaet", "vorgang", "vorgangsposition"] and documentID is not None:
            raise ValueError(
                "documentID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
        elif resource in ["aktivitaet", "vorgang", "vorgangsposition"] and documentID is not None and not isinstance(documentID, int):
            raise ValueError("documentID must be an integer")
        if resource not in ["aktivitaet", "vorgang", "vorgangsposition"] and plenaryprotocolID is not None:
            raise ValueError(
                "plenaryprotocolID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
        elif resource in ["aktivitaet", "vorgang", "vorgangsposition"] and plenaryprotocolID is not None and not isinstance(plenaryprotocolID, int):
            raise ValueError("plenaryprotocolID must be an integer")
        if resource not in ["vorgangsposition"] and processID is not None:
            raise ValueError(
                "processID must be combined with resource 'vorgangsposition'")
        elif resource in ["vorgangsposition"] and processID is not None and not isinstance(processID, int):
            raise ValueError("processID must be an integer")
        if plenaryprotocolID is not None and documentID is not None:
            raise ValueError(
                "Can't select more than one of documentID, plenaryprotocolID and processID")
        if plenaryprotocolID is not None and processID is not None:
            raise ValueError(
                "Can't select more than one of documentID, plenaryprotocolID and processID")
        if documentID is not None and processID is not None:
            raise ValueError(
                "Can't select more than one of documentID, plenaryprotocolID and processID")
        if not isinstance(num, int) or num <= 0:
            raise ValueError("num mus be an integer larger than zero")
        r_url = BASE_URL+resource
        return_object = False
        if rformat == "object":
            rformat = "json"
            return_object = True
        if isinstance(fid, list) is True:
            fid = '&f.id='.join(map(str, fid))
        payload = {"apikey": self.apikey,
                   "format": rformat,
                   "f.id": fid,
                   "f.datum.start": datestart,
                   "f.datum.end": dateend,
                   "f.drucksache": documentID,
                   "f.plenarprotokoll": plenaryprotocolID,
                   "f.vorgang": processID,
                   "f.zuordnung": institution,
                   "cursor": None}
        data = []
        prs = True
        while prs is True:
            r = requests.get(r_url, params=payload)
            # print(r.url)
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
                return("A syntax error occured. Code {code}: {message}".format(code=r.status_code, message=r.reason))
            elif r.status_code == 401:
                return("An authorization error occured. Likely an error with you API key. Code {code}: {message}".format(code=r.status_code, message=r.reason))
            elif r.status_code == 404:
                return("The API is not reachable. Code {code}: {message}".format(code=r.status_code, message=r.reason))
            else:
                return("An error occured. Code {code}: {message}".format(code=r.status_code, message=r.reason))
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
        return data

    def search_procedure(self,
                         rformat="json",
                         num=100,
                         fid=None,
                         datestart=None,
                         dateend=None):
        """
        Searches procedures specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a procedure entity. Can be a list to retrieve more than
            one entity
        datestart: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        dateend: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedures

        """
        data = self.query(resource="vorgang",
                          rformat=rformat,
                          fid=fid,
                          datestart=datestart,
                          dateend=dateend,
                          num=num,)
        return data

    def search_procedureposition(self,
                                 rformat="json",
                                 num=100,
                                 fid=None,
                                 datestart=None,
                                 dateend=None,
                                 processID=None):
        """
        Searches procedure positions specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of an procedure position entity. Can be a list to retrieve more
            than one entity
        datestart: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        dateend: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        processID: int, optional
            Entity ID of a process. Can be used to select procedure positions
            that are connected to the process

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedure positions
        """

        data = self.query(resource="vorgangsposition",
                          rformat=rformat,
                          fid=fid,
                          datestart=datestart,
                          dateend=dateend,
                          processID=processID,
                          num=num,)
        return data

    def search_document(self,
                        rformat="json",
                        num=100,
                        fid=None,
                        datestart=None,
                        dateend=None,
                        institution=None):
        """
        Searches documents specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a document entity. Can be a list to retrieve more than one entity
        datestart: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        dateend: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        institution: str, optional
            Filter results by institution BT, BR, BV or EK

        Returns
        -------
        data: list
            a list of dictionaries or class objects of documents
        """

        data = self.query(resource="drucksache-text",
                          rformat=rformat,
                          fid=fid,
                          datestart=datestart,
                          dateend=dateend,
                          institution=institution,
                          num=num,)
        return data

    def search_person(self,
                      rformat="json",
                      num=100,
                      fid=None):
        """
        Searches persons specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a person entity. Can be a list to retrieve more than one entity

        Returns
        -------
        data: list
            a list of dictionaries or class objects of persons
        """

        data = self.query(resource="person",
                          rformat=rformat,
                          fid=fid,
                          num=num,)
        return data

    def search_plenaryprotocol(self,
                               rformat="json",
                               num=100,
                               fid=None,
                               datestart=None,
                               dateend=None,
                               institution=None):
        """
        Searches plenary protocols specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of a plenary protocol entity. Can be a list to retrieve more
            than one entity
        datestart: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        dateend: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        institution: str, optional
            Filter results by institution BT, BR, BV or EK

        Returns
        -------
        data: list
            a list of dictionaries or class objects of plenary protocols
        """

        data = self.query(resource="drucksache-text",
                          rformat=rformat,
                          fid=fid,
                          datestart=datestart,
                          dateend=dateend,
                          institution=institution,
                          num=num,)

        return data

    def search_activity(self,
                        rformat="json",
                        num=100,
                        fid=None,
                        datestart=None,
                        dateend=None,
                        documentID=None,
                        plenaryprotocolID=None,
                        institution=None):
        """
        Searches activities specified by the parameters

        Parameters
        ----------
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects
        num: int, optional
            Number of maximal results to be returned. Defaults to 100
        fid: int/list, optional
            ID of an activity entity. Can be a list to retrieve more than
            one entity
        datestart: str, optional
            Date after which entities should be retrieved. Format
            is "YYYY-MM-DD"
        dateend: str, optional
            Date before which entities should be retrieved. Format
            is "YYYY-MM-DD"
        documentID: int, optional
            Entity ID of a document. Can be used to select activities,
            procedures and procedure positions that are connected to the
            document
        plenaryprotocolID: int, optional
            Entity ID of a plenary protocol. Can be used to select activities,
            procedures and procedure positions that are connected to the
            protocol
        institution: str, optional
            Filter results by institution BT, BR, BV or EK

        Returns
        -------
        data: list
            a list of dictionaries or class objects of activities
        """

        data = self.query(resource="drucksache-text",
                          rformat=rformat,
                          fid=fid,
                          datestart=datestart,
                          dateend=dateend,
                          institution=institution,
                          documentID=documentID,
                          plenaryprotocolID=plenaryprotocolID,
                          num=num)

        return data

    def get_activity(self, btid, rformat="json"):
        """
        Retrieves activities specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of an activity entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of activities
        """

        data = self.query(resource="aktivitaet",
                          fid=btid, rformat=rformat)
        return data

    def get_procedure(self, btid, rformat="json"):
        """
        Retrieves procedures specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a procedure entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedures
        """

        data = self.query(resource="vorgang", fid=btid)
        return data

    def get_procedureposition(self, btid, rformat="json"):
        """
        Retrieves procedure positions specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a procedure position entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of procedure positions
        """

        data = self.query(resource="vorgangsposition", fid=btid)
        return data

    def get_document(self, btid, rformat="json"):
        """
        Retrieves documents specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a document entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of documents
        """

        data = self.query(resource="drucksache-text", fid=btid)
        return data

    def get_person(self, btid, rformat="json"):
        """
        Retrieves persons specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a person entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of persons
        """

        data = self.query(resource="person", fid=btid, rformat=rformat)
        return data

    def get_plenaryprotocol(self, btid, rformat="json"):
        """
        Retrieves plenary protocols specified by IDs

        Parameters
        ----------
        btid: int/list, optional
            ID of a plenary protocol entity. Can be a list to retrieve more than
            one entity
        rformat: str, optional
            Return format of the data. Defaults to json. XML not implemented
            yet. Other option is "object" which will return results as class
            objects

        Returns
        -------
        data: list
            a list of dictionaries or class objects of plenary protocols
        """

        data = self.query(resource="plenarprotokoll-text", fid=btid,
                          rformat=rformat)
        return data


class Person:
    """This class represents a German parliamentarian"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        if "nachname" in dictionary:
            self.lastname = dictionary["nachname"]
        else:
            self.lastname = None
        if "vorname" in dictionary:
            self.firstname = dictionary["vorname"]
        else:
            self.firstname = None
        mdbrole = False
        if "basisdatum" in dictionary:
            self.basedate = dictionary["basisdatum"]
        else:
            self.basedate = None
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "namenszusatz" in dictionary:
            self.nameaddendum = dictionary["namenszusatz"]
        ttl = dictionary["titel"].split(",")
        if ttl[1] == " MdB":
            self.faction = ttl[2].strip()
            mdbrole = True
        elif "person_roles" in dictionary:
            if "fraktion" in dictionary["person_roles"][0]:
                self.faction = dictionary["person_roles"][0]["fraktion"]
        else:
            self.faction = None
        if ttl[0].split(dictionary["vorname"])[0] != "":
            self.titel = ttl[0].split(dictionary["vorname"])[0].strip()
        else:
            self.titel = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None
        if "person_roles" in dictionary:
            liro = []
            for r in dictionary["person_roles"]:
                liro.append(Role(r))
            self.roles = liro
        elif "person_roles" not in dictionary and mdbrole is True and "wahlperiode" in dictionary:
            self.roles = [Role({"funktion": "MdB",
                               "fraktion": self.faction,
                                "nachname": self.lastname,
                                "vorname": self.firstname,
                                "wahlperiode_nummer": self.legislativeperiod
                                })]
        else:
            self.roles = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None

    def returnroles(self):
        for r in self.roles:
            print(r.returnrole())

    def updateByID(self, apikey=None):
        if apikey is None:
            raise ValueError("Function needs an API key.")
        dat1 = self.query(apikey, resource="person", fid=self.btid)
        dictionary = dat1["documents"][0]
        mdbrole = False
        if "basisdatum" in dictionary:
            self.basedate = dictionary["basisdatum"]
        else:
            self.basedate = None
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "namenszusatz" in dictionary:
            self.nameaddendum = dictionary["namenszusatz"]
        ttl = dictionary["titel"].split(",")
        if ttl[1] == " MdB":
            self.faction = ttl[2].strip()
            mdbrole = True
        elif "person_roles" in dictionary:
            if "fraktion" in dictionary["person_roles"][0]:
                self.faction = dictionary["person_roles"][0]["fraktion"]
        else:
            self.faction = None
        if ttl[0].split(dictionary["vorname"])[0] != "":
            self.titel = ttl[0].split(dictionary["vorname"])[0].strip()
        else:
            self.titel = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None
        if "person_roles" in dictionary:
            liro = []
            for r in dictionary["person_roles"]:
                liro.append(Role(r))
            self.roles = liro
        elif "person_roles" not in dictionary and mdbrole is True and "wahlperiode" in dictionary:
            self.roles = [Role({"funktion": "MdB",
                               "fraktion": self.faction,
                                "nachname": self.lastname,
                                "vorname": self.firstname,
                                "wahlperiode_nummer": self.legislativeperiod
                                })]
        else:
            self.roles = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None


class Role:
    """This class presents a role in the German parliamentary system."""

    def __init__(self, dictionary):
        self.function = dictionary["funktion"]
        if "wahlperiode_nummer" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode_nummer"]
        else:
            self.legislativeperiod = None
        if "namenszusatz" in dictionary:
            self.nameaddendum = dictionary["namenszusatz"]
        else:
            self.nameaddendum = None
        if "funktionszusatz" in dictionary:
            self.functionaddendum = dictionary["funktionszusatz"]
        else:
            self.functionaddendum = None
        if "fraktion" in dictionary:
            self.faction = dictionary["fraktion"]
        else:
            self.faction = None
        if "bundesland" in dictionary:
            self.federalstate = dictionary["bundesland"]
        else:
            self.federalstate = None
        if "nachname" in dictionary:
            self.lastname = dictionary["nachname"]
        else:
            self.lastname = None
        if "vorname" in dictionary:
            self.firstname = dictionary["vorname"]
        else:
            self.firstname = None
        if "wahlkreiszusatz" in dictionary:
            self.districtaddendum = dictionary["wahlkreiszusatz"]
        else:
            self.districtaddendum = None
        if "ressort_titel" in dictionary:
            self.department = dictionary["ressort_titel"]
        else:
            self.department = None

    def __str__(self):
        return f'Person: {self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""} - {self.function}'

    def __repr__(self):
        return f'Person: {self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""} - {self.function}'

    def returnrole(self):
        return(
            f'{self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""},'
            f'{self.function}{" - " if self.functionaddendum!= None else ""}{self.functionaddendum if self.functionaddendum!= None else ""}{", " if self.department!= None else ""}{self.department if self.department!= None else ""}{" (" if self.federalstate!=None else ""}{self.federalstate if self.federalstate!=None else ""}{")" if self.federalstate!=None else ""}')


class Drucksache:
    """This class represents a document of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        if "herausgeber" in dictionary:
            if dictionary["herausgeber"] == "BT":
                self.publisher = "Bundestag"
            elif dictionary["herausgeber"] == "BR":
                self.publisher = "Bundesrat"
            elif dictionary["herausgeber"] is not None and dictionary["herausgeber"] != "BR" and dictionary["herausgeber"] != "BT":
                self.publisher = dictionary["herausgeber"]
        else:
            self.publisher = None
        if "urheber" in dictionary:
            self.originator = dictionary["urheber"]
        else:
            self.originator = None
        if "autoren_anzahl" in dictionary:
            self.author_nr = dictionary["autoren_anzahl"]
        else:
            self.author_nr = None
        if "ressort" in dictionary:
            self.author_nr = dictionary["ressort"]
        else:
            self.author_nr = None
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None
        if "titel" in dictionary:
            self.title = dictionary["titel"]
        else:
            self.title = None
        if "drucksachetyp" in dictionary:
            self.doctype = dictionary["drucksachetyp"]
        else:
            self.doctype = None
        if "fundstelle" in dictionary:
            if "pdf_url" in dictionary["fundstelle"]:
                self.pdf_url = dictionary["fundstelle"]["pdf_url"]
            self.reference = dictionary["fundstelle"]
        else:
            self.reference = None
        if "dokumentart" in dictionary:
            self.docname = dictionary["dokumentart"]
        else:
            self.docname = None
        if "typ" in dictionary:
            self.instance = dictionary["typ"]
        else:
            self.instance = None
        if "dokumentnummer" in dictionary:
            self.docnumber = dictionary["dokumentnummer"]
        else:
            self.docnumber = None
        if "autoren_anzeige" in dictionary:
            auan = []
            auanid = []
            for a in dictionary["autoren_anzeige"]:
                auan.append(a["titel"])
                auanid.append(a["id"])
            self.author = auan
            self.authorid = auanid
            self.authordisplay = dictionary["autoren_anzeige"]
        else:
            self.author = None
            self.authordisplay = None
        if "text" in dictionary:
            self.text = dictionary["text"]
        else:
            self.text = None

    def __str__(self):
        return f'{self.instance}: ({self.btid}) {self.doctype} - {self.title} - {self.date}'

    def __repr__(self):
        return f'{self.instance}: ({self.btid}) {self.doctype} - {self.title} - {self.date}'

    def get_authors(self, apikey):
        pass


class Aktivitaet:
    """This class represents an activity in the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        self.activitytype = dictionary["aktivitaetsart"]
        self.date = dictionary["datum"]
        self.title = dictionary["titel"]
        self.type = dictionary["typ"]
        self.doctype = dictionary["dokumentart"]
        self.parlsession = dictionary["wahlperiode"]
        self.numprocedure = dictionary["vorgangsbezug_anzahl"]
        self.procedure_reference = dictionary["vorgangsbezug"][0]["id"]
        self.document_reference = dictionary["fundstelle"]["id"]

    def __str__(self):
        return f'{self.instance}: ({self.btid}) {self.activitytype} - {self.title} - {self.date}'

    def get_procedure(self, apikey):
        data = self.query(apikey=apikey, resource="vorgang",
                          fid=self.procedure_reference)
        data = Vorgang(data[0])
        return data

    def get_document(self, apikey):
        data = self.query(
            apikey=apikey, resource="drucksache-text", fid=self.document_reference)
        data = Drucksache(data[0])
        return data


class Vorgang:
    """This class represents a legislative process in of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        self.process_positions = []
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "titel" in dictionary:
            self.title = dictionary["titel"]
        else:
            self.title = None
        if "typ" in dictionary:
            self.instance = dictionary["typ"]
        else:
            self.instance = None
        if "vorgangstyp" in dictionary:
            self.processtype = dictionary["vorgangstyp"]
        else:
            self.processtype = None
        if "initiative" in dictionary:
            self.initiativ = dictionary["initiative"]
        else:
            self.initiativ = None
        if "abstract" in dictionary:
            self.abstract = dictionary["abstract"]
        else:
            self.abstract = None
        if "archiv" in dictionary:
            self.archive = dictionary["archiv"]
        else:
            self.archive = None
        if "beratungsstand" in dictionary:
            self.status = dictionary["beratungsstand"]
        else:
            self.status = None
        if "deskriptor" in dictionary:
            self.descriptor = dictionary["deskriptor"]
        else:
            self.descriptor = None
        if "gesta" in dictionary:
            self.gesta = dictionary["gesta"]
        else:
            self.gesta = None
        if "inkrafttreten" in dictionary:
            self.effectivedate = dictionary["inkrafttreten"][0]["datum"]
        else:
            self.effectivedate = None
        if "kom" in dictionary:
            self.kom = dictionary["kom"]
        else:
            self.kom = None
        if "mitteilung" in dictionary:
            self.notification = dictionary["mitteilung"]
        else:
            self.notification = None
        if "ratsdok" in dictionary:
            self.eucouncilnr = dictionary["ratsdok"]
        else:
            self.eucouncilnr = None
        if "sachgebiet" in dictionary:
            self.subject = dictionary["sachgebiet"]
        else:
            self.subject = None
        if "verkuendung" in dictionary:
            self.announcement = dictionary["verkuendung"]
        else:
            self.announcement = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None
        if "zustimmungsbeduerftigkeit" in dictionary:
            self.approvalnecessary = dictionary["zustimmungsbeduerftigkeit"]
            self.approvalnecessaryBool = dictionary["zustimmungsbeduerftigkeit"][len(
                dictionary["zustimmungsbeduerftigkeit"])-1].split(",")[0]
            if any("bes.eilbed." in s for s in dictionary["zustimmungsbeduerftigkeit"]):
                self.urgency = True
        else:
            self.approvalnecessary = None
            self.approvalnecessaryBool = None
            self.urgency = None

    def get_positions(self):
        data = self.query("vorgangsposition", processID=self.btid)
        for d in data:
            self.process_positions.append(Vorgangsposition(d))

    def show_positions(self):
        for pp in self.process_positions:
            print(pp)

    def __str__(self):
        return f'{self.instance}: ({self.btid}) {self.processtype} - {self.title} - {self.date}'

    def __repr__(self):
        return f'{self.instance}: ({self.btid}) {self.processtype} - {self.title} - {self.date}'


class Vorgangsposition:
    """This class represents a step in a legislative process in the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        if "aktivitaet_anzeige" in dictionary:
            pass
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "dokumentart" in dictionary:
            self.docname = dictionary["dokumentart"]
        else:
            self.docname = None
        if "fortsetzung" in dictionary:
            self.continuation = dictionary["fortsetzung"]
        else:
            self.continuation = None
        if "gang" in dictionary:
            self.course = dictionary["gang"]
        else:
            self.course = None
        if "gang" in dictionary:
            self.course = dictionary["gang"]
        else:
            self.course = None
        if "nachtrag" in dictionary:
            self.Supplement = dictionary["nachtrag"]
        else:
            self.Supplement = None
        if "titel" in dictionary:
            self.title = dictionary["titel"]
        else:
            self.title = None
        if "typ" in dictionary:
            self.instance = dictionary["typ"]
        else:
            self.instance = None
        if "urheber" in dictionary:
            self.originator = dictionary["urheber"]
        else:
            self.originator = None
        if "vorgang_id" in dictionary:
            self.processid = dictionary["vorgang_id"]
        else:
            self.processid = None
        if "vorgangsposition" in dictionary:
            self.processposition = dictionary["vorgangsposition"]
        else:
            self.processposition = None
        if "vorgangstyp" in dictionary:
            self.processtype = dictionary["vorgangstyp"]
        else:
            self.processtype = None
        if "zuordnung" in dictionary:
            if dictionary["zuordnung"] == "BT":
                self.institution = "Bundestag"
            elif dictionary["zuordnung"] == "BR":
                self.institution = "Bundesrat"
            elif dictionary["zuordnung"] is not None and dictionary["zuordnung"] != "BR" and dictionary["zuordnung"] != "BT":
                self.institution = dictionary["zuordnung"]
        else:
            self.institution = None

    def __str__(self):
        return f'{self.instance}: ({self.processid}) {self.processtype} - {self.title} - {self.date}'

    def __repr__(self):
        pass


class Plenarprotokoll:
    """This class represents a plenary protocol of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        if "datum" in dictionary:
            self.date = dictionary["datum"]
        else:
            self.date = None
        if "dokumentart" in dictionary:
            self.docname = dictionary["dokumentart"]
        else:
            self.docname = None
        if "titel" in dictionary:
            self.title = dictionary["titel"]
        else:
            self.title = None
        if "typ" in dictionary:
            self.instance = dictionary["typ"]
        else:
            self.instance = None
        if "herausgeber" in dictionary:
            if dictionary["herausgeber"] == "BT":
                self.publisher = "Bundestag"
            elif dictionary["herausgeber"] == "BR":
                self.publisher = "Bundesrat"
            elif dictionary["herausgeber"] is not None and dictionary["herausgeber"] != "BR" and dictionary["herausgeber"] != "BT":
                self.publisher = dictionary["herausgeber"]
        else:
            self.publisher = None
        if "wahlperiode" in dictionary:
            self.legislativeperiod = dictionary["wahlperiode"]
        else:
            self.legislativeperiod = None
        if "text" in dictionary:
            self.text = dictionary["text"]
        else:
            self.text = None
        if "fundstelle" in dictionary:
            if "pdf_url" in dictionary["fundstelle"]:
                self.pdf_url = dictionary["fundstelle"]["pdf_url"]
            self.reference = dictionary["fundstelle"]
        else:
            self.reference = None
        if "sitzungsbemerkung" in dictionary:
            self.sessioncomment = dictionary["sitzungsbemerkung"]
        else:
            self.sessioncomment = None
        if "dokumentnummer" in dictionary:
            self.docnumber = dictionary["dokumentnummer"]
        else:
            self.docnumber = None

    def __str__(self):
        return f'{self.docname}: {self.docnumber} - {self.title} - {self.date}'

    def __repr__(self):
        pass
