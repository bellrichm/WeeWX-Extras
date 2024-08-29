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

class ObservationTime(weewx.engine.StdService):
    ''' Save additional lightning event data to the WeeWX packet.'''
    def __init__(self, engine, config_dict):
        super(ObservationTime, self).__init__(engine, config_dict)

        # service_dict = config_dict.get('Lightning', {})
        self.observations = {}
        self.observations['lightning_distance'] = {}

        self.observations['lightning_distance']['last'] = {}
        self.observations['lightning_distance']['last']['observation_name'] = 'lightning_last_distance'
        self.observations['lightning_distance']['last']['observation_time_name'] = 'lightning_last_det_time'
        self.observations['lightning_distance']['last']['observation'] = None
        self.observations['lightning_distance']['last']['observation_time'] = None

        self.observations['lightning_distance']['first'] = {}
        self.observations['lightning_distance']['first']['observation_name'] = 'lightning_first_distance'
        self.observations['lightning_distance']['first']['observation_time_name'] = 'lightning_first_det_time'
        self.observations['lightning_distance']['first']['observation'] = None
        self.observations['lightning_distance']['first']['observation_time'] = None

        self.observations['lightning_distance']['min'] = {}
        self.observations['lightning_distance']['min']['observation_name'] = 'lightning_min_distance'
        self.observations['lightning_distance']['min']['observation_time_name'] = 'lightning_min_det_time'
        self.observations['lightning_distance']['min']['observation'] = None
        self.observations['lightning_distance']['min']['observation_time'] = None

        self.observations['lightning_distance']['max'] = {}
        self.observations['lightning_distance']['max']['observation_name'] = 'lightning_max_distance'
        self.observations['lightning_distance']['max']['observation_time_name'] = 'lightning_max_det_time'
        self.observations['lightning_distance']['max']['observation'] = None
        self.observations['lightning_distance']['max']['observation_time'] = None

        self.bind(weewx.PRE_LOOP, self.pre_loop)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def pre_loop(self, _event):
        ''' Handle the WeeWX PRE_LOOP event. '''
        for _observation, observation_data in self.observations.items():
            for observation_type in observation_data:
                observation_data[observation_type]['observation'] = None
                observation_data[observation_type]['observation_time'] = None

    def new_loop_packet(self, event):
        ''' Handle the WeeWX POST_LOOP event.'''
        date_time = event.packet['dateTime']
        for observation, observation_data in self.observations.items():
            if observation not in event.packet:
                continue

            log.info(event.packet)
            for observation_type in observation_data:
                observation_value = event.packet[observation]
                log.info(observation_type)
                log.info(observation_data[observation_type]['observation'])
                log.info(observation_data[observation_type]['observation_time'])

                if observation_type == 'last':
                    self._set_values(observation_data, observation_type, observation_value, date_time)

                if observation_type == 'first' and observation_data[observation_type]['observation'] is None:
                    self._set_values(observation_data, observation_type, observation_value, date_time)

                if observation_type == 'min' and \
                    (observation_data[observation_type]['observation'] is None or \
                     observation_value <= observation_data[observation_type]['observation']):
                    self._set_values(observation_data, observation_type, observation_value, date_time)

                if observation_type == 'max' and \
                    (observation_data[observation_type]['observation'] is None or \
                     observation_value >= observation_data[observation_type]['observation']):
                    self._set_values(observation_data, observation_type, observation_value, date_time)

                event.packet[observation_data[observation_type]['observation_name']] = observation_data[observation_type]['observation']
                event.packet[observation_data[observation_type]['observation_time_name']] =\
                      observation_data[observation_type]['observation_time']

    def _set_values(self, observation_data, observation_type, observation_value, date_time):
        log.info(observation_data[observation_type]['observation'])
        log.info(observation_data[observation_type]['observation_time'])
        log.info("Setting %s observation %s and time %s", observation_type, observation_value, date_time)

        observation_data[observation_type]['observation'] = observation_value
        observation_data[observation_type]['observation_time'] = date_time
    