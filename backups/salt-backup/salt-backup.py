#!/usr/bin/python3
import yaml
import os
import sys
import socket
import subprocess
import shutil
from datetime import datetime
import tempfile
from influxdb import InfluxDBClient

HOST_NAME = socket.gethostname()
CONFIG_FILE = "./salt-backup.yaml"

if not os.path.exists(CONFIG_FILE):
    print(f"failed to find config file '{CONFIG_FILE}'")
    sys.exit()

with open(CONFIG_FILE, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("Running salt backup")

# Make zip of files to backup
dirs = ["/etc/salt", "/srv/pillar"]
temp_dir = tempfile.mkdtemp()
for dir in dirs:
    shutil.copytree(dir, os.path.join(temp_dir, os.path.basename(dir)))
zip_file = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}_salt-backup.zip"
shutil.make_archive(zip_file.replace(".zip", ""), 'zip', temp_dir)


# Upload backup to each endpoint
success = 1
for endpoint in config['endpoints']:
    os.environ['AWS_ACCESS_KEY_ID'] = endpoint['access_key']
    os.environ['AWS_SECRET_ACCESS_KEY'] = endpoint['secret_key']    
    command = f"s5cmd --endpoint-url {endpoint['url']} cp {zip_file} s3://{endpoint['bucket_name']}/{zip_file}"
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        success = 0
        print(f"salt backup command '{command}' failed")

os.remove(zip_file)

print("Logging to influx")
json_body = [{
        "measurement": "backup",
        "tags": {
            "host": HOST_NAME,
        },
        "fields": {
            "success": float(success),
        }
    }]
client = InfluxDBClient(**config['influx'])
print(json_body)
client.write_points(json_body)

if success == 1:
    print("Finished salt backups successfully")
else:
    print("Failed to finish salt backups")
