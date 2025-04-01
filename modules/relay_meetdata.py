import time
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.conf_models import BaseConf
from modules.fetch_meetdata import FetchMeetdata
from modules.write_mqtt import WriteMqtt


class RelayMeetdata:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayMeetdata class instantiated")

        self.gridkenter = FetchMeetdata(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)
        self.influxdb_initialized = False

        self.logger.info("Starting RelayMeetdata on separate thread")
        self.start()

    def start(self):
        self.logger.debug("RelayMeetdata waiting 5sec to initialize docker-compose containers")
        time.sleep(5)
        
        daystobackfill = self.conf.meetdata_nl_days_backfill

        while 1:
            try:
                for daysback in range(self.conf.meetdata_nl_days_back, self.conf.meetdata_nl_days_back + 1 + daystobackfill):
                    grid_measurement_data = self.gridkenter.fetch_gridkenter_data(self.conf.meetdata_nl_meter_sysname, self.conf.meetdata_nl_meter_ean, self.conf.meetdata_nl_meter_id, daysback)
                    self.write_gridkenter_to_influxdb(grid_measurement_data)
                    self.write_gridkenter_to_pvoutput(grid_measurement_data)

                    if self.conf.meetdata_nl_meter2_enabled:
                        grid_measurement_data = self.gridkenter.fetch_gridkenter_data(self.conf.meetdata_nl_meter2_sysname, self.conf.meetdata_nl_meter2_ean, self.conf.meetdata_nl_meter2_id, daysback)
                        self.write_gridkenter_to_influxdb(grid_measurement_data)
                        #No support for pvoutput on 2 EAN codes yet (needs summing of kenter data or pvoutput support for 2 distinct systems)
                        #self.write_gridkenter_to_pvoutput(grid_measurement_data)

                    # Wait 5 secs for next backfill day
                    if daystobackfill > 0: time.sleep(5);

                # Don't backfill after initial backfill
                daystobackfill = 0
            except:
                self.logger.exception(
                    "Uncaught exception in RelayMeetdata data processing loop."
                )

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.meetdata_nl_interval)

    def write_gridkenter_to_pvoutput(self, grid_measurement_data):
        if self.conf.pvoutput_enabled:
            try:
                self.pvoutput.write_meetdata_to_pvoutput(grid_measurement_data)
            except:
                self.logger.exception("Error writing GridData to PVOutput.org")

    def write_gridkenter_to_influxdb(self, grid_measurement_data):
        if self.conf.influxdb_enabled:
            if self.influxdb_initialized == False:
                self.influxdb_initialized = self.influxdb.initialize()

            if self.influxdb_initialized:
                self.influxdb.pvinflux_write_griddata(grid_measurement_data)
        else:
            self.logger.debug("Writing data to Influx skipped, not initialized yet.")


