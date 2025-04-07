import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.models import KenterTransformerMeasurements
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.conf_models import PyFusionSolarSettings, KenterMeterSettings
from modules.fetch_kenter import FetchKenter, FetchKenterMissingChannelId
from modules.write_mqtt import WriteMqtt


class RelayKenter:
    def __init__(self, conf: PyFusionSolarSettings, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayKenter class instantiated")

        self.kenter_api = FetchKenter(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)

        self.logger.info("Starting RelayKenter on separate thread")

        # Fetch meter list once
        try:
            self.kenter_api.print_gridkenter_meters()
        except Exception as e:
            self.logger.exception(f"Could not fetch meterlist from Kenter API {e}")

        self.logger.debug("RelayKenter waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.fetch_on_startup:
            self.logger.info("Starting process_kenter_meters() at init, before waiting for cron, because fetch_on_startup is set")
            self.process_kenter_meters()

        self.logger.info(f"Setting cron trigger to run kenter meter processing at hour: [{self.conf.kenter_fetch_cron_hour}], minute: [{self.conf.kenter_fetch_cron_minute}]")
        self.sched = BlockingScheduler(standalone=True)
        self.sched.add_job(self.process_kenter_meters, trigger="cron", hour=self.conf.kenter_fetch_cron_hour, minute=self.conf.kenter_fetch_cron_minute)
        self.sched.start()

    def process_kenter_meters(self):
        # Run API fetch loop for each day to process for each metering point
        daystobackfill = self.conf.kenter_days_backfill
        for meter_settings in self.conf.kenter_metering_points:
            if meter_settings.enabled:
                for daysback in range(self.conf.kenter_days_back, self.conf.kenter_days_back + 1 + daystobackfill):
                    try:
                        transformer_measurements = self.kenter_api.fetch_gridkenter_data(
                            meter_settings.descriptive_name, meter_settings.connection_id, meter_settings.metering_point_id, meter_settings.channel_id, daysback
                        )
                        self.write_gridkenter_to_influxdb(transformer_measurements, meter_settings)
                    except FetchKenterMissingChannelId as e:
                        self.logger.warning(
                            f"Channel {meter_settings.channel_id} not available for date, or available at all for kenter meter [{meter_settings.descriptive_name}], connectionId: [{meter_settings.connection_id}] meteringPointId: [{meter_settings.metering_point_id}]."
                        )
                    except Exception as e:
                        self.logger.exception(
                            f"Exception while processing keter meter [{meter_settings.descriptive_name}], connectionId: [{meter_settings.connection_id}] meteringPointId: [{meter_settings.metering_point_id}]:\n{e}"
                        )

                    # Go easy on the API to avoid HTTP status 429 (too many requests)
                    time.sleep(5)
            else:
                self.logger.info(
                    f"Skipping disabled kenter meter [{meter_settings.descriptive_name}], connectionId: [{meter_settings.connection_id}] meteringPointId: [{meter_settings.metering_point_id}]..."
                )

        # Don't backfill after initial backfill
        daystobackfill = 0

        self.logger.debug("Waiting for next cron job...")

    def write_gridkenter_to_influxdb(self, transformer_measurements: KenterTransformerMeasurements, transformer_settings: KenterMeterSettings):
        if self.conf.influxdb_module_enabled and transformer_settings.output_influxdb:
            try:
                self.influxdb.write_kenterdata_to_influxdb(transformer_measurements)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error publishing Kenter data to InfluxDB for meter [{transformer_measurements.descriptive_name}], connectionId: [{transformer_measurements.connection_id}] meteringPointId: [{transformer_measurements.metering_point_id}]: {e}"
                )
        else:
            self.logger.info(
                f"InfluxDB output disabled for Kenter meter [{transformer_measurements.descriptive_name}], connectionId: [{transformer_measurements.connection_id}] meteringPointId: [{transformer_measurements.metering_point_id}]..."
            )
