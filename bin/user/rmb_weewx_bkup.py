""" Backup WeeWx."""
# to use add the following to the report services, user.rmb_weewx_bkup.MyBackup

import time
import datetime

import syslog
import subprocess

import weewx
from weewx.wxengine import StdService
#from weeutil.weeutil import timestamp_to_string, option_as_list
from weeutil.weeutil import to_bool

def get_curr_time():
    """" Get the current time. """
    curr_hr = time.strftime("%H")
    curr_min = time.strftime("%M")
    curr_sec = time.strftime("%S")
    curr_time = datetime.time(int(curr_hr), int(curr_min), int(curr_sec))
    return curr_time

def time_in_range(start, end, value):
    """Return true if value is in the range [start, end]"""
    # syslog.syslog(syslog.LOG_INFO, ' **** Backup date check %s %s %s' % (start, end ,x))
    if start <= end:
        return start <= value <= end
    else:
        return start <= value or value <= end

def save_last_run(save_file, last_run):
    """ Save date/time of last backup. """
    file_ptr = open(save_file, "w")
    file_ptr.write(str(last_run))
    file_ptr.close()

def get_last_run(save_file):
    """ Get date of last backup. """
    try:
        file_ptr = open(save_file, "r")
    except Exception as exception:
        return ""
    line = file_ptr.read()
    file_ptr.close()
    temp = line.split('-')
    return datetime.date(int(temp[0]), int(temp[1]), int(temp[2]))

class MyBackup(StdService):
    """Custom service that sounds an alarm if an arbitrary expression evaluates true"""

    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(MyBackup, self).__init__(engine, config_dict)

        service_dict = config_dict.get('MyBackup', {})

        enable = to_bool(service_dict.get('enable', True))
        if not enable:
            syslog.syslog(syslog.LOG_INFO, "MyBackup is not enabled, exiting")
            return

        syslog.syslog(syslog.LOG_INFO, "*** Backup intializing 1")
        self.home_dir = '/home/weewx/'

        # keep track of last backup in this file
        # This file must exist!!
        # and have one line with the format of YYYY-MM-DD
        save_file = self.home_dir + 'thebells/weewx_bkup/last_backup.txt'
        self.save_file = save_file
        self.last_msg_ts = 0
        self.last_run = get_last_run(save_file)
        if not self.last_run:
            self.last_run = datetime.date.today()
            syslog.syslog(
                syslog.LOG_INFO, "Lastrun not found, settng to today: %s" % self.last_run)
        # backup will only run between 3 and 3:30
        self.start = datetime.time(3, 0, 0)
        self.end = datetime.time(3, 30, 0)

        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event): # Need to match signature pylint: disable=unused-argument
        """Gets called on a new archive record event."""
        curr_date = datetime.date.today()
        print(curr_date)

        curr_time = get_curr_time()
        print(curr_time)

        # if the current time is within the start and end range
        # AND if the backup has not run on this date, then do it
        # if True:
        if time_in_range(self.start, self.end, curr_time) and self.last_run != curr_date:
            syslog.syslog(syslog.LOG_INFO, ' **** do Backup now')
            print('do Backup now\n')
            self.last_run = curr_date
            save_last_run(self.save_file, self.last_run)
            # the perl file that performs the backup
            var = self.home_dir + "thebells/weewxaddons/tools/bin/weewx_bkup.pl"
            retcode = subprocess.call(["/usr/bin/perl", var])
        else:
            # syslog.syslog(syslog.LOG_INFO, ' **** no Backup needed')
            print('no Backup needed\n')

# print last_run
