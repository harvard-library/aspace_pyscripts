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


def main():
    user_ctr = missing = 0
    main_log.info('Beginning missing email check')
    aspace = ASpace()
    for user in aspace.users:
        user_ctr += 1
        email = first_name = last_name =''
        try:
            email = user.email
        except AttributeError as ae:
            email = ''
        try:
            first_name = user.first_name
        except AttributeError as ae:
            first_name = ''
        try:
            last_name = user.last_name
        except AttributeError as ae:
            last_name = ''
        if email == '':
            missing += 1
            main_log.info('User {} [{} {}] missing email'.format(user.username, first_name, last_name))
    main_log.info('Final count: of {} users, {} are missing emails'.format(user_ctr, missing))
main()


