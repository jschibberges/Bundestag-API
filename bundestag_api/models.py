# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 22:45:35 2024

@author: jschi
"""

# Classes


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

    def update_by_id(self, apikey=None):
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
        return (
            f'{self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""},'
            f'{self.function}{" - " if self.functionaddendum!= None else ""}{self.functionaddendum if self.functionaddendum!= None else ""}{", " if self.department!= None else ""}{self.department if self.department!= None else ""}{" (" if self.federalstate!=None else ""}{self.federalstate if self.federalstate!=None else ""}{")" if self.federalstate!=None else ""}')


class Drucksache:
    """This class represents a document of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = int(dictionary["id"])
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
        data = self.query("vorgangsposition", procedureID=self.btid)
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
            self.procedureID = dictionary["vorgang_id"]
        else:
            self.procedureID = None
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
        return f'{self.instance}: ({self.procedureID}) {self.processtype} - {self.title} - {self.date}'

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
