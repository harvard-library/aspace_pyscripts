#!/usr/bin/python3

import sys, getopt, attr, structlog, yaml
import logging
from datetime import datetime

# set up logging here, so nothing can grab it first!
logging.basicConfig(filename="logs/pdfStorer_{}.log".format(datetime.today().strftime("%Y%m%d")), format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S', level=logging.WARNING)


main_log = logging.getLogger(__name__)
main_log.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(name)-12s: %(levelname)-8s %(asctime)s %(message)s'))
main_log.addHandler(console)

import requests
from boltons.dictutils import OMD
from os.path import exists, expanduser
import os
from asnake.aspace import ASpace
from utils.utils import get_latest_update, already_running, get_filetype
from utils.pickler import pickler
from s3_support.s3 import S3
from SolrClient import SolrClient
import pprint




pp =  pprint.PrettyPrinter(indent=4)
omd = ''
ctr = 0
counters = {'created': 0, 'deleted': 0, 'errors':0}
pidfilepath = 'pdfstorerdaemon.pid'
all = False
repo_code = None

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
    return dttm
        

def get_pdf(uri, directory, name):
    """Fetch the PDF from the PUI and write it to the directory
    with the supplied name
    The 'pdfurl' value is a string to be formated with the uri
    """
    # check for the directory and name being non-empty?
    filename = directory + name + ".pdf"
    url = omd.get('pdfurl').format(uri)
    r = requests.get(url, stream=True)
    with open(filename, 'wb') as fd:
        for chunk in r.iter_content(3000):
          fd.write(chunk)
          
def needs_update(uri, last_dttm):
    global pdf_upd
    dttm = get_latest_datetm(uri)
    if dttm is None or last_dttm > dttm:
        return False
    else:
        pdf_upd += 1
        return True

def process_repository(repo):
    global ctr
    main_log.info("Starting repository {} {} {}".format(repo.id, repo.repo_code, repo.name))        
    pdf_ctr = 0
    pdf_del = 0
    global pdf_upd
    pdf_upd = 0
    for resource in repo.resources:
        pdf = process_resource(resource, repo.publish)
        if pdf:
            pdf_ctr +=1
        else:
            pdf_del +=1
        ctr +=1
        if ctr % 10 == 0:
            pkl.save()
    pkl.save() # always save at end of repo
    main_log.info("Finished repository {} {} {}. {} published pdfs  {} unpublished resources {} pdfs needing updating".format(repo.id, repo.repo_code, repo.name,pdf_ctr, pdf_del, pdf_upd))

def process_resource(resource, publish):
    """Determine whether to get this resource's pdf;
    if so, pass to get_pdf with a directory and name
    """
    res_ident  = resource.uri.replace("/", "_")
    try:
        name = resource.ead_id 
    except AttributeError as ae:
        name = res_ident
        if publish:
            main_log.warning("No EAD ID for \t{}; \tname is: {}".format(resource.title,name));
    except Exception as e:
        raise e
    published = False
    if publish and resource.publish:
        # resource.uri is like /repositories/4/resource/34
        if  all or not (res_ident in pkl.obj) or needs_update(resource.uri, pkl.obj[res_ident]):
            get_pdf(resource.uri, tmpdir, name)
            key = name + ".pdf"
            filepath = tmpdir + key
            filetype = get_filetype(filepath)
            if filetype.upper().startswith('PDF'):
                s3.upload(filepath, key)
                #pp.pprint(s3.get_object_head(key))
                pkl.obj[res_ident] = datetime.utcnow()
                os.remove(filepath)
                counters['created'] += 1
                published = True
            else:
                logging.error("Retrieved file {} for resource {}  has filetype of {}, not PDF".format(filepath, resource.uri, filetype))
                counters['errors'] += 1
        else:
            published = True # even if we don't need a new pdf, we count it as "published"
    else:
        s3.remove(name)
        if res_ident in pkl.obj:
            counters['deleted'] +=1
            pkl.obj.pop(res_ident, None)
    return published
    

def main():
    global omd
    global s3
    global pkl # the pickle
    global tmpdir
    global ctr
    global solr
    global console
    console.setLevel(logging.INFO)
    main_log.info('Beginning PDF storing run: all is %r, repo_code is %r' % (all, repo_code)) 
    console.setLevel(logging.ERROR)
    # "mute" the INFO, DEBUG level of sub-components
    logging.getLogger("connectionpool.py").setLevel(logging.WARNING)
    omd = get_details()
    main_log.debug("temp: {} url: {} s3 yaml:{} ".format(omd.get('tmpdir'), omd.get('pdfurl'), omd.get('s3_yaml')))
    instance =  omd.get('instance')
    main_log.info("Instance: " + instance)
    main_log.info("retrieving pickle, if any")
    pkl = pickler(omd.get("pickle"))
    if all:
        pkl.clear();
    else:
        solr = SolrClient(omd.get('solr_url'))
    tmpdir = omd.get('tmpdir')
    try:
        s3 = S3(configpath = omd.get('s3_yaml'))
    except Exception as e:
        raise e
    aspace = ASpace()
    repo_ctr = 0
    #TODO: allow for single repository
    for repo in aspace.repositories:
        if all or repo_code is None  or repo.repo_code == repo_code:
            process_repository(repo)
            repo_ctr += 1
    pkl.save() # last time for good luck!
    console.setLevel(logging.INFO)
    main_log.info("Completed. Processed {} repositories, {} resources: {} pdfs created, {} pdfs deleted, {} errors".format(repo_ctr, ctr, counters['created'], counters['deleted'], counters['errors']))
    sys.exit(0)

if already_running(pidfilepath):
    main_log.error(sys.argv[0] + " already running.  Exiting")
    print(sys.argv[0] + " already running.  Exiting")
    sys.exit()
try:
    opts, args = getopt.getopt(sys.argv[1:],"har:",["repo=", "help="])
except getopt.GetoptError:
    print('pdfStorer.py -r <repository code> -a [if clearing and starting from scratch]')
    sys.exit(2)
for opt,arg in opts:
    if opt in ("-h", "--help"):
        print('pdfStorer.py -r <repository code> -a [if clearing and starting from scratch]')
        sys.exit(0)
    elif opt == '-a':
        all = True
    elif opt in ("-r", "--repo"):
        repo_code = arg.upper()
main()
os.unlink(pidfilepath)
