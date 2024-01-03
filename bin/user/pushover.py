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


    [[observations]]
        [[[extraTemp6]]]
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
import json
import logging
import os
import time
import urllib
from concurrent.futures import ThreadPoolExecutor

import configobj

import weewx
from weewx.engine import StdService
from weeutil.weeutil import to_int

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

        self.fatal_error_log_frequency = skin_dict.get('fatal_error_log_frequency', 3600)
        wait_time = skin_dict.get('wait_time', 3600)
        count = skin_dict.get('count', 10)

        self.observations = {}
        for observation in skin_dict['observations']:
            self.observations[observation] = {}
            self.observations[observation]['name'] = skin_dict['observations'][observation].get('name', observation)

            min_value = skin_dict['observations'][observation].get('min', None)
            if min_value:
                self.observations[observation]['min'] = {}
                self.observations[observation]['min']['value'] = to_int(min_value)
                self.observations[observation]['min']['count'] = to_int(skin_dict['observations'][observation].get('min_count', count))
                self.observations[observation]['min']['wait_time'] = \
                    to_int(skin_dict['observations'][observation].get('min_wait_time', wait_time))
                self.observations[observation]['min']['last_sent_timestamp'] = 0
                self.observations[observation]['min']['counter'] = 0

            max_value = skin_dict['observations'][observation].get('max', None)
            if max_value:
                self.observations[observation]['max'] = {}
                self.observations[observation]['max']['value'] = to_int(max_value)
                self.observations[observation]['max']['count'] = to_int(skin_dict['observations'][observation].get('max_count', count))
                self.observations[observation]['max']['wait_time'] = \
                    to_int(skin_dict['observations'][observation].get('max_wait_time', wait_time))
                self.observations[observation]['max']['last_sent_timestamp'] = 0
                self.observations[observation]['max']['counter'] = 0

            equal_value = skin_dict['observations'][observation].get('equal', None)
            if equal_value:
                self.observations[observation]['equal'] = {}
                self.observations[observation]['equal']['value'] = to_int(equal_value)
                self.observations[observation]['equal']['count'] = to_int(skin_dict['observations'][observation].get('equal_count', count))
                self.observations[observation]['equal']['wait_time'] = \
                    to_int(skin_dict['observations'][observation].get('equal_wait_time', wait_time))
                self.observations[observation]['equal']['last_sent_timestamp'] = 0
                self.observations[observation]['equal']['counter'] = 0

        self.fatal_error_timestamp = 0
        self.fatal_error_last_logged = 0

        self.executor = ThreadPoolExecutor(max_workers=5)

    def _process_data(self, observation_detail, title, msgs):
        print("start")
        msg = ''
        for _, value in msgs.items():
            if value:
                msg += value
        connection = http.client.HTTPSConnection(f"{self.server}")
        connection.request("POST",
                           f"{self.api}",
                           urllib.parse.urlencode({
                               "token": self.app_token,
                               "user": self.user_key,
                               "message": msg,
                               "title": title,                               
                               }),
                            { "Content-type": "application/x-www-form-urlencoded" })
        response = connection.getresponse()
        print(response.code)
        now = time.time()

        if response.code == 200:
            if msgs['min']:
                observation_detail['min']['last_sent_timestamp'] = now
            if msgs['max']:
                observation_detail['max']['last_sent_timestamp'] = now
            if msgs['equal']:
                observation_detail['equal']['last_sent_timestamp'] = now
        else:
            log.error("Received code %s", response.code)
            if response.code >= 400 and response.code < 500:
                self.fatal_error_timestamp = now
                self.fatal_error_last_logged = now
            response_body = response.read().decode()
            print(response_body)
            try:
                response_dict = json.loads(response_body)
                print(response_dict)
                log.error('\n'.join(response_dict['errors']))
            except json.JSONDecodeError as exception:
                log.error("Unable to parse %s.", exception.doc)
                log.error("Error at %s, line: %s column: %s",
                          exception.pos, exception.lineno, exception.colno)

        print("done")

    def _check_min_value(self, name, observation_detail, value):
        msg = ''
        if value < observation_detail['value']:
            observation_detail['counter'] += 1
            if observation_detail['counter'] >= observation_detail['count']:
                if abs(time.time() - observation_detail['last_sent_timestamp']) >= observation_detail['wait_time']:
                    msg = f"{name} value {value} is less than {observation_detail['value']}.\n"

        return msg

    def _check_max_value(self, name, observation_detail, value):
        msg = ''
        if value > observation_detail['value']:
            observation_detail['counter'] += 1
            if observation_detail['counter'] >= observation_detail['count']:
                if abs(time.time() - observation_detail['last_sent_timestamp']) >= observation_detail['wait_time']:
                    msg = f"{name} value {value} is greater than {observation_detail['value']}.\n"

        return msg

    def _check_equal_value(self, name, observation_detail, value):
        msg = ''
        if value != observation_detail['value']:
            observation_detail['counter'] += 1
            if observation_detail['counter'] >= observation_detail['count']:
                if abs(time.time() - observation_detail['last_sent_timestamp']) >= observation_detail['wait_time']:
                    msg += f"{name} value {value} is not equal {observation_detail['value']}.\n"

        return msg

    def new_loop_packet(self, event):
        """ Handle the new loop packet event. """
        if self.fatal_error_timestamp:
            if abs(time.time() - self.fatal_error_last_logged) >= self.fatal_error_log_frequency:
                log.error("Fatal error occurred at %s, Pushover skipped.", self.fatal_error_timestamp)
                self.fatal_error_last_logged = time.time()
                return

        msgs = {}
        for observation, observation_detail in self.observations.items():
            title = None
            if observation in event.packet:
                if observation_detail['min']:
                    msgs['min'] = self._check_min_value(observation_detail['name'], observation_detail['min'], event.packet[observation])
                    title = f"Unexpected value for {observation}."
                if observation_detail['max']:
                    msgs['max'] = self._check_max_value(observation_detail['name'], observation_detail['max'], event.packet[observation])
                    title = f"Unexpected value for {observation}."
                if observation_detail['equal']:
                    msgs['equal'] = self._check_equal_value(observation_detail['name'], observation_detail['equal'], event.packet[observation])
                    title = f"Unexpected value for {observation}."
            print("before")
            print(msgs)
            #self.executor.submit(self._process_data, event.packet)
            self._process_data(observation_detail, title, msgs)

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
              'extraTemp6': 6,
            }

    # Now we can instantiate our slim engine, using the DummyEngine class...
    engine = weewx.engine.DummyEngine(min_config_dict)

    pushover = Pushover(engine, config_dict)

    # Create a NEW_LOOP_PACKET event
    event = weewx.Event(weewx.NEW_LOOP_PACKET, packet=packet)

    pushover.new_loop_packet(event)

    #pushover.new_loop_packet(event)

    print("time to quit")
    pushover.shutDown()

    print("quitting time")

if __name__ == '__main__':
    main()
