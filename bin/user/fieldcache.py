"""
WeeWX service that will cache archive record field values.
If the next archive record is missing the value, the cached value is used.
This can be useful for field values that 'arrive' less frequently than the archive interval.

Installation:
    Put this file in the bin/user directory.
    Update weewx.conf [FieldCache] as needed to configure the service.
    Add the service to the engine service's configuration.

Configuration:
[FieldCache]
    # The unit system of the cache.
    # Default is US.
    unit_system = US
    # The WeeWX fields to cache.
    [[fields]]
        # The name of the field to cache.
        [[[field1]]]
            # In seconds how long the cache is valid.
            # Value of 0 means the cache is always expired.
            # Useful if missing fields should have a value of None instead of the previous value.
            # Value of None means the cache never expires.
            # Default is None.
            expires_after = None
"""

import time
import configobj
import weewx
from weeutil.weeutil import to_float
from weewx.wxengine import StdService

VERSION = "0.1"

try:
    import weeutil.logger # pylint: disable=unused-import
    import logging
    log = logging.getLogger(__name__) # pylint: disable=invalid-name

    def logdbg(msg):
        """ Log debug messages. """
        log.debug(msg)

    def loginf(msg):
        """ Log informational messages. """
        log.info(msg)

    def logerr(msg):
        """ Log error messages. """
        log.error(msg)

except ImportError:
    import syslog

    def logmsg(level, msg):
        """ Log the message."""
        syslog.syslog(level, 'filepile: %s:' % msg)

    def logdbg(msg):
        """ Log debug messages. """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ Log informational messages. """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ Log error messages. """
        logmsg(syslog.LOG_ERR, msg)

class Cache(object):
    """ Manage the cache. """
    def __init__(self, unit_system):
        self.unit_system = unit_system
        self.cached_values = {}

    def get_value(self, key, timestamp, expires_after):
        """ Get the cached value. """
        if key in self.cached_values and \
            (expires_after is None or timestamp - self.cached_values[key]['timestamp'] < expires_after):
            return self.cached_values[key]['value']

        return None

    def update_value(self, key, value, unit_system, timestamp):
        """ Update the cached value. """
        if unit_system != self.unit_system:
            raise ValueError("Unit system does not match unit system of the cache. %s vs %s"
                             % (unit_system, self.unit_system))
        self.cached_values[key] = {}
        self.cached_values[key]['value'] = value
        self.cached_values[key]['timestamp'] = timestamp

    def update_timestamp(self, key, timestamp):
        """ Update the ts. """
        if key in self.cached_values:
            self.cached_values[key]['timestamp'] = timestamp

    def remove_value(self, key):
        """ Remove a cached value. """
        if key in self.cached_values:
            del self.cached_values[key]

    def clear_cache(self):
        """ Clear the cache """
        self.cached_values = {}

class FieldCache(StdService):
    """ Fill in any missing field data with data from the previous record. """
    def __init__(self, engine, config_dict):
        super(FieldCache, self).__init__(engine, config_dict)

        fieldcache_dict = config_dict.get('FieldCache', {})

        unit_system_name = fieldcache_dict.get('unit_system', 'US').strip().upper()
        if unit_system_name not in weewx.units.unit_constants:
            raise ValueError("FieldCache: Unknown unit system: %s" % unit_system_name)
        unit_system = weewx.units.unit_constants[unit_system_name]

        self.fields = {}
        fields_dict = fieldcache_dict.get('fields', {})
        for field in fieldcache_dict.get('fields', {}):
            self.fields[field] = {}
            self.fields[field]['expires_after'] = to_float(fields_dict[field].get('expires_after', None))

        loginf(fieldcache_dict)
        self.cache = Cache(unit_system)

        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        """ Handle the new archive record event. """
        target_data = {}

        for field in self.fields:
            if field in event.record:
                self.cache.update_value(field,
                                        event.record[field],
                                        event.record['usUnits'],
                                        time.time())
            else:
                target_data[field] = self.cache.get_value(field,
                                                          time.time(),
                                                          self.fields[field]['expires_after'])

        event.record.update(target_data)

# A mini integration "test"
if __name__ == "__main__":
    import os
    import weeutil.weeutil
    import weeutil.logger
    from weewx.engine import StdEngine # pylint: disable=ungrouped-imports
    weewx.debug = 1
    weeutil.logger.setup('', {})

    MIN_CONFIG_DICT = {
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

    std_engine = StdEngine(MIN_CONFIG_DICT) # pylint: disable=invalid-name

    config_file = 'weewx.conf' # pylint: disable=invalid-name
    config_path = os.path.abspath(config_file) # pylint: disable=invalid-name
    config = configobj.ConfigObj(config_path, file_error=True) # pylint: disable=invalid-name
    service = FieldCache(std_engine, config) # pylint: disable=invalid-name

    data = { # pylint: disable=invalid-name
        'usUnits': 1,
        'dateTime': time.time(),
        'field1': 'value1-a',
        'field2': 'value2-a',
        'field3': 'value3-a',
        'field4': 'value4-a'
    }
    print(weeutil.weeutil.to_sorted_string(data))

    new_archive_record_event = weewx.Event(weewx.NEW_ARCHIVE_RECORD, # pylint: disable=invalid-name
                                           record=data,
                                           origin='hardware')

    service.new_archive_record(new_archive_record_event)
    print(weeutil.weeutil.to_sorted_string(data))

    del data['field1']
    del data['field2']
    del data['field3']
    data['field4'] = 'value4-b'
    print(weeutil.weeutil.to_sorted_string(data))

    service.new_archive_record(new_archive_record_event)
    print(weeutil.weeutil.to_sorted_string(data))
