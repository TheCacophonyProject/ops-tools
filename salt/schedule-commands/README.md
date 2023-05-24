## Schedule commands
Schedule commands will listen to devices connecting to salt and wait for given devices to connect and then run a command on them.

This is configured in the `commands.txt` file where examples commands can be seen.

### Setup
- Copy `schedule-commands.service file` into `/etc/systemd/system/`
- `sudo pip install salt`
- Enable service `systemctl enable schedule-commands`
- Start service `sudo systemctl start schedule-commands.service`
- Check logs with `journalctl -u schedule-commands.service` to ensure no errors.