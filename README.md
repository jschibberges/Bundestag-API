# Bundestag-API
A wrapper for the official Bundestag (German Federal Parliament) API in Python. It aim is to make querying the API a little easier in Python and relieve you from writing a lot of boilerplate code. 

It currently doesn't encompass a 100% of the lastest API parameters (see To-Do section) but aims to do so shortly.

The official information on the API can be found here: [Bundestag.de](https://dip.bundestag.de/%C3%BCber-dip/hilfe/api)

## Installation

### Pip install (recommended)

```
$ pip3 install bundestag_api
```

### Install from source

```
$ git clone https://github.com/jschibberges/Bundestag-API.git
$ cd Bundestag-API
$ pip install -r requirements.txt
```

## Setup
The API requires a key to authenticate requests. Personal key can be requested from the [Bundestag administration](mailto:parlamentsdokumentation@bundestag.de). However a general API key has been published that is valid until May 31st 2024. This key is automatically used until that date when no other key is supplied by the user.

## Usage
To save your API key create a connection-object, that you can then pass to the search functions. It will save you time, should you have to change API keys at a later date. If you don't supply an API key, the official API key will be used until 31st of May 2024. 
```
import bundestag_api
bta = bundestag_api.btaConnection() #if you want to use your own API key, supply it via "apikey="XXX")
data = bta.search_document()
for d in data:
    print(d["drucksachetyp"]+": "+d["titel"])
```
The query-function serves as a general search function that can be used to query all resources of the API. However, you will also have to specify all relevant parameters for your search. Data is returned as a dictionary (which can easily be saved as json). Minimally the resource type needs to specified.

For each resource type the api offers a search function and a get function are implemented. Get functions retrieve data for specific entity ids while search function offer all parameters that are relevant to the resource type. Example for documents (Drucksachen):
```
bta.search_document(datestart="2022-11-01",dateend="2022-11-01",institution="BT")
bta.get_document(btid=264030)
```
The Bundestag API serves 8 different resources though 2 are doubled with the only difference being whether the document text is returned via the API. 

### Activities ("Aktivität")
Get one or more activities by their ID
```
bta.get_activity(btid)
```
Search for documents by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_activity()
```
### Documents / Full-Text ("Drucksache")
Get one or more documents by their ID
```
bta.get_document(btid)
```
Search for documents by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_document()
```
"fulltext=True" can be passed as parameter to retrieve the full text of the document (if available). It defaults to False.

### Persons ("Person")
Get one or more persons by their ID
```
bta.get_person(btid)
```
Search for persons by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_person()
```
### Plenary Protocols / Full-Text ("Plenarprotokoll")
Get one or more plenary protocols by their ID
```
bta.get_plenaryprotocol(btid)
```
Search for plenary protocols by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_plenaryprotocol()
```
"fulltext=True" can be passed as parameter to retrieve the full text of the plenary protocols (if available). It defaults to False.

### Procedures ("Vorgang")
Get one or more procedures by their ID
```
bta.get_procedure(btid)
```
Search for procedures by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_procedure()
```
### Procedure Positions ("Vorgangsposition")
Get one or more procedure positions by their ID
```
bta.get_procedure(btid)
```
Search for procedure positions by specifying parameters for start and end date or institution. Important: The standard number of entities returned are 100. If more are desired, the "num" parameter must be set.
```
bta.search_procedure()
```

## ToDo's
- Implement filters for GESTA-Number, Beratungsstand, Fundstelle, Initiative, Ressort (federführend), Verkündungsblatt_Kürzel, Vorgangstyp, Vorgangstyp-Notation
- Implement retries before failure
- Implement sufficient unit tests
- Implement more extensive logging
- Parallelize requests for larger queries
- Extend Class methods