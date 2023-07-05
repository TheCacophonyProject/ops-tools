# Object Backup
## Setup
- Clone/download `ops-tools` repository to `/opt/ops-tools` if not already. If installed in a different directory you will need to change the path in the cron file.
    ```
    cd /opt
    sudo git clone https://github.com/TheCacophonyProject/ops-tools.git
    cd ops-tools/backups/object-backup
    ```
- Copy `object-backup_TEMPLATE.yaml` to `object-backup.yaml` and fill out the config file. You might want to have multiple config files.
    ```
    sudo cp object-backup_TEMPLATE.yaml object-backup.yaml
    sudo vi object-backup.yaml
    ```
- Setup the Python virtual environment. This should be run in the `object-backup` directory.
    ```
    sudo python3 -m venv object-backup-env
    ```
- Install requirements:
    ```
    sudo ./object-backup-env/bin/pip3 install -r requirements.txt
    ```
- Test script:
    ```
    object-backup-env/bin/python3 ./object-backup.py <config file> --dry-run
    ```
- Copy `object-backup-cron` to `/etc/cron.d/object-backup-cron`. The cron job can be modified to run multiple times with different config files.
    ```
    sudo cp object-backup-cron /etc/cron.d/object-backup-cron
    sudo vi /etc/cron.d/object-backup-cron
    ```
