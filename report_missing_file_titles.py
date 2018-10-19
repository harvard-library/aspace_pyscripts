#!/usr/bin/python3
""" Find all the collections (resources) that are missing an EAD Filing Title

This script reports out, by Repository, any Collection (Resource) 
that is missing an EAD Filing Title

"""



import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime
from os.path import exists, expanduser, dirname, realpath
import os
logname  = os.path.dirname(os.path.realpath(__file__)) + "/logs/missing_file_title.log"
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
        ctr += 1
        file_title = ''
        try:
            file_title = resource.finding_aid_filing_title
        except AttributeError as ae:
            file_title = ''
        if file_title.strip() == '':
            main_log.info("EADID {}, {}".format(resource.ead_id, resource.title))
            miss_ctr += 1
    main_log.info("Out of {} collections, {} are missing filing titles ({}%)".format(ctr, miss_ctr, (miss_ctr/ctr * 100)))

def main():
    ctr = 0
    main_log.info("Starting analysis {}".format(datetime.now().strftime(DATEFORMAT) ))
    aspace = ASpace()
    for repo in aspace.repositories:
        main_log.info("\n ****** Checking {}".format(repo.name))
        check_resources(repo)

    main_log.info("Completed! {}".format(datetime.now().strftime(DATEFORMAT) ))

main()
    
