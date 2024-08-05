'''
Run WeeWX reports. Useful for looking for memory 'leaks'
'''
# PYTHONPATH=~/weewx/src:~/weewx-data/bin python3 ~/weewx-data/bin/user/runreports.py

# import user.jas
import logging
import os
import resource
import socket
import sys
import traceback

import weewx
import weewx.engine
import weecfg
import weeutil
import weeutil.logger
import weeutil.startup


reports = ['jas']
RUNS = 100
CONFIG = '/home/richbell/weewx-data/run/weewx.conf'

PID = os.getpid()
PAGE_SIZE = resource.getpagesize()

if __name__ == "__main__":
    def get_data():
        ''' Get the data'''
        record = {}
        try:
            procfile = f"/proc/{PID}/statm"
            with open(procfile, encoding="utf-8") as file:
                mem_tuple = file.read().split()
                # Unpack the tuple:
                (size, resident, share, _text, _lib, _data, _dt) = mem_tuple
                mb = 1024 * 1024
                record['mem_size']  = float(size)     * PAGE_SIZE/ mb
                record['mem_rss']   = float(resident) * PAGE_SIZE / mb
                record['mem_share'] = float(share)    * PAGE_SIZE/ mb
        except (ValueError, IOError, KeyError) as exception:
            print(f'memory_info failed: {exception}')

        return record

    def main():
        ''' The program. '''
        print("In main")
        _config_path, config_dict = weecfg.read_config(CONFIG)

        try:
            # Customize the logging with user settings.
            weeutil.logger.setup('weectl', config_dict)
        except Exception as e:
            print(f"Unable to set up logger: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(weewx.CONFIG_ERROR)

        # Get a logger. This one will have the requested configuration.
        log = logging.getLogger(__name__)
        # Announce the startup
        log.info("Initializing weectl version %s", weewx.__version__)
        log.info("Command line: %s", ' '.join(sys.argv))

        # Add USER_ROOT to PYTHONPATH, read user.extensions:
        weeutil.startup.initialize(config_dict)

        socket.setdefaulttimeout(10)

        # Instantiate the dummy engine. This will cause services to get loaded, which will make
        # the type extensions (xtypes) system available.
        engine = weewx.engine.DummyEngine(config_dict)

        stn_info = weewx.station.StationInfo(**config_dict['Station'])

        try:
            binding = config_dict['StdArchive']['data_binding']
        except KeyError:
            binding = 'wx_binding'

        # Retrieve the appropriate record from the database
        with weewx.manager.DBBinder(config_dict) as db_binder:
            db_manager = db_binder.get_manager(binding)
            ts = db_manager.lastGoodStamp()
            record = db_manager.getRecord(ts)

        first_run = True
        print (get_data())
        for run  in range(RUNS):
            # Instantiate the report engine with the retrieved record and required timestamp
            t = weewx.reportengine.StdReportEngine(config_dict, stn_info, record=record, gen_ts=ts, first_run=first_run)

            try:
                # Although the report engine inherits from Thread, we can just run it in the main thread:
                log.info("**** Running run: %i of %i ****", run+1, RUNS)
                t.run(reports)
                print(f"{run+1} {get_data()}")
                first_run = False
            except KeyError as e:
                print(f"Unknown report: {e}", file=sys.stderr)

        # Shut down any running services,
        engine.shutDown()

        print("Done.")


main()
