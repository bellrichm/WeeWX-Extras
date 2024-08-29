#
#    Copyright (c) 2024 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import random
import time

import unittest
import mock

import user.observationtime
import weewx

observation_name = 'observation'
last_value_field_name = 'observation_last_value'
last_time_field_name = 'observation_last_time'
first_time_field_name = 'observation_first_value'
first_det_time_field_name = 'observation_first_time'
min_value_field_name = 'observation_min_value'
min_time_field_name = 'observation_min_time'
max_value_field_name = 'observation_max_value'
max_time_field_name = 'observation_max_time'

observations = {}
observations[observation_name] = {}

observations[observation_name]['last'] = {}
observations[observation_name]['last']['observation_name'] = last_value_field_name
observations[observation_name]['last']['observation_time_name'] = last_time_field_name

observations[observation_name]['first'] = {}
observations[observation_name]['first']['observation_name'] = first_time_field_name
observations[observation_name]['first']['observation_time_name'] = first_det_time_field_name

observations[observation_name]['min'] = {}
observations[observation_name]['min']['observation_name'] = min_value_field_name
observations[observation_name]['min']['observation_time_name'] = min_time_field_name

observations[observation_name]['max'] = {}
observations[observation_name]['max']['observation_name'] = max_value_field_name
observations[observation_name]['max']['observation_time_name'] = max_time_field_name

class TestFirstLoopPacket(unittest.TestCase):
    def test_first_packet(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        current_time = int(time.time())
        current_value = random.randint(1, 50)

        prior_value = None
        prior_time = None

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)

        SUT.observations[observation_name]['last']['observation'] = prior_value
        SUT.observations[observation_name]['last']['observation_time'] = prior_time
        SUT.observations[observation_name]['first']['observation'] = prior_value
        SUT.observations[observation_name]['first']['observation_time'] = prior_time
        SUT.observations[observation_name]['min']['observation'] = prior_value
        SUT.observations[observation_name]['min']['observation_time'] = prior_time
        SUT.observations[observation_name]['max']['observation'] = prior_value
        SUT.observations[observation_name]['max']['observation_time'] = prior_time

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': current_time,
            observation_name: current_value,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_value_field_name], current_value)
        self.assertEqual(event.packet[last_time_field_name], current_time)
        self.assertEqual(event.packet[first_time_field_name], current_value)
        self.assertEqual(event.packet[first_det_time_field_name], current_time)
        self.assertEqual(event.packet[min_value_field_name], current_value)
        self.assertEqual(event.packet[min_time_field_name], current_time)
        self.assertEqual(event.packet[max_value_field_name], current_value)
        self.assertEqual(event.packet[max_time_field_name], current_time)

    def test_new_min_value(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        current_time = int(time.time())
        current_value = random.randint(1, 50)

        prior_value = current_value + random.randint(1, 50)
        prior_time = current_time - 60 * 60

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)

        SUT.observations[observation_name]['last']['observation'] = prior_value
        SUT.observations[observation_name]['last']['observation_time'] = prior_time
        SUT.observations[observation_name]['first']['observation'] = prior_value
        SUT.observations[observation_name]['first']['observation_time'] = prior_time
        SUT.observations[observation_name]['min']['observation'] = prior_value
        SUT.observations[observation_name]['min']['observation_time'] = prior_time
        SUT.observations[observation_name]['max']['observation'] = prior_value
        SUT.observations[observation_name]['max']['observation_time'] = prior_time

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': current_time,
            observation_name: current_value,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_value_field_name], current_value)
        self.assertEqual(event.packet[last_time_field_name], current_time)
        self.assertEqual(event.packet[first_time_field_name], prior_value)
        self.assertEqual(event.packet[first_det_time_field_name], prior_time)
        self.assertEqual(event.packet[min_value_field_name], current_value)
        self.assertEqual(event.packet[min_time_field_name], current_time)
        self.assertEqual(event.packet[max_value_field_name], prior_value)
        self.assertEqual(event.packet[max_time_field_name], prior_time)

    def test_new_max_value(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        current_time = int(time.time())
        current_value = random.randint(1, 50)

        prior_value = current_value - random.randint(1, 50)
        prior_time = current_time - 60 * 60

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)

        SUT.observations[observation_name]['last']['observation'] = prior_value
        SUT.observations[observation_name]['last']['observation_time'] = prior_time
        SUT.observations[observation_name]['first']['observation'] = prior_value
        SUT.observations[observation_name]['first']['observation_time'] = prior_time
        SUT.observations[observation_name]['min']['observation'] = prior_value
        SUT.observations[observation_name]['min']['observation_time'] = prior_time
        SUT.observations[observation_name]['max']['observation'] = prior_value
        SUT.observations[observation_name]['max']['observation_time'] = prior_time

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': current_time,
            observation_name: current_value,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_value_field_name], current_value)
        self.assertEqual(event.packet[last_time_field_name], current_time)
        self.assertEqual(event.packet[first_time_field_name], prior_value)
        self.assertEqual(event.packet[first_det_time_field_name], prior_time)
        self.assertEqual(event.packet[min_value_field_name], prior_value)
        self.assertEqual(event.packet[min_time_field_name], prior_time)
        self.assertEqual(event.packet[max_value_field_name], current_value)
        self.assertEqual(event.packet[max_time_field_name], current_time)

if __name__ == '__main__':
    unittest.main(exit=False)
