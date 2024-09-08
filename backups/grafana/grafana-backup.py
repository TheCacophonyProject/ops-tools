#!/usr/bin/python3
import os
import shutil
import datetime
import socket
from b2sdk.v1 import B2Api, InMemoryAccountInfo, UploadSourceBytes
import yaml
from influxdb import InfluxDBClient


HOST_NAME = socket.gethostname()
CONFIG_FILE = "./grafana-backup.yaml"

if not os.path.exists(CONFIG_FILE):
    print(f"failed to find config file '{CONFIG_FILE}'")
    sys.exit()

with open(CONFIG_FILE, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("Running grafana backup")

# File paths for Grafana configuration, database files, and plugins folder
GRAFANA_INI_FILE = "/etc/grafana/grafana.ini"
GRAFANA_DB_FILE = "/var/lib/grafana/grafana.db"
GRAFANA_PLUGINS_FOLDER = "/var/lib/grafana/plugins/"

# Temporary backup file names
TMP_BACKUP_INI_FILE = "/tmp/grafana_backup_ini.ini"
TMP_BACKUP_DB_FILE = "/tmp/grafana_backup_db.db"
TMP_BACKUP_PLUGINS_ZIP = "/tmp/grafana_backup_plugins.zip"

# Backup path target file names
BACKUP_INI_FILE = "grafana.ini"
BACKUP_DB_FILE = "grafana.db"
BACKUP_PLUGINS_ZIP = "grafana_plugins.zip"

# Copy files to temporary backup files
print("Copying files to temporary backup files")
shutil.copy2(GRAFANA_INI_FILE, TMP_BACKUP_INI_FILE)
shutil.copy2(GRAFANA_DB_FILE, TMP_BACKUP_DB_FILE)

# Zip plugins folder
print("Zipping plugins folder")
archive_path, _ = os.path.splitext(
    TMP_BACKUP_PLUGINS_ZIP
)  # Remove extension as make_archive will add it
shutil.make_archive(archive_path, "zip", GRAFANA_PLUGINS_FOLDER)

# Initialize Backblaze B2 API
print("Initializing Backblaze B2 API")
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account(
    "production", config["b2"]["app_key_id"], config["b2"]["app_key"]
)
bucket = b2_api.get_bucket_by_name(config["b2"]["bucket"])


# Upload file to Backblaze B2 and delete original file
def upload_to_b2(file_name, object_name):
    try:
        with open(file_name, "rb") as f:
            data = f.read()
        source = UploadSourceBytes(data)
        bucket.upload(source, object_name)
        print(f"File {file_name} uploaded to Backblaze B2 as {object_name}")
        os.remove(file_name)
        return True
    except Exception as e:
        print(f"File {file_name} could not be uploaded to Backblaze B2. Error: {e}")
        return False


print("Uploading files to Backblaze B2")
success = True
success &= upload_to_b2(TMP_BACKUP_INI_FILE, BACKUP_INI_FILE)
success &= upload_to_b2(TMP_BACKUP_DB_FILE, BACKUP_DB_FILE)
success &= upload_to_b2(TMP_BACKUP_PLUGINS_ZIP, BACKUP_PLUGINS_ZIP)

if success:
    print("Grafana backup success")
else:
    print("Grafana backup failed")

print("Logging to influx")
json_body = [
    {
        "measurement": "backup",
        "tags": {
            "host": HOST_NAME,
        },
        "fields": {
            "success": 1.0 if success else 0.0,
        },
    }
]
client = InfluxDBClient(**config["influx"])
print(json_body)
client.write_points(json_body)

print("Finished grafana backups")
