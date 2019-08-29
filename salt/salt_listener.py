import salt.config
import salt.utils.event

ETC_SALT_MASTER = "/etc/salt/master"


class SaltListener:
    def __init__(self, timeout=None):
        opts = salt.config.client_config(ETC_SALT_MASTER)
        self.listener = salt.utils.event.get_event(
            "master", sock_dir=opts["sock_dir"], transport=opts["transport"], opts=opts
        )
        if timeout is None:
            self.timeout_secs = 0
        else:
            self.timeout_secs = timeout.total_seconds()

    def __iter__(self):
        while True:
            yield self.listener.get_event(wait=self.timeout_secs, full=True)
