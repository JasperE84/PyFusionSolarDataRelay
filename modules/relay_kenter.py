import time
from modules.models import KenterTransformerKpi
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.conf_models import BaseConf
from modules.fetch_kenter import FetchKenter, FetchKenterMissingChannel16180
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
            for meter in self.conf.kenter_metering_points:
                if meter.enabled:
                    try:
                        for daysback in range(self.conf.kenter_days_back, self.conf.kenter_days_back + 1 + daystobackfill):
                            transformer_data = self.kenter_api.fetch_gridkenter_data(meter.descriptive_name, meter.connection_id, meter.metering_point_id, daysback)
                            self.write_gridkenter_to_influxdb(transformer_data)

                            # Wait 5 secs for next backfill day
                            if daystobackfill > 0: time.sleep(5);

                        # Don't backfill after initial backfill
                        daystobackfill = 0
                    except FetchKenterMissingChannel16180 as e:
                        self.logger.error(e)
                    except Exception as e:
                        self.logger.exception("Uncaught exception in RelayKenter data processing loop.", e)

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.kenter_interval)

    def write_gridkenter_to_influxdb(self, transformer_data: KenterTransformerKpi):
        if self.conf.influxdb_module_enabled:
            if self.influxdb_initialized == False:
                self.influxdb_initialized = self.influxdb.initialize()

            if self.influxdb_initialized:
                self.influxdb.write_kenterdata_to_influxdb(transformer_data)
        else:
            self.logger.debug("Writing data to Influx skipped, module disabled.")


