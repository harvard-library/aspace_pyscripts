import os, sys, time, pickle, magic
import pprint
from SolrClient import SolrClient #https://github.com/moonlitesolutions/SolrClient
from datetime import datetime

pp = pprint.PrettyPrinter(indent=4)

# check to see if process is already running  (from RockefellerArchives's 'checkPid')
def already_running(pidfilepath):
    currentPid = str(os.getpid())
    if os.path.isfile(pidfilepath):
        pidfile = open(pidfilepath, "r")
        for line in pidfile:
            pid=int(line.strip())
        if pid_exists(pid):
            return True;
        else:
            with open(pidfilepath, 'w') as pf:
                pf.write(currentPid)
    else:
         with open(pidfilepath, 'w') as pf:
             pf.write(currentPid)
    return False



# get the file type
def get_filetype(filepath):
    return  magic.from_file(filepath)


# get the latest update for a resource from solr
def get_latest_update(url,collection, query):
    dttm = None
    solr = SolrClient(url)
    res = solr.query(collection, {
            'q': query,
            'rows': 1,
            'sort': 'system_mtime desc'
    })
    pp.pprint(res.get_results_count())
    
    if res.get_results_count() == 1:
        pp.pprint(res.docs[0]['system_mtime'])
        date = res.docs[0]['system_mtime']
        dttm = datetime.strptime(date,"%Y-%m-%dT%H:%M:%SZ")
        pp.pprint(dttm)
    return dttm

def pid_exists(pid):
    """ examines the linux /proc/{pid}/status file, if it exists.
    Code "borrowed" from psutils, specifically 
    https://github.com/giampaolo/psutil/blob/1b5f8d55d22167d640eeb52d0b82f69dec83d210/psutil/_pslinux.py
    """
    if pid == 0:
        return True
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == 3: # ESRCH
            return False
        elif err.errno == 1:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH) therefore we should never get
            # here. If we do let's be explicit in considering this
            # an error.
            raise err
    else:
        procpath = "/proc/%s/status" % pid
        try:
            with open(procpath, 'rb') as f: 
                for line in f:
                    if line.startswith(b"Tgid:"):
                        tgid = int(line.split()[1])
                        # If tgid and pid are the same then we're
                        # dealing with a process PID.
                        return tgid == pid
                raise ValueError("'Tgid' line not found in %s" % procpath)
        except (EnvironmentError, ValueError):
            return pid in [int(x) for x in os.listdir(b(get_procfs_path())) if x.isdigit()]


#  h/t Tim Elliot of Harvard's Library Technology Services
def send_mail(mailTo, mailFrom, subject, message = False):
    """ sends mail.
     Parameters
        mailTo       Email address to send message to
        mailFrom     Email address to use as the 'From'
        subject      Message to appear in subject line
        message      Optional, the subject we be used in the
        body of the email if message is not set
    """
    import smtplib, re
    from email.mime.text import MIMEText

    # Create a text/plain message
    msgEmail = MIMEText(message)
    
    msgEmail['Subject'] = subject
    msgEmail['From']    = mailFrom
    msgEmail['To']      = mailTo
        
    # Convert scalar to array if more than 1 address is used
    matched = re.match('.+,.+', mailTo)
    if matched != None:
        mailTo = mailTo.split(',')
        
    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(mailFrom, mailTo, msgEmail.as_string())
    smtp.quit()            

    return
 
