import time
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.conf_models import BaseConf
from modules.fetch_kenter import FetchKenter
from modules.write_mqtt import WriteMqtt


class RelayKenter:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayKenter class instantiated")

        self.kenter_api = FetchKenter(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)
        self.influxdb_initialized = False

        self.logger.info("Starting RelayKenter on separate thread")
        self.start()

    def start(self):
         
        # Fetch meter list once
        try:
            self.kenter_api.fetch_gridkenter_meters()
        except Exception as e:
            err_msg = f"Could not fetch meterlist from Kenter API"
            self.logger.warning(err_msg, e)


        self.logger.debug("RelayKenter waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        daystobackfill = self.conf.kenter_days_backfill

        while 1:
            try:
                for daysback in range(self.conf.kenter_days_back, self.conf.kenter_days_back + 1 + daystobackfill):
                    grid_measurement_data = self.kenter_api.fetch_gridkenter_data(self.conf.kenter_meter_sysname, self.conf.kenter_meter_connection_id, self.conf.kenter_meter_metering_point_id, daysback)
                    self.write_gridkenter_to_influxdb(grid_measurement_data)

                    if self.conf.kenter_meter2_enabled:
                        grid_measurement_data = self.kenter_api.fetch_gridkenter_data(self.conf.kenter_meter2_sysname, self.conf.kenter_meter2_connection_id, self.conf.kenter_meter2_metering_point_id, daysback)
                        self.write_gridkenter_to_influxdb(grid_measurement_data)

                    # Wait 5 secs for next backfill day
                    if daystobackfill > 0: time.sleep(5);

                # Don't backfill after initial backfill
                daystobackfill = 0
            except:
                self.logger.exception(
                    "Uncaught exception in RelayKenter data processing loop."
                )

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.kenter_interval)

    def write_gridkenter_to_influxdb(self, grid_measurement_data):
        if self.conf.influxdb_enabled:
            if self.influxdb_initialized == False:
                self.influxdb_initialized = self.influxdb.initialize()

            if self.influxdb_initialized:
                self.influxdb.pvinflux_write_griddata(grid_measurement_data)
        else:
            self.logger.debug("Writing data to Influx skipped, not initialized yet.")


