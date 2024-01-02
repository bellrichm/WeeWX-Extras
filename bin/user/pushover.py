#
#    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
'''
[Pushover]
    server = api.pushover.net:443
    api = /1/messages.json
    app_token = REPLACE_ME
    user_key = REPLACE_ME
    #title = 


    [[conditions]]
        [[[refrigerator]]]
            # The time in seconds to wait before sending a notification
            wait_time = 3600

            # The number of times the minimum needs to be reached before sending a notification
            min_count = 10
            min = 30

            max_count = 10
            max = 42
            name = Kitchen refigerator
        #[[[refigerator_freezer]]]
'''

import argparse
import http.client
import logging
import os
import time
import urllib
from concurrent.futures import ThreadPoolExecutor

import configobj

import weewx
from weewx.engine import StdService

log = logging.getLogger(__name__)

class Pushover(StdService):
    """ Manage sending Pushover notifications."""
    def __init__(self, engine, config_dict):
        """Initialize an instance of Pushover"""
        super().__init__(engine, config_dict)
        
        skin_dict = config_dict.get('Pushover', {})

        self.user_key = skin_dict.get('user_key', None)
        self.app_token = skin_dict.get('app_token', None)
        self.server = skin_dict.get('server', 'api.pushover.net:443')
        self.api = skin_dict.get('api', '/1/messages.json')

        self.executor = ThreadPoolExecutor(max_workers=5)

    def _process_data(self, data):
        print("start")
        connection = http.client.HTTPSConnection(f"{self.server}")
        connection.request("POST",
                           f"{self.api}",
                           urllib.parse.urlencode({
                               "token": self.app_token,
                               "user": self.user_key,
                               "message": data,
                               }),
                            { "Content-type": "application/x-www-form-urlencoded" })
        response = connection.getresponse()
        response_body = response.read().decode()
        print(response_body)
        print("done")

    def new_loop_packet(self, event):
        """ Handle the new loop packet event. """
        print("before")
        #self.executor.submit(self._process_data, event.packet)
        #self._process_data(event.packet)

        print("after1")

    def new_archive_record(self):
        """ Handle the new archive record event. """
        #pass

    def shutDown(self): # need to override parent - pylint: disable=invalid-name
        """Run when an engine shutdown is requested."""
        self.executor.shutdown(wait=False)

def main():
    """ The main routine. """
    min_config_dict = {
        'Station': {
            'altitude': [0, 'foot'],
            'latitude': 0,
            'station_type': 'Simulator',
            'longitude': 0
        },
        'Simulator': {
            'driver': 'weewx.drivers.simulator',
        },
        'Engine': {
            'Services': {}
        }
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",
                        required=True,
                        help="The WeeWX configuration file. Typically weewx.conf.")
    options = parser.parse_args()


    config_path = os.path.abspath(options.conf)

    config_dict = configobj.ConfigObj(config_path, file_error=True)

    packet = {'dateTime': int(time.time()),
            }

    # Now we can instantiate our slim engine, using the DummyEngine class...
    engine = weewx.engine.DummyEngine(min_config_dict)

    pushover = Pushover(engine, config_dict)

    # Create a NEW_LOOP_PACKET event
    event = weewx.Event(weewx.NEW_LOOP_PACKET, packet=packet)

    pushover.new_loop_packet(event)

    print("time to quit")
    pushover.shutDown()

    print("quitting time")

if __name__ == '__main__':
    main()
