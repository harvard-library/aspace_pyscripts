#!/usr/bin/python3

import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime
from os.path import exists, expanduser, dirname, realpath
import os
logname  = os.path.dirname(os.path.realpath(__file__)) + "/logs/missing_emails.log"
logging.basicConfig(filename=logname,level=logging.INFO)
main_log = logging.getLogger(__name__)
main_log.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(name)-12s: %(levelname)-8s %(asctime)s %(message)s'))
main_log.addHandler(console)

import requests
from boltons.dictutils import OMD
from asnake.aspace import ASpace
import pprint



def user_repo(user):
    global aspace
    admin = "Is an Admin" if user.is_admin else ""
    first_name = last_name =''
    try:
        first_name = user.first_name
    except AttributeError as ae:
        first_name = ''
    try:
        last_name = user.last_name
    except AttributeError as ae:
        last_name = ''
    info = "{} {} {} {}".format(user.username, first_name, last_name, admin)
    permissions = aspace.users(user.id).permissions
    keys = list(permissions.keys())
    for key in keys:
        if key in repos:
            missing[key].append(info)
        else:
            missing["unknown"].append(info)

def missing_report():
    global missing
    global repos
    for uri in missing.keys():
        if len(missing[uri]) > 0:
            line = repos[uri] if uri in repos else "Unspecified repository"
            for info in missing[uri]:
                line += "\n\t" + info
            main_log.info(line)

def main():
    global aspace
    global missing
    global repos
    user_ctr = miss_ctr = 0
    main_log.info('Beginning missing email check')
    aspace = ASpace()
    miss_ctr = 0;
    for repo in aspace.repositories:
        missing[repo.uri] = []
        repos[repo.uri] = repo.name
    for user in aspace.users:
        user_ctr += 1
        try:
            email = user.email
        except AttributeError as ae:
            user_repo(user)
            miss_ctr += 1
    main_log.info('Final count: of {} users, {} are missing emails'.format(user_ctr, miss_ctr))
    missing_report()

aspace = None
repos = {}
missing = {}
missing['unknown'] = []

main()


