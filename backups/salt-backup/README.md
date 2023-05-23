# Salt backup

## Buckets and Keys setup
The script will not delete the files so it is recommended to setup the bucket to have rules about automatically deleting files after a set period of time.

### Backblaze b2 bucket
Setup a bucket in backblaze with these config settings:
- Lifecycle settings
    - File Path: "/"
    - Days Till Hide: 365
    - Days Till Delete: 10  
- Object Lock, Default Retention Policy: 365

After setting up the bucket create a key that has read/write permissions just for that bucket for the salt server to use.

### Amazon AWS S3
//TODO


## Backups script Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools`. If installed in different directory you will need to change the path in the cron file.
- Copy `salt-backup-cron` to `/etc/cron.d/salt-backup-cron`
- Copy `salt-backup_TEMPLATE.yaml` to `salt-backup.yaml` and fill out the config file.
- Run `sudo pip3 install -r requirements.txt`
- Make sure `s5cmd` is installed, this should already be installed on a salt server when it was setup.
- Test with `sudo ./salt-backup.py`