# Salt backup
## Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to change the path in the cron file.
- Copy `salt-backup-cron` to `/etc/cron.d/salt-backup-cron`
- Copy `salt-backup_TEMPLATE.yaml` to `salt-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt`
- Install backblaze tool b2 https://www.backblaze.com/b2/docs/quick_command_line.html
- Run `sudo b2 authorize-account` to add key for root user for the bucket you want to backup to.
- Test with `sudo ./salt-backup.py`