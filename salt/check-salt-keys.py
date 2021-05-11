#!/usr/bin/python3
import subprocess

## Put all the salt keys that you want to check in a local file called `salt-keys` with a new line for each key
raw_keys = subprocess.run(['cat', 'salt-keys'], stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")
filtered_keys = []
for i in raw_keys:
    if i != '':
        filtered_keys.append(i)

salt_keys = subprocess.run(['cat', 'salt-keys-test-out'], stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")

salt_accepted_keys = []
salt_denied_keys = []
salt_unaccepted_keys = []
salt_rejected_keys = []

for i in salt_keys:
    if i == "Accepted Keys:":
        active_list = salt_accepted_keys
    elif i == "Denied Keys:":
        active_list = salt_denied_keys
    elif i == "Unaccepted Keys:":
        active_list = salt_unaccepted_keys
    elif i == "Rejected Keys:":
        active_list = salt_rejected_keys
    else:
        active_list.append(i)

accepted_keys = []
denied_keys = []
unaccepted_keys = []
rejected_keys = []
unknown_keys = []

for i in filtered_keys:
    if i in salt_accepted_keys:
        accepted_keys.append(i)
    elif i in salt_denied_keys:
        denied_keys.append(i)
    elif i in salt_unaccepted_keys:
        unaccepted_keys.append(i)
    elif i in salt_rejected_keys:
        rejected_keys.append(i)
    else:
        unknown_keys.append(i)

#print("accepted keys:", accepted_keys)
print("denied keys:", denied_keys)
print("unaccepted keys:", unaccepted_keys)
print("rejected keys:", rejected_keys)
print("unknown keys:", unknown_keys)