# object backup
## Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to chang the path in the cron file.
- Copy `object-backup-cron` to `/etc/cron.d/object-backup-cron`
- Copy `object-backup_TEMPLATE.yaml` to `object-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt`
- Test script with `./object-backup.py --dry-run` Might have to switch user to root so correct minio config file is used.