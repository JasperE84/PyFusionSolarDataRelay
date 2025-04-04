import logging
import time
from modules.models import KenterTransformerKpi
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.conf_models import BaseConf, KenterMeterMetric
from modules.fetch_kenter import FetchKenter, FetchKenterMissingChannel16180
from modules.write_mqtt import WriteMqtt


class RelayKenter:
    def __init__(self, conf: BaseConf, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayKenter class instantiated")

        self.kenter_api = FetchKenter(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)

        self.logger.info("Starting RelayKenter on separate thread")
        self.logger.debug("RelayKenter waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        self.start()

    def start(self):
        # Fetch meter list once
        try:
            self.kenter_api.fetch_gridkenter_meters()
        except Exception as e:
            self.logger.exception(f"Could not fetch meterlist from Kenter API {e}")

        # Run API fetch loop for each day to process for each metering point
        daystobackfill = self.conf.kenter_days_backfill
        while 1:
            for meter in self.conf.kenter_metering_points:
                if meter.enabled:
                    for daysback in range(self.conf.kenter_days_back, self.conf.kenter_days_back + 1 + daystobackfill):
                        try:
                            transformer_data = self.kenter_api.fetch_gridkenter_data(meter.descriptive_name, meter.connection_id, meter.metering_point_id, daysback)
                            self.write_gridkenter_to_influxdb(transformer_data, meter)
                            # Wait 5 secs for each next backfill day
                            if daystobackfill > 0:
                                time.sleep(5)
                        except FetchKenterMissingChannel16180 as e:
                            self.logger.exception(f"Channel 16180 is missing for kenter meter [{meter.descriptive_name}], connectionId: [{meter.connection_id}] meteringPointId: [{meter.metering_point_id}]:\n{e}")
                        except Exception as e:
                            self.logger.exception(f"Exception while processing keter meter [{meter.descriptive_name}], connectionId: [{meter.connection_id}] meteringPointId: [{meter.metering_point_id}]:\n{e}")

                    # Don't backfill after initial backfill
                    daystobackfill = 0
                else:
                    self.logger.info(f"Skipping disabled kenter meter [{meter.descriptive_name}], connectionId: [{meter.connection_id}] meteringPointId: [{meter.metering_point_id}]...")

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.kenter_interval)

    def write_gridkenter_to_influxdb(self, transformer_data: KenterTransformerKpi, meter_conf: KenterMeterMetric):
        if self.conf.influxdb_module_enabled and meter_conf.output_influxdb:
            try:
                self.influxdb.write_kenterdata_to_influxdb(transformer_data)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing Kenter data to InfluxDB for meter [{transformer_data.descriptive_name}], connectionId: [{transformer_data.connection_id}] meteringPointId: [{transformer_data.metering_point_id}]: {e}")
        else:
            self.logger.info(f"InfluxDB output disabled for Kenter meter [{transformer_data.descriptive_name}], connectionId: [{transformer_data.connection_id}] meteringPointId: [{transformer_data.metering_point_id}]...")

