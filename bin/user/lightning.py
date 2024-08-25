import logging

import weewx
import weewx.engine

log = logging.getLogger(__name__)

class Lightning(weewx.engine.StdService):
    def __init__(self, engine, config_dict):
        super(Lightning, self).__init__(engine, config_dict)

        self.strike_count_total = None

        service_dict = config_dict.get('Lightning', {})
        self.contains_total = service_dict.get('contains_total', True)

        self.lightning_count_field_name = service_dict.get('lightning_count_field_name', 'lightning_count')
        self.lightning_distance_field_name = service_dict.get('lightning_distance_field_name', 'lightning_distance')

        self.strike_count_field_name = service_dict.get('strike_count_field_name', 'strike_count')
        self.strike_distance_field_name = service_dict.get('strike_distance_field_name', 'storm_distance_km')

        self.last_distance_field_name = service_dict.get('last_distance_field_name', 'lightning_last_distance')
        self.last_det_time_field_name = service_dict.get('last_det_time_field_name', 'lightning_last_det_time')

        self.first_distance_field_name = service_dict.get('first_distance_field_name', 'lightning_first_distance')
        self.first_det_time_field_name = service_dict.get('first_det_time_field_name', 'lightning_first_det_time')

        self.min_distance_field_name = service_dict.get('min_distance_field_name', 'lightning_min_distance')
        self.min_det_time_field_name = service_dict.get('min_det_time_field_name', 'lightning_min_det_time')

        self.bind(weewx.PRE_LOOP, self.pre_loop)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def pre_loop(self, _event):
        print("pre loop")
        self.last_strike_distance = None
        self.last_strike_time = None
        self.first_strike_distance = None
        self.first_strike_time = None
        self.min_strike_distance = None
        self.min_strike_time = None

    def new_loop_packet(self, event):
        if self.strike_count_field_name not in event.packet or self.strike_distance_field_name not in event.packet:
            return
        
        log.info(event.packet)
        log.info(self.strike_count_total)
        log.info(self.last_strike_distance)
        log.info(self.last_strike_time)
        log.info(self.first_strike_distance)
        log.info(self.first_strike_time)
        log.info(self.min_strike_distance)
        log.info(self.min_strike_time)
       
        date_time = event.packet['dateTime']
        strike_distance = event.packet[self.strike_distance_field_name]
        strike_count_total = event.packet[self.strike_count_field_name]
        strike_count = None

        if self.contains_total:
            log.info(f"Calculating delta {self.strike_count_total} {strike_count_total}")
            if self.strike_count_total is not None and strike_count_total is not None:
                if strike_count_total - self.strike_count_total > 0:
                    strike_count = strike_count_total - self.strike_count_total
                else:
                    strike_count = self.strike_count_total
            self.strike_count_total = strike_count_total
        else:
            strike_count = strike_count_total

        if strike_count:
            log.info(f"Setting last strike distance {strike_distance} and time {date_time}")
            self.last_stike_distance = strike_distance
            self.last_strike_time = date_time

            if self.first_strike_distance is None:
                log.info(f"Setting first strike distance {strike_distance} and time {date_time}")
                self.first_strike_distance = strike_distance
                self.first_strike_time = date_time

            if self.min_strike_distance <= strike_distance:
                log.info(f"Setting min strike distance {strike_distance} and time {date_time}")
                self.min_strike_distance = strike_distance
                self.min_strike_time = date_time

        event.packet[self.strike_count_field_name] = strike_distance
        event.packet[self.strike_distance_field_name] = strike_count
        event.packet[self.last_distance_field_name] = self.last_strike_distance
        event.packet[self.last_det_time_field] = self.last_strike_time
        event.packet[self.first_distance_field_name] = self.first_strike_distance
        event.packet[self.first_det_time_field] = self.first_strike_time
        event.packet[self.min_distance_field_name] = self.min_strike_distance
        event.packet[self.min_det_time_field] = self.min_strike_time
               
        log.info(event.packet)