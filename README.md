# aspace_pyscripts
Python scripts to support ongoing [ArchivesSpace](http://www.archivesspace.org) work at Harvard.

The first script is designed to create PUI-side PDF files to be stored in an AWS S3 bucket, so that they can be served from the Harvard's ArchivesSpace [Public User Interface](https://github.com/harvard-library/aspace-hvd-pui), as opposed to generating them on-the-fly.

This work depends heavily on [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake).

Functionality that is potentially useful for additional scripts has been factored out into sub-folders.

## Requirements and Dependencies

These scripts were written with Python 3.6.5

The following python libraries must be installed; they are all available in [PyPi](https://pypi.org):
* ArchivesSnake  
* boto3
* SolrClient
* python-magic

There is a [bash script](.bin/install_libraries.sh) provided for installing these libraries on the **user** level.

### Important Note:

The scripts in this repository that use ArchivesSnake are relying on there being an **.archivessnake.yml** configuration file in the home directory of the user. 
An example configuration file:

``` yaml
baseurl: http://localhost:4567
username: admin
password: admin
```

## <a name="installation">Installation</a>

* Make sure you have Python v 3.6.5 or higher installed, with the appropriate PIP tool
* Clone or download this repository as a zip
* Install the required python libraries
* Create **.archivessnake** with the baseurl, username, and password for your ArchivesSpace instance
* Create **pdf_store.yml** and **s3.yml**, using the included templates.

## Script: Batch-create and store PDFs

[pdfStorer.py](./pdfStorer.py) runs through one or all repositories, creating a PDF and storing it in an AWS S3 bucket when the Resource is marked as **published**, and removing the analogous PDF from the S3 bucket if the Resource has been marked as **unpublished**.

The script uses ~~[pickle](https://docs.python.org/3.5/library/pickle.html)~~ the **json** library in the `utils/savestate.py` script to create a file, `pdfs/savedstate.json`  to keep track of the last time that the PDF was created for the resource. 
However, if that file is missing, or the targeted resource isn't in it, the code will query the bucket for the last update; the combination of these two mechanisms  allows using  a cron job to create a new PDF if the resource is subsequently updated. 

### Use:

```bash
python3 pdfStorer.py [-a] [-r {repository_code}] [-t {email_address -f {email_address}]
```

| Flag | Description |
| --- | ---|
| -a |   clears the pickle file completely.  Use this if you want to completely refresh your S3 PDF holdings|
| -r {repository_code} |  For those institutions (like Harvard :smile:) that have more than one repository, you may choose to run this script serially for each repository (or just some of them).|
| -t {email_address}| Address to receive a completion message |
| -f {email_address}| the "From" address for that completion message|
 
 **Note** that, at the moment, only *one* instance of the script may run at a time.
 
 ### Configuration:
 
  This script requires two yaml files: **pdf_store.yml** (see [template](pdf_store.yml.template)), which is expected to be in the same directory as the script, and **s3.yml** (see [template](s3.yml.template)), which can be anywhere, as its path is specified in **pdf_store.yml**
  
  At the moment, the logging configuration is hard-coded such that the logs will be written to the **/logs** folder, and have the format **pdf_storer_YYYYMMDD.log**. This may change in subsequent releases.
  
 **In addition**, the *already_running* function in the [utilities subpackage](utils/utils.py), which is used to determine if there already is a **pdfStorer** process running, assumes that the operating system is linux.  Feel free to fork and contribute back! 

## Script: Identify Users without emails

[missing_emails.py](./missing_emails.py) runs through ArchivesSpace's entire **User** table, identifies those user records that have an empty or null **email** field, and reports out, sorting by Repository.

### Use:

```bash 
python3 missing_emails.py
```

The results are reported in *logs/missing_emails.log*.

### Configuration:

This script uses ArchivesSnake, so the **.archivessnake** file (as defined above in the *<a href="#installation">Installation</a>* section) must be present.

## Script: Report permissions for all or selected users

[report_permissions.py](./report_permissions.py) reports on the permissions granted to users, by repository.  If no usernames are specified, the entire user list will be reported on.

### Use:

```bash
python3 report_permissions.py   # to report on all users
```
**OR**
```bash
python3 report_permissions.py "username1,username2,username3"  # a comma-delimited list on those you want reports on
```

The results are reported in *logs/report_permssions.log*.*.

### Configuration:

This script uses ArchivesSnake, so the **.archivessnake** file (as defined above in the *<a href="#installation">Installation</a>* section) must be present.


## Reusable functionality

### Handling S3 buckets

The [S3](s3_support/S3.py) class is used to manage an S3 bucket. An S3 object can be instantiated with keyword arguments as follows:

| Key | Value|
| -- | -- |
|configpath | The filepath to an **s3.yml** file |
|accesskey | The AWS S3 accesskey|
|secret| The AWS S3 secret |
| bucket | The name of the bucket to be addressed |

If you define **configpath**, and the s3.yml file is properly filled in, you need not use the other keyword arguments.

#### Use:
```python
  s3 = s3(configpath = '/my/s3.yml')
  s3.upload('/my/object/path', 'mykey')
  s3.get_object_head('mykey')
  s3.download('mykey', '/my/new/object/path')
  s3.remove('mykey')
```

| Method | Function |
| -- | -- |
|*initialize*| See above |
| download | downloads the file from the bucket|
| get_object_head | returns the **head_object** as defined by AWS|
| remove | removes the file from the S3 bucket|
| upload|  loads the file into the S3 bucket|


### Script: Empty out an S3 bucket

[bucket_clear.py](./bucket_clear.py) is a convenience script that empties a given S3 bucket without deleting the actual bucket.  

#### Use:

```bash
  python3 bucket_clear.py
```

If the **s3.yml** file cannot be found in the directory from which you are running this script, you will be asked for the filepath.

Once the script has found the S3 bucket as defined in the yml file, you will be asked to confirm.

### Pickler

The [pickler](utils/pickler.py) class was abstracted out so that more than one script could use it, rather than endlessly cutting and pasting.  The object to be "pickled" is assumed to be a *dict* datatype.

#### Use:
```python
  pkl = pickler(filepath)
  if 'foo' not in pkl.obj:
     pkl.obj['foo'] = 'bar'
  pkl.save()
```
where filepath is the path to the file that will hold/holds the pickled object. 

| Method | Function |
| -- | -- |
| *initialize* | Opens the file and invokes the *load* method. the pickled object.|
| load | loads the pickled object from the file. If the file doesn't exist, the object is created as an empty *dict* |
| clear | empties the object |
| save| pickles the object and writes it to the file (pickle.dump)|


### One-off scripts

Scripts that have been written for one-off or one-use purposes are included here as exemplars:
 * [publish_unpublished_dos.py](./publish_unpublished_dos.py)

### Utilities

[TBD: a description of the utilities in [utils/utils.py](utils/utils.py) ]


## Contributors

* Bobbi Fox: [@bobbi-SMR](https://github.com/bobbi-SMR) (maintainer)
* h/t [@helrond](https://github.com/helrond) of the Rockefeller Archives Center, some of whose ideas in https://github.com/RockefellerArchiveCenter/asExportIncremental I "borrowed".
