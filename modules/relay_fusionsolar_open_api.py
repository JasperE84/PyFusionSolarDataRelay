import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from modules.conf_models import PyFusionSolarSettings, FusionSolarOpenApiInverterSettings
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.fetch_fusion_solar_open_api import FetchFusionSolarOpenApi
from modules.write_mqtt import WriteMqtt
from modules.models import *
from modules.decorators import job_timeout, JobTimeoutError, JobExecutionTracker


class RelayFusionSolarOpenApi:
    def __init__(self, conf: PyFusionSolarSettings, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayFusionSolarOpenApiOpenApi class instantiated")

        self.fs_open_api = FetchFusionSolarOpenApi(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)
        
        # Initialize job execution tracker
        self.job_tracker = JobExecutionTracker(logger)
        self.job_id = "process_fusionsolar_open_apis"

        self.logger.info("Starting RelayFusionSolarOpenApi on separate thread...")
        self.logger.debug("RelayFusionSolarOpenApi waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.fetch_on_startup:
            self.logger.info("Starting process_fusionsolar_open_apis() at init, before waiting for cron, because fetch_on_startup is set")
            self._execute_job_with_timeout()

        self.logger.info(f"Setting cron trigger to run fusionsolar open_api processing at hour: [{self.conf.fusionsolar_open_api_cron_hour}], minute: [{self.conf.fusionsolar_open_api_cron_minute}]")
        self.logger.info(f"Job timeout configured for {self.conf.fusionsolar_open_api_job_timeout_seconds} seconds, cancellation {'enabled' if self.conf.fusionsolar_open_api_allow_job_cancellation else 'disabled'}")
        
        self.sched = BlockingScheduler(standalone=True)
        # Use the wrapper method instead of the direct method
        self.sched.add_job(
            self._execute_job_with_timeout,
            trigger="cron",
            hour=self.conf.fusionsolar_open_api_cron_hour,
            minute=self.conf.fusionsolar_open_api_cron_minute,
            max_instances=1,
            coalesce=True,
            id=self.job_id
        )
        
        # Add job event listeners
        self.sched.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        self.sched.start()

    def _execute_job_with_timeout(self):
        """
        Wrapper method that handles job execution with timeout and overlap prevention.
        """
        # Check if job is already running and handle accordingly
        if self.job_tracker.is_job_running(self.job_id):
            current_duration = self.job_tracker.get_job_duration(self.job_id)
            
            if current_duration and current_duration >= self.conf.fusionsolar_open_api_job_timeout_seconds:
                if self.conf.fusionsolar_open_api_allow_job_cancellation:
                    self.logger.warning(f"Previous job has been running for {current_duration:.1f} seconds (>= {self.conf.fusionsolar_open_api_job_timeout_seconds}s timeout). Cleaning up and starting new job.")
                    self.job_tracker.cleanup_stale_jobs(self.conf.fusionsolar_open_api_job_timeout_seconds)
                else:
                    self.logger.warning(f"Previous job has been running for {current_duration:.1f} seconds (>= {self.conf.fusionsolar_open_api_job_timeout_seconds}s timeout), but cancellation is disabled. Skipping this execution.")
                    return
            else:
                self.logger.info(f"Previous job still running ({current_duration:.1f}s). Skipping this execution to prevent overlap.")
                return
        
        # Start tracking this job execution
        if not self.job_tracker.start_job(self.job_id):
            self.logger.warning("Failed to start job tracking. Another job may be running.")
            return
        
        try:
            if self.conf.fusionsolar_open_api_allow_job_cancellation:
                # Execute with timeout if cancellation is enabled
                self._process_with_timeout()
            else:
                # Execute without timeout if cancellation is disabled
                self.process_fusionsolar_open_apis()
        except JobTimeoutError as e:
            self.logger.error(f"Job execution timed out: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during job execution: {e}")
        finally:
            # Always clean up job tracking
            self.job_tracker.finish_job(self.job_id)
    
    def _process_with_timeout(self):
        """Execute the main processing with timeout decorator."""
        @job_timeout(self.conf.fusionsolar_open_api_job_timeout_seconds, self.logger)
        def timed_process():
            return self.process_fusionsolar_open_apis()
        
        return timed_process()
    
    def _job_listener(self, event):
        """Listen to job events for additional logging and cleanup."""
        if event.job_id == self.job_id:
            if event.exception:
                self.logger.error(f"Job {self.job_id} failed with exception: {event.exception}")
            else:
                self.logger.debug(f"Job {self.job_id} completed successfully")

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
            self.logger.debug(f"Skipping publishing to PvOutpu, module disabled, or PVOutput disabled in fusionsolar open_api config.")

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
