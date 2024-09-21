#
#    Copyright (c) 2024 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

'''
WeeWX service to capture times and values for the first, last, min, and max of an observation in an archive period.

Prerequistes:
Python 3.7+
WeeWX 5.x+

Installation:
    1. Put this file in the bin/user directory.
    2. Update weewx.conf [ObservationTime] as needed to configure the service.
    3. Add the service, user.observationtime.ObservationTime to the appropriate 'service group'.
       This would typically be the 'data_services' group.
       But it might be the 'process_services' group if it needs to run after any of the WeeWX services in this group.

Overview:
For a configured WeeWX observation, capture any of the last, first, min, or max values in an archive period. 
In addition to capturing the value, the time that the value was observed is also captured.
These values and times are added to the loop packet.
The WeeWX accumulator function is used to populate the archive record with these values.

Important:
The daily summaries cannot be used to get the time (observation_time_name) of the value.
This is because the daily summary will have the min/max of the time, not the time of the min/max value.

Configuration:
[ObservationTime]
    [[observations]]
        # The first observation whose 'event' value and time will be captured.
        # For example: lightning_distance, windGust, etc.
        [[[REPLACE_ME]]]
            [[[[last]]]]
                # The name of the WeeWX to store the last observation's value.
                # For example: lightning_last_distance, windGust_last, etc.
                observation_name =
                # The name of the WeeWX to store the last observation's time.
                # For example: lightning_last_det_time, windGust_last_time, etc.                
                observation_time_name =
            [[[[first]]]]
            # The name of the WeeWX to store the first observation's value.
                # For example: lightning_first_distance, windGust_first, etc.            
                observation_name =
                # The name of the WeeWX to store the first observation's time.
                # For example: lightning_first_det_time, windGust_first_time, etc.                                
                observation_time_name =
            [[[[min]]]]
                # The name of the WeeWX to store the min observation's value.
                # For example: lightning_min_distance, windGust_min, etc.            
                observation_name
                # The name of the WeeWX to store the min observation's time.
                # For example: lightning_min_det_time, windGust_min_time, etc.                                
                observation_time_name =
            [[[[max]]]]
                # The name of the WeeWX to store the max observation's value.
                # For example: lightning_max_distance, windGust_max, etc.            
                observation_name =
                # The name of the WeeWX to store the max observation's time.
                # For example: lightning_max_det_time, windGust_max_time, etc.                                
                observation_time_name =
        # The next observation whose 'event' value and time will be captured.
        [[[REPLACE_ME_TOO]]]
                
Below is an example of a 'complete' configuration to capture the last, first, and closest lightning strike in an archive period.
This assumes that in the WeeWX loop packet, the 'lightning_distance' field captures the distance to the strike.
[Engine]
    [[Services]]
        data_services = user.observationtime.ObservationTime

[Accumulator]
    [[lightning_last_distance]]
        extractor = last
    [[lightning_last_det_time]]
        extractor = last
    # Note, extractor = last would work because the first detection is added to every loop by the ObservationTime service.
    [[lightning_first_distance]]
        extractor = first
    [[lightning_first_det_time]]
        extractor = first
    [[lightning_min_distance]]
        extractor = last
    [[lightning_min_det_time]]
        extractor = last

[ObservationTime]
    [[observations]]
        [[[lightning_distance]]]
            [[[[last]]]]
                observation_name = lightning_last_distance
                observation_time = lightning_last_det_time
            [[[[first]]]]
                observation_name = lightning_first_distance
                observation_time = lightning_first_det_time
            [[[[min]]]]
                observation_name = lightning_min_distance
                observation_time = lightning_min_det_time

Add the additional fields to the database.
weectl database add-column lightning_last_distance --type=REAL
weectl database add-column lightning_last_det_time --type=INTEGER

weectl database add-column lightning_first_distance --type=REAL
weectl database add-column lightning_first_det_time --type=INTEGER

weectl database add-column lightning_min_distance --type=REAL
weectl database add-column lightning_min_det_time --type=INTEGER

Update bin/user/extensions.py with the units for the new fields.
import weewx.units
weewx.units.obs_group_dict['lightning_last_distance'] = 'group_distance'
weewx.units.obs_group_dict['lightning_last_det_time'] = 'group_time'
weewx.units.obs_group_dict['lightning_first_distance'] = 'group_distance'
weewx.units.obs_group_dict['lightning_first_det_time'] = 'group_time'
weewx.units.obs_group_dict['lightning_min_distance'] = 'group_distance'
weewx.units.obs_group_dict['lightning_min_det_time'] = 'group_time'

'''

# ToDo: Decide if the aggregate types should be new/unique, or to continue to override WeeWX's existing types.

import logging

import weewx
import weewx.engine
import weedb

from weeutil.weeutil import to_bool

VERSION = '0.1.0'

log = logging.getLogger(__name__)

class ObservationTime(weewx.engine.StdService):
    ''' Save the times and values of the first, last, min, and max of an observation.'''
    def __init__(self, engine, config_dict):
        log.info("Version is: %s", VERSION)
        super(ObservationTime, self).__init__(engine, config_dict)

        # ToDo: perform a deep copy
        service_dict = config_dict.get('ObservationTime', {})
        self.observations = service_dict.get('observations', {})
        log.debug("The configuration is: %s", self.observations)

        if to_bool(service_dict.get('augment_loop', True)):
            self.bind(weewx.PRE_LOOP, self.pre_loop)
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

        self.observation_time_xtype = ObservationTimeXtype(self.observations)
        weewx.xtypes.xtypes.insert(0, self.observation_time_xtype)

    def shutDown(self):
        """Run when an engine shutdown is requested."""
        weewx.xtypes.xtypes.remove(self.observation_time_xtype)

    def pre_loop(self, _event):
        ''' Handle the WeeWX PRE_LOOP event. '''
        for _observation, observation_data in self.observations.items():
            for observation_type in observation_data:
                observation_data[observation_type]['observation'] = None
                observation_data[observation_type]['observation_time'] = None

    def new_loop_packet(self, event):
        ''' Handle the WeeWX POST_LOOP event.'''
        log.debug("Incoming packet is: %s", event.packet)
        for observation, observation_data in self.observations.items():
            if observation not in event.packet:
                continue

            log.debug("Processing observation: %s %s", observation, observation_data)
            observation_value = event.packet[observation]
            observation_time = event.packet['dateTime']
            
            log.debug("Processing current value: %s and current time: %s", observation_value, observation_time)
            if observation_value is None:
                continue
            
            for observation_type in observation_data:
                observation_name = observation_data[observation_type]['observation_name']
                observation_time_name = observation_data[observation_type]['observation_time_name']
                previous_value = observation_data[observation_type]['observation']
                previous_time = observation_data[observation_type]['observation_time']
                observation_data[observation_type]['observation'] = previous_value
                observation_data[observation_type]['observation_time'] = previous_time

                log.debug("Processing type: %s with observation name: %s and observation time name: %s",
                          observation_type,
                          observation_name,
                          observation_time_name)
                log.debug("Processing previous value: %s and previous time: %s", previous_value, previous_time)

                if observation_type == 'last' and observation_value is not None:
                    log.debug("Setting %s of %s value %s and time %s", observation_type, observation, observation_value, observation_time)
                    observation_data[observation_type]['observation'] = observation_value
                    observation_data[observation_type]['observation_time'] = observation_time

                if observation_type == 'first' and observation_value is not None and previous_value is None:
                    log.debug("Setting %s of %s value %s and time %s", observation_type, observation, observation_value, observation_time)
                    observation_data[observation_type]['observation'] = observation_value
                    observation_data[observation_type]['observation_time'] = observation_time

                if observation_type == 'min' and observation_value is not None and \
                    (previous_value is None or observation_value <= previous_value):
                    log.debug("Setting %s of %s value %s and time %s", observation_type, observation, observation_value, observation_time)
                    observation_data[observation_type]['observation'] = observation_value
                    observation_data[observation_type]['observation_time'] = observation_time

                if observation_type == 'max' and observation_value is not None and \
                    (previous_value is None or observation_value >= previous_value):
                    log.debug("Setting %s of %s value %s and time %s", observation_type, observation, observation_value, observation_time)
                    observation_data[observation_type]['observation'] = observation_value
                    observation_data[observation_type]['observation_time'] = observation_time

                event.packet[observation_name] = observation_data[observation_type]['observation']
                event.packet[observation_time_name] = observation_data[observation_type]['observation_time']

        log.debug("Outgoing packet is: %s", event.packet)

class ObservationTimeXtype(weewx.xtypes.XType):
    ''' XType to add the aggregate types to get the dependent time observation's data.'''
    def __init__(self, observations):
        self.observation_time_names = {}
        for _observation, observation_data in observations.items():
            for observation_type, observation_type_data in observation_data.items():
                observation_time_name = observation_type_data['observation_time_name']
                self.observation_time_names[observation_time_name] = {}
                self.observation_time_names[observation_time_name]['observation_name'] = observation_type_data['observation_name']
                self.observation_time_names[observation_time_name]['observation_type'] = observation_type

        self.sql_stmts = {
            'first': "SELECT {input} FROM {table_name} "
                "WHERE dateTime > {start} AND dateTime <= {stop} AND {primary_observation} IS NOT NULL "
                "ORDER BY dateTime ASC LIMIT 1;",
            'last': "SELECT {input} FROM {table_name} "
                "WHERE dateTime > {start} AND dateTime <= {stop} AND {primary_observation} IS NOT NULL "
                "ORDER BY dateTime DESC LIMIT 1;",
            'min': "SELECT {input} FROM {table_name} "
                "WHERE dateTime > {start} AND dateTime <= {stop} AND {primary_observation} IS NOT NULL "
                "ORDER BY {primary_observation} ASC, dateTime DESC LIMIT 1;",
            'max': "SELECT {input} FROM {table_name} "
                "WHERE dateTime > {start} AND dateTime <= {stop} AND {primary_observation} IS NOT NULL "
                "ORDER BY {primary_observation} DESC, dateTime DESC LIMIT 1;",
        }

    def get_aggregate(self, obs_type, timespan, aggregate_type, db_manager, **option_dict):
        if obs_type not in self.observation_time_names:
            raise weewx.UnknownType(obs_type)

        if aggregate_type != self.observation_time_names[obs_type]['observation_type']:
            raise weewx.UnknownAggregation(aggregate_type)

        interpolation_dict = {
            'start': timespan.start,
            'stop': timespan.stop,
            'table_name': db_manager.table_name,
            'input': obs_type,
            'primary_observation': self.observation_time_names[obs_type]['observation_name']
        }

        sql_stmt = self.sql_stmts[aggregate_type].format(**interpolation_dict)

        try:
            row = db_manager.getSql(sql_stmt)
        except weedb.NoColumnError:
            raise weewx.UnknownType(obs_type) from weedb.NoColumnError

        if not row or None in row:
            aggregate_value = None
        else:
            aggregate_value = row[0]

        unit_type, group = weewx.units.getStandardUnitType(db_manager.std_unit_system, obs_type, aggregate_type)
        return weewx.units.ValueTuple(aggregate_value, unit_type, group)
