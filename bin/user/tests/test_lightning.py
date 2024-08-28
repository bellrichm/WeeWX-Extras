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

import user.lightning
import weewx

class TestFirstLoopPacket(unittest.TestCase):
    def test_first_lightning_packet(self):
        mock_engine = mock.Mock()
        config_dict = {}
        now = int(time.time())
        strike_distance = random.randint(1, 50)

        SUT = user.lightning.Lightning(mock_engine, config_dict)

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': now,
            'lightning_distance': strike_distance,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(event.packet[SUT.last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.last_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.first_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.first_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.min_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.min_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.max_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.max_det_time_field_name], now)

    def test_new_min_value(self):
        mock_engine = mock.Mock()
        config_dict = {}
        now = int(time.time())
        strike_distance = random.randint(1, 50)

        prior_lightning_distance = strike_distance + random.randint(1, 50)
        prior_lightning_time = now - 60 * 60

        SUT = user.lightning.Lightning(mock_engine, config_dict)

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

        self.assertEqual(event.packet[SUT.last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.last_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.first_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[SUT.first_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[SUT.min_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.min_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.max_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[SUT.max_det_time_field_name], prior_lightning_time)

    def test_new_max_value(self):
        mock_engine = mock.Mock()
        config_dict = {}
        now = int(time.time())
        strike_distance = random.randint(1, 50)

        prior_lightning_distance = strike_distance - random.randint(1, 50)
        prior_lightning_time = now - 60 * 60

        SUT = user.lightning.Lightning(mock_engine, config_dict)

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

        self.assertEqual(event.packet[SUT.last_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.last_det_time_field_name], now)
        self.assertEqual(event.packet[SUT.first_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[SUT.first_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[SUT.min_distance_field_name], prior_lightning_distance)
        self.assertEqual(event.packet[SUT.min_det_time_field_name], prior_lightning_time)
        self.assertEqual(event.packet[SUT.max_distance_field_name], strike_distance)
        self.assertEqual(event.packet[SUT.max_det_time_field_name], now)

if __name__ == '__main__':
    unittest.main(exit=False)
