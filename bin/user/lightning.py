#
#    Copyright (c) 2024 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

'''
WeeWX service to augment lightning data.
'''

import logging

import weewx
import weewx.engine

log = logging.getLogger(__name__)

class Lightning(weewx.engine.StdService):
    ''' Save additional lightning event data to the WeeWX packet.'''
    def __init__(self, engine, config_dict):
        super(Lightning, self).__init__(engine, config_dict)

        self.strike_count_total = None
        self.last_strike_distance = None
        self.last_strike_time = None
        self.first_strike_distance = None
        self.first_strike_time = None
        self.min_strike_distance = None
        self.min_strike_time = None
        self.max_strike_distance = None
        self.max_strike_time = None

        service_dict = config_dict.get('Lightning', {})
        self.contains_total = service_dict.get('contains_total', True)

        self.lightning_count_field_name = service_dict.get('lightning_count_field_name', 'lightning_count')
        self.lightning_distance_field_name = service_dict.get('lightning_distance_field_name', 'lightning_distance')

        self.strike_count_field_name = service_dict.get('strike_count_field_name', 'strike_count')
        self.strike_distance_field_name = service_dict.get('strike_distance_field_name', 'storm_distance_km')

        self.last_distance_field_name = service_dict.get('last_distance_field_name', 'lightning_last_distance')
        self.last_det_time_field_name = service_dict.get('last_det_time_field_name', 'lightning_last_det_time')

        self.first_distance_field_name = service_dict.get('first_distance_field_name', 'lightning_first_distance')
        self.first_det_time_field_name = service_dict.get('first_det_time_field_name', 'lightning_first_det_time')

        self.min_distance_field_name = service_dict.get('min_distance_field_name', 'lightning_min_distance')
        self.min_det_time_field_name = service_dict.get('min_det_time_field_name', 'lightning_min_det_time')

        self.max_distance_field_name = service_dict.get('max_distance_field_name', 'lightning_max_distance')
        self.max_det_time_field_name = service_dict.get('max_det_time_field_name', 'lightning_max_det_time')

        self.bind(weewx.PRE_LOOP, self.pre_loop)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def pre_loop(self, _event):
        ''' Handle the WeeWX PRE_LOOP event. '''
        self.last_strike_distance = None
        self.last_strike_time = None
        self.first_strike_distance = None
        self.first_strike_time = None
        self.min_strike_distance = None
        self.min_strike_time = None
        self.max_strike_distance = None
        self.max_strike_time = None

    def new_loop_packet(self, event):
        ''' Handle the WeeWX POST_LOOP event.'''
        if self.strike_count_field_name not in event.packet or self.strike_distance_field_name not in event.packet:
            return

        log.info(event.packet)
        log.info(self.strike_count_total)
        log.info(self.last_strike_distance)
        log.info(self.last_strike_time)
        log.info(self.first_strike_distance)
        log.info(self.first_strike_time)
        log.info(self.min_strike_distance)
        log.info(self.min_strike_time)
        log.info(self.max_strike_distance)
        log.info(self.max_strike_time)

        date_time = event.packet['dateTime']
        strike_distance = event.packet[self.strike_distance_field_name]
        strike_count_total = event.packet[self.strike_count_field_name]
        strike_count = None

        if self.contains_total:
            log.info("Calculating delta %s %s", self.strike_count_total, strike_count_total)
            if self.strike_count_total is not None and strike_count_total is not None:
                if strike_count_total - self.strike_count_total > 0:
                    strike_count = strike_count_total - self.strike_count_total
                else:
                    strike_count = self.strike_count_total
            self.strike_count_total = strike_count_total
        else:
            strike_count = strike_count_total

        log.info("Setting last strike distance %s and time %s", strike_distance, date_time)
        self.last_strike_distance = strike_distance
        self.last_strike_time = date_time

        if self.first_strike_distance is None:
            log.info("Setting first strike distance %s and time %s", strike_distance, date_time)
            self.first_strike_distance = strike_distance
            self.first_strike_time = date_time

        if self.min_strike_distance is None or strike_distance <= self.min_strike_distance:
            log.info("Setting min strike distance %s and time %s", strike_distance, date_time)
            self.min_strike_distance = strike_distance
            self.min_strike_time = date_time

        if self.max_strike_distance is None or strike_distance >= self.max_strike_distance:
            log.info("Setting max strike distance %s and time %s", strike_distance, date_time)
            self.max_strike_distance = strike_distance
            self.max_strike_time = date_time

        if strike_count:
            event.packet[self.lightning_count_field_name] = strike_count
            event.packet[self.lightning_distance_field_name] = strike_distance
        else:
            event.packet[self.lightning_count_field_name] = None
            event.packet[self.lightning_distance_field_name] = None

        event.packet[self.last_distance_field_name] = self.last_strike_distance
        event.packet[self.last_det_time_field_name] = self.last_strike_time
        event.packet[self.first_distance_field_name] = self.first_strike_distance
        event.packet[self.first_det_time_field_name] = self.first_strike_time
        event.packet[self.min_distance_field_name] = self.min_strike_distance
        event.packet[self.min_det_time_field_name] = self.min_strike_time
        event.packet[self.max_distance_field_name] = self.max_strike_distance
        event.packet[self.max_det_time_field_name] = self.max_strike_time

        log.info(event.packet)
