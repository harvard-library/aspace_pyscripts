from os.path import exists
import yaml
from boltons.dictutils import OMD
import boto3
from botocore.exceptions import ClientError
import dateutil.parser
import logging
from pprint import pprint
class S3:
    """ This class supports S3 activity on a SINGLE bucket.  
    It raises a ValueError if the credentails are invalid, or the bucket hasn't been created
    """
    def __init__(self, **kwargs):
        access = kwargs.get('accesskey', None)
        secret = kwargs.get('secret', None)
        bucket = kwargs.get('bucket', '')
        configpath = kwargs.get('configpath', None)
        omd = OMD()
        omd.update({
            'accesskey': access,
            'secret': secret,
            'bucket': bucket
        })
        if configpath is not None and exists(configpath):
            with open(configpath, 'r') as f:
                omd.update_extend(yaml.safe_load(f))
        self.access = omd.get('accesskey', access)
        self.secret = omd.get('secret', secret)
        bucket_name = omd.get('bucket',bucket)
        cd = None
        try:
            self.s3 = boto3.client('s3', aws_access_key_id=self.access, aws_secret_access_key=self.secret)
            self.bucket = boto3.resource('s3', aws_access_key_id=self.access, aws_secret_access_key=self.secret).Bucket(bucket_name)
            cd = self.bucket.creation_date
            # make sure you actually have a bucket
        except ClientError as e:
            raise ValueError(e.response['Error']['Message'])
        if cd is None:
            raise ValueError("This bucket [" + self.bucket.name + "] does not exist") 
        logging.getLogger("connectionpool.py").setLevel(logging.WARNING)
        logging.getLogger("connectionpool").setLevel(logging.WARNING)
    def __str__(self):
        if self.bucket:
            return "S3 bucket " + self.bucket.name
        else:
            return "S3 with no bucket!"
    
    def clear_bucket(self):
        #empties out the entire bucket
        self.bucket.objects.all().delete()

    def download(self,key, filepath):
        self.bucket.download_file(key, filepath)

    def get_datetm(self,key):
        """ returns None if it doesn't exist,
        otherwise returns a datetime object
        """
        datetm = None
        meta = self.get_key_metadata(key)
        if meta:
            datetm =  meta['LastModified']
            if type(datetm) is str:   # probably not needed anymore,but...
                datetm = dateutil.parser.parse(datetm)
        return datetm

    def get_key_metadata(self,key):
        head = None
        try:
            head = self.s3.head_object(Bucket=self.bucket.name, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise
        return head

    def remove(self, key):
        self.s3.delete_object(Bucket = self.bucket.name, Key = key)

    def upload(self,filepath, key):
        self.bucket.upload_file(filepath, key)
