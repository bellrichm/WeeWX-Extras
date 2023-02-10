#!/usr/bin/python

from __future__ import unicode_literals
import configobj
import io
import json
import sys
import syslog
import time

from future.moves.urllib.request import Request
from queue import Queue  # after pip install future

import weewx.manager
import weewx.restx

from weeutil.weeutil import timestamp_to_string, to_bool

VERSION = "0.0.1"
REQUIRED_WEEWX_VERSION = "3.8"

defaults = """
[WeeWxHistory]

    protocol = http
    host = localhost
    port = 5000
    login_api = api/user/login
    conditions_api = api/conditions

    [[history_fields]]
        # These items will be included in the post to the database.
        dateTime = DateTime
        usUnits = USUnits
        interval = Interval
        barometer = Barometer
        pressure = Pressure
        altimeter = Altimeter
        outTemp = OutsideTemperature
        outHumidity = OutsideHumidity
        windSpeed = WindSpeed
        windDir = WindDirection
        windGust = WindGust
        windGustDir = WindGustDirection
        rainRate = RainRate
        rain = Rain
        dewpoint = DewPoint
        windchill = Windchill
        heatindex = HeatIndex
        ET = Evapotranspiration
        radiation = Radiation
        UV = Ultraviolet
        extraTemp1 = ExtraTemperature1
        extraTemp2 = ExtraTemperature2
        extraTemp3 = ExtraTemperature3
        soilTemp1 = SoilTemperature1
        soilTemp2 = SoilTemperature2
        soilTemp3 = SoilTemperature3
        soilTemp4 = SoilTemperature4
        leafTemp1 = LeafTemperature1
        leafTemp2 = LeafTemperature2
        extraHumid1 = ExtraHumidity1
        extraHumid2 = ExtraHumidity2
        soilMoist1 = SoilMoisture1
        soilMoist2 = SoilMoisture2
        soilMoist3 = SoilMoisture3
        soilMoist4 = SoilMoisture4
        leafWet1 = LeafWetness1
        leafWet2 = LeafWetness2
"""
weewxhistory_defaults = configobj.ConfigObj(
    io.StringIO(defaults), encoding='utf8')

if weewx.__version__ < REQUIRED_WEEWX_VERSION:
    raise weewx.UnsupportedFeature(
        "weewx %s is required, found %s" %
        (REQUIRED_WEEWX_VERSION, weewx.__version__))


def log_msg(level, msg):
    syslog.syslog(level, 'restx: WeeWxHistory: %s' % msg)


def log_debug(msg):
    log_msg(syslog.LOG_DEBUG, msg)


def log_info(msg):
    log_msg(syslog.LOG_INFO, msg)


def log_error(msg):
    log_msg(syslog.LOG_ERR, msg)


def get_config(config_dict):
    site_dict = weewx.restx.check_enable(
        config_dict, 'WeeWxHistory', 'username', 'password')

    if site_dict is None:
        return None

    site_dict['manager_dict'] = weewx.manager.get_manager_dict(
        config_dict['DataBindings'], config_dict['Databases'],
        'wx_binding')

    config = configobj.ConfigObj(
        weewxhistory_defaults)['WeeWxHistory']

    config.merge(site_dict)
    return config


def get_dateTimes(dbm, start_date, end_date):
    start_dateTime = time.mktime(start_date.timetuple())
    end_dateTime = time.mktime(end_date.timetuple())

    records = dbm.genSql(
        """SELECT dateTime FROM archive WHERE dateTime>=? AND dateTime<?""",
        (start_dateTime, end_dateTime))

    dateTimes = []
    for record in records:
        dateTimes.append(record[0])

    return dateTimes


class WeeWxHistory(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):

        super(WeeWxHistory, self).__init__(engine, config_dict)
        log_info("service version is %s" % VERSION)

        weewxhistory_config = get_config(config_dict)
        if weewxhistory_config is None:
            return

        self.archive_queue = Queue()
        self.archive_thread = WeeWxHistoryThread(
            self.archive_queue, **weewxhistory_config)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        log_debug("Adding record %s to queue" % event.record["dateTime"])
        self.archive_queue.put(event.record)


class WeeWxHistoryThread(weewx.restx.RESTThread):

    def __init__(
            self, queue, manager_dict,
            protocol, host, port, conditions_api, login_api,
            username, password, history_fields,
            protocol_name="WeeWxHistory",
            skip_upload=False,
            post_interval=300, max_backlog=sys.maxsize, stale=None,
            log_success=True, log_failure=True,
            timeout=60, max_tries=3, retry_wait=5):

        log_info("thread initializing")

        super(WeeWxHistoryThread, self).__init__(
            queue, protocol_name=protocol_name,
            manager_dict=manager_dict,
            post_interval=post_interval, max_backlog=max_backlog, stale=stale,
            log_success=log_success, log_failure=log_failure,
            timeout=timeout, max_tries=max_tries, retry_wait=retry_wait)

        self.protocol = protocol
        self.host = host
        self.port = port
        self.conditions_api = conditions_api
        self.login_api = login_api
        self.username = username
        self.password = password
        self.history_fields = history_fields
        self.skip_upload = to_bool(skip_upload)

    def get_request(self, url):
        request = Request(url)
        if not self.skip_upload:
            jwt = self.login()
            request.add_header("authorization", "bearer " + jwt)

        return request

    def format_url(self, _):
        url = "%s://%s:%s/%s" % (
            self.protocol, self.host, self.port, self.conditions_api)
        log_debug("url %s" % url)

        return url

    def login(self):
        # Post to get the token/login
        url = "%s://%s:%s/%s" % (
            self.protocol, self.host, self.port, self.login_api)
        log_debug("login url %s" % url)

        request = Request(url)
        request.add_header("Content-Type", "application/json")
        body = {}
        body['userName'] = self.username
        body['password'] = self.password
        self.post_with_retries(request, json.dumps(body))

        # Get the token
        json_response = json.loads(self.response)
        jwt = json_response['jsonWebToken']
        log_debug("jwt %s" % jwt)

        return jwt

    def check_response(self, response):
        self.response = response.read()
        log_debug("response %s" % self.response)

    def get_post_body(self, record):
        data = {}
        for k, v in list(self.history_fields.items()):
            try:
                data[v] = record[k]
            except KeyError:
                pass

        log_debug("post data is %s" % data)

        return tuple((json.dumps(data), 'application/json'))


usagestr = """%prog CONFIG_FILE|--config=CONFIG_FILE
                  [--binding=BINDING]
                  [--sdate=YYYY-mm-dd]
                  [--edate=YYYY-mm-dd]
                  [--verbose]
                  [--help]

"""
if __name__ == '__main__':
    import configobj
    import datetime
    import optparse
    from optparse import OptionParser

    import weecfg

    parser = optparse.OptionParser(usage=usagestr)  # todo usage help string

    parser.add_option(
        "-c", "--config", type="string", dest="config", metavar="CONFIG_PATH",
        help="Use configuration file CONFIG_PATH. "
        "Default is /etc/weewx/weewx.conf or /home/weewx/weewx.conf.")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Print useful extra output.")

    parser.add_option(
        "-s", "--sdate", type="string", dest="sdate", metavar="YYYY-mm-dd",
        help="Start date to upload, in form o YYYY-mm-dd. Default is today.")

    parser.add_option(
        "-e", "--edate", type="string", dest="edate", metavar="YYYY-mm-dd",
        help="End date to upload, in form of YYYY-mm-dd. Default is today.")

    parser.add_option(
        "-b", "--binding", type="string", dest="binding",
        metavar="BINDING", default='wx_binding',
        help="The database binding to be used. Default is 'wx_binding'.")

    (options, args) = parser.parse_args()

    syslog.openlog("weewx", syslog.LOG_PID | syslog.LOG_CONS)
    if options.verbose:
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
    else:
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))

    config_fn, config_dict = weecfg.read_config(options.config, args)
    print(("Using configuration file %s." % config_fn))
    log_info("Using configuration file %s." % config_fn)

    weewxhistory_config = get_config(config_dict)
    if weewxhistory_config is None:
        exit

    db_binding = options.binding
    database = config_dict['DataBindings'][db_binding]['database']
    print(("Using database binding '%s', which is bound to database '%s'" % (
        db_binding, database)))
    log_info("Using database binding '%s', which is bound to database '%s'" % (
        db_binding, database))

    dbmanager = weewx.manager.open_manager_with_config(
        config_dict, db_binding)

    if options.sdate:
        date = time.strptime(options.sdate, "%Y-%m-%d")
        start_date = datetime.date(date.tm_year, date.tm_mon, date.tm_mday)
    else:
        start_date = datetime.date.today()

    if options.edate:
        date = time.strptime(options.edate, "%Y-%m-%d")
        end_date = datetime.date(date.tm_year, date.tm_mon, date.tm_mday)
    else:
        end_date = datetime.date.today()

    print(("Processing dates from '%s' to '%s'" % (
        start_date, end_date)))
    log_info("Processing dates from '%s' to '%s'" % (
        start_date, end_date))

    weeWxHistoryThread = WeeWxHistoryThread(queue=None, **weewxhistory_config)

    dateTimes = get_dateTimes(dbmanager, start_date, end_date)

    i = 0
    for dateTime in dateTimes:
        i += 1
        print(("processing %s of %s" % (i, len(dateTimes))))
        record = dbmanager.getRecord(dateTime)

        try:
            weeWxHistoryThread.process_record(record, dbmanager)
        except weewx.restx.AbortedPost:
            log_info("Skipped record %s" % (
                timestamp_to_string(record['dateTime'])))
