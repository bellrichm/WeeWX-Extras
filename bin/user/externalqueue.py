#
#    Copyright (c) 2020-2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
Write loop and/or archive data to a persistent queue. The persistent queue is implemented via a relational database.

Configuration:
[ExternalQueue]
   # Whether the service is enabled or not.
   # Valid values: True or False
   # Default is True.
   # enable = True

    # The database binding.
    # Default is ext_queue_binding
    # data_binding = ext_queue_binding

    # The binding, loop or archive.
    # Default is loop.
    # Only used by the service.
    binding = loop
"""

# todo - rename table

# need to be python 2 compatible pylint: disable=bad-option-value, raise-missing-from, super-with-arguments
# pylint: enable=bad-option-value
import json
import time
import traceback

import weewx
from weewx.engine import StdService

from weeutil.weeutil import to_bool

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

        weeutil.logger.setup('wee_MQTTSS', config_dict)

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
        # Replace '__name__' with something to identify your application.
        syslog.syslog(level, '__name__: %s:' % msg)

    def logdbg(msg):
        """ Log debug level. """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ Log informational level. """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ Log error level. """
        logmsg(syslog.LOG_ERR, msg)

schema = [ # confirm to standards pylint: disable=invalid-name
    ('dateTime', 'INTEGER NOT NULL'),
    ('usUnits', 'INTEGER'),
    ('interval', 'INTEGER'),
    ('dataType', 'STRING'),
    ('data', 'STRING'),
    ]

def gettid():
    """Get TID as displayed by htop.
       This is architecture dependent."""
    import ctypes #  need to be python 2 compatible, Want to keep this piece of code self contained. pylint: disable=bad-option-value, import-outside-toplevel
    # pylint: enable=bad-option-value
    libc = 'libc.so.6'
    for cmd in (186, 224, 178):
        tid = ctypes.CDLL(libc).syscall(cmd)
        if tid != -1:
            return tid

    return 0

class ExternalQueue(StdService):
    """ A service to put data on to an external queue. """
    def __init__(self, engine, config_dict):
        super(ExternalQueue, self).__init__(engine, config_dict)

        service_dict = config_dict.get('ExternalQueue', {})

        self.enable = to_bool(service_dict.get('enable', True))
        if not self.enable:
            loginf("Not enabled, exiting.")
            return

        data_binding = service_dict.get('data_binding', 'ext_queue_binding')
        binding = weeutil.weeutil.option_as_list(service_dict.get('binding', ['loop']))
        self.dbm = self.engine.db_binder.get_manager(data_binding=data_binding, initialize=True)
        self.dbm.getSql("PRAGMA journal_mode=WAL;")

        if 'loop' in binding:
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

        if 'archive' in binding:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        # logdbg("Threadid of ExternalQueue is: %s" % gettid())

    def shutDown(self): # need to override parent - pylint: disable=invalid-name
        """Run when an engine shutdown is requested."""
        try:
            self.dbm.close()
        except Exception as exception: # pylint: disable=broad-except
            logerr("Close queue dbm failed %s" %exception)
            logerr(traceback.format_exc())

    def new_loop_packet(self, event):
        """ Handle loop packets. """
        self.process_record('loop', event.packet)

    def new_archive_record(self, event):
        """ Handle archive records. """
        self.process_record('archive', event.record)

    def process_record(self, data_type, record):
        """ Add the loop data to the queue """
        # todo
        #if self.topics[topic]['augment_record'] and dbmanager is not None:
        #    updated_record = self.get_record(updated_record, dbmanager)
        log.debug("      Queueing   (%s): %s", int(time.time()), int(record['dateTime']))
        self.dbm.getSql( \
                  "INSERT INTO archive (dateTime, usUnits, interval, dataType, data) VALUES (?, ?, ?, ?, ?);",
                  [record['dateTime'], 0, 0, data_type, json.dumps(record)])

if __name__ == "__main__":
    pass
