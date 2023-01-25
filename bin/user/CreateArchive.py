import syslog
import time
import sys

import weewx.accum
import weeutil.weeutil

from weewx.engine import BreakLoop
from weewx.engine import StdArchive
from weeutil.weeutil import to_bool, to_int

# Stole from six module. Added to eliminate dependency on six when running under WeeWX 3.x
PY2 = sys.version_info[0] == 2
if PY2:
    MAXSIZE = sys.maxint # (only a python 3 error) pylint: disable=no-member
else:
    MAXSIZE = sys.maxsize

class CreateArchive(StdArchive):
    """Service that archives LOOP and archive data in the SQL databases."""
    
    # This service manages an "accumulator", which records high/lows and
    # averages of LOOP packets over an archive period. At the end of the
    # archive period it then emits an archive record.
    
    def __init__(self, engine, config_dict):
        super(CreateArchive, self).__init__(engine, config_dict) 
        # self.record_generation = 'software' # force to software for testing

    def startup(self, event):  # @UnusedVariable
        try:
            generator = self.engine.console.genStartupRecords
            # todo - more investigation
            #for record in generator(None):
            for record in generator(1):
                print("*** %s %s" % (weeutil.weeutil.timestamp_to_string(record['dateTime']), weeutil.weeutil.to_sorted_string(record)))
                print("*** done")
        except NotImplementedError:
            pass

    def new_loop_packet(self, event):
        """Called when A new LOOP record has arrived."""
        super(CreateArchive, self).new_loop_packet(event) 

    def check_loop(self, event):
        """Called after any loop packets have been processed. This is the opportunity
        to break the main loop by throwing an exception."""
        super(CreateArchive, self).check_loop(event)         


    def post_loop(self, event):  # @UnusedVariable
        """The main packet loop has ended, so process the old accumulator."""
        super(CreateArchive, self).post_loop(event)     
        
    def new_archive_record(self, event):
        """Called when a new archive record has arrived. """

        # If requested, extract any extra information we can out of the 
        # accumulator and put it in the record.
        if self.record_augmentation and self.old_accumulator \
                and event.record['dateTime'] == self.old_accumulator.timespan.stop:
            self.old_accumulator.augmentRecord(event.record)

        #dbmanager = self.engine.db_binder.get_manager(self.data_binding)
        #dbmanager.addRecord(event.record, accumulator=self.old_accumulator)

    def setup_database(self, config_dict):  # @UnusedVariable
        """Setup the main database archive"""
        pass

    def _software_catchup(self):
        """The main packet loop has ended, so process the old accumulator."""
        super(CreateArchive, self)._software_catchup()

    def _catchup(self, generator):
        """Pull any unarchived records off the console and archive them.
        #
        #If the hardware does not support hardware archives, an exception of
        #type NotImplementedError will be thrown.""" 

        #lastgood_ts = self.end_archive_period_ts - self.archive_interval
        #print("%i %i %i" %(lastgood_ts, self.end_archive_period_ts, time.time()))
        #print("%i" % self.archive_interval)

        dbmanager = self.engine.db_binder.get_manager(self.data_binding)
        ## Find out when the database was last updated.
        lastgood_ts = dbmanager.lastGoodStamp()

        try:
            # Now ask the console for any new records since then.
            # (Not all consoles support this feature).
            for record in generator(lastgood_ts):
                self.engine.dispatchEvent(weewx.Event(weewx.NEW_ARCHIVE_RECORD,
                                                      record=record,
                                                      origin='hardware'))
        except weewx.HardwareError as e:
            syslog.syslog(syslog.LOG_ERR, "engine: Internal error detected. Catchup abandoned")
            syslog.syslog(syslog.LOG_ERR, "**** %s" % e)

