#!/usr/bin/env python3

import contextlib
import logging
import logging.config
import signal

from datetime import datetime, timedelta

from unoserver.server import UnoServer  # type: ignore

from pandora.default import AbstractManager, get_config

logging.config.dictConfig(get_config('logging'))


class UnoserverLauncher(AbstractManager):

    def __init__(self, loglevel: int=logging.INFO):
        super().__init__(loglevel)
        self.script_name = 'unoserver'
        self.timeout = 3600

    def _launch_unoserver(self):
        unoserver = UnoServer()
        return unoserver.start(), datetime.now()

    @staticmethod
    def _raise_timeout(_, __):
        raise TimeoutError

    @contextlib.contextmanager
    def _timeout_context(self):
        if self.timeout != 0:
            # Register a function to raise a TimeoutError on the signal.
            signal.signal(signal.SIGALRM, self._raise_timeout)
            signal.alarm(self.timeout)
            try:
                yield
            except TimeoutError:
                self.process.kill()
            finally:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
        else:
            yield

    def safe_run(self):
        # it sometimes fails but simply restarting the server fixes it
        self.process, start_time = self._launch_unoserver()
        self.set_running()
        retry = 0
        while True:
            with self._timeout_context():
                self.run(sleep_in_sec=10)
            if self.shutdown_requested():
                break
            if retry >= 3:
                self.logger.critical(f'Unable to restart {self.script_name}.')
                break
            if datetime.now() - start_time > timedelta(seconds=60):
                retry = 0
            else:
                retry += 1
            self.process, start_time = self._launch_unoserver()
            self.set_running()


def main():
    u = UnoserverLauncher()
    u.safe_run()


if __name__ == '__main__':
    main()
