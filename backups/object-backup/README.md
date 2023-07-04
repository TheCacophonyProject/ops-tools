# object backup
## Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to chang the path in the cron file.\
- Copy `object-backup_TEMPLATE.yaml` to `object-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt` Make sure you do this as the user that will be running the cron script.
- Test script with `./object-backup.py <config file> --dry-run`
- Copy `object-backup-cron` to `/etc/cron.d/object-backup-cron` Cron job can be modified to run multiple times running with different config files.