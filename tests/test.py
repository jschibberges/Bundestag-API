# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 20:55:52 2022

@author: jschi
"""

import bundestag_api as bta

con = bta.BTA_Connection()

test = bta.btapi_query(apikey=con, resource="vorgang")
