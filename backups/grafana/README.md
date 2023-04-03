# Grafana backup
## Setup
- Requires python3.7 or later.
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to change the path in the cron file.
- Copy `grafana-backup-cron` to `/etc/cron.d/grafana-backup-cron`
- Copy `grafana-backup_TEMPLATE.yaml` to `grafana-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt`
- Test with `sudo ./grafana-backup.py`