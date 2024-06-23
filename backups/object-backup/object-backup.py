#!/usr/bin/python3
import boto3
import botocore
import concurrent.futures
import yaml
import threading
import sys
import time
import socket
import os
from influxdb import InfluxDBClient
import random
import tempfile


dry_run = False

# check if there is at least one parameter: the config file path
if len(sys.argv) < 2:
    print("Usage: python script.py <config_path> [--dry-run]")
    sys.exit()

config_path = sys.argv[1]

# check if a second parameter exists: the dry run option
if len(sys.argv) > 2:
    if sys.argv[2] != "--dry-run":
        print(f"Unknown parameter {sys.argv[2]}")
        sys.exit()
    else:
        print("Doing a dry run")
        dry_run = True

# use the config file path provided as an argument
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

print(
    f"Backing up from {config['local']['bucket']} at {config['local']['endpoint_url']} to {config['archive']['bucket']} at {config['archive']['endpoint_url']}"
)

# Local S3 storage
local_s3 = boto3.resource(
    "s3",
    aws_access_key_id=config["local"]["aws_access_key_id"],
    aws_secret_access_key=config["local"]["aws_secret_access_key"],
    endpoint_url=config["local"]["endpoint_url"],
)
local_bucket = local_s3.Bucket(config["local"]["bucket"])
try:
    _ = [obj.key for obj in local_bucket.objects.limit(1)]
except:
    print("Failed to read from local bucket. Check auth and bucket name.")
    sys.exit()

# Archive S3 storage
archive_s3 = boto3.resource(
    "s3",
    aws_access_key_id=config["archive"]["aws_access_key_id"],
    aws_secret_access_key=config["archive"]["aws_secret_access_key"],
    endpoint_url=config["archive"]["endpoint_url"],
)
archive_bucket = archive_s3.Bucket(config["archive"]["bucket"])
try:
    _ = [
        obj.key for obj in archive_bucket.objects.limit(1)
    ]  # Check that can read from bucket
except:
    print("Failed to read from archive bucket. Check auth and bucket name.")
    sys.exit()


def get_archive_key(key):
    return os.path.join(config["archive"]["prefix"], key)


# It is very easy to configure it to upload to the wrong bucket, so this checks that at least 80
# out a random 100 recordings are already on the target bucket. Meaning it's probably the correct bucket.
print(
    "Check that some files already match as a way of checking that the correct buckets are being/prefix used."
)
keys = []
i = 0
for obj in local_bucket.objects.page_size(10000):
    keys.append(obj.key)
    i += 1
    if i >= 10000:
        break

random_keys = []
for i in range(100):
    random_keys.append(random.choice(keys))

matching = 0


def check_matching_key(key):
    global matching
    local_obj = local_bucket.Object(key)
    archive_obj = archive_bucket.Object(get_archive_key(key))
    if local_obj.e_tag == archive_obj.e_tag:
        matching += 1


with concurrent.futures.ThreadPoolExecutor() as executor:
    for key in random_keys:
        executor.submit(check_matching_key, key)

if matching < 50:
    print(
        f"{matching} out of 100 objects are already on the target bucket. Canceling backup."
    )
    time.sleep(2)
    sys.exit(0)
print("Done.")


total_transferred = 0
total_transferred_lock = threading.Lock()
success = 1
success_lock = threading.Lock()
upload_count = 0
upload_count_lock = threading.Lock()
total_file_count = 0
processed_file_count = 0
processed_file_count_lock = threading.Lock()
modified_files = []
modified_files_lock = threading.Lock()


# Copies a file from a local S3 bucket to an archive S3 bucket if it does not exist in the archive bucket,
# and verifies that the object exists in both buckets. If the object exists but has been modified,
# raises an error.
def handle_file(obj):
    global total_transferred
    global success
    global upload_count
    global file_changed_count
    global matching_count
    try:
        if obj.key.endswith("-thumb"):
            return
        archive_key = os.path.join(config["archive"]["prefix"], obj.key)
        archive_obj = archive_bucket.Object(archive_key)
        archive_obj = archive_s3.Object(config["archive"]["bucket"], archive_key)
        archive_obj.load()  # load() will raise an exception if the object does not exist
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # The object does not exist, so we copy it
            print(f"copying file '{obj.key}' to archive bucket as {archive_key}")
            if dry_run:
                print("skipping copy in dry run")
            else:
                local_obj = local_s3.Object(config["local"]["bucket"], obj.key)
                archive_obj.put(Body=local_obj.get()["Body"].read())
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
        # Check that the object has been modified.
        modified = True
        if obj.e_tag == archive_obj.e_tag:
            modified = False
        elif (
            "-" in obj.e_tag or "-" in archive_obj.e_tag
        ) and obj.size == archive_obj.content_length:  # archive_object is a s3.Object so use content_length to get the size
            # Hashes will not match when in multipart upload.
            # https://www.digitalocean.com/community/questions/contents-of-etag-returned-from-spaces-isn-t-always-md-5
            # Compare size for now but TODO, write hash in metadata so can be compared or some better way of comparing.
            modified = False

        if modified:
            print(f"Error: object {obj.key} has been modified.")
            with success_lock:
                success = 0
            with modified_files_lock:
                modified_files.append(obj.key)
            return


def run_handle_file(obj):
    global success
    global processed_file_count
    failed_count = 0
    max_attempts = 3
    while True:
        try:
            handle_file(obj)
            break
        except Exception as e:
            failed_count += 1
            if failed_count == max_attempts:
                with success_lock:
                    success = 0
                print(e)
                break
            else:
                print(
                    f"Failed to copy file {obj.key}, attempt {failed_count}/{max_attempts} ",
                    e,
                )

    with processed_file_count_lock:
        processed_file_count += 1
        if processed_file_count % 10000 == 0:
            print(f"processed files count: {processed_file_count}")


start_time = time.time()
print("Starting backup process")
# Use a ThreadPoolExecutor to handle multiple files at once
with concurrent.futures.ThreadPoolExecutor(
    max_workers=config["max_workers"]
) as executor:
    for obj in local_bucket.objects.page_size(config["page_size"]):
        executor.submit(run_handle_file, obj)
        total_file_count += 1

end_time = time.time()
execution_time = end_time - start_time


print(f"Total transferred: {total_transferred}")
print(f"Success: {success}")
print(f"Upload count: {upload_count}")
print(f"Total file count: {total_file_count}")
print(f"File changed count: {len(modified_files)}")
print(f"Execution time: {execution_time}")

if len(modified_files):
    with tempfile.NamedTemporaryFile("w", delete=False) as temp:
        for key in modified_files:
            temp.write(key + "\n")
        print(f"List of modified files: {temp.name}")


print("Logging to influx")
json_body = [
    {
        "measurement": "object_backup",
        "tags": {"bucket": config["local"]["bucket"]},
        "fields": {
            "success": float(success),
            "data_transferred": total_transferred,
            "total_files": total_file_count,
        },
    }
]
client = InfluxDBClient(**config["influx"])

print(f"JSON body posting to influx: {json_body}")
if dry_run:
    print("Skipping reporting to influx in dry run.")
else:
    client.write_points(json_body)

print("Finished object storage backup.")
