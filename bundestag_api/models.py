# -*- coding: utf-8 -*-

class Person:
    """This class represents a German parliamentarian"""

    def __init__(self, dictionary):
        self.btid = dictionary.get("id")
        self._from_dict(dictionary)

    def _from_dict(self, dictionary):
        """Helper to parse dictionary data and set attributes."""
        self.lastname = dictionary.get("nachname")
        self.firstname = dictionary.get("vorname")
        self.basedate = dictionary.get("basisdatum")
        self.date = dictionary.get("datum")
        self.nameaddendum = dictionary.get("namenszusatz")
        self.legislativeperiod = dictionary.get("wahlperiode")

        # Simplified role and faction parsing
        mdbrole = False
        self.faction = None
        self.titel = None

        titel_str = dictionary.get("titel", "")
        titel_parts = titel_str.split(",")
        if len(titel_parts) > 1 and " MdB" in titel_parts[1]:
            mdbrole = True
            if len(titel_parts) > 2:
                self.faction = titel_parts[2].strip()
        
        person_roles = dictionary.get("person_roles")
        if not self.faction and person_roles and "fraktion" in person_roles[0]:
            self.faction = person_roles[0].get("fraktion")

        if self.firstname and titel_parts[0].split(self.firstname)[0] != "":
            self.titel = titel_parts[0].split(self.firstname)[0].strip()

        if person_roles:
            self.roles = [Role(r) for r in person_roles]
        elif mdbrole and self.legislativeperiod:
            self.roles = [Role({"funktion": "MdB",
                               "fraktion": self.faction,
                                "nachname": self.lastname,
                                "vorname": self.firstname,
                                "wahlperiode_nummer": self.legislativeperiod
                                })]
        else:
            self.roles = None

    def __repr__(self):
        return f"Person(btid={self.btid}, name='{self.firstname} {self.lastname}')"

    def returnroles(self):
        if not self.roles:
            return
        for r in self.roles:
            print(r.returnrole())


class Role:
    """This class presents a role in the German parliamentary system."""

    def __init__(self, dictionary):
        self.function = dictionary["funktion"]
        if "wahlperiode_nummer" in dictionary:
            self.legislativeperiod = dictionary.get("wahlperiode_nummer")
        self.nameaddendum = dictionary.get("namenszusatz")
        self.functionaddendum = dictionary.get("funktionszusatz")
        self.faction = dictionary.get("fraktion")
        self.federalstate = dictionary.get("bundesland")
        self.lastname = dictionary.get("nachname")
        self.firstname = dictionary.get("vorname")
        self.districtaddendum = dictionary.get("wahlkreiszusatz")
        self.department = dictionary.get("ressort_titel")

    def __str__(self):
        return f'Person: {self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""} - {self.function}'

    def __repr__(self):
        return f"Role(function='{self.function}', name='{self.firstname} {self.lastname}')"

    def returnrole(self):
        return (
            f'{self.firstname}{" " if self.nameaddendum!=None else ""}{self.nameaddendum if self.nameaddendum!=None else ""} {self.lastname} {"(" if self.faction!= None else ""}{self.faction if self.faction!= None else ""}{")" if self.faction!= None else ""},'
            f'{self.function}{" - " if self.functionaddendum!= None else ""}{self.functionaddendum if self.functionaddendum!= None else ""}{", " if self.department!= None else ""}{self.department if self.department!= None else ""}{" (" if self.federalstate!=None else ""}{self.federalstate if self.federalstate!=None else ""}{")" if self.federalstate!=None else ""}')


class Drucksache:
    """This class represents a document of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = int(dictionary["id"])
        self.publisher = dictionary.get("herausgeber")
        if self.publisher == "BT": self.publisher = "Bundestag"
        if self.publisher == "BR": self.publisher = "Bundesrat"
        
        self.originator = dictionary.get("urheber")
        self.author_nr = dictionary.get("autoren_anzahl")
        self.ressort = dictionary.get("ressort")
        self.date = dictionary.get("datum")
        self.legislativeperiod = dictionary.get("wahlperiode")
        self.title = dictionary.get("titel")
        self.doctype = dictionary.get("drucksachetyp")
        
        self.reference = dictionary.get("fundstelle")
        self.pdf_url = None
        if self.reference and "pdf_url" in self.reference:
            self.pdf_url = self.reference.get("pdf_url")

        self.docname = dictionary.get("dokumentart")
        self.instance = dictionary.get("typ")
        self.docnumber = dictionary.get("dokumentnummer")
        
        self.author = None
        self.authordisplay = None
        self.authorid = None
        if "autoren_anzeige" in dictionary:
            auan = []
            auanid = []
            for a in dictionary["autoren_anzeige"]:
                auan.append(a["titel"])
                auanid.append(a["id"])
            self.author = auan
            self.authorid = auanid
            self.authordisplay = dictionary["autoren_anzeige"]
        self.text = dictionary.get("text")

    def __str__(self):
        return f'{self.instance}: ({self.btid}) {self.doctype} - {self.title} - {self.date}'

    def __repr__(self):
        return f'{self.instance}: ({self.btid}) {self.doctype} - {self.title} - {self.date}'


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

    def __repr__(self):
        return f'Aktivitaet(btid={self.btid}, activitytype="{self.activitytype}")'

class Vorgang:
    """This class represents a legislative process in of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        self.process_positions = []
        self.date = dictionary.get("datum")
        self.title = dictionary.get("titel")
        self.instance = dictionary.get("typ")
        self.processtype = dictionary.get("vorgangstyp")
        self.initiativ = dictionary.get("initiative")
        self.abstract = dictionary.get("abstract")
        self.archive = dictionary.get("archiv")
        self.status = dictionary.get("beratungsstand")
        self.descriptor = dictionary.get("deskriptor")
        self.gesta = dictionary.get("gesta")
        self.effectivedate = None
        if dictionary.get("inkrafttreten"):
            self.effectivedate = dictionary["inkrafttreten"][0]["datum"]
        self.kom = dictionary.get("kom")
        self.notification = dictionary.get("mitteilung")
        self.eucouncilnr = dictionary.get("ratsdok")
        self.subject = dictionary.get("sachgebiet")
        self.announcement = dictionary.get("verkuendung")
        self.legislativeperiod = dictionary.get("wahlperiode")
        
        self.approvalnecessary = None
        self.approvalnecessaryBool = None
        self.urgency = None
        if dictionary.get("zustimmungsbeduerftigkeit"):
            self.approvalnecessary = dictionary["zustimmungsbeduerftigkeit"]
            self.approvalnecessaryBool = dictionary["zustimmungsbeduerftigkeit"][len(
                dictionary["zustimmungsbeduerftigkeit"])-1].split(",")[0]
            if any("bes.eilbed." in s for s in dictionary["zustimmungsbeduerftigkeit"]):
                self.urgency = True

    def show_positions(self):
        if not self.process_positions:
            return
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
        self.date = dictionary.get("datum")
        self.docname = dictionary.get("dokumentart")
        self.continuation = dictionary.get("fortsetzung")
        self.course = dictionary.get("gang")
        self.Supplement = dictionary.get("nachtrag")
        self.title = dictionary.get("titel")
        self.instance = dictionary.get("typ")
        self.originator = dictionary.get("urheber")
        self.procedureID = dictionary.get("vorgang_id")
        self.processposition = dictionary.get("vorgangsposition")
        self.processtype = dictionary.get("vorgangstyp")
        
        self.institution = None
        if "zuordnung" in dictionary:
            if dictionary["zuordnung"] == "BT":
                self.institution = "Bundestag"
            elif dictionary["zuordnung"] == "BR":
                self.institution = "Bundesrat"
            elif dictionary["zuordnung"] is not None and dictionary["zuordnung"] != "BR" and dictionary["zuordnung"] != "BT":
                self.institution = dictionary["zuordnung"]

    def __str__(self):
        return f'{self.instance}: ({self.procedureID}) {self.processtype} - {self.title} - {self.date}'

    def __repr__(self):
        return f'Vorgangsposition(btid={self.btid}, procedureID={self.procedureID})'


class Plenarprotokoll:
    """This class represents a plenary protocol of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = dictionary["id"]
        self.date = dictionary.get("datum")
        self.docname = dictionary.get("dokumentart")
        self.title = dictionary.get("titel")
        self.instance = dictionary.get("typ")
        
        self.publisher = dictionary.get("herausgeber")
        if self.publisher == "BT": self.publisher = "Bundestag"
        if self.publisher == "BR": self.publisher = "Bundesrat"

        self.legislativeperiod = dictionary.get("wahlperiode")
        self.text = dictionary.get("text")
        
        self.reference = dictionary.get("fundstelle")
        self.pdf_url = None
        if self.reference and "pdf_url" in self.reference:
            self.pdf_url = self.reference.get("pdf_url")

        self.sessioncomment = dictionary.get("sitzungsbemerkung")
        self.docnumber = dictionary.get("dokumentnummer")

    def __str__(self):
        return f'{self.docname}: {self.docnumber} - {self.title} - {self.date}'

    def __repr__(self):
        return f'Plenarprotokoll(btid={self.btid}, docnumber="{self.docnumber}")'
