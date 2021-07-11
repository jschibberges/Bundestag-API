# -*- coding: utf-8 -*-

from utils import *
from classes import *

def search_procedure(apikey,
                rformat="json",
                num=None,
                fid=None,
                datestart=None,
                dateend=None,
                institution=None,
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
    dat1=btapi_query(apikey,
                           resource="vorgang",
                           rformat=rformat,
                           fid=fid,
                           datestart=datestart,
                           dateend=dateend,
                           institution=institution,
                           processID=processID,
                           num=num,)
    return dat1
    

def search_document():
    pass

def search_person():
    pass

def search_plenaryprotocol():
    pass

def get_procedure(btid):
    dat1=utils.btapi_query(apikey,resource="vorgang",fid=btid)
    data=utils.classes.Vorgang(dat1["documents"][0])
    return data

def get_document(btid):
    dat1=utils.btapi_query(apikey,resource="drucksache-text",fid=btid)
    data=utils.classes.Drucksache(dat1["documents"][0])
    return data

def get_person(btid,dformat,output=None):
    if dformat=="raw-json":
        dfrmt="json"
    if dformat=="raw-xml":
        dfrmt="xml"
    dat1=utils.btapi_query(apikey,resource="person",fid=btid,rformat=dfrmt)
    if dformat=="pandas":
        import pandas as pd
        data=pd.DataFrame(dat1["documents"][0])
        return data
        #format as DF
    elif dformat=="raw-xml":
        print("XML not supported yet")
        #return dict
    elif dformat=="raw-json":
        data=json(dat1["documents"])
        return data
    else:
        data=classes.Person(dat1["documents"][0])
        return data
    

def get_plenaryprotocol(btid):
    dat1=utils.btapi_query(apikey,resource="plenarprotokoll-text",fid=btid)
    data=utils.classes.Plenarprotokoll(dat1["documents"][0])
    return data

