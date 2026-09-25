"""Model parsing tests using payloads shaped like the DIP OpenAPI specification."""
from bundestag_api.models import Aktivitaet, Drucksache, Vorgang, Vorgangsposition, Plenarprotokoll, Person


def test_drucksache_parses_authors_per_spec():
    d = Drucksache({
        "id": "68852",
        "autoren_anzeige": [
            {"id": "546", "title": "Kai Gehring, MdB, BÜNDNIS 90/DIE GRÜNEN", "autor_titel": "Kai Gehring"},
        ],
    })
    assert d.btid == 68852
    assert d.author == ["Kai Gehring"]
    assert d.authorid == [546]


def _aktivitaet(**overrides):
    data = {
        "id": "1493545", "aktivitaetsart": "Rede", "typ": "Aktivität",
        "dokumentart": "Plenarprotokoll", "wahlperiode": 19, "datum": "2020-12-11",
        "titel": "Olaf Scholz, Bundesmin., Bundesministerium der Finanzen",
        "vorgangsbezug_anzahl": 0, "fundstelle": {"id": "908"}, "person_id": "2413",
    }
    data.update(overrides)
    return data


def test_aktivitaet_without_vorgangsbezug():
    a = Aktivitaet(_aktivitaet())
    assert a.procedure_reference is None
    assert a.document_reference == 908


def test_aktivitaet_with_vorgangsbezug_and_str():
    a = Aktivitaet(_aktivitaet(vorgangsbezug=[{"id": "84393", "titel": "x", "vorgangstyp": "y"}],
                               vorgangsbezug_anzahl=1))
    assert a.procedure_reference == 84393
    assert "Rede" in str(a)
    assert "Aktivität" in str(a)


def test_ids_are_integers_across_models():
    assert Vorgang({"id": "84343"}).btid == 84343
    vp = Vorgangsposition({"id": "173376", "vorgang_id": "84343"})
    assert vp.btid == 173376 and vp.procedureID == 84343
    assert Plenarprotokoll({"id": "908"}).btid == 908
    assert Person({"id": "1728", "titel": ""}).btid == 1728


def test_vorgang_approval_is_boolean():
    v = Vorgang({"id": "1", "zustimmungsbeduerftigkeit": [
        "Ja, laut Gesetzentwurf (Drs 20/1)", "Nein, laut Verkündung (BGBl I)"]})
    assert v.approvalnecessaryBool is False
    v = Vorgang({"id": "1", "zustimmungsbeduerftigkeit": ["Ja, laut Gesetzentwurf (Drs 20/1)"]})
    assert v.approvalnecessaryBool is True
    assert Vorgang({"id": "1"}).approvalnecessaryBool is None


def test_person_role_without_function():
    """Live data contains person_roles entries without 'funktion' (despite the spec)."""
    p = Person({"id": "1", "nachname": "Muster", "vorname": "Anna", "titel": "Anna Muster, MdB, SPD",
                "person_roles": [{"nachname": "Muster", "vorname": "Anna", "fraktion": "SPD"}]})
    assert p.roles[0].function is None
    assert "Muster" in p.roles[0].returnrole()
