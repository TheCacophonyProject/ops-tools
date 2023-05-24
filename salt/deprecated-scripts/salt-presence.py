#!/usr/bin/python -u

"""
This tool subscribes to minion events from the Salt master and writes presence
events to InfluxDB. This is used to drive a Grafana dashboard.
"""

from __future__ import print_function

from datetime import datetime, timedelta
from influxdb import InfluxDBClient
import sys
import time

from salt_listener import SaltListener

# How often to check for dead minions to mark as such.
UPDATE_DEAD_INTERVAL = timedelta(seconds=30)

# Minions must ping or re-auth at least this period in order to be considered
# alive.
PRESENCE_INTERVAL = timedelta(minutes=5)

# Stop writing "down" events if minion has been continuously dead for this long.
MAX_DOWN_INTERVAL = timedelta(days=10)


def main():
    influx = influx_connect()

    # Give extra time on watcher startup for minions to report in to avoid
    # marking minions as down if the watcher has been down for a while.
    last_update_t = datetime.now() + UPDATE_DEAD_INTERVAL

    print("listening for events")
    up_count = 0
    for event in SaltListener(timeout=UPDATE_DEAD_INTERVAL / 2):
        minion_id, ts = process_event(event)
        if minion_id:
            up_count += 1
            write_presence(influx, minion_id, True, ts)

        now = datetime.now()
        if (now - last_update_t) > UPDATE_DEAD_INTERVAL:
            print("{} up events received".format(up_count))
            process_down_minions(influx)
            last_update_t = now


def process_event(event):
    if event is None:
        return None, None

    tag = event.get("tag", "")
    data = event.get("data", {})

    if tag == "salt/event/exit":
        sys.exit()
    elif tag in ("salt/auth", "minion_ping"):
        return data.get("id"), parse_stamp(data.get("_stamp"))
    return None, None


def parse_stamp(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")


def influx_connect():
    client = InfluxDBClient("localhost", 8086, database="device-status")
    client.create_database("device-status")
    return client


def write_presence(client, minion_id, up, stamp=None):
    if stamp is None:
        stamp = datetime.utcnow()
    client.write_points(
        [
            {
                "measurement": "presence",
                "time": stamp,
                "tags": {"device": minion_id},
                "fields": {"up": up},
            }
        ]
    )


def process_down_minions(client):
    now = datetime.now()
    presence_update_t = datetime_to_t(now - PRESENCE_INTERVAL)
    max_down_t = datetime_to_t(now - MAX_DOWN_INTERVAL)

    results = client.query(
        "select device, last(up) as up from presence group by device", epoch="s"
    )
    for r in results.get_points():
        # A "down" event is written event for even for minions which are
        # already marked as down so that Grafana will still see them even when
        # displaying a small time range.
        #
        # However, if a minion has been down for over some long time
        # (MAX_DOWN_INTERVAL) then stop writing out down records so that
        # permanently dead minions eventually disappear from the dashboard.
        if max_down_t < r["time"] < presence_update_t:
            write_presence(client, r["device"], False)


def datetime_to_t(dt):
    return time.mktime(dt.timetuple())


if __name__ == "__main__":
    main()
