#
#    Copyright (c) 2024 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

'''
WeeWX service to capture times and values for the first, last, min, and max of an observation.
'''

import logging

import weewx
import weewx.engine

log = logging.getLogger(__name__)

class ObservationTime(weewx.engine.StdService):
    ''' Save the times and values of the first, last, min, and max of an observation.'''
    def __init__(self, engine, config_dict):
        super(ObservationTime, self).__init__(engine, config_dict)

        # ToDo: perform a deep copy
        self.observations = config_dict.get('ObservationTime', {}).get('observations', {})
        log.info(self.observations)

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
        log.info("checking: %s", event.packet)
        for observation, observation_data in self.observations.items():
            if observation not in event.packet:
                continue

            log.info("processing observation: %s %s", observation, observation_data)
            log.info("processing: %s", event.packet)
            observation_value = event.packet[observation]
            for observation_type in observation_data:
                log.info("processing type: %s", observation_type)
                log.info("processing prev value: %s", observation_data[observation_type]['observation'])
                log.info("processing prev time: %s", observation_data[observation_type]['observation_time'])
                log.info("processing curr value: %s", observation_value)
                log.info("processing curr time: %s", date_time)

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
        log.info("processing Setting %s observation %s and time %s", observation_type, observation_value, date_time)
        observation_data[observation_type]['observation'] = observation_value
        observation_data[observation_type]['observation_time'] = date_time
    