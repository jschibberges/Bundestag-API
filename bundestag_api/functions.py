# -*- coding: utf-8 -*-

from bta_utils import btapi_query, BTA_Connection, Person, Vorgang, \
    Vorgangsposition, Aktivitaet, Drucksache, Plenarprotokoll
import json


def search_procedure(apikey,
                     rformat="json",
                     num=100,
                     fid=None,
                     datestart=None,
                     dateend=None,
                     processID=None):
    """


    Parameters
    ----------
    apikey : API key for the Bundestag API.
    rformat : TYPE, optional
        DESCRIPTION. The default is "json".
    num : TYPE, optional
        DESCRIPTION. The default is None.
    fid : TYPE, optional
        DESCRIPTION. The default is None.
    datestart : TYPE, optional
        DESCRIPTION. The default is None.
    dateend : TYPE, optional
        DESCRIPTION. The default is None.
    institution : TYPE, optional
        DESCRIPTION. The default is None.
    processID : TYPE, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    dat1 : TYPE
        DESCRIPTION.

    """
    data = btapi_query(apikey,
                       resource="vorgang",
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

    data = btapi_query(apikey,
                       resource="drucksache-text",
                       rformat=rformat,
                       fid=fid,
                       datestart=datestart,
                       dateend=dateend,
                       institution=institution,
                       num=num,)

    return data


def get_procedure(btid,
                  apikey):
    data = btapi_query(apikey, resource="vorgang", fid=btid)
    data = Vorgang(data["documents"][0])
    return data


def get_document(btid,
                 apikey):
    data = btapi_query(apikey, resource="drucksache-text", fid=btid)
    data = Drucksache(data["documents"][0])
    return data


def get_person(btid, dformat, apikey, output=None):
    if dformat == "raw-json":
        dfrmt = "json"
    if dformat == "raw-xml":
        dfrmt = "xml"
    dat1 = btapi_query(apikey, resource="person", fid=btid, rformat=dfrmt)
    if dformat == "pandas":
        import pandas as pd
        data = pd.DataFrame(dat1["documents"][0])
        return data
        # format as DF
    elif dformat == "raw-xml":
        print("XML not supported yet")
        # return dict
    elif dformat == "raw-json":
        data = json(dat1["documents"])
        return data
    else:
        data = Person(dat1["documents"][0])
        return data


def get_plenaryprotocol(btid,
                        apikey):
    data = btapi_query(apikey, resource="plenarprotokoll-text", fid=btid)
    data = Plenarprotokoll(data["documents"][0])
    return data
