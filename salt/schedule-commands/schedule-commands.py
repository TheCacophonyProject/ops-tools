#!/usr/bin/python3 -u

"""Automatically run commands on devices when they connect"""

from __future__ import print_function

import sys
import shlex

import salt.client

from salt_listener import SaltListener

COMMAND_FILE = "/opt/ops-tools/salt/commands.txt"


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
        line = getMinionCommand(minion_id)
        while line != None:
            print("Line:", line.strip())
            split = shlex.split(line)
            minion_id = split[0]
            command = split[1]
            args = split[2:] if 2 < len(split) else []
            print(
                "Running command. Minion:",
                minion_id,
                ", Command:",
                command,
                ", Args:",
                args,
            )
            job = salt_client.cmd(minion_id, command, args)
            print("Result: (" + line.strip() + "):", job)
            line = getMinionCommand(minion_id)


def getMinionCommand(minion_id):
    with open(COMMAND_FILE, "r") as file:
        lines = file.readlines()
    for line in lines:
        words = line.strip().split()
        if len(words) == 0:
            continue
        if words[0] == minion_id:
            lines.remove(line)
            with open(COMMAND_FILE, "w") as fw:
                for l in lines:
                    fw.write(l)
            return line
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
