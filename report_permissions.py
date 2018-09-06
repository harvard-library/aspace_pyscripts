#!/usr/bin/python3

import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime
from os.path import exists, expanduser, dirname, realpath
import os
logname  = os.path.dirname(os.path.realpath(__file__)) + "/logs/report_permissions.log"
logging.basicConfig(filename=logname,level=logging.INFO)
main_log = logging.getLogger(__name__)
main_log.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(name)-12s: %(levelname)-8s %(asctime)s %(message)s'))
main_log.addHandler(console)
console.setLevel(logging.ERROR)

import requests
from boltons.dictutils import OMD
from asnake.aspace import ASpace
import pprint



def user_repo(user):
    global aspace
    email = first_name = last_name =''
    try:
        email = user.email
    except AttributeError as ae:
        email = "NONE"
    try:
        first_name = user.first_name
    except AttributeError as ae:
        first_name = ''
    try:
        last_name = user.last_name
    except AttributeError as ae:
        last_name = ''
    info = "{} {} {} {} is an Admin? {}".format(user.username, first_name, last_name, email, user.is_admin)
    try:
        permissions = aspace.users(user.id).permissions
        keys = list(permissions.keys())
        for key in keys:
            repo = repos[key]  if key in repos else key
            info += "\n\tRepository " + repo
            for perm in permissions[key]:
                info += "\n\t\t" + perm
    except AttributeError as ae:
        info += "\nNO PERMISSIONS"
    main_log.info(info)

def main():
    global aspace
    global repos
    global all
    global usernames
    user_ctr = 0
    main_log.info('Beginning report')
    aspace = ASpace()
    for repo in aspace.repositories:
        repos[repo.uri] = repo.name
    for user in aspace.users:
        if all or user.username in usernames:
            user_ctr += 1
            user_repo(user)
    main_log.info('Final count: of {} users'.format(user_ctr))


aspace = None
repos = {}
all = True
usernames = None

if len(sys.argv) == 2:
    all = False
    usernames = sys.argv[1].split(",")
main_log.info("All? {}. Usernames? {}".format(all, usernames))

main()


