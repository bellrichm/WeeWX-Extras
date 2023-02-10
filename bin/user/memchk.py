# Copyright 2016 Matthew Wall
"""weewx module that track memory use

This requires guppy:

sudo pip install guppy

sudo apt-get install python-guppy

[MemoryCheck]
    filename = /var/tmp/memchk.txt
"""

import syslog
import time
from guppy import hpy
import weewx
from weewx.engine import StdService

VERSION = "0.1"

def logmsg(level, msg):
    syslog.syslog(level, 'memchk: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)


class MemoryCheck(StdService):

    def __init__(self, engine, config_dict):
        super(MemoryCheck, self).__init__(engine, config_dict)
        d = config_dict.get('MemoryCheck', {})
        self.filename = d.get('filename', '/var/tmp/memchk.txt')
        loginf("logging heap to %s on each archive record" % self.filename)
        self.heapy = hpy()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        self.check_memory(self.filename, self.heapy.heap())
        # make the next heap relative to this one
        self.heapy.setrelheap()

    @staticmethod
    def check_memory(filename, newheap):
        tstr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        with open(filename, "a") as f:
            f.write("%s heap:\n" % tstr)
            f.write(str(newheap))
            f.write("\n")


if __name__ == "__main__":
    h = hpy()
    MemoryCheck.check_memory('/var/tmp/memchktest.txt', h.heap(), None)
