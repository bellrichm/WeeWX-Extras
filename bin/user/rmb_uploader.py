import copy
#import httplib
import json
import Queue
import re
#import socket
import sys
import syslog
import time
import urllib
import urllib2

import weewx.manager
import weewx.restx
#import weeutil
from weeutil.weeutil import to_bool

VERSION = "1.0.0"

# TODO: Rename to RMBArchiveUpload
# TODO: Investigate why I need a usUnits column and dateTime column
# TODO: Write something to process failed upload records

if weewx.__version__ < "3":
    raise weewx.UnsupportedFeature("weewx 3 is required, found %s" %
                                   weewx.__version__)
def logmsg(level, msg):
    syslog.syslog(level, 'restx: RmbUploader: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

class RmbUploader(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):

        super(RmbUploader, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)

        # TODO: baseurl should also be required
        site_dict = weewx.restx.check_enable(config_dict, 'RmbUpload', 'username', 'password')
        if site_dict is None:
            return

        site_dict['manager_dict'] = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'wx_binding')

        archiveUpload_manager_dict = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'RMBArchiveUpload_binding')
        site_dict['archiveUpload_manager_dict'] = archiveUpload_manager_dict

        self.archiveUploadDBM = weewx.manager.open_manager(archiveUpload_manager_dict)

        self.archive_queue = Queue.Queue()
        self.archive_thread = RmbUploaderThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        loginf("Adding record %s to queue" %event.record["dateTime"])
        # Adding to DB here, incase the queuing fails
        self.archiveUploadDBM.getSql('INSERT INTO %s ("dateTime", "run_dateTime") VALUES (?, ?)' %
                                     self.archiveUploadDBM.table_name, (str(event.record["dateTime"]), str(int(time.time()))))
        self.archive_queue.put(event.record)

class RmbUploaderThread(weewx.restx.RESTThread):

    def __init__(self, queue, username, password, baseurl, archiveUpload_manager_dict, manager_dict,
                 skip_upload=False,
                 post_interval=300, max_backlog=sys.maxint, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5):
        super(RmbUploaderThread, self).__init__(queue,
                                                protocol_name='RmbUploader',
                                                manager_dict=manager_dict,
                                                post_interval=post_interval,
                                                max_backlog=max_backlog,
                                                stale=stale,
                                                log_success=log_success,
                                                log_failure=log_failure,
                                                max_tries=max_tries,
                                                timeout=timeout,
                                                retry_wait=retry_wait)
        self.username = username
        self.password = password
        self.baseurl = baseurl
        self.skip_upload = to_bool(skip_upload)
        self.archiveUpload_manager_dict = archiveUpload_manager_dict

    def process_record(self, record, dbm):
        # TODO: Constructor is a different thread, so have to do this here. Possibly cache this?
        self.archiveUploadDBM = weewx.manager.open_manager(self.archiveUpload_manager_dict)

        jsonarray = json.dumps(record)
        jsonarray = '[' + jsonarray + ']' # hacking to an array works

        url = self.baseurl + "/api/archive"
        req = urllib2.Request(url)
        req.add_header("requestid", record["dateTime"])
        req.add_header("Content-Type", "application/json")

        self.post_with_retries(req, jsonarray)
        currDateTime = int(time.time())
        self.archiveUploadDBM.getSql('UPDATE %s SET upload_dateTime = ? WHERE dateTime= ?' %
                                     self.archiveUploadDBM.table_name, (str(currDateTime), record["dateTime"]))
        return

    def post_request(self, request, payload=None):
        # Post to get the token/login
        userUrl = self.baseurl + "/api/user"
        userReq = urllib2.Request(userUrl)
        userReq.add_header("Content-Type", "application/x-www-form-urlencoded")
        data = {}
        data['name'] = self.username
        data['password'] = self.password
        uData = urllib.urlencode(data)
        userResponse = self.performPost(userReq, uData)

        # Get the token
        jsonData = userResponse.read()
        data = json.loads(jsonData)
        jwt = data['access_token']

        # Post the updated weather archive record
        request.add_header("authorization", "bearer " + jwt)
        _response = self.performPost(request, payload)

        return _response

    def performPost(self, request, payload=None):
        try:
            _response = urllib2.urlopen(request, data=payload, timeout=self.timeout)
            # TODO: check status code and if not 2xx, log and raise exception?
            # self.log_post_error_request(request)
            # self.log_post_error_response(_response)
            # raise weewx.restx.PostFailed

        # log some detail before passing the exception along
        except (urllib2.HTTPError) as e:
            self.log_post_error_request(request)
            self.log_post_error_response(e)
            raise e
        except (Exception) as e:
            self.log_post_error_request(request)
            raise e

        return _response

    def log_post_error_request(self, request):
        for header in request.headers:
            logerr("Post failed: request header is %s: %s" % (header, request.headers[header]))
        logerr("Post failed: request body is %s" % (re.sub(r"password=[^\&]*", "password=XXX", request.get_data())))

    def log_post_error_response(self, response):
        logerr("Post failed: response code is %s" % (response.code))
        for header in response.headers:
            logerr("Post failed: response header is  %s: %s" % (header, response.info().getheader(header)))
        logerr("Post failed: response body is %s" % (re.sub(r"password=[^\&]*", "password=XXX", response.read())))
        logerr("Post failed: response is %s" % (response.read()))

# To test this extension, do the following:
#
# cd /home/weewx
# PYTHONPATH=bin python bin/user/rmb_uploader.py /home/weewx/weewx.conf
#
def run_invalid_url(rec):
    msg = "**** Testing - invalid URL"
    logdbg(msg)
    print(msg)
    dictionary = copy.deepcopy(config_dict)
    dictionary['StdRESTful']['RmbUpload']['baseurl'] = 'http://somehost.com'
    dictionary['StdRESTful']['RmbUpload']['password'] = ''
    runit(dictionary, rec)

def run_invalid_user(rec):
    msg = "**** Testing - invalid user"
    logdbg(msg)
    print(msg)
    dictionary = copy.deepcopy(config_dict)
    dictionary['StdRESTful']['RmbUpload']['password'] = 'INVALID'
    runit(dictionary, rec)

def run_valid_rec(rec):
    msg = "**** Testing - valid record"
    logdbg(msg)
    print(msg)
    dictionary = copy.deepcopy(config_dict)
    runit(dictionary, rec)

def runit(dictionary, rec):
    engine = StdEngine(dictionary)
    restService = RmbUploader(engine, dictionary)

    event = weewx.Event(weewx.NEW_ARCHIVE_RECORD, record=rec)
    restService.new_archive_record(event)
    time.sleep(1) # Need to wait for the queue to be processed in seconds - not sure how short this can be

def catchUp():
    # Unfortunately, this is dependent on the underlying databases being SQLite
    dictionary = copy.deepcopy(config_dict)
    dictionary['StdRESTful']['RmbUpload']['max_tries'] = '3'
    dictionary['StdRESTful']['RmbUpload']['retry_wait'] = '5'

    attachSQL = "ATTACH DATABASE '/home/weewx/archive/weewx.sdb' as weewx;"
    # This where clause gets all archive data that does not have a record stating int was processed
    # whereClause = "WHERE weewx.archive.dateTime IN (SELECT dateTime FROM uploadarchive where uploadarchive.upload_dateTime is NULL) "
    # This where clause gets all archive data that has not been marked as processed
    # whereClause = "WHERE weewx.archive.dateTime NOT IN (SELECT dateTime FROM uploadarchive) "
    selectSQL = "SELECT \
                    `dateTime`, `usUnits`, `interval`, `barometer`, `pressure`, `altimeter`, `inTemp`, `outTemp`, \
                     `inHumidity`, `outHumidity`, `windSpeed`, `windDir`, `windGust`, `windGustDir`, \
                     `rainRate`, `rain`, `dewpoint`, `windchill`, `heatindex`, `ET`, `radiation`, `UV`, \
                     `extraTemp1`, `extraTemp2`, `extraTemp3`, `soilTemp1`, `soilTemp2`, `soilTemp3`, `soilTemp4`, \
                     `leafTemp1`, `leafTemp2`, `extraHumid1`, `extraHumid2`, `soilMoist1`, `soilMoist2`, `soilMoist3`, `soilMoist4`, \
                     `leafWet1`, `leafWet2`, `rxCheckPercent`, `txBatteryStatus`, `consBatteryVoltage`, `hail`, `hailRate`, \
                     `heatingTemp`, `heatingVoltage`, `supplyVoltage`, `referenceVoltage`, \
                     `windBatteryStatus`, `rainBatteryStatus`, `outTempBatteryStatus`, `inTempBatteryStatus` \
        FROM weewx.archive \
            WHERE weewx.archive.dateTime IN (SELECT dateTime FROM uploadarchive where uploadarchive.upload_dateTime is NULL) \
            OR weewx.archive.dateTime IN (SELECT dateTime FROM uploadarchive where uploadarchive.upload_dateTime is NULL) \
            ORDER BY dateTime ASC ;"

    site_dict = weewx.restx.check_enable(dictionary, 'RmbUpload', 'username', 'password')
    if site_dict is None:
        return

    archiveUpload_manager_dict = weewx.manager.get_manager_dict(
        config_dict['DataBindings'], config_dict['Databases'], 'RMBArchiveUpload_binding')
    site_dict['archiveUpload_manager_dict'] = archiveUpload_manager_dict

    archiveUploadDBM = weewx.manager.open_manager(archiveUpload_manager_dict)

    archiveUploadDBM.getSql(attachSQL)

    dataRecords = archiveUploadDBM.genSql(selectSQL)
    i = 0
    archiveRecords = []
    for dataRecord in dataRecords:
        archiveRecords.append({})
        archiveRecords[i]['dateTime'] = dataRecord[0]
        archiveRecords[i]['usUnits'] = dataRecord[1]
        archiveRecords[i]['interval'] = dataRecord[2]
        archiveRecords[i]['barometer'] = dataRecord[3]
        archiveRecords[i]['pressure'] = dataRecord[4]
        archiveRecords[i]['altimeter'] = dataRecord[5]
        archiveRecords[i]['inTemp'] = dataRecord[6]
        archiveRecords[i]['outTemp'] = dataRecord[7]
        archiveRecords[i]['inHumidity'] = dataRecord[8]
        archiveRecords[i]['outHumidity'] = dataRecord[9]
        archiveRecords[i]['windSpeed'] = dataRecord[10]
        archiveRecords[i]['windDir'] = dataRecord[11]
        archiveRecords[i]['windGust'] = dataRecord[12]
        archiveRecords[i]['windGustDir'] = dataRecord[13]
        archiveRecords[i]['rainRate'] = dataRecord[14]
        archiveRecords[i]['rain'] = dataRecord[15]
        archiveRecords[i]['dewpoint'] = dataRecord[16]
        archiveRecords[i]['windchill'] = dataRecord[17]
        archiveRecords[i]['heatindex'] = dataRecord[18]
        archiveRecords[i]['ET'] = dataRecord[19]
        archiveRecords[i]['radiation'] = dataRecord[20]
        archiveRecords[i]['UV'] = dataRecord[21]
        archiveRecords[i]['extraTemp1'] = dataRecord[22]
        archiveRecords[i]['extraTemp2'] = dataRecord[23]
        archiveRecords[i]['extraTemp3'] = dataRecord[24]
        archiveRecords[i]['soilTemp1'] = dataRecord[25]
        archiveRecords[i]['soilTemp2'] = dataRecord[26]
        archiveRecords[i]['soilTemp3'] = dataRecord[27]
        archiveRecords[i]['soilTemp4'] = dataRecord[28]
        archiveRecords[i]['leafTemp1'] = dataRecord[29]
        archiveRecords[i]['leafTemp2'] = dataRecord[30]
        archiveRecords[i]['extraHumid1'] = dataRecord[31]
        archiveRecords[i]['extraHumid2'] = dataRecord[32]
        archiveRecords[i]['soilMoist1'] = dataRecord[33]
        archiveRecords[i]['soilMoist2'] = dataRecord[34]
        archiveRecords[i]['soilMoist3'] = dataRecord[35]
        archiveRecords[i]['soilMoist4'] = dataRecord[36]
        archiveRecords[i]['leafWet1'] = dataRecord[37]
        archiveRecords[i]['leafWet2'] = dataRecord[38]
        archiveRecords[i]['rxCheckPercent'] = dataRecord[39]
        archiveRecords[i]['txBatteryStatus'] = dataRecord[40]
        archiveRecords[i]['consBatteryVoltage'] = dataRecord[41]
        archiveRecords[i]['hail'] = dataRecord[42]
        archiveRecords[i]['hailRate'] = dataRecord[43]
        archiveRecords[i]['heatingTemp'] = dataRecord[44]
        archiveRecords[i]['heatingVoltage'] = dataRecord[45]
        archiveRecords[i]['supplyVoltage'] = dataRecord[46]
        archiveRecords[i]['referenceVoltage'] = dataRecord[47]
        archiveRecords[i]['windBatteryStatus'] = dataRecord[48]
        archiveRecords[i]['rainBatteryStatus'] = dataRecord[49]
        archiveRecords[i]['outTempBatteryStatus'] = dataRecord[50]
        archiveRecords[i]['inTempBatteryStatus'] = dataRecord[51]
        i = i+1

    # upload all at once. This will not add an entry into the rmbuploadarchive DB
    #jsonarray = json.dumps(archiveRecords)
    #print jsonarray
    # Hacky way to post the json array
    #engine = StdEngine(dictionary)
    #restService = RmbUploader(engine, dictionary)
    #url = url = "http://192.168.1.110:8080" + "/api/archive" # TODO: use configuration data
    #request = urllib2.Request(url)
    #request.add_header("Content-Type", "application/json")
    #restService.archive_thread.post_request(request, jsonarray)

    # Upload single record at a time
    j = 0
    engine = StdEngine(dictionary)
    restService = RmbUploader(engine, dictionary)
    for archiveRecord in archiveRecords:
        print("record %i of %i: %i" %(j, i, archiveRecord['dateTime']))
        event = weewx.Event(weewx.NEW_ARCHIVE_RECORD, record=archiveRecord)
        restService.new_archive_record(event)
        j = j+ 1
        time.sleep(1) # Need to wait for the queue to be processed in seconds - not sure how short this can be

    time.sleep(j*10) # Need to wait for the queue to be processed in seconds - not sure how short this can be

if __name__ == '__main__':
    #import sys
    #import time
    import configobj
    from optparse import OptionParser
    from weewx.engine import StdEngine

    parser = OptionParser()
    (options, args) = parser.parse_args()

    if len(args) < 1:
        sys.stderr.write("Missing argument(s).\n")
        exit()

    config_path = args[0]

    weewx.debug = 1

    try:
        config_dict = configobj.ConfigObj(config_path, file_error=True)
    except IOError:
        print("Unable to open configuration file %s" % config_path)
        exit()

    # Override some of the configuration settings
    config_dict['Station']['station_type'] = 'Simulator'
    config_dict['Simulator'] = {}
    config_dict['Simulator']['driver'] = 'weewx.drivers.simulator'
    config_dict['Simulator']['mode'] = 'simulator'
    config_dict['Engine'] = {}
    config_dict['Engine']['Services'] = {}
    config_dict['StdRESTful']['RmbUpload']['post_interval'] = '0'
    config_dict['StdRESTful']['RmbUpload']['max_tries'] = '1'
    config_dict['StdRESTful']['RmbUpload']['retry_wait'] = '0'

    # create a test record
    rec = {'extraTemp1': 1.0,
           'outTemp'   : 38.2,
           'dateTime'  : 1}

    #run_invalid_user(rec)
    #run_valid_rec(rec)
    #run_valid_rec(rec)
    #run_invalid_url(rec)

    # while True:
    catchUp()

    weewx.debug = 0

    print("Don't forget to cleanup the database")
    print("SELECT * FROM testArchive WHERE dateTime = 1;")
    print("DELETE FROM testArchive WHERE dateTime = 1;")
    