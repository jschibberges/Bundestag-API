# -*- coding: utf-8 -*-

import bundestag_api

bta = bundestag_api.btaConnection()

test = bta.btapi_query(resource="drucksache")


data = bta.get_document(btid=264035)

resourcetypes = ["aktivitaet", "drucksache", "drucksache-text", "person",
                 "plenarprotokoll", "plenarprotokoll-text", "vorgang",
                 "vorgangsposition"]
bta = bundestag_api.BTA_Connection("GmEPb1B.bfqJLIhcGAsH9fTJevTglhFpCoZyAArrhp")
data = bta.query(resource="vorgang")
data2 = bta.query(resource="vorgang", rformat="object")
dat2 = bta.query(resource="person", rformat="object")

for r in resourcetypes:
    dat2 = bta.query(resource=r, rformat="object")
