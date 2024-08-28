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

        self.last_lightning_distance = None
        self.last_lightning_time = None
        self.first_lightning_distance = None
        self.first_lightning_time = None
        self.min_lightning_distance = None
        self.min_lightning_time = None
        self.max_lightning_distance = None
        self.max_lightning_time = None

        service_dict = config_dict.get('Lightning', {})

        self.lightning_distance_field_name = service_dict.get('lightning_distance_field_name', 'lightning_distance')

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
        self.last_lightning_distance = None
        self.last_lightning_time = None
        self.first_lightning_distance = None
        self.first_lightning_time = None
        self.min_lightning_distance = None
        self.min_lightning_time = None
        self.max_lightning_distance = None
        self.max_lightning_time = None

    def new_loop_packet(self, event):
        ''' Handle the WeeWX POST_LOOP event.'''
        if self.lightning_distance_field_name not in event.packet:
            return

        log.info(event.packet)
        log.info(self.last_lightning_distance)
        log.info(self.last_lightning_time)
        log.info(self.first_lightning_distance)
        log.info(self.first_lightning_time)
        log.info(self.min_lightning_distance)
        log.info(self.min_lightning_time)
        log.info(self.max_lightning_distance)
        log.info(self.max_lightning_time)

        date_time = event.packet['dateTime']
        lightning_distance = event.packet[self.lightning_distance_field_name]

        log.info("Setting last lightning distance %s and time %s", lightning_distance, date_time)
        self.last_lightning_distance = lightning_distance
        self.last_lightning_time = date_time

        if self.first_lightning_distance is None:
            log.info("Setting first lightning distance %s and time %s", lightning_distance, date_time)
            self.first_lightning_distance = lightning_distance
            self.first_lightning_time = date_time

        if self.min_lightning_distance is None or lightning_distance <= self.min_lightning_distance:
            log.info("Setting min lightning distance %s and time %s", lightning_distance, date_time)
            self.min_lightning_distance = lightning_distance
            self.min_lightning_time = date_time

        if self.max_lightning_distance is None or lightning_distance >= self.max_lightning_distance:
            log.info("Setting max lightning distance %s and time %s", lightning_distance, date_time)
            self.max_lightning_distance = lightning_distance
            self.max_lightning_time = date_time

        event.packet[self.last_distance_field_name] = self.last_lightning_distance
        event.packet[self.last_det_time_field_name] = self.last_lightning_time
        event.packet[self.first_distance_field_name] = self.first_lightning_distance
        event.packet[self.first_det_time_field_name] = self.first_lightning_time
        event.packet[self.min_distance_field_name] = self.min_lightning_distance
        event.packet[self.min_det_time_field_name] = self.min_lightning_time
        event.packet[self.max_distance_field_name] = self.max_lightning_distance
        event.packet[self.max_det_time_field_name] = self.max_lightning_time

        log.info(event.packet)
