#
#    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
Configure additional observations and units for WeeWX to use.
See, http://weewx.com/docs/customizing.htm#Creating_a_new_unit_group
This assumes a good knowledge of customizing WeeWX.
This will make maintenance easier.

This was directly stolen from MQTTSubscribe, so the configuration names and levels may not make the most sense here.
But, the _config_weewx method can be copied and pasted with no changes.

[AdditionalObservations]
    [[weewx]]
        [[[observations]]]
            # The observation and unit group it belongs to.
            observation-name = unit-group-name

        [[[units]]]
            # The unit to be added
            [[[[unit-name-a]]]]
                # The unit system this unit belongs to.
                unit_system = us
                # The unit group this unit belongs to.
                group = unit-group-name
                # Formatting for this unit.
                format = formatting for unit
                # Label for this unit.
                label = label for unit
                [[[[[conversion]]]]]
                    # Conversion formula to other unit.
                    to-unit-name-b = function to convert from unit to to-unit

            [[[[unit-name-b]]]]
                unit_system = metric, metricwx
"""

# need to be python 2 compatible pylint: disable=bad-option-value, raise-missing-from, super-with-arguments
# pylint: enable=bad-option-value
import os

import configobj

import weewx

from weeutil.weeutil import to_bool
from weewx.engine import StdService

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


class AddObservations(StdService):
    """ Add observations to WeeWX """

    def __init__(self, engine, config_dict):
        super(AddObservations, self).__init__(engine, config_dict)

        service_dict = config_dict.get('AdditionalObservations', {})

        enable = to_bool(service_dict.get('enable', True))
        if not enable:
            loginf("Not enabled, exiting.")
            return

        weewx_config = service_dict.get('weewx')
        if weewx_config:
            self._config_weewx(weewx_config)

    @staticmethod
    def _config_weewx(weewx_config):
        # pylint: disable=too-many-branches
        units = weewx_config.get('units')
        if units:
            for unit in units.sections:
                unit_config = units.get(unit)

                group = unit_config.get('group')
                if not group:
                    raise ValueError("%s is missing a group." % unit)

                unit_systems = weeutil.weeutil.option_as_list(unit_config.get('unit_system'))
                if not unit_systems:
                    raise ValueError("%s is missing an unit_system." % unit)

                for unit_system in unit_systems:
                    if unit_system == 'us':
                        weewx.units.USUnits.extend({group: unit})
                    elif unit_system == 'metric':
                        weewx.units.MetricUnits.extend({group: unit})
                    elif unit_system == 'metricwx':
                        weewx.units.MetricWXUnits.extend({group: unit})
                    else:
                        raise ValueError("Invalid unit_system %s for %s." % (unit_system, unit))

                format_config = unit_config.get('format')
                if format_config:
                    weewx.units.default_unit_format_dict[unit] = format_config
                label = unit_config.get('label')
                if label:
                    weewx.units.default_unit_label_dict[unit] = label

                conversion = unit_config.get('conversion')
                if conversion:
                    for to_unit in conversion:
                        if unit not in weewx.units.conversionDict:
                            weewx.units.conversionDict[unit] = {}

                        weewx.units.conversionDict[unit][to_unit] = eval(conversion[to_unit]) # pylint: disable=eval-used

        observations = weewx_config.get('observations')
        if observations:
            for observation in observations.keys():
                weewx.units.obs_group_dict.extend({observation: observations[observation]})

if __name__ == "__main__":

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

    std_engine = weewx.engine.StdEngine(MIN_CONFIG_DICT) # pylint: disable=invalid-name

    config_file = 'weewx.conf' # pylint: disable=invalid-name
    config_path = os.path.abspath(config_file) # pylint: disable=invalid-name
    config = configobj.ConfigObj(config_path, file_error=True) # pylint: disable=invalid-name
    service = AddObservations(std_engine, config) # pylint: disable=invalid-name

    print("weewx.units.USUnits:\n%s" % weewx.units.USUnits)
    print("weewx.units.MetricUnits:\n%s" % weewx.units.MetricUnits)
    print("weewx.units.MetricWXUnits:\n%s" % weewx.units.MetricWXUnits)
    print("weewx.units.default_unit_format_dict:\n%s" % weewx.units.default_unit_format_dict)
    print("weewx.units.default_unit_label_dict:\n%s" % weewx.units.default_unit_label_dict)
    print("weewx.units.conversionDict:\n%s" % weewx.units.conversionDict)
    print("weewx.units.obs_group_dict:\n%s" % weewx.units.obs_group_dict)
