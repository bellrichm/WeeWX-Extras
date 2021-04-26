#
#    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
This driver just emits NEW_ARCHIVE_RECORD events. It can be used to trigger events without archiving a
record to the DB. When using it, the StdArchive service should be removed.
It is an example of 'abusing' WeeWX to do things it was never intended to do.
"""

# need to be python 2 compatible pylint: disable=bad-option-value, raise-missing-from, super-with-arguments
# pylint: enable=bad-option-value
import sys
import time

import configobj

import weewx

from weeutil.weeutil import to_int, to_sorted_string

from weewx.engine import StdEngine
from weewx.drivers import AbstractConfEditor

DRIVER_NAME = 'ArchiveDriver'
DRIVER_VERSION = '0.1'
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

    def logdbg(name, msg):
        """ Log debug level. """
        log.debug("(%s) %s", name, msg)

    def loginf(name, msg):
        """ Log informational level. """
        log.info("(%s) %s", name, msg)

    def logerr(name, msg):
        """ Log error level. """
        log.error("(%s) %s", name, msg)

except ImportError:
    # Old-style weewx logging
    import syslog
    def setup_logging(logging_level, config_dict): # Need to match signature pylint: disable=unused-argument
        """ Setup logging for running in standalone mode."""
        syslog.openlog('wee_MQTTSS', syslog.LOG_PID | syslog.LOG_CONS)
        if logging_level:
            syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
        else:
            syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))

    def logmsg(level, name, msg):
        """ Log the message at the designated level. """
        # Replace '__name__' with something to identify your application.
        syslog.syslog(level, '__name__: %s: (%s)' % (name, msg))

    def logdbg(name, msg):
        """ Log debug level. """
        logmsg(syslog.LOG_DEBUG, name, msg)

    def loginf(name, msg):
        """ Log informational level. """
        logmsg(syslog.LOG_INFO, name, msg)

    def logerr(name, msg):
        """ Log error level. """
        logmsg(syslog.LOG_ERR, name, msg)

def loader(config_dict, engine):
    """ Load and return the driver. """
    return ArchiveDriver(engine, **config_dict[DRIVER_NAME])

def confeditor_loader():
    """ Load and return the configuration editor. """
    return ArchiveDriverConfigurationEditor()

class ArchiveDriverConfigurationEditor(AbstractConfEditor):
    """ Methods for producing and updating configuration stanzas for use in configuration file. """
    @property
    def default_stanza(self):
        return ""

class ArchiveDriver(weewx.drivers.AbstractDevice): # (methods not used) pylint: disable=abstract-method
    """ Add observations to WeeWX """
    def __init__(self, engine, **stn_dict):
        self.engine = engine
        self._archive_interval = to_int(stn_dict.get('archive_interval', 300))
        self.delay = to_int(stn_dict.get('delay', 0))
        self.units = to_int(stn_dict.get('units', 1))

    def closePort(self):
        pass

    @property
    def hardware_name(self):
        return 'ArchiveDriver'

    @property
    def archive_interval(self):
        """ The archive interval. """
        return self._archive_interval

    def genLoopPackets(self):
        while True:
            data = {'usUnits': self.units, 'interval': self._archive_interval, 'dateTime': 0}
            current_time = int(time.time() + 0.5)
            end_period_ts = (int(current_time / self._archive_interval) + 1) * self._archive_interval
            end_delay_ts = end_period_ts + self.delay
            sleep_amount = end_delay_ts - current_time
            print(current_time)
            print("Sleeping %i seconds" % sleep_amount)
            time.sleep(sleep_amount)
            print(int(time.time()))

            data['dateTime'] = end_period_ts
            new_archive_record_event = weewx.Event(weewx.NEW_ARCHIVE_RECORD, origin='software', record=data)
            self.engine.dispatchEvent(new_archive_record_event)

def main():
    """ Mainline function """
    min_config_dict = {
        'Station': {
            'altitude': [0, 'foot'],
            'latitude': 0,
            'station_type': 'Simulator',
            'longitude': 0
        },
        'Simulator': {
            'driver': 'weewx.drivers.simulator',
        },
        'Engine': {
            'Services': {}
        }
    }

    engine = StdEngine(min_config_dict)

    config = {DRIVER_NAME: {}}
    config_dict = configobj.ConfigObj(config)
    driver = "user.archivedriver"
    __import__(driver)
    # This is a bit of Python wizardry. First, find the driver module
    # in sys.modules.
    driver_module = sys.modules[driver]
    # Find the function 'loader' within the module:
    loader_function = getattr(driver_module, 'loader')
    driver = loader_function(config_dict, engine)

    for packet in driver.genLoopPackets():
        print("Packet is: %s %s"
              % (weeutil.weeutil.timestamp_to_string(packet['dateTime']),
                 to_sorted_string(packet)))

if __name__ == "__main__":
    main()
