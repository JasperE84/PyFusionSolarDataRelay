import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.conf_models import BaseConf, FusionSolarOpenApiInverter
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.fetch_fusion_solar_open_api import FetchFusionSolarOpenApi
from modules.write_mqtt import WriteMqtt
from modules.models import *

class RelayFusionSolarOpenApi:
    def __init__(self, conf: BaseConf, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayFusionSolarOpenApiOpenApi class instantiated")

        self.fs_open_api = FetchFusionSolarOpenApi(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)

        self.logger.info("Starting RelayFusionSolarOpenApi on separate thread...")
        self.logger.debug("RelayFusionSolarOpenApi waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.fetch_on_startup:
            self.logger.info("Starting process_fusionsolar_open_apis() at init, before waiting for cron, because fetch_on_startup is set")
            self.process_fusionsolar_open_apis()

        self.logger.info(f"Setting cron trigger to run fusionsolar open_api processing at hour: [{self.conf.fusionsolar_open_api_cron_hour}], minute: [{self.conf.fusionsolar_open_api_cron_minute}]")
        sched = BlockingScheduler(standalone=True)
        sched.add_job(self.process_fusionsolar_open_apis, trigger="cron", hour=self.conf.fusionsolar_open_api_cron_hour, minute=self.conf.fusionsolar_open_api_cron_minute)
        sched.start()

    def process_fusionsolar_open_apis(self):
        self.process_fusionsolar_inverters()
        # ToDo: Implement meters too

        self.logger.info("Waiting for next FusionSolar interval...")

    def process_fusionsolar_inverters(self):
        try:
            self.logger.info(f"Processing fusionsolar open_api inverters...")
            inverter_data = self.fs_open_api.fetch_fusionsolar_inverter_device_kpis()


            for fs_conf in self.conf.fusionsolar_open_api_inverters:
                if fs_conf.enabled:
                    pass
                    #for inverter in inverter_data:
                    #    self.write_pvdata_to_influxdb(inverter, fs_conf)
                    #    self.write_pvdata_to_pvoutput(inverter, fs_conf)
                    #    self.publish_pvdata_to_mqtt(inverter, fs_conf)
                else:
                    self.logger.info(f"Skipping disabled fusionsolar open_api {fs_conf.descriptive_name}, with dev_id {fs_conf.dev_id}...")


        except Exception as e:
            self.logger.exception(f"Exception while processing fusionsolar open_api inverters:\n{e}")

    def write_pvdata_to_pvoutput(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarOpenApiInverter):
        if self.conf.pvoutput_module_enabled and fs_conf.output_pvoutput:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(inverter_data, fs_conf)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error writing PV data to PVOutput.org for fusionsolar open_api [{fs_conf.descriptive_name}] with dev_id [{fs_conf.dev_id}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or PVOutput disabled in fusionsolar open_api config.")

    def publish_pvdata_to_mqtt(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarOpenApiInverter):
        if self.conf.mqtt_module_enabled and fs_conf.output_mqtt:
            try:
                self.mqtt.publish_pvdata_to_mqtt(inverter_data)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to MQTT for fusionsolar open_api [{fs_conf.descriptive_name}] with dev_id [{fs_conf.dev_id}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to MQTT, module disabled, or MQTT output disabled in fusionsolar open_api config.")

    def write_pvdata_to_influxdb(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarOpenApiInverter):
        if self.conf.influxdb_module_enabled and fs_conf.output_influxdb:
            try:
                self.influxdb.write_fsolar_open_api_data_to_influxdb(inverter_data)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to InfluxDB for fusionsolar open_api [{fs_conf.descriptive_name}] with dev_id [{fs_conf.dev_id}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or InfluxDB output disabled in fusionsolar open_api config.")
