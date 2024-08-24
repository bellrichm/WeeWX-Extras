import weewx
import weewx.engine
import weedb

table = [('dateTime',               'INTEGER NOT NULL UNIQUE PRIMARY KEY'),
         ('usUnits',                'INTEGER NOT NULL'),
         ('interval',               'INTEGER NOT NULL'),
         ('model',                  'TEXT'),
         ('id',                     'INTEGER'),
# model = ERT-SCM
         ('ert_type',               'INTEGER'),
         ('consumption_data',       'FLOAT'),
         ('encoder_tamper',         'INTEGER'),
         ('physical_tamper',        'INTEGER'),
# model = Neptune-R900
         ('consumption',            'INTEGER'),
         ('backflow',               'INTEGER'),
         ('leak',                   'INTEGER'),
         ('leaknow',                'INTEGER'),
         ('extra',                  'TEXT'),
         ('nouse',                  'INTEGER'),
         ('unkn1',                  'INTEGER'),
         ('unkn2',                  'INTEGER'),
         ('unkn3',                  'INTEGER'),
# model = FineOffset-WH31L
         ('strike_count',           'INTEGER'),
         ('storm_distance_km',      'INTEGER'),
         ('state',                  'TEXT'),
         ('battery_ok',             'INTEGER'),
         ('flags',                  'INTEGER'),

         ('time',                   'TEXT'),
         ]

day_summaries = [(e[0], 'scalar') for e in table
                 if e[0] not in ('dateTime', 'usUnits', 'interval')] + [('wind', 'VECTOR')]

schema = {
    'table': table,
    'day_summaries' : day_summaries
}

class RTLSDR(weewx.engine.StdService):
    def __init__(self, engine, config_dict):
        super(RTLSDR, self).__init__(engine, config_dict)

        service_dict = config_dict.get('RTLSDR', {})
        binding = service_dict.get('data_binding', 'rtlsdr_binding')

        self.dbm = self.engine.db_binder.get_manager(data_binding=binding,
                                                     initialize=True)

        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def shutDown(self):
        try:
            self.dbm.close()
        except weedb.DatabaseError:
            pass

    def new_loop_packet(self, event):
        event.packet['interval'] = 0
        event.packet['dateTime'] = int(event.packet['dateTime'])
        self.dbm.addRecord(event.packet)
