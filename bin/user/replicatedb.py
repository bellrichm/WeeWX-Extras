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

class ReplicateDB(weewx.engine.StdArchive):
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

        #dbmanager = self.engine.db_binder.get_manager(self.data_binding)
        #dbmanager.addRecord(event.record,
        #                    accumulator=self.old_accumulator,
        #                    log_success=self.log_success,
        #                    log_failure=self.log_failure)

        for database in self.databases:
            if database['event_catchup']:
                database['secondary_dbm'].addRecord(event.record)
            else:
                self._replicate(database['primary_binding'], database['secondary_dbm'])

    def _create_events(self, primarydb_binding, secondary_dbm):
        last_good_time = secondary_dbm.lastGoodStamp()
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)
        for record in primary_dbm.genBatchRecords(last_good_time):
            self.engine.dispatchEvent(weewx.Event(weewx.NEW_ARCHIVE_RECORD,
                                                  record=record,
                                                  origin='hardware'))

    def _replicate(self, primarydb_binding, secondary_dbm):
        last_good_time = secondary_dbm.lastGoodStamp()
        primary_dbm = weewx.manager.open_manager_with_config(self.config_dict, primarydb_binding)
        records = primary_dbm.genBatchRecords(last_good_time)
        secondary_dbm.addRecord(records)
        primary_dbm.close()
        print("done")
