#!/usr/bin/python3

import sys, getopt, attr, structlog, yaml, traceback
import logging
from datetime import datetime, timezone
import dateutil.parser
from os.path import exists, expanduser, dirname, realpath
import os

DATEFORMAT ='%Y-%m-%d %H:%M:%S'
MAILSUBJECT = "Batch Processing of ArchivesSpace PDFs Completed"
relative_dir =  os.path.dirname(os.path.realpath(__file__))
logname_template = os.path.dirname(os.path.realpath(__file__)) + "/logs/pdfStorer_{}.log"
# set up logging here, so nothing can grab it first!
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")), format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s',datefmt=DATEFORMAT, level=logging.WARNING)


main_log = logging.getLogger(__name__)
main_log.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(name)-12s: %(levelname)-8s %(asctime)s %(message)s'))
main_log.addHandler(console)

from requests import Session
from boltons.dictutils import OMD
from asnake.aspace import ASpace
from utils.utils import get_latest_update, already_running, get_filetype, send_mail
from utils.savestate import savestate
from s3_support.s3 import S3
from SolrClient import SolrClient
import pprint




pp =  pprint.PrettyPrinter(indent=4)
omd = ''
ctr = 0
counters = {'created': 0, 'updated': 0, 'deleted': 0, 'errors':0}
repo_ctr = 0
pidfilepath = 'pdfstorerdaemon.pid'
all = False
repo_code = None
http = Session()

def add_to_ss(key, dt):
    """Convert the incoming date to ISO format
    for serialization before saving
    """
    date = dt
    if type(date) is datetime:
        date = dt.isoformat()
    ss.obj[key] = date

def remove_from_ss(key):
    """ remove the key
    """
    ss.pop(key, None)

def get_details():
    '''looks for values in pdf_store.yml '''
    yaml_path = "pdf_store.yml"
    omd = OMD()
    # Fallback to defaults for local devserver
    omd.update({
        's3_yaml': 's3.yml',
        'tmpdir': './tmp/',
        'instance': 'dev'
    })
    if exists(yaml_path):
        with open(yaml_path, 'r') as f:
            omd.update_extend(yaml.safe_load(f))
    return omd

def get_latest_datetm(resource_uri):
    query = "resource:\"{uri}\" OR uri:\"{uri}\"".format(uri=resource_uri)
    res = solr.query(omd.get('solr_collection'), {
        'q': query,
        'rows' : 1,
        'sort': 'system_mtime desc'
    })
    dttm = None
    if res.get_results_count() == 1:
        date = res.docs[0]['system_mtime']
        dttm = datetime.strptime(date,"%Y-%m-%dT%H:%M:%SZ")
        dttm = dttm.astimezone(tz=None)
    return dttm


def get_pdf(uri, directory, name):
    """Fetch the PDF from the PUI and write it to the directory
    with the supplied name
    The 'pdfurl' value is a string to be formated with the uri
    """
    # check for the directory and name being non-empty?
    filename = directory + name + ".pdf"
    url = omd.get('pdfurl').format(uri)
    main_log.info(f"Fetching: {url}")
    r = http.get(url, stream=True)
    with open(filename, 'wb') as fd:
        for chunk in r.iter_content(3000):
          fd.write(chunk)

def needs_update(uri,res_ident, name):
    global pdf_upd
    if all:
        pdf_upd += 1
        return True
    last_dttm = None
    if res_ident in ss.obj:
        last_dttm =  dateutil.parser.parse(ss.obj[res_ident])
    else:
        last_dttm = s3.get_datetm(name + '.pdf')
    if not last_dttm:
        return True
    last = startDateTime or last_dttm
    dttm = get_latest_datetm(uri)
    if dttm is None or last > dttm:
        return False
    else:
        pdf_upd += 1
        return True

def process_repository(repo):
    global ctr
    global pdf_upd
    main_log.info("Starting repository {} {} {}".format(repo.id, repo.repo_code, repo.name))
    pdf_ctr = 0
    pdf_del = 0
    pdf_upd = 0
    for resource in repo.resources:
        pdf = process_resource(resource, repo.publish)
        if pdf:
            pdf_ctr +=1
        else:
            pdf_del +=1
        ctr +=1
        if ctr % 10 == 0:
            ss.save()
    ss.save() # always save at end of repo
    main_log.info("Finished repository {} {} {}. {} published pdfs  {} unpublished resources {} pdfs needing updating".format(repo.id, repo.repo_code, repo.name,pdf_ctr, pdf_del, pdf_upd))

# Removing the file
def remove_file(name, res_ident):
     s3.remove(name + ".pdf")
     if res_ident in ss.obj:
         counters['deleted'] +=1
         remove_from_ss(res_ident)

def process_resource(resource, publish):
    """Determine whether to get this resource's pdf;
    if so, pass to get_pdf with a directory and name
    """
    res_ident  = resource.uri.replace("/", "_")
    try:
        name = resource.ead_id
    except AttributeError as ae:
        name = res_ident
        if resource.level != 'collection':
            remove_file(name, res_ident)
            return False
        if publish and resource.publish:
            main_log.warning("No EAD ID for \t{}; \tname is: {}".format(resource.title,name));
    except Exception as e:
        raise e
    published = False
    if publish and resource.publish:
        # resource.uri is like /repositories/4/resource/34
        if needs_update(resource.uri, res_ident,name):
            get_pdf(resource.uri, tmpdir, name)
            key = name + ".pdf"
            filepath = tmpdir + key
            filetype = get_filetype(filepath)
            if filetype.upper().startswith('PDF'):
                s3.upload(filepath, key)
                #pp.pprint(s3.get_object_head(key))
                add_to_ss(res_ident,  datetime.now(timezone.utc))
                os.remove(filepath)
                counters['created'] += 1
                published = True
            else:
                logging.error("Retrieved file {} for resource {}  has filetype of {}, not PDF".format(filepath, resource.uri, filetype))
                remove_file(name, res_ident)
                counters['errors'] += 1
        else:
            published = True # even if we don't need a new pdf, we count it as "published"
    else:
        remove_file(name, res_ident)
    return published

def do_it():
    global omd
    global s3
    global ss # the pickle
    global tmpdir
    global ctr
    global solr
    global repo_ctr
    omd = get_details()
    main_log.debug("temp: {} url: {} s3 yaml:{} ".format(omd.get('tmpdir'), omd.get('pdfurl'), omd.get('s3_yaml')))
    instance =  omd.get('instance')
    main_log.info("Instance: " + instance)
    main_log.info("retrieving saved state, if any, at {}".format(omd.get("savedstate")))
    ss = savestate(omd.get("savedstate"))
    if all:
        ss.clear()
    solr = SolrClient(omd.get('solr_url'))
    tmpdir = omd.get('tmpdir')
    try:
        s3 = S3(configpath = omd.get('s3_yaml'))
    except Exception as e:
        raise e
    aspace = ASpace()
    for repo in aspace.repositories:
        if all or repo_code is None  or repo.repo_code == repo_code:
            process_repository(repo)
            repo_ctr += 1
    ss.save() # last time for good luck!

def main():
    mailmsg = ''
    global console
    console.setLevel(logging.INFO)
    os.chdir(relative_dir)
    start_msg = 'Beginning PDF storing run: all is %r, repo_code is %r , from is %r, to is %r' % (all, repo_code, efrom, eto)
    main_log.info(start_msg)
    mail_msg = datetime.now().strftime(DATEFORMAT) + " " + start_msg + "\n\t Logfile is at {}/logs/pdf_storer_{}.log".format(os.getcwd(), datetime.today().strftime("%Y%m%d"))
    console.setLevel(logging.ERROR)
    # "mute" the INFO, DEBUG level of sub-components
    logging.getLogger("connectionpool.py").setLevel(logging.WARNING)
    clean = True
    try:
        do_it()
        console.setLevel(logging.INFO)
        end_msg = "Completed. Processed {} repositories, {} resources: {} pdfs created, {} pdfs deleted, {} errors".format(repo_ctr, ctr, counters['created'], counters['deleted'], counters['errors'])
        main_log.info(end_msg)
        mail_msg = mail_msg + "\n" + datetime.now().strftime(DATEFORMAT) + " " + end_msg
    except Exception as e:
        tb = sys.exc_info()
        try:
            end_msg = "Processed {} repositories, {} resources: {} pdfs created, {} pdfs deleted, {} errors".format(repo_ctr, ctr, counters['created'], counters['deleted'], counters['errors'])
        except Exception as em:
            end_msg = "Problem creating the completion line {}".format(em)
        error_msg = "An Error was encountered: ({}). Processing halted\n {}".format(e, end_msg)
        traceback.print_exc()
        main_log.error(error_msg)
        mail_msg = mail_msg + "\n" + datetime.now().strftime(DATEFORMAT) + " " + error_msg
        clean = False
    if (clean):
        if efrom and eto:
            send_mail(eto, efrom, MAILSUBJECT, mail_msg)
    else:
        if efrom and eto:
            send_mail(eto, efrom, MAILSUBJECT +' WITH ERROR', mail_msg)
        raise Exception("error")


if already_running(pidfilepath):
    main_log.error(sys.argv[0] + " already running.  Exiting")
    print(sys.argv[0] + " already running.  Exiting")
    sys.exit()
try:
    opts, args = getopt.getopt(sys.argv[1:],"har:t:f:d:",["repo=", "help=", "from=", "to=", "date="])
except getopt.GetoptError:
    print('pdfStorer.py [-r <repository code>] [-a (if clearing and starting from scratch)] [-f <from address> -t <to address>] [-d <starting at datetime YYYYMMDDTHH[MM]]')
    sys.exit(2)
efrom = eto = startDateTime = None
for opt,arg in opts:
    if opt in ("-h", "--help"):
        print('pdfStorer.py [-r <repository code> -a [if clearing and starting from scratch] -d <start date in ISO format> [-f <from email> -t <to email>]]')
        sys.exit(0)
    elif opt == '-a':
        all = True
    elif opt in ("-r", "--repo"):
        repo_code = arg.upper()
    elif opt in ("-f", "--from"):
        efrom = arg
    elif opt in ("-t", "--to"):
        eto = arg
    elif opt in ("-d", "--date"):
        startDateTime = dateutil.parser.parse(arg)
if not efrom or not eto:
    efrom = eto = None
try:
    main()
    os.unlink(pidfilepath)
    sys.exit(0)
except Exception:
    os.unlink(pidfilepath)
    sys.exit(1)
