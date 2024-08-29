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

lightning_distance_name = 'lightning_distance'
last_distance_field_name = 'lightning_last_distance'
last_det_time_field_name = 'lightning_last_det_time'
first_distance_field_name = 'lightning_first_distance'
first_det_time_field_name = 'lightning_first_det_time'
min_distance_field_name = 'lightning_min_distance'
min_det_time_field_name = 'lightning_min_det_time'
max_distance_field_name = 'lightning_max_distance'
max_det_time_field_name = 'lightning_max_det_time'

observations = {}
observations[lightning_distance_name] = {}

observations[lightning_distance_name]['last'] = {}
observations[lightning_distance_name]['last']['observation_name'] = last_distance_field_name
observations[lightning_distance_name]['last']['observation_time_name'] = last_det_time_field_name
observations[lightning_distance_name]['last']['observation'] = None
observations[lightning_distance_name]['last']['observation_time'] = None

observations[lightning_distance_name]['first'] = {}
observations[lightning_distance_name]['first']['observation_name'] = first_distance_field_name
observations[lightning_distance_name]['first']['observation_time_name'] = first_det_time_field_name
observations[lightning_distance_name]['first']['observation'] = None
observations[lightning_distance_name]['first']['observation_time'] = None

observations[lightning_distance_name]['min'] = {}
observations[lightning_distance_name]['min']['observation_name'] = min_distance_field_name
observations[lightning_distance_name]['min']['observation_time_name'] = min_det_time_field_name
observations[lightning_distance_name]['min']['observation'] = None
observations[lightning_distance_name]['min']['observation_time'] = None

observations[lightning_distance_name]['max'] = {}
observations[lightning_distance_name]['max']['observation_name'] = max_distance_field_name
observations[lightning_distance_name]['max']['observation_time_name'] = max_det_time_field_name
observations[lightning_distance_name]['max']['observation'] = None
observations[lightning_distance_name]['max']['observation_time'] = None

class TestFirstLoopPacket(unittest.TestCase):
    def test_first_lightning_packet(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        now = int(time.time())
        strike_distance = random.randint(1, 50)

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': now,
            'lightning_distance': strike_distance,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[last_det_time_field_name], now)
        self.assertEqual(event.packet[first_distance_field_name], strike_distance)
        self.assertEqual(event.packet[first_det_time_field_name], now)
        self.assertEqual(event.packet[min_distance_field_name], strike_distance)
        self.assertEqual(event.packet[min_det_time_field_name], now)
        self.assertEqual(event.packet[max_distance_field_name], strike_distance)
        self.assertEqual(event.packet[max_det_time_field_name], now)

    def test_new_min_value(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        now = int(time.time())
        strike_distance = random.randint(1, 50)

        prior_lightning_distance = strike_distance + random.randint(1, 50)
        prior_lightning_time = now - 60 * 60

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)
        SUT.observations[lightning_distance_name]['last']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['last']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['first']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['first']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['min']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['min']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['max']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['max']['observation_time'] = prior_lightning_time

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': now,
            'lightning_distance': strike_distance,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[last_det_time_field_name], now)
        self.assertEqual(event.packet[first_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[first_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[min_distance_field_name], strike_distance)
        self.assertEqual(event.packet[min_det_time_field_name], now)
        self.assertEqual(event.packet[max_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[max_det_time_field_name], prior_lightning_time)

    def test_new_max_value(self):
        mock_engine = mock.Mock()
        config_dict = {
            'ObservationTime': {
                'observations': observations
            }
        }

        now = int(time.time())
        strike_distance = random.randint(1, 50)

        prior_lightning_distance = strike_distance - random.randint(1, 50)
        prior_lightning_time = now - 60 * 60

        SUT = user.observationtime.ObservationTime(mock_engine, config_dict)
        SUT.observations[lightning_distance_name]['last']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['last']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['first']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['first']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['min']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['min']['observation_time'] = prior_lightning_time

        SUT.observations[lightning_distance_name]['max']['observation'] = prior_lightning_distance
        SUT.observations[lightning_distance_name]['max']['observation_time'] = prior_lightning_time

        SUT.last_lightning_distance = prior_lightning_distance
        SUT.last_lightning_time = prior_lightning_time
        SUT.first_lightning_distance = prior_lightning_distance
        SUT.first_lightning_time = prior_lightning_time
        SUT.min_lightning_distance = prior_lightning_distance
        SUT.min_lightning_time = prior_lightning_time
        SUT.max_lightning_distance = prior_lightning_distance
        SUT.max_lightning_time = prior_lightning_time

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': now,
            'lightning_distance': strike_distance,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[last_det_time_field_name], now)
        self.assertEqual(event.packet[first_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[first_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[min_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[min_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[max_distance_field_name], strike_distance)
        self.assertEqual(event.packet[max_det_time_field_name], now)

if __name__ == '__main__':
    unittest.main(exit=False)
