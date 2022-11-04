# -*- coding: utf-8 -*-

from .bta_utils import btapi_query, Person, Vorgang, \
    Vorgangsposition, Aktivitaet, Drucksache, Plenarprotokoll


def search_procedure(apikey,
                     rformat="json",
                     num=100,
                     fid=None,
                     datestart=None,
                     dateend=None):
    """
    Searches procedures specified by the parameters

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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
    data = btapi_query(apikey,
                       resource="vorgang",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       num=num,)
    return data


def search_procedureposition(apikey,
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
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey,
                       resource="vorgangsposition",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       processID=processID,
                       num=num,)
    return data


def search_document(apikey,
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
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey,
                       resource="drucksache-text",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       institution=institution,
                       num=num,)
    return data


def search_person(apikey,
                  rformat="json",
                  num=100,
                  fid=None):
    """
    Searches persons specified by the parameters

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey,
                       resource="person",
                       rformat=rformat,
                       fid=fid,
                       num=num,)
    return data


def search_plenaryprotocol(apikey,
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
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey,
                       resource="drucksache-text",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       institution=institution,
                       num=num,)

    return data


def search_activity(apikey,
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
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey,
                       resource="drucksache-text",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       institution=institution,
                       documentID=documentID,
                       plenaryprotocolID=plenaryprotocolID,
                       num=num)

    return data


def get_activity(apikey, btid, rformat="json"):
    """
    Retrieves activities specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey, resource="aktivitaet",
                       fid=btid, rformat=rformat)
    return data


def get_procedure(apikey, btid, rformat="json"):
    """
    Retrieves procedures specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey, resource="vorgang", fid=btid)
    if isinstance(data, str) is True:
        return data
    else:
        data = Vorgang(data[0])
        return data


def get_procedureposition(apikey, btid, rformat="json"):
    """
    Retrieves procedure positions specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey, resource="vorgangsposition", fid=btid)
    if isinstance(data, str) is True:
        return data
    else:
        data = Vorgangsposition(data[0])
        return data


def get_document(apikey, btid, rformat="json"):
    """
    Retrieves documents specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey=apikey, resource="drucksache-text", fid=btid)
    if isinstance(data, str) is True:
        return data
    else:
        data = Drucksache(data[0])
        return data


def get_person(apikey, btid, rformat="json"):
    """
    Retrieves persons specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey, resource="person", fid=btid, rformat=rformat)
    return data


def get_plenaryprotocol(apikey, btid, rformat="json"):
    """
    Retrieves plenary protocols specified by IDs

    Parameters
    ----------
    apikey: str/BTA_Connection
        Either an API key in string format or a BTA_Connection object
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

    data = btapi_query(apikey, resource="plenarprotokoll-text", fid=btid,
                       rformat=rformat)
    return data
