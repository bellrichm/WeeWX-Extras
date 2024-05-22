#
#    Copyright (c) 2020-2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""
Replicate SQLite DB(s) by pulling data from the primary/source and updating the secondary/target.

Installation:
    1. Put this file in the bin/user directory.
    2. Update weewx.conf [ReplicateDB] as needed to configure the service.
    3. Replace weewx.engine.StdArchive with user.replicatedb.ReplicateDB in the [engine] stanza.

Overview:
Replicate the SQLite DBs by inserting any records from the secondary binding
that have a dateTime greater than the last dateTime in the primary bindng.
The main WeeWX database has additional options. Instead of directly inserting the data into the primary DB,
a new archive record event can be created. This allows the WeeWX pipeline to run as normal.
The other option is to add the new archive event record to the database, like StdArchive would.

Note: Currently there is no error checking that these options are configured correctly.

Configuration:
[ReplicateDB]
    # When set to True, the archive event record is stored in the DB (ala StdArchive processing.)
    # When set to False, the archive event record is ignored and therefore the DB must be configured below.
    # Currently there is no checking that when the value is False that the DB is configued below.
    # Nor is there any checking that when the fslue us True that the DB is NOT configued below.
    # Default is False.
    store_archive_event_record = True

    # The databases to replicate.
    # Each section [[DBn]] identifies a database pair, primary and secondary.
    # The section name can be any value.
    [[db01]]
        # When set to True, an archive event is raised enabling processing that listens on this event to happen.
        # When set to False, the data is added directly to the secondary DB.
        # Default is False.
        event_catchup = True
        # The WeeWX database binding of the primary DB.
        # The WeeWX database binding of the secondary DB.
        primary_binding = primary_db_binding
        secondary_binding = secondary_db_binding

    # Additional databases to replicate
    [[db02]]
        primary_binding = primary_db02_binding
        secondary_binding = secondary_db02_binding
    [[db03]]
        ...
"""

# todo - mainline routine to fill in 'holes' of secondary db

# need to be python 2 compatible pylint: disable=bad-option-value, raise-missing-from, super-with-arguments
# pylint: enable=bad-option-value
import weewx
from weewx.engine import StdArchive

class ReplicateDB(StdArchive):
    """ Replicate a SQLite db. """
    def __init__(self, engine, config_dict):
        super(ReplicateDB, self).__init__(engine, config_dict)

        self.config_dict = config_dict
        service_dict = config_dict.get('ReplicateDB', {})
        self.store_archive_event_record = service_dict.get('store_archive_event_record', False)
        self.databases = []
        for section in service_dict.sections:
            db_dict = service_dict.get(section, {})
            database = {}
            database['name'] = section
            database['event_catchup'] = db_dict.get('event_catchup', False)
            database['primary_binding'] = db_dict['primary_binding']
            database['secondary_binding'] = db_dict['secondary_binding']
            database['secondary_dbm'] = weewx.manager.open_manager_with_config(
                config_dict,
                database['secondary_binding'],
                initialize=True)
            self.databases.append(database)

        print("catching up")
        for database in self.databases:
            if not database['event_catchup']:
                self._replicate(database['primary_binding'], database['secondary_dbm'])

    def startup(self, event): # Need to match signature pylint: disable=unused-argument
        """ WeeWX startup event. """
        print("replicatedb startup")
        for database in self.databases:
            if database['event_catchup']:
                self._create_events(database['primary_binding'], database['secondary_dbm'])

        super(ReplicateDB, self).startup(event)

    def new_archive_record(self, event): # Need to match signature pylint: disable=unused-argument
        """ WeeWX new archive record event. """
        print("replicatedb new_archive_record")

        # If requested, extract any extra information we can out of the accumulator and put it in
        # the record. Not necessary in the case of software record generation because it has
        # already been done.
        if self.record_augmentation \
                and self.old_accumulator \
                and event.record['dateTime'] == self.old_accumulator.timespan.stop \
                and event.origin != 'software':
            self.old_accumulator.augmentRecord(event.record)

        if self.store_archive_event_record:
            dbmanager = self.engine.db_binder.get_manager(self.data_binding)
            dbmanager.addRecord(event.record,
                                accumulator=self.old_accumulator,
                                log_success=self.log_success,
                                log_failure=self.log_failure)

        for database in self.databases:
            if database['event_catchup']:
                database['secondary_dbm'].addRecord(event.record,
                                accumulator=self.old_accumulator,
                                log_success=self.log_success,
                                log_failure=self.log_failure)
            else:
                self._replicate(database['primary_binding'], database['secondary_dbm'])

    def _create_events(self, primarydb_binding, secondary_dbm):
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)

        last_good_time = secondary_dbm.lastGoodStamp()
        # retrieve the records into storage in hopes that it will eliminate the database locking
        records = []
        for record in primary_dbm.genBatchRecords(last_good_time):
            records.append(record)

        for record in records:
            self.engine.dispatchEvent(weewx.Event(weewx.NEW_ARCHIVE_RECORD,
                                                  record=record,
                                                  origin='hardware'))

    def _replicate(self, primarydb_binding, secondary_dbm):
        last_good_time = secondary_dbm.lastGoodStamp()
        # ToDo - next line sometimes fails with: sqlite3.OperationalError: attempt to write a readonly database
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)
        records = primary_dbm.genBatchRecords(last_good_time)
        secondary_dbm.addRecord(records)
        primary_dbm.close()

def main():
    """ Mainline function """
    import os
    import configobj

    print("main")
    config_file = 'weewx.raspberrypi.conf'
    database = 'weewx'
    config_path = os.path.abspath(config_file)
    config_dict = configobj.ConfigObj(config_path, file_error=True)
    service_dict = config_dict.get('ReplicateDB', {})
    for section in service_dict.sections:
        if section == database:
            db_dict = service_dict.get(section, {})
            primary_dbm = weewx.manager.open_manager_with_config(config_dict, db_dict['primary_binding'])
            secondary_dbm = weewx.manager.open_manager_with_config(config_dict, db_dict['secondary_binding'])
            break

    # ToDo - convert to sql to get list of timestamps
    print("get secondary timestamps")
    secondary_records = secondary_dbm.genBatchRecords(startstamp=None, stopstamp=None)
    #secondary_timestamps = []
    secondary_timestamps = set()
    for record in secondary_records:
        #secondary_timestamps.append(record['dateTime'])
        secondary_timestamps.add(record['dateTime'])

    print("start compare")
    primary_records = primary_dbm.genBatchRecords(startstamp=None, stopstamp=None)
    missing_records = []
    for record in primary_records:
        if record['dateTime'] not in secondary_timestamps:
            missing_records.append(record)

    secondary_dbm.addRecord(missing_records)

    print("done")


if __name__ == "__main__":
    main()
