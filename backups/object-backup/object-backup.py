#!/usr/bin/python3
import boto3
import botocore
import concurrent.futures
import yaml
import threading
import sys
import time

dry_run = False
if len(sys.argv) > 1:
    if sys.argv[1] != "--dry-run":
        print(f"Unknown parameter {sys.argv[1]}")
        sys.exit()
    else:
        print("Doing a dry run")
        dry_run = True

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

total_transferred = 0
total_transferred_lock = threading.Lock()
success = 1
success_lock = threading.Lock()
upload_count = 0
upload_count_lock = threading.Lock()
total_file_count = 0
file_changed_count = 0
file_changed_count_lock = threading.Lock()

# Copies a file from a local S3 bucket to an archive S3 bucket if it does not exist in the archive bucket,
# and verifies that the object exists in both buckets. If the object exists but has been modified,
# raises an error.
def handle_file(obj):
    global total_transferred
    global success
    global upload_count
    global file_changed_count

    try:
        archive_obj = archive_s3.Object(config['archive']['bucket'], obj.key)
        archive_obj.load() # load() will raise an exception if the object does not exist
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # The object does not exist, so we copy it
            print(f"copying file '{obj.key}' to archive bucket")
            if dry_run:
                print("skipping copy in dry run")
            else:
                local_obj = local_s3.Object(config['local']['bucket'], obj.key)
                archive_obj.put(Body=local_obj.get()['Body'].read())
            with total_transferred_lock:
                total_transferred += obj.size
            with upload_count_lock:
                upload_count += 1
        else:
            # Something else has gone wrong
            with success_lock:
                success = 0
            raise
    else:
        # Check that the objects match.
        if obj.e_tag != archive_obj.e_tag:
            print(f"Error: object {obj.key} has been modified.")
            with success_lock:
                success = 0
            with file_changed_count_lock:
                file_changed_count += 1
            return
        #print(f"object is in archive bucket: '{obj.key}'")

start_time = time.time()
# Use a ThreadPoolExecutor to handle multiple files at once
with concurrent.futures.ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
    for obj in local_bucket.objects.page_size(config['page_size']):
        if obj.key.endswith("-thumb"):
            continue
        executor.submit(handle_file, obj)
        total_file_count += 1

end_time = time.time()
execution_time = end_time - start_time


print(f"Total transferred: {total_transferred}")
print(f"Success: {success}")
print(f"Upload count: {upload_count}")
print(f"Total file count: {total_file_count}")
print(f"File changed count: {file_changed_count}")
print(f"Execution time: {execution_time}")
