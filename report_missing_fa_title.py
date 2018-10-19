#!/usr/bin/python3
""" Find all the collections (resources) that are missing a Finding Aid Title

This script reports out, by Repository, any Collection (Resource) 
that is missing a Finding Aid Title

"""



import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime
from os.path import exists, expanduser, dirname, realpath
import os
logname  = os.path.dirname(os.path.realpath(__file__)) + "/logs/missing_fa_title.log"
logging.basicConfig(filename=logname,level=logging.INFO)
main_log = logging.getLogger(__name__)
main_log.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter(' %(message)s'))
main_log.addHandler(console)
console.setLevel(logging.ERROR)

import requests
from boltons.dictutils import OMD
from asnake.aspace import ASpace
import pprint

DATEFORMAT ='%Y-%m-%d %H:%M:%S'

def check_resources(repo):
    ctr = 0
    miss_ctr = 0
    for resource in repo.resources:
        if not resource.publish:
            continue
        ctr += 1
        # check for ead_id first!!
        ead_id = ''
        try:
            ead_id = resource.ead_id
        except AttributeError as ae:
            main_log.error("Missing EAD ID: Resource {} {}".format(resource.uri, resource.title))
            continue
        fa_title = ''
        try:
            fa_title = resource.finding_aid_title
        except AttributeError as ae:
            fa_title = ''
        if fa_title.strip() == '':
            main_log.info("EADID {}, {}".format(ead_id, resource.title))
            miss_ctr += 1
    if ctr > 0:
        main_log.info("Out of {} published collections, {} are missing finding aid titles ({}%)".format(ctr, miss_ctr, (miss_ctr/ctr * 100)))
    else:
        main_log.info("No published collections found in {}".format(repo.name))

def main():
    ctr = 0
    main_log.info("Starting analysis {}".format(datetime.now().strftime(DATEFORMAT) ))
    aspace = ASpace()
    for repo in aspace.repositories:
        if not repo.publish:
            continue
        main_log.info("\n ****** Checking {} **********\n".format(repo.name))
        check_resources(repo)

    main_log.info("Completed! {}".format(datetime.now().strftime(DATEFORMAT) ))

main()
    
