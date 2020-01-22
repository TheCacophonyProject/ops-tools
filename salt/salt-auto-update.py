#!/usr/bin/python -u


"""Automatically schedule a state.apply for Raspberry Pis when they
connect to the Salt master.

Updates will not be scheduled for a device if it has already received
one within MIN_UPDATE_INTERVAL.

A blacklist file exists at MINION_BLACKLIST_PATH to block automatic
updates for specific devices.
"""

from __future__ import print_function

from datetime import datetime, timedelta
from itertools import imap, ifilter
import re
import sys

from dateutil.parser import parse as parse_date
from influxdb import InfluxDBClient
import salt.client

from salt_listener import SaltListener

# don't update a device if it was last updated less than this long ago
MIN_UPDATE_INTERVAL = timedelta(hours=23)

# path to a file listing minions which should never be auto-updated
MINION_BLACKLIST_PATH = "/etc/salt/autoupdate.blacklist"

# InfluxDB database used to track state
DB_NAME = "last-updated"

def main():
    print("loading blacklist")
    blacklist = load_file_lines(MINION_BLACKLIST_PATH)

    print("connecting to InfluxDB")
    state = UpdateState(DB_NAME, MIN_UPDATE_INTERVAL)

    print("creating Salt client")
    salt_client = salt.client.LocalClient(auto_reconnect=True)

    # listen to salt-master events, filter out anything other than
    # minion ping events
    ping_events = imap(match_minion_ping, iter(SaltListener()))
    ping_events = ifilter(bool, ping_events)

    # extract out minion_ids, filter out servers
    minion_ids = ifilter(not_server, ping_events)

    # filter out blacklisted minions
    minion_ids = ifilter(lambda m: not m in blacklist, minion_ids)

    # filter out minions that have already been updated recently
    minion_ids = ifilter(state.is_update_required, minion_ids)

    print("listening for minion ping events")
    for minion_id in minion_ids:
        print("scheduling update for", minion_id)
        job_id = salt_client.cmd_async(minion_id, "state.apply")
        print("  job id", job_id)
        state.record_update(minion_id, job_id)


def load_file_lines(filename):
    try:
        return set(x.strip() for x in open(filename))
    except IOError:
        return set()


def match_minion_ping(event):
    if event is None:
        return None

    tag = event.get("tag", "")
    if tag == "salt/event/exit":
        sys.exit()

    if tag == "minion_ping":
        data = event.get("data")
        if data == None:
            return None
        return data.get("id")
    return None

def not_server(minion_id):
    return not minion_id.startswith("server-")


class UpdateState:
    def __init__(self, db_name, min_interval):
        self.influx = InfluxDBClient("localhost", 8086, database=db_name)
        self.min_interval = min_interval

    def is_update_required(self, minion_id):
        last_t = self.last_update_time(minion_id)
        if not last_t:
            return True  # never auto-updated before

        now = datetime.now(last_t.tzinfo)
        return (now - last_t) > self.min_interval

    def record_update(self, minion_id, job_id):
        ts = datetime.utcnow()
        self.influx.write_points(
            [
                {
                    "measurement": "updates",
                    "time": ts,
                    "tags": {"device": minion_id},
                    "fields": {"job_id": job_id},
                }
            ]
        )

    def last_update_time(self, minion_id):
        results = list(
            self.influx.query(
                "select last(*) from updates where device = '{}'".format(minion_id)
            ).get_points()
        )
        if not results:
            return None
        return parse_date(results[0]["time"])


if __name__ == "__main__":
    main()
