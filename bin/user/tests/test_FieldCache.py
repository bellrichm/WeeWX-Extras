# pylint: disable=wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import configobj
import random
import string
import mock
import unittest

from user.fieldcache import FieldCache
class NEW_LOOP_PACKET(object):
    """Event issued when a new LOOP packet is available. The event contains
    attribute 'packet', which is the new LOOP packet."""
class NEW_ARCHIVE_RECORD(object):
    """Event issued when a new archive record is available. The event contains
    attribute 'record', which is the new archive record."""

class Event(object):
    """Represents an event."""
    def __init__(self, event_type, **argv):
        self.event_type = event_type

        for key in argv:
            setattr(self, key, argv[key])

class Test_new_archive_record(unittest.TestCase):
    def test_field_missing(self):
        mock_StdEngine = mock.Mock()
        fieldname = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
        config_dict = {
            'FieldCache': {
                'fields': {
                    fieldname: {}
                }
            }
        }

        config = configobj.ConfigObj(config_dict)

        with mock.patch('user.fieldcache.Cache'):
            # pylint: disable=no-member
            SUT = FieldCache(mock_StdEngine, config)

            record = {}
            event = Event(NEW_ARCHIVE_RECORD, record=record)

            SUT.new_archive_record(event)
            SUT.cache.get_value.assert_called_once()

    def test_field_exists(self):
        # pylint: disable=no-member
        mock_StdEngine = mock.Mock()
        fieldname = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
        config_dict = {
            'FieldCache': {
                'fields': {
                    fieldname: {}
                }
            }
        }

        config = configobj.ConfigObj(config_dict)

        with mock.patch('user.fieldcache.Cache'):
            SUT = FieldCache(mock_StdEngine, config)

            record = {
                'usUnits': random.randint(1, 10),
                fieldname: round(random.uniform(1, 100), 2)
            }

            event = Event(NEW_ARCHIVE_RECORD, record=record)

            SUT.new_archive_record(event)
            SUT.cache.update_value.assert_called_once()

if __name__ == '__main__':
    unittest.main(exit=False)
