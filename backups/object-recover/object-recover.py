#!/bin/python3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import yaml
import psycopg2
import subprocess
import os
from minio import Minio

def check_file_exists(minio_client, bucket_name, object_name):
    try:
        minio_client.stat_object(bucket_name, object_name)
        return True
    except:
        return False


print("Running object recover script")

with open("object-recover.yaml", "r") as file:
    config = yaml.safe_load(file)

print("Connecting to postgres")
postgres = config["postgres"]
psql_conn = psycopg2.connect(
    host=postgres["host"],
    port=postgres["port"],
    dbname=postgres["database"],
    user=postgres["user"],
    password=postgres["password"],
)
cursor = psql_conn.cursor()

b2 = config["b2"]
minio = config["minio"]


print("Running query for file object keys")
sql_query = 'select "fileKey" from "Files";'
cursor.execute(sql_query)
file_object_keys = cursor.fetchall()

print("Running query for rawFiles object keys")
sql_query = 'select "rawFileKey" from "Recordings" where "recordingDateTime" notnull and "deletedAt" isnull order by "recordingDateTime" DESC;'
cursor.execute(sql_query)
raw_file_object_keys = cursor.fetchall()
cursor.close()
psql_conn.close()
object_keys = file_object_keys + raw_file_object_keys

minio_client = Minio(
        minio["endpoint"],
        access_key=minio["access_key"],
        secret_key=minio["secret_key"],
        secure=minio["http"],
    )

print("Finding keys that are not in local object store")
transfers = []
for object_key in object_keys:
    object_key = object_key[0]
    source = os.path.join(b2["gateway"], b2["bucket"], b2["prefix"], object_key)
    destination = os.path.join(minio["gateway"], minio["bucket"], object_key)
    if not check_file_exists(minio_client, minio["bucket"], object_key):
        transfers.append((source, destination))


completed_transfers = 0
lock = Lock()

def transfer_file(source, destination):
    try:
        subprocess.run(
            ["mc", "cp", "--quiet", source, destination],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True)
        with lock:
            global completed_transfers
            completed_transfers += 1
            print(f"{completed_transfers}/{len(transfers)} Transferred '{source}' to '{destination}'")
    except subprocess.CalledProcessError as e:
        print(f"Failed to transfer '{source}': {e}")

size = len(transfers)
print(f"Objects to recover: {size}")


with ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(lambda args: transfer_file(*args), transfers))
 