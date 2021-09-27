# PostgreSQL backup
## Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to chang the path in the cron file.
- Copy `psql-backup.cron` to `/etc/cron.d/psql-backup.cron`
- Copy `psql-backup_TEMPLATE.yaml` to `psql-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt`
- Test script with `./psql-backup.py --dry-run`