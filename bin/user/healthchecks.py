#
#    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
'ping' healthchecks on every archive record.
See, https://healthchecks.io/docs/

Configuration:
[HealthChecks]
   # Whether the service is enabled or not.
   # Valid values: True or False
   # Default is True.
   # enable = True

    # The host to 'ping'
    # Default is hc-ping.com
    # host = hc-ping.com

    # The HealthChecks uuid
    uuid =

    # The http request timeout
    # The default is 10
    # timeout = 10
"""

import socket
import urllib.request
import threading

import weewx
from weewx.engine import StdService

from weeutil.weeutil import to_bool, to_int

VERSION = "0.1"

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__) # confirm to standards pylint: disable=invalid-name
    def setup_logging(logging_level, config_dict):
        """ Setup logging for running in standalone mode."""
        if logging_level:
            weewx.debug = logging_level

        weeutil.logger.setup('wee_HealthChecks', config_dict)

    def logdbg(msg):
        """ Log debug level. """
        log.debug(msg)

    def loginf(msg):
        """ Log informational level. """
        log.info(msg)

    def logerr(msg):
        """ Log error level. """
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        """ Log the message at the designated level. """
        syslog.syslog(level, 'wee_HealthChecks: %s:' % msg)

    def logdbg(msg):
        """ Log debug level. """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ Log informational level. """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ Log error level. """
        logmsg(syslog.LOG_ERR, msg)

class HealthChecks(StdService):
    """ A service to ping a healthchecks server.. """
    def __init__(self, engine, config_dict):
        super(HealthChecks, self).__init__(engine, config_dict)

        service_dict = config_dict.get('HealthChecks', {})

        self.enable = to_bool(service_dict.get('enable', True))
        if not self.enable:
            loginf("Not enabled, exiting.")
            return

        host = service_dict.get('host', 'hc-ping.com')
        timeout = to_int(service_dict.get('timeout', 10))
        uuid = service_dict.get('uuid')
        if not uuid:
            raise ValueError("uuid option is required.")

        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        self._thread = HealthChecksThread(host, uuid, timeout)
        self._thread.start()

    def new_archive_record(self, event):
        """The new archive record event."""
        self._thread.threading_event.set()

    def shutDown(self):
        """Run when an engine shutdown is requested."""
        loginf("SHUTDOWN - initiated")
        if self._thread:
            loginf("SHUTDOWN - thread initiated")
            self._thread.running = False
            self._thread.threading_event.set()
            self._thread.join(20.0)
            if self._thread.is_alive():
                logerr("Unable to shut down %s thread" %self._thread.name)

            self._thread = None

class HealthChecksThread(threading.Thread):
    """A service to send 'pings' to a HealthChecks server. """
    def __init__(self, host, uuid, timeout):
        threading.Thread.__init__(self)

        self.running = False

        self.host = host
        self.uuid = uuid
        self.timeout = timeout

        self.threading_event = threading.Event()

    def run(self):
        self.running = True
        self._send_ping("start")

        while self.running:
            self.threading_event.wait()
            self._send_ping()

            self.threading_event.clear()

        self._send_ping("fail")

    def _send_ping(self, ping_type=None):
        if ping_type:
            url = "https://%s/%s/%s" %(self.host, self.uuid, ping_type)
        else:
            url = "https://%s/%s" %(self.host, self.uuid)

        try:
            urllib.request.urlopen(url, timeout=self.timeout)
        except socket.error as exception:
            logerr("Ping failed: %s" % exception)

if __name__ == "__main__":
    pass
