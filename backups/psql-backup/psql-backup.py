#!/usr/bin/python3
import yaml
import os
import sys
import boto3
import datetime
import subprocess
from influxdb import InfluxDBClient
import socket

HOST_NAME = socket.gethostname()
CONFIG_FILE = "./psql-backup.yaml"
DUMP_EXT = ".pgdump"

dry_run = False
success = 1
if len(sys.argv) > 1:
    if sys.argv[1] != "--dry-run":
        print(f"Unknown parameter {sys.argv[1]}")
        sys.exit()
    else:
        print("Doing a dry run")
        dry_run = True

print("Running DB backup")

if not os.path.exists(CONFIG_FILE):
    print(f"failed to find config file '{CONFIG_FILE}'")
    sys.exit()

with open(CONFIG_FILE, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

database = config['database']

date_str = datetime.datetime.now().strftime("%F")
print("Making pgdump file")
dump_name = f"{database}_{date_str}{DUMP_EXT}"
dump_path = os.path.join('/var/lib/postgresql', dump_name)
dump_size = 0
if dry_run:
    print("Skipping making dump file in dry run")
else:
    subprocess.call(["sudo", "-i", "-u", "postgres", "pg_dump", "-Fc", database, "--file", dump_name])
    dump_size = os.path.getsize(dump_path)
    ##TODO exit if failed

# Backup to each of the daily endpoints
print('Running daily backups')
date_limit = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(config['daily']['days'])
prefix = os.path.join(config['prefix'],"daily", HOST_NAME)
dump_key = os.path.join(prefix, dump_name)
for daily_backup in config['daily']['buckets']:
    s3_config = config['s3_auths'][daily_backup['s3_auth']]
    bucket_name = daily_backup["bucket"]
    print(f'Connecting to bucket {bucket_name}')
    s3 = boto3.resource('s3', **s3_config)
    bucket = s3.Bucket(bucket_name)
    print(f'Uploading {dump_path} as {dump_key}')
    if dry_run:
        print("Skipping upload in dry run")
    else:
        bucket.upload_file(dump_path, dump_key)
    # Deleting backup files older than 30 days
    uploaded = False
    for file in bucket.objects.filter(Prefix=prefix):
        if file.key.endswith(DUMP_EXT):
            if (file.last_modified <= date_limit):
                print(f'Deleting old backup {file.key}')
                if dry_run:
                    print('Skipping deletion in dry run')
                else:
                    print('deleting //TODO')
        if file.key == dump_key and file.size == dump_size:
            uploaded = True
    if not uploaded:
        print('File was not uploaded successfully')
        success = 0.0
    print(f'Finished backup on {bucket_name}')
print("Finished daily backups")  

# Monthly backups
print("Running monthly backups")
prefix = os.path.join(config['prefix'], "monthly", HOST_NAME)
dump_key = os.path.join(prefix, dump_name)
month_start = datetime.datetime.now(datetime.timezone.utc).replace(day=1,hour=0,minute=0, second=0)
for monthly_backup in config['monthly']['buckets']:
    s3_config = config['s3_auths'][monthly_backup['s3_auth']]
    bucket_name = monthly_backup["bucket"]
    print(f'Connecting to bucket {bucket_name}')
    s3 = boto3.resource('s3', **s3_config)
    bucket = s3.Bucket(bucket_name)

    already_monthly_backup = False
    print(f'Checking for backups this month')
    for file in bucket.objects.filter(Prefix=prefix):
        if file.key.endswith(DUMP_EXT):
            if (file.last_modified > month_start):
                print(f"Monthly backup already found {file.key}")
                already_monthly_backup = True
                break
    if not already_monthly_backup:
        print("No backup from this month found.")
        print(f'Uploading {dump_path} as {dump_key}')
        if dry_run:
            print("Skipping upload in dry run")
        else:
            bucket.upload_file(dump_path, dump_key)

print("Finished monthly backups")

print("Deleting local backup")
os.remove(dump_path)

print("Logging to influx")
json_body = [{
        "measurement": "backup",
        "tags": {
            "host": HOST_NAME,
            "postgresql": config['database']
        },
        "fields": { "success": float(success) }
    }]
client = InfluxDBClient(**config['influx'])
print(json_body)
if dry_run:
    print("Skipping reporting to influx")
else:
    client.write_points(json_body)

print("Finished PostgreSQL backups")