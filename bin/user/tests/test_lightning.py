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
    def test_lightning_count_is_total(self):
        print("start")

        mock_engine = mock.Mock()
        now = int(time.time())
        strike_count = random.randint(1, 255)
        strike_distance = random.randint(1, 50)

        SUT = user.lightning.Lightning(mock_engine, {})

        event = weewx.NEW_LOOP_PACKET()
        event.packet = {
            'dateTime': now,
            SUT.strike_count_field_name: strike_count,
            SUT.strike_distance_field_name: strike_distance,
        }
        SUT.new_loop_packet(event)

        self.assertEqual(SUT.strike_count_total, strike_count)

        print("done")

if __name__ == '__main__':
    unittest.main(exit=False)
