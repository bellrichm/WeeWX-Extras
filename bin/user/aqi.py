#
#    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
WeeWX module to manage the registration of the AQI XType.
The AQI XType is part of weewx-airlink extension.
It can be found here,https://github.com/chaunceygardiner/weewx-airlink.
"""

from weewx.engine import StdService
import weewx.xtypes
import user.airlink

def logdbg(msg):
    """ Log debug level. """
    log.debug(msg)

def loginf(msg):
    """ Log informational level. """
    log.info(msg)

def logerr(msg):
    """ Log error level. """
    log.error(msg)

class AQI(StdService):
    """ A class to manage the registration of the AQI XType"""
    def __init__(self, engine, config_dict):
        super(AQI, self).__init__(engine, config_dict)

        loginf("This extension has been deprecated and replaced by, https://github.com/bellrichm/weewx-airlink")

        # register the XType
        self.aqi = user.airlink.AQI()
        weewx.xtypes.xtypes.append(self.aqi)

        # ToDo - configure what, if anything, to add to the loop packet
        #self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def shutDown(self):
        """Run when an engine shutdown is requested."""
        weewx.xtypes.xtypes.remove(self.aqi)

    def new_loop_packet(self, event):
        """ Handle the new loop packet event. """
        if 'pm2_5' in event.packet:
            event.packet['pm2_5_aqi'] = user.airlink.AQI.compute_pm2_5_aqi(event.packet['pm2_5'])
            event.packet['pm2_5_aqi_color'] = user.airlink.AQI.compute_pm2_5_aqi_color(event.packet['pm2_5_aqi'])
