import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.conf_models import BaseConf, FusionSolarOpenApiInverterSettings
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
        self.process_fusionsolar_openapi_inverters()
        self.process_fusionsolar_openapi_grid_meters()

        self.logger.info("Waiting for next FusionSolar interval...")

    def process_fusionsolar_openapi_inverters(self):
        try:
            self.logger.info(f"Processing fusionsolar OpenAPI inverters...")
            inverter_measurements = self.fs_open_api.fetch_fusionsolar_inverter_device_kpis()
            
            for inverter_measurement in inverter_measurements:
                if not (inverter_measurement.settings is not None and inverter_measurement.settings.enabled == False):
                    self.write_pvdata_to_influxdb(inverter_measurement)
                    self.publish_pvdata_to_mqtt(inverter_measurement)
                    self.write_pvdata_to_pvoutput(inverter_measurement)
                else:
                    self.logger.info(f"Skipping disabled fusionsolar open_api {inverter_measurement.settings_descriptive_name}, with dev_id {inverter_measurement.settings_device_id}...")

        except Exception as e:
            self.logger.exception(f"Exception while processing fusionsolar open_api inverters:\n{e}")

    def process_fusionsolar_openapi_grid_meters(self):
        try:
            self.logger.info(f"Processing fusionsolar OpenAPI grid meters...")
            grid_meter_measurements = self.fs_open_api.fetch_fusionsolar_grid_meter_device_kpis()
            for grid_meter_measurement in grid_meter_measurements:
                if not (grid_meter_measurement.settings is not None and grid_meter_measurement.settings.enabled == False):
                    self.write_grid_data_to_influxdb(grid_meter_measurement)
                    self.publish_grid_data_to_mqtt(grid_meter_measurement)
                else:
                    self.logger.info(f"Skipping disabled fusionsolar open_api {grid_meter_measurement.settings_descriptive_name}, with dev_id {grid_meter_measurement.settings_device_id}...")

        except Exception as e:
            self.logger.exception(f"Exception while processing fusionsolar open_api grid meters:\n{e}")

    def write_pvdata_to_pvoutput(self, inverter_measurement: FusionSolarInverterMeasurement):
        if self.conf.pvoutput_module_enabled and (inverter_measurement.settings is not None and inverter_measurement.settings.output_pvoutput):
            try:
                self.pvoutput.write_pvdata_to_pvoutput(inverter_measurement, inverter_measurement.settings.dev_id, inverter_measurement.settings.output_pvoutput_system_id)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error writing PV data to PVOutput.org for fusionsolar open_api [{inverter_measurement.settings_descriptive_name}] with dev_id [{inverter_measurement.settings_device_id}]: {e}"
                )
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or PVOutput disabled in fusionsolar open_api config.")

    def publish_pvdata_to_mqtt(self, inverter_measurement: FusionSolarInverterMeasurement):
        if self.conf.mqtt_module_enabled and ((inverter_measurement.settings is not None and inverter_measurement.settings.output_mqtt) or self.conf.fusionsolar_open_api_mqtt_for_discovered_dev):
            try:
                self.mqtt.publish_pvdata_to_mqtt(inverter_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error publishing PV data to MQTT for fusionsolar open_api [{inverter_measurement.settings_descriptive_name}] with dev_id [{inverter_measurement.settings_device_id}]: {e}"
                )
        else:
            self.logger.debug(f"Skipping publishing to MQTT, module disabled, or MQTT output disabled in fusionsolar open_api config.")

    def write_pvdata_to_influxdb(self, inverter_measurement: FusionSolarInverterMeasurement):
        if self.conf.influxdb_module_enabled and (
            (inverter_measurement.settings is not None and inverter_measurement.settings.output_influxdb) or self.conf.fusionsolar_open_api_influxdb_for_discovered_dev
        ):
            try:
                self.influxdb.write_pvdata_to_influxdb(inverter_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error publishing PV data to InfluxDB for fusionsolar open_api [{inverter_measurement.settings_descriptive_name}] with dev_id [{inverter_measurement.settings_device_id}]: {e}"
                )
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or InfluxDB output disabled in fusionsolar open_api config.")

    def publish_grid_data_to_mqtt(self, meter_measurement: FusionSolarMeterMeasurement):
        if self.conf.mqtt_module_enabled and ((meter_measurement.settings is not None and meter_measurement.settings.output_mqtt) or self.conf.fusionsolar_open_api_mqtt_for_discovered_dev):
            try:
                self.mqtt.publish_grid_data_to_mqtt(meter_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error publishing grid meter data to MQTT for fusionsolar open_api [{meter_measurement.settings_descriptive_name}] with dev_id [{meter_measurement.settings_device_id}]: {e}"
                )
        else:
            self.logger.debug(f"Skipping publishing to MQTT, module disabled, or MQTT output disabled in fusionsolar open_api config.")

    def write_grid_data_to_influxdb(self, meter_measurement: FusionSolarMeterMeasurement):
        if self.conf.influxdb_module_enabled and (
            (meter_measurement.settings is not None and meter_measurement.settings.output_influxdb) or self.conf.fusionsolar_open_api_influxdb_for_discovered_dev
        ):
            try:
                self.influxdb.write_grid_data_to_influxdb(meter_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(
                    f"Error publishing grid meter data to InfluxDB for fusionsolar open_api [{meter_measurement.settings_descriptive_name}] with dev_id [{meter_measurement.settings_device_id}]: {e}"
                )
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or InfluxDB output disabled in fusionsolar open_api config.")
