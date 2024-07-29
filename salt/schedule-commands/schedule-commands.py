#!/usr/bin/python3 -u

"""Automatically run commands when devices connect"""

from __future__ import print_function
import os
import subprocess
import sys
import shlex

import salt.client

from salt_listener import SaltListener

COMMAND_FILE = "/opt/ops-tools/salt/schedule-commands/commands.txt"

def main():
    print("creating Salt client")
    salt_client = salt.client.LocalClient(auto_reconnect=True)

    # listen to salt-master events, filter out anything other than
    # minion ping events
    ping_events = map(match_minion_ping, iter(SaltListener()))
    minion_ids = filter(bool, ping_events)

    # minion_ids = ["pi-1755"]    # For testing

    print("listening for minion ping events")
    for minion_id in minion_ids:
        command = getMinionCommand(minion_id)
        while command != None:
            print(f"'{minion_id}' connected, running '{command}'")
            result = subprocess.run(command.split(), capture_output=True, text=True)
            print(result.stdout)
            print(result.stderr)

def getMinionCommand(minion_id):
    with open(COMMAND_FILE, "r") as file:
        lines = file.readlines()

    for line in lines:
        parts = line.strip().split(":", 1)
        # Should be two parts, the minion id and the command
        if len(parts) == 2 and parts[0] == minion_id:
            # Found command to run. Remove it from the file then return it.
            lines.remove(line)
            with open(COMMAND_FILE, "w") as fw:
                for l in lines:
                    fw.write(l)
            return parts[1].strip()
    return None


def match_minion_ping(event):
    if event is None:
        return None

    tag = event.get("tag", "")
    if tag == "salt/event/exit":
        sys.exit()

    if tag == "minion_ping" or "salt/auth":
        data = event.get("data")
        if not data:
            return None
        return data.get("id")
    return None


if __name__ == "__main__":
    main()
