#
#    Copyright (c) 2020-2021 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
""" Replicate a SQLite DB. """

# todo - mainline routine to fill in 'holes' of secondary db

# need to be python 2 compatible pylint: disable=bad-option-value, raise-missing-from, super-with-arguments
# pylint: enable=bad-option-value
import weewx

class ReplicateDB(weewx.engine.StdService):
    """ Replicate a SQLite db. """
    def __init__(self, engine, config_dict):
        super(ReplicateDB, self).__init__(engine, config_dict)

        self.config_dict = config_dict
        service_dict = config_dict.get('ReplicateDB', {})
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

        self.bind(weewx.STARTUP, self.startup)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        print("catching up")
        for database in self.databases:
            if not database['event_catchup']:
                self._replicate(database['primary_binding'], database['secondary_dbm'])

    def startup(self, event): # Need to match signature pylint: disable=unused-argument
        """ WeeWX startup event. """
        for database in self.databases:
            if database['event_catchup']:
                self._create_events(database['primary_binding'], database['secondary_dbm'])

    def new_archive_record(self, event): # Need to match signature pylint: disable=unused-argument
        """ WeeWX new archive record event. """
        for database in self.databases:
            if database['event_catchup']:
                database['secondary_dbm'].addRecord(event.record)
            else:
                self._replicate(database['primary_binding'], database['secondary_dbm'])

    def _create_events(self, primarydb_binding, secondary_dbm):
        last_good_time = secondary_dbm.lastGoodStamp()
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)
        # retrieve the records into storage in hopes that it will eliminate the database locking
        records = []
        for record in primary_dbm.genBatchRecords(last_good_time):
            records.append(record)

        for record in records:
            self.engine.dispatchEvent(weewx.Event(weewx.NEW_ARCHIVE_RECORD,
                                                  record=record,
                                                  origin='hardware'))

        # ToDo - need to call it again, incase new records appear

    def _replicate(self, primarydb_binding, secondary_dbm):
        last_good_time = secondary_dbm.lastGoodStamp()
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)
        records = primary_dbm.genBatchRecords(last_good_time)
        secondary_dbm.addRecord(records)
        primary_dbm.close()
        print("done")
