""" Backup WeeWx."""
# to use add the following to the report services, user.rmb_weewx_bkup.MyBackup

import time
import datetime
import glob
import os
import shutil
import subprocess

import weewx
from weewx.wxengine import StdService
from weeutil.weeutil import to_bool, option_as_list

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
        super(MyBackup, self).__init__(engine, config_dict)

        loginf("Version is %s" % VERSION)

        service_dict = config_dict.get('Backup', {})
        enable = to_bool(service_dict.get('enable', True))
        if not enable:
            loginf("MyBackup is not enabled, exiting")
            return

        self.working_dir = service_dict.get('working_dir', None)
        if self.working_dir is None:
            raise ValueError("A value for 'working_dir' is required.")

        start = service_dict.get('start', None)
        if start is None:
            raise ValueError("A value for 'start' is required.")
        self.start = datetime.datetime.strptime(start, '%H:%M').time()

        end = service_dict.get('end', None)
        if end is None:
            raise ValueError("A value for 'end' is required.")
        self.end = datetime.datetime.strptime(end, '%H:%M').time()

        self.db_names = option_as_list(service_dict.get('db_names', None))
        if self.db_names is None:
            raise ValueError("A value for 'db_names' is required.")

        self.db_location = service_dict.get('db_location', 'archive')

        self.verbose = service_dict.get('verbose', '')

        self.backup_file = service_dict.get('backup_file', 'last_backup.txt')

        self.weewx_root = self.config_dict['WEEWX_ROOT']

        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        print("exit")

    def new_archive_record(self, event): # Need to match signature pylint: disable=unused-argument
        """Gets called on a new archive record event."""
        curr_date = datetime.date.today()
        print(curr_date)

        curr_time = get_curr_time()
        print(curr_time)

        save_file = os.path.join(self.working_dir, self.backup_file)
        last_run = get_last_run(save_file)

        # if the current time is within the start and end range
        # AND if the backup has not run on this date, then do it
        if True:
        #if time_in_range(self.start, self.end, curr_time) and last_run != curr_date:
            loginf(' **** do Backup now')
            save_last_run(save_file, curr_date)
            self.do_backup()
        else:
            loginf(' **** no Backup needed')

        print("done")

    def do_backup(self):
        log_file = os.path.join(self.working_dir, 'backup.txt')
        err_file = os.path.join(self.working_dir, 'backup_err.txt')

        now = datetime.datetime.now()
        day_of_week = str(datetime.datetime.today().weekday())
        curr_dir = os.path.join(self.working_dir, 'bkup' + day_of_week)
        prev_dir = os.path.join(self.working_dir, 'prevbkup' + day_of_week)

        log_file_ptr = open(log_file, "w")
        log_file_ptr.write("%s\n" % now)
        err_file_ptr = open(err_file, "w")
        err_file_ptr.write("%s\n" % now)

        cwd = os.getcwd()
        os.chdir(self.working_dir)

        self.rotate_dirs(prev_dir, curr_dir)
        self.backup_code(os.path.join(self.weewx_root, '*'), curr_dir, log_file_ptr, err_file_ptr)

        os.makedirs(os.path.join(curr_dir, self.db_location))
        for db_name in self.db_names:
            print(db_name)
            db_file_name = os.path.join(self.weewx_root, self.db_location, db_name)
            self.check_db(db_file_name, log_file_ptr, err_file_ptr)
            self.backup_db(db_file_name, os.path.join(curr_dir, self.db_location, db_name), log_file_ptr, err_file_ptr)
            self.check_db(os.path.join(curr_dir, self.db_location, db_name), log_file_ptr, err_file_ptr)
            print("done")

        os.chdir(cwd)

        log_file_ptr.close()
        err_file_ptr.close()

    def check_db(self, db_file, log_file_ptr, err_file_ptr):
        """ Check the database. """
        process = subprocess.Popen(['sqlite3', '-line', db_file, 'pragma integrity_check'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        log_file_ptr.write("%s\n" % db_file)
        log_file_ptr.write(stdout.decode("utf-8"))
        err_file_ptr.write("%s\n" % db_file)
        err_file_ptr.write(stderr.decode("utf-8"))

        print("done")

    # ToDo - handle db name 'as monitor'
    def backup_db(self, db_file, backup_db, log_file_ptr, err_file_ptr):
        process = subprocess.Popen(['sqlite3',
                                    '-cmd', 'attach "' + db_file + '" as monitor',
                                    '-cmd', '.backup monitor ' + backup_db,
                                    '-cmd', 'detach monitor'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("start")
        stdout, stderr = process.communicate()
        log_file_ptr.write(stdout.decode("utf-8"))
        err_file_ptr.write(stderr.decode("utf-8"))

        print("done")

    def backup_code(self, source_dir, dest_dir, log_file_ptr, err_file_ptr):
        """ Backup the code."""
        cmd = ['rsync', '-p', '-a', '-L', self.verbose]
        cmd.extend(['--exclude=.Trash*/',
                    '--exclude=weewx_bkup/',
                    '--exclude=archive*/',
                    '--exclude=run/',
                    '--exclude=lost+found/',
                    '--exclude=.git/'])
        cmd.extend(glob.glob(source_dir))
        cmd.extend([dest_dir])
        print(cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()
        return_code = process.returncode
        log_file_ptr.write(stdout.decode("utf-8"))
        err_file_ptr.write(stderr.decode("utf-8"))
        print(return_code)

    def rotate_dirs(self, prev_dir, curr_dir):
        """ Rotate the backup directories."""
        try:
            shutil.rmtree(prev_dir)
        except FileNotFoundError as exception:
            loginf("Directory %s does not exist," % prev_dir)
            logdbg("Directory delete failed : (%d) %s\n" % (exception.errno, exception.strerror))

        try:
            shutil.move(curr_dir, prev_dir)
        except FileNotFoundError as exception:
            loginf("Directory %s does not exist," % prev_dir)
            logdbg("Directory delete failed : (%d) %s\n" % (exception.errno, exception.strerror))
