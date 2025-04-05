import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.conf_models import BaseConf, FusionSolarKioskMetric
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.fetch_fusionsolar_kiosk import FetchFusionSolarKiosk
from modules.write_mqtt import WriteMqtt
from modules.models import *


class RelayFusionSolarKiosk:
    def __init__(self, conf: BaseConf, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayFusionSolarKioskKiosk class instantiated")

        self.fs_kiosk = FetchFusionSolarKiosk(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)

        self.logger.info("Starting RelayFusionSolarKiosk on separate thread...")
        self.logger.debug("RelayFusionSolarKiosk waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.fetch_on_startup:
            self.logger.info("Starting process_fusionsolar_kiosks() at init, before waiting for cron, because fetch_on_startup is set")
            self.process_fusionsolar_kiosks()

        self.logger.info(f"Setting cron trigger to run fusionsolar kiosk processing at hour: [{self.conf.fusionsolar_kiosk_fetch_cron_hour}], minute: [{self.conf.fusionsolar_kiosk_fetch_cron_minute}]")
        sched = BlockingScheduler(standalone=True)
        sched.add_job(self.process_fusionsolar_kiosks, trigger="cron", hour=self.conf.fusionsolar_kiosk_fetch_cron_hour, minute=self.conf.fusionsolar_kiosk_fetch_cron_minute)
        sched.start()

    def process_fusionsolar_kiosks(self):
        for fs_conf in self.conf.fusionsolar_kiosks:
            if fs_conf.enabled:
                try:
                    self.logger.info(f"Processing fusionsolar kiosk {fs_conf.descriptive_name}, with kkid {fs_conf.api_kkid}...")
                    inverter_data = self.fs_kiosk.fetch_fusionsolar_status(fs_conf)
                    self.write_pvdata_to_influxdb(inverter_data, fs_conf)
                    self.write_pvdata_to_pvoutput(inverter_data, fs_conf)
                    self.publish_pvdata_to_mqtt(inverter_data, fs_conf)
                except Exception as e:
                    self.logger.exception(f"Exception while processing fusionsolar kiosk [{fs_conf.descriptive_name}] with kkid [{fs_conf.api_kkid}]:\n{e}")
            else:
                self.logger.info(f"Skipping disabled fusionsolar kiosk {fs_conf.descriptive_name}, with kkid {fs_conf.api_kkid}...")

        self.logger.info("Waiting for next FusionSolar interval...")

    def write_pvdata_to_pvoutput(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarKioskMetric):
        if self.conf.pvoutput_module_enabled and fs_conf.output_pvoutput:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(inverter_data, fs_conf.api_kkid, fs_conf.output_pvoutput_system_id)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error writing PV data to PVOutput.org for fusionsolar kiosk [{fs_conf.descriptive_name}] with kkid [{fs_conf.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or PVOutput disabled in fusionsolar kiosk config.")

    def publish_pvdata_to_mqtt(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarKioskMetric):
        if self.conf.mqtt_module_enabled and fs_conf.output_mqtt:
            try:
                self.mqtt.publish_pvdata_to_mqtt(inverter_data)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to MQTT for fusionsolar kiosk [{fs_conf.descriptive_name}] with kkid [{fs_conf.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to MQTT, module disabled, or MQTT output disabled in fusionsolar kiosk config.")

    def write_pvdata_to_influxdb(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarKioskMetric):
        if self.conf.influxdb_module_enabled and fs_conf.output_influxdb:
            try:
                self.influxdb.write_pvdata_to_influxdb(inverter_data)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to InfluxDB for fusionsolar kiosk [{fs_conf.descriptive_name}] with kkid [{fs_conf.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or InfluxDB output disabled in fusionsolar kiosk config.")
