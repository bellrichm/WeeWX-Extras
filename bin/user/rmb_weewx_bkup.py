""" Backup WeeWx."""
# to use add the following to the report services, user.rmb_weewx_bkup.MyBackup

import time
import datetime
import os
#import subprocess

import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool

VERSION = "0.0.1"

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__) # confirm to standards pylint: disable=invalid-name
    def setup_logging(logging_level, config_dict):
        """ Setup logging for running in standalone mode."""
        if logging_level:
            weewx.debug = logging_level

        weeutil.logger.setup('wee_MQTTSS', config_dict)

    def logdbg(msg):
        """ Log debug level. """
        log.debug(msg)

    def loginf(msg):
        """ Log informational level. """
        log.info(msg)

    def logerr(msg):
        """ Log error level. """
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog
    def setup_logging(logging_level, config_dict): # Need to match signature pylint: disable=unused-argument
        """ Setup logging for running in standalone mode."""
        syslog.openlog('wee_MQTTSS', syslog.LOG_PID | syslog.LOG_CONS)
        if logging_level:
            syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
        else:
            syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))

    def logmsg(level, msg):
        """ Log the message at the designated level. """
        # Replace '__name__' with something to identify your application.
        syslog.syslog(level, '__name__: %s' % (msg))

    def logdbg(msg):
        """ Log debug level. """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ Log informational level. """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ Log error level. """
        logmsg(syslog.LOG_ERR, msg)


def get_curr_time():
    """" Get the current time. """
    curr_hr = time.strftime("%H")
    curr_min = time.strftime("%M")
    curr_sec = time.strftime("%S")
    curr_time = datetime.time(int(curr_hr), int(curr_min), int(curr_sec))
    return curr_time

def time_in_range(start, end, value):
    """Return true if value is in the range [start, end]"""
    logdbg(' **** Backup date check %s %s %s' % (start, end, value))
    if start <= end:
        return start <= value <= end

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
    except FileNotFoundError:
        last_run = datetime.date.today()
        loginf("Lastrun not found, setting to today: %s" %last_run)
        return last_run
    line = file_ptr.read()
    file_ptr.close()
    temp = line.split('-')
    return datetime.date(int(temp[0]), int(temp[1]), int(temp[2]))

class MyBackup(StdService):
    """Custom service that sounds an alarm if an arbitrary expression evaluates true"""

    def __init__(self, engine, config_dict):
        # Pass the initialization information on to my superclass:
        super(MyBackup, self).__init__(engine, config_dict)

        loginf("Version is %s" % VERSION)

        service_dict = config_dict.get('MyBackup', {})

        enable = to_bool(service_dict.get('enable', True))
        if not enable:
            loginf("MyBackup is not enabled, exiting")
            return

        backup_file = service_dict.get('backup_file', 'run/last_backup.txt')

        self.save_file = os.path.join(self.config_dict['WEEWX_ROOT'], backup_file)
        self.last_run = get_last_run(self.save_file)

        self.start = datetime.datetime.strptime('3:00', '%H:%M').time()
        self.end = datetime.datetime.strptime('3:30', '%H:%M').time()

        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event): # Need to match signature pylint: disable=unused-argument
        """Gets called on a new archive record event."""
        curr_date = datetime.date.today()
        print(curr_date)

        curr_time = get_curr_time()
        print(curr_time)

        # if the current time is within the start and end range
        # AND if the backup has not run on this date, then do it
        if True:
        #if time_in_range(self.start, self.end, curr_time) and self.last_run != curr_date:
            loginf(' **** do Backup now')
            self.last_run = curr_date
            save_last_run(self.save_file, self.last_run)
            # the perl file that performs the backup
            ##var = self.home_dir + "thebells/weewxaddons/tools/bin/weewx_bkup.pl"
            #retcode = subprocess.call(["/usr/bin/perl", var])
        else:
            loginf(' **** no Backup needed')

        # Proof of Concept - backing up DBs
        # sqlite3 -cmd 'attach /home/fork.weewx/archive/weather.sdb as weather;' -cmd '.backup weather /home/fork.weewx/run/tempd.sdb' -cmd  'detach database weather;'

        print("done")
