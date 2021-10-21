#!/usr/bin/python3
import yaml
import os
import sys
import subprocess
from influxdb import InfluxDBClient
import socket

HOST_NAME = socket.gethostname()
CONFIG_FILE = "./object-backup.yaml"
MC = '/usr/local/bin/mc'

exp = {
    "G": 1000000000,
    "M": 1000000,
    "K": 1000,
    "B": 1,
}

def data_count(keyword, data):
    i = data.index(keyword)
    if i == -1:
        print(f"failed to parse '{keyword}' in '{data}'")
        sys.exit()
    return float(data[i+1]) * exp[data[i+2][0]]

dry_run = False
if len(sys.argv) > 1:
    if sys.argv[1] != "--dry-run":
        print(f"Unknown parameter {sys.argv[1]}")
        sys.exit()
    else:
        print("Doing a dry run")
        dry_run = True

if not os.path.exists(CONFIG_FILE):
    print(f"failed to find config file '{CONFIG_FILE}'")
    sys.exit()

with open(CONFIG_FILE, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

localstore = config['localstore']
remotestore = os.path.join(config['remotestore'], config['remotePrefix'])

mc_command = ["/usr/local/bin/mc", "mirror", "--quiet", localstore, remotestore]
if dry_run:
    mc_command.insert(mc_command.index("mirror")+1, "--fake")

print(f"running '{' '.join(mc_command)}'")

out = subprocess.check_output(mc_command)
out = out.decode("utf-8")
lines = out.split("\n")

total_files = 0
data_total = 0
data_transferred = 0
data_speed = 0

success = 1
for line in lines:
    if line.__contains__('Failed'):
        success = 0
        print(line)
    if len(line) == 0:
        continue
    if line.startswith(f"`{localstore}"):
        total_files += 1
    elif line.startswith("Total"):
        parts = line.split(" ")
        data_total = data_count("Total:", parts)
        data_transferred = data_count("Transferred:", parts)
        data_speed = data_count("Speed:", parts)
    else:
        print(f"unknown line: {line}")
        sys.exit()

print("Logging to influx")
json_body = [{
        "measurement": "object_backup",
        "tags": {
            "host": HOST_NAME,
            "object_storage": remotestore
        },
        "fields": {
            "success": float(success),
            "data_total": data_total,
            "data_transferred": data_transferred,
            "data_speed": data_speed,
            "total_files": total_files,
        }
    }]
client = InfluxDBClient(**config['influx'])
print(json_body)
if dry_run:
    print("Skipping reporting to influx")
else:
    client.write_points(json_body)

print("Finished objectstorage backup")
