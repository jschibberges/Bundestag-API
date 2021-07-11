# -*- coding: utf-8 -*-

import requests

base_url="https://search.dip.bundestag.de/api/v1/"
resourcetypes=["aktivitaet","drucksache","drucksache-text","person","plenarprotokoll","plenarprotokoll-text","vorgang","vorgangsposition"]
institutions=["BT","BR", "BV", "EK"]

def btapi_query(apikey,
                resource,
                rformat="json",
                num=None,
                fid=None,
                datestart=None,
                dateend=None,
                institution=None,
                documentID=None,
                plenaryprotocolID=None,
                processID=None):
    base_url="https://search.dip.bundestag.de/api/v1/"
    if not isinstance(apikey, str) and len(apikey)==42:
            raise ValueError("No (correct) API key provided")
    if resource not in resourcetypes:
        raise ValueError("No or wrong resource")
    if  isinstance(fid, list):
        for i in fid:
            if not isinstance(i, int):
                raise TypeError("IDs must be integers")
    elif fid!=None:
        if not isinstance(fid, int): 
            raise TypeError("IDs must be integers")
    if rformat not in ["json","xml"]:
        raise ValueError("Not a correct format!")
    if institution!=None and institution not in institutions:
        raise ValueError("Unknown institution")
    if resource not in ["aktivitaet","vorgang","vorgangsposition"] and documentID!=None:
        raise ValueError("documentID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
    elif resource in ["aktivitaet","vorgang","vorgangsposition"] and documentID!=None and not isinstance(documentID,int):
        raise ValueError("documentID must be an integer")
    if resource not in ["aktivitaet","vorgang","vorgangsposition"] and plenaryprotocolID!=None:
        raise ValueError("plenaryprotocolID must be combined with resource 'aktivitaet', 'vorgang' or 'vorgangsposition'")
    elif resource in ["aktivitaet","vorgang","vorgangsposition"] and plenaryprotocolID!=None and not isinstance(plenaryprotocolID,int):
        raise ValueError("plenaryprotocolID must be an integer")
    if resource not in ["vorgangsposition"] and processID!=None:
        raise ValueError("processID must be combined with resource 'vorgangsposition'")
    elif resource in ["vorgangsposition"] and processID!=None and not isinstance(processID,int):
        raise ValueError("processID must be an integer")
    if plenaryprotocolID!=None and documentID!=None:
        raise ValueError("Can't select more than one of documentID, plenaryprotocolID and processID")
    if plenaryprotocolID!=None and processID!=None:
        raise ValueError("Can't select more than one of documentID, plenaryprotocolID and processID")
    if documentID!=None and processID!=None:
        raise ValueError("Can't select more than one of documentID, plenaryprotocolID and processID")
    if not isinstance(num, int) or num<=0:
        raise ValueError("num mus be an integer larger than zero")
    r_url=base_url+resource
    payload = {"apikey": apikey,
           "format": rformat,
           "f.id":fid,
           "f.datum.start":datestart,
           "f.datum.end":dateend,
           "f.drucksache":documentID,
           "f.plenarprotokoll":plenaryprotocolID,
           "f.vorgang":processID, 
           "f.zuordnung":institution,
           "cursor": None}
    data=[]
    prs=True
    while prs==True:
        r = requests.get(r_url,params=payload)
        print(r.url)
        if r.status_code == requests.codes.ok:
            content=r.json()
            if content["numFound"]==0:
                #print("No data was returned.")
                data="No data was returned."
                prs=False
            elif content["numFound"]>0 and content["numFound"]<=50:
                data.extend(content["documents"])
                prs=False
            elif content["numFound"]>50:
                if payload["cursor"]==content["cursor"]:
                    prs=False
                data.extend(content["documents"])
                if num!=None and len(data)>=num:
                    data=data[0:num]
                    prs=False
                payload["cursor"]=content["cursor"]
        elif r.status_code==400:
            return("A syntax error occured. Code {code}: {message}".format(code=r.status_code,message=r.reason))
        elif r.status_code==404:
            return("The API is not reachable. Code {code}: {message}".format(code=r.status_code,message=r.reason))
        else:
            return("An error occured. Code {code}: {message}".format(code=r.status_code,message=r.reason))
    return data






