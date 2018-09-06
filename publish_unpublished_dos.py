#!/usr/bin/python3
#
#   This is a one-off script that is used to set the 'publish' flag to True for
#   digital objects (and their file versions) for a particular repository
#
#TODO: parameterize the repository number
#TODO: (future) parameterize the search params and/or what gets modified
#
import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime
from os.path import exists, expanduser, dirname, realpath
import os
import pprint
import json
from asnake.aspace import ASpace

pp = pprint.PrettyPrinter(indent=4)
repo_id = '/repositories/8'

aspace = ASpace()
repo = aspace.repositories(8)
yn = input("Repository " + repo.name + " continue? Y/N: ")
if yn.lower() != 'y':
    print("... exiting")
    sys.exit(0)
ctr = 0
for do in repo.search.with_params(q="primary_type:digital_object AND publish:false"):
    ctr += 1
    do_json = json.loads(do.json()['json'])
    do_uri = do_json['uri']
#    print(do_uri)
    for fv in do_json['file_versions']:
        fv['publish'] = True
    do_json['publish'] = True
    print("Updating {} [{}]".format(do.title, do_uri))
    resp = aspace.client.post(do_uri, json= do_json)
    if resp.status_code == 200:
        print("\t...Updated")
    else:
        print("\tUNABLE TO UPDATE; status code: {}".format(resp.status_code))
print(str(ctr) + " digital objects updated")

        
