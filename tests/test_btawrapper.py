# -*- coding: utf-8 -*-

import pytest
from datetime import datetime
import bundestag_api
from random import randrange


def checkdates(date, dateL, dateE=None):
    date = datetime.strptime(date, "%Y-%m-%d")
    dateL = datetime.strptime(dateL, "%Y-%m-%d")
    if dateE is not None:
        dateE = datetime.strptime(dateE, "%Y-%m-%d")
        if date <= dateL and date >= dateE:
            return True
        else:
            return False
    if date <= dateL:
        return True
    else:
        return False


def test_checkdates():
    date = "2022-05-11"
    dateL = "2022-05-15"
    dateE = "2022-05-01"
    erl = []
    if checkdates(date, dateL) == True:
        erl.append(False)
    else:
        erl.append(True)
    if checkdates(date, dateL, dateE=dateE) == True:
        erl.append(False)
    else:
        erl.append(True)
    assert len(erl) == 2 and not any(erl)


def test_genapikey():
    bta = bundestag_api.btaConnection()
    assert bta.apikey == "GmEPb1B.bfqJLIhcGAsH9fTJevTglhFpCoZyAAAdhp"


def test_wrongapikey():
    bta2 = bundestag_api.btaConnection("GmEPb1B.bfqJLIhcGAsH9fTJevTglhFpCoZyAArrhp")
    test = bta2.search_document()
    assert test == 'An authorization error occured. Likely an error with you API key. Code 401: Unauthorized'


@pytest.fixture
def bta_object():
    bta = bundestag_api.btaConnection()
    return bta


@pytest.mark.parametrize("resourcetypes", ["aktivitaet", "drucksache", "drucksache-text", "person",
                                           "plenarprotokoll", "plenarprotokoll-text", "vorgang",
                                           "vorgangsposition"])
def test_query_resources(resourcetypes):
    bta = bundestag_api.btaConnection()
    data = bta.query(resource=resourcetypes)
    assert isinstance(data, list)


def test_query_resources_num(resourcetypes):
    bta = bundestag_api.btaConnection()
    data = bta.query(resource=resourcetypes, num=150)
    assert len(data) == 150


def test_query_docID():
    bta = bundestag_api.btaConnection()
    data = bta.query(resource="vorgang", documentID=259520)
    assert data["id"] == "284323"


def test_query_docID_fail():
    with pytest.raises(ValueError):
        bta = bundestag_api.btaConnection()
        data = bta.query(resource="drucksache", documentID=259520)


def test_query_resources_noreturn(bta_object):
    bta = bta_object
    data = bta.query(resource="vorgang", dateend="2050-01-01", datestart="2050-01-01")
    assert data == "No data was returned."


def test_getdocument(bta_object):
    bta = bta_object
    data = bta.get_document(btid=264026)
    assert data["titel"] == "Rettungsschirm für Spitzenforschungseinrichtungen"


def test_getdocument_object(bta_object):
    bta = bta_object
    data = bta.get_document(btid=264026, rformat="object")
    assert data.doctype == "Kleine Anfrage"


with pytest.raises(TypeError):
    bta = bundestag_api.btaConnection()
    data = bta.get_document(btid="264026")


def test_searchplenary(bta_object):
    bta = bta_object
    erl = []
    data = bta.search_plenaryprotocol(num=50)
    if len(data) == 50:
        erl.append("False")
    else:
        erl.append("True")
    data = bta.search_plenaryprotocol(num=10, datestart="2022-05-01", dateend="2022-05-11")
    if len(data) == 10:
        erl.append("False")
    else:
        erl.append("True")
    erl.append(checkdates(data[randrange(10)]["datum"], "2022-05-11", dateE="2022-05-01"))
    data = bta.search_plenaryprotocol(num=10, rformat="object")
    tl = list(data.keys())
    if type(data[tl[randrange(9)]]) == bundestag_api.bta_wrapper.Plenarprotokoll:
        erl.append("False")
    else:
        erl.append("True")
    data = bta.search_plenaryprotocol(num=10, rformat="json", institution="BR")
    if data[randrange(10)]["herausgeber"] == "BR":
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 5 and not any(erl)


def test_getplenary(bta_object):
    bta = bta_object
    erl = []
    data = bta.get_plenaryprotocol(btid=5511)
    if data["dokumentnummer"] == "1024":
        erl.append("False")
    else:
        erl.append("True")
    data = bta.get_plenaryprotocol(btid=5511, rformat="object")
    tl = list(data.keys())
    if type(data[tl[randrange(9)]]) == bundestag_api.bta_wrapper.Plenarprotokoll:
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 2 and not any(erl)


def test_searchactivity(bta_object):
    bta = bta_object
    erl = []
    data = bta.search_activity(num=50)
    if len(data) == 50 and data[0]["typ"] == "Aktivität":
        erl.append("False")
    else:
        erl.append("True")
    data = bta.search_activity(num=10, datestart="2022-05-01", dateend="2022-05-11")
    if len(data) == 10:
        erl.append("False")
    else:
        erl.append("True")
    erl.append(checkdates(data[randrange(10)]["datum"], "2022-05-11", dateE="2022-05-01"))
    data = bta.search_activity(num=10, rformat="object")
    tl = list(data.keys())
    if type(data[tl[randrange(9)]]) == bundestag_api.bta_wrapper.Aktivitaet:
        erl.append("False")
    else:
        erl.append("True")
    data = bta.search_activity(num=10, rformat="json", institution="BT")
    if data[randrange(10)]["herausgeber"] == "BT":
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 5 and not any(erl)


def test_getactivity(bta_object):
    bta = bta_object
    erl = []
    data = bta.get_activity(btid=1618465)
    if data["aktivitaetsart"] == "Kleine Anfrage":
        erl.append("False")
    else:
        erl.append("True")
    data = bta.get_activity(btid=5511, rformat="object")
    tl = list(data.keys())
    if type(data[tl[0]]) == bundestag_api.bta_wrapper.Aktivitaet:
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 2 and not any(erl)


def test_searchperson(bta_object):
    bta = bta_object
    erl = []
    data = bta.search_person(num=50)
    if len(data) == 50 and data[0]["typ"] == "Person":
        erl.append("False")
    else:
        erl.append("True")
    data = bta.search_person(rformat="object")
    tl = list(data.keys())
    if type(data[tl[0]]) == bundestag_api.bta_wrapper.Person:
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 2 and not any(erl)


def test_getperson(bta_object):
    bta = bta_object
    erl = []
    data = bta.get_person(btid=7302)
    if data["nachname"] == "Hennig-Wellsow":
        erl.append("False")
    else:
        erl.append("True")
    data = bta.get_person(btid=7302, rformat="object")
    if type(data) == bundestag_api.bta_wrapper.Person:
        erl.append("False")
    else:
        erl.append("True")
    assert len(erl) == 2 and not any(erl)
