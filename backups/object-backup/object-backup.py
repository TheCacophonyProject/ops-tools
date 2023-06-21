#!/usr/bin/python3
import boto3
import botocore
import concurrent.futures
import yaml
import threading

with open('object-backup.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Local S3 storage
local_s3 = boto3.resource('s3',
    aws_access_key_id=config['local']['aws_access_key_id'],
    aws_secret_access_key=config['local']['aws_secret_access_key'],
    endpoint_url=config['local']['endpoint_url'])
local_bucket = local_s3.Bucket(config['local']['bucket'])

# Archive S3 storage
archive_s3 = boto3.resource('s3',
    aws_access_key_id=config['archive']['aws_access_key_id'],
    aws_secret_access_key=config['archive']['aws_secret_access_key'],
    endpoint_url=config['archive']['endpoint_url'])
archive_bucket = archive_s3.Bucket(config['archive']['bucket'])

# Copies a file from a local S3 bucket to an archive S3 bucket if it does not exist in the archive bucket,
# and verifies that the object exists in both buckets. If the object exists but has been modified,
# raises an error.
def handle_file(obj):
    try:
        local_obj = local_s3.Object(config['local']['bucket'], obj.key)
        try:
            archive_obj = archive_s3.Object(config['archive']['bucket'], obj.key)
            archive_obj.load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist, so we copy it
                print(f"copying file {obj.key} to archive bucket")
                archive_obj.put(Body=local_obj.get()['Body'].read())
            else:
                # Something else has gone wrong
                raise
        else:
            if obj.e_tag != archive_obj.e_tag:
                print(f"Error: object {obj.key} has been modified.")
            print(f"Object {obj.key} exists in both buckets. Skipping.")
    
    except Exception as e:
        print(f"Error handling object {obj.key}: {e}")


# Use a ThreadPoolExecutor to handle multiple files at once
with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
    for obj in local_bucket.objects.page_size(1000):
        if obj.key.endswith("-thumbnail"):
            continue
        executor.submit(handle_file, obj)

