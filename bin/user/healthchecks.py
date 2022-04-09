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
import threading

try:
    # Python 3
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from urllib2 import urlopen

import weewx
from weewx.engine import StdService
from weewx.reportengine import ReportGenerator

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

def send_ping(host, uuid, timeout, ping_type=None):
    """Send the HealthChecks 'ping'."""
    if ping_type:
        url = "https://%s/%s/%s" %(host, uuid, ping_type)
    else:
        url = "https://%s/%s" %(host, uuid)

    try:
        urlopen(url, timeout=timeout)
    except socket.error as exception:
        logerr("Ping failed: %s" % exception)

class HealthChecksService(StdService):
    """ A service to ping a healthchecks server.. """
    def __init__(self, engine, config_dict):
        super(HealthChecksService, self).__init__(engine, config_dict)

        # service_dict = config_dict.get('HealthChecks', {})
        skin_dict = self.config_dict.get('StdReport', {}).get('HealthChecks', {})

        self.enable = to_bool(skin_dict.get('enable', True))
        if not self.enable:
            loginf("Not enabled, exiting.")
            return

        self.host = skin_dict.get('host', 'hc-ping.com')
        self.timeout = to_int(skin_dict.get('timeout', 10))
        self.uuid = skin_dict.get('uuid')
        if not self.uuid:
            raise ValueError("uuid option is required.")

        send_ping(self.host, self.uuid, self.timeout, "start")

        # possible option to run as a service only
        # self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        # self._thread = HealthChecksServiceThread(self.host, self.uuid, self.timeout)
        # self._thread.start()

    def new_archive_record(self, event):
        """The new archive record event."""
        self._thread.threading_event.set()

    def shutDown(self):
        """Run when an engine shutdown is requested."""
        loginf("SHUTDOWN - initiated")

        send_ping(self.host, self.uuid, self.timeout, "fail")
        loginf("fail ping sent")

        if self._thread:
            loginf("SHUTDOWN - thread initiated")
            self._thread.running = False
            self._thread.threading_event.set()
            self._thread.join(20.0)
            if self._thread.is_alive():
                logerr("Unable to shut down %s thread" %self._thread.name)

            self._thread = None

class HealthChecksServiceThread(threading.Thread):
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

        while self.running:
            self.threading_event.wait()
            send_ping(self.host, self.uuid, self.timeout)
            self.threading_event.clear()

        loginf("exited loop")

class HealthChecksGenerator(ReportGenerator):
    """Class for managing the healthchecks generator."""
    def __init__(self, config_dict, skin_dict, *args, **kwargs):
        """Initialize an instance of HealthChecksGenerator"""
        weewx.reportengine.ReportGenerator.__init__(self, config_dict, skin_dict, *args, **kwargs)

        self.host = skin_dict.get('host', 'hc-ping.com')
        self.timeout = to_int(skin_dict.get('timeout', 10))
        self.uuid = skin_dict.get('uuid')
        if not self.uuid:
            raise ValueError("uuid option is required.")

    def run(self):
        send_ping(self.host, self.uuid, self.timeout)

if __name__ == "__main__":
    pass
