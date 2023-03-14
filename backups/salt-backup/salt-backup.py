#!/usr/bin/python3
import yaml
import os
import sys
import socket
import subprocess
from influxdb import InfluxDBClient

HOST_NAME = socket.gethostname()
CONFIG_FILE = "./salt-backup.yaml"

if not os.path.exists(CONFIG_FILE):
    print(f"failed to find config file '{CONFIG_FILE}'")
    sys.exit()

with open(CONFIG_FILE, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


print("Running salt backup")
command = "b2 sync /etc/salt b2://salt-backup/salt"
result = subprocess.run(command, shell=True)

if result.returncode == 0:
    success = 1
    print("salt backup success")
else:
    success = 0
    print("salt backup failed")
    sys.exit()

print("Logging to influx")
json_body = [{
        "measurement": "backup",
        "tags": {
            "host": HOST_NAME,
            #"postgresql": config['database']
        },
        "fields": {
            "success": float(success),
        }
    }]
client = InfluxDBClient(**config['influx'])
print(json_body)
client.write_points(json_body)

print("Finished salt backups")
