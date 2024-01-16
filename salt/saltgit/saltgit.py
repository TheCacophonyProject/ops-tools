import os
import subprocess
import logging
import sys
import socket
from influxdb import InfluxDBClient

import yaml

CHECK_TIME_MINUTES = 5
HOST_NAME = socket.gethostname()


def main(config_file):
    print("Running saltgit check")
    config = load_grafana_config(config_file)

    cmd = [
        "journalctl",
        "-u",
        "salt-master",
        "--since",
        f"{CHECK_TIME_MINUTES} minutes ago",
    ]
    #   | grep "anything"'
    grep_cmd = [
        "grep",
        "-E",
        "(salt-run cache.clear_git_lock gitfs type=update|Error occurred fetching gitfs remote .https://github.com/TheCacophonyProject/saltops.git)",
    ]
    out = ""
    try:
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(grep_cmd, stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
        out, err = p2.communicate()
        success = True
    except:
        logging.error("Error running %s", cmd, exc_info=True)
        success = False
    json_body = [
        {
            "measurement": "salt-git",
            "tags": {
                "host": HOST_NAME,
            },
            "fields": {
                "success": success,
                "salt-git-ok": 1 if success and len(out) == 0 else 0,
            },
        }
    ]

    print("Logging to influx")

    client = InfluxDBClient(**config["influx"])
    client.write_points(json_body)


def load_grafana_config(config_file):
    if not os.path.exists(config_file):
        print(f"failed to find config file '{config_file}'")
        sys.exit()

    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def init_logging():
    """Set up logging for use by various classifier pipeline scripts.

    Logs will go to stderr.
    """

    fmt = "%(process)d %(thread)s:%(levelname)7s %(message)s"
    logging.basicConfig(
        stream=sys.stderr, level=logging.INFO, format=fmt, datefmt="%Y-%m-%d %H:%M:%S"
    )


if __name__ == "__main__":
    # check if there is at least one parameter: the config file path
    if len(sys.argv) < 2:
        print("Usage: python script.py <config_path>")
        sys.exit()
    init_logging()
    main(sys.argv[1])
