# -*- coding: utf-8 -*-


def _to_int(value):
    """Convert numeric IDs (delivered as strings by the API) to int; keep None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


class Person:
    """This class represents a German parliamentarian"""

    def __init__(self, dictionary):
        self.btid = _to_int(dictionary.get("id"))
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
        self.btid = _to_int(dictionary["id"])
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
                # The API delivers "autor_titel" (name) and "title" (name, role, faction)
                auan.append(a.get("autor_titel") or a.get("title") or a.get("titel"))
                auanid.append(_to_int(a.get("id")))
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
        self.btid = _to_int(dictionary["id"])
        self.activitytype = dictionary.get("aktivitaetsart")
        self.date = dictionary.get("datum")
        self.title = dictionary.get("titel")
        self.type = dictionary.get("typ")
        self.doctype = dictionary.get("dokumentart")
        self.parlsession = dictionary.get("wahlperiode")
        self.numprocedure = dictionary.get("vorgangsbezug_anzahl")
        # "vorgangsbezug" is optional and may be empty
        vorgangsbezug = dictionary.get("vorgangsbezug") or []
        self.procedure_reference = _to_int(vorgangsbezug[0].get("id")) if vorgangsbezug else None
        fundstelle = dictionary.get("fundstelle") or {}
        self.document_reference = _to_int(fundstelle.get("id"))

    def __str__(self):
        return f'{self.type}: ({self.btid}) {self.activitytype} - {self.title} - {self.date}'

    def __repr__(self):
        return f'Aktivitaet(btid={self.btid}, activitytype="{self.activitytype}")'

class Vorgang:
    """This class represents a legislative process in of the German federal parliaments"""

    def __init__(self, dictionary):
        self.btid = _to_int(dictionary["id"])
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
            # The last entry is the most recent assessment, e.g. "Nein, laut Verkündung (BGBl I)"
            latest = dictionary["zustimmungsbeduerftigkeit"][-1].split(",")[0].strip().lower()
            if latest == "ja":
                self.approvalnecessaryBool = True
            elif latest == "nein":
                self.approvalnecessaryBool = False
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
        self.btid = _to_int(dictionary["id"])
        self.date = dictionary.get("datum")
        self.docname = dictionary.get("dokumentart")
        self.continuation = dictionary.get("fortsetzung")
        self.course = dictionary.get("gang")
        self.Supplement = dictionary.get("nachtrag")
        self.title = dictionary.get("titel")
        self.instance = dictionary.get("typ")
        self.originator = dictionary.get("urheber")
        self.procedureID = _to_int(dictionary.get("vorgang_id"))
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
        self.btid = _to_int(dictionary["id"])
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
