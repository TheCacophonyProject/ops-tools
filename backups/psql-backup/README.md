# PostgreSQL backup

## Setup

- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in a different directory you will need to change the path in the cron file and the shebang line in `psql-backup.py`.
- Copy `psql-backup_TEMPLATE.yaml` to `psql-backup.yaml` and fill out the config file.
- Create a virtual environment and install dependencies:

  ``` bash
  cd /opt/ops-tools/backups/psql-backup
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
  ```

- Copy `psql-backup-cron` to `/etc/cron.d/psql-backup-cron`
- Test script with `./psql-backup.py --dry-run`
