#!/usr/bin/python3
import sys,  yaml
from os.path import exists
from s3_support.s3 import S3


def get_yaml_path(yaml_path):
    while yaml_path != '':
        if not exists(yaml_path):
             yaml_path = ''
             try:
                 yaml_path = input("Filepath to S3 yml file: ")
             except EOFError as e:
                 yaml_path = ''
        else:
            return(yaml_path)
    return None


def main():
    yaml_path = "s3.yml"
    # in case the S3 yml isn't in the same directory or has a different name
    config_path = get_yaml_path(yaml_path)
    if config_path != None:
        try:
             s3 = S3(configpath = config_path)
        except  Exception as e:
            raise e
        if input("{}. Are you sure? y/n: ".format(s3)) == 'y':
            s3.clear_bucket()
            print("done")
        else:
            print("Bucket not cleared.")
    else:
        print("No path found. Ending.")
main()
