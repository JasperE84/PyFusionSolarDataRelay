import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from modules.conf_models import PyFusionSolarSettings, FusionSolarKioskSettings
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.fetch_fusionsolar_kiosk import FetchFusionSolarKiosk
from modules.write_mqtt import WriteMqtt
from modules.models import *
from modules.decorators import job_timeout, JobTimeoutError, JobExecutionTracker


class RelayFusionSolarKiosk:
    def __init__(self, conf: PyFusionSolarSettings, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayFusionSolarKioskKiosk class instantiated")

        self.fs_kiosk = FetchFusionSolarKiosk(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)
        self.influxdb = WriteInfluxDb(self.conf, self.logger)
        
        # Initialize job execution tracker
        self.job_tracker = JobExecutionTracker(logger)
        self.job_id = "process_fusionsolar_kiosks"

        self.logger.info("Starting RelayFusionSolarKiosk on separate thread...")
        self.logger.debug("RelayFusionSolarKiosk waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.fetch_on_startup:
            self.logger.info("Starting process_fusionsolar_kiosks() at init, before waiting for cron, because fetch_on_startup is set")
            self._execute_job_with_timeout()

        self.logger.info(
            f"Setting cron trigger to run fusionsolar kiosk processing at hour: [{self.conf.fusionsolar_kiosk_fetch_cron_hour}], minute: [{self.conf.fusionsolar_kiosk_fetch_cron_minute}]"
        )
        self.logger.info(f"Kiosk job timeout configured for {self.conf.fusionsolar_kiosk_job_timeout_seconds} seconds, cancellation {'enabled' if self.conf.fusionsolar_kiosk_allow_job_cancellation else 'disabled'}")
        
        self.sched = BlockingScheduler(standalone=True)
        # Use the wrapper method instead of the direct method
        self.sched.add_job(
            self._execute_job_with_timeout,
            trigger="cron",
            hour=self.conf.fusionsolar_kiosk_fetch_cron_hour,
            minute=self.conf.fusionsolar_kiosk_fetch_cron_minute,
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
            
            if current_duration and current_duration >= self.conf.fusionsolar_kiosk_job_timeout_seconds:
                if self.conf.fusionsolar_kiosk_allow_job_cancellation:
                    self.logger.warning(f"Previous kiosk job has been running for {current_duration:.1f} seconds (>= {self.conf.fusionsolar_kiosk_job_timeout_seconds}s timeout). Cleaning up and starting new job.")
                    self.job_tracker.cleanup_stale_jobs(self.conf.fusionsolar_kiosk_job_timeout_seconds)
                else:
                    self.logger.warning(f"Previous kiosk job has been running for {current_duration:.1f} seconds (>= {self.conf.fusionsolar_kiosk_job_timeout_seconds}s timeout), but cancellation is disabled. Skipping this execution.")
                    return
            else:
                self.logger.info(f"Previous kiosk job still running ({current_duration:.1f}s). Skipping this execution to prevent overlap.")
                return
        
        # Start tracking this job execution
        if not self.job_tracker.start_job(self.job_id):
            self.logger.warning("Failed to start kiosk job tracking. Another job may be running.")
            return
        
        try:
            if self.conf.fusionsolar_kiosk_allow_job_cancellation:
                # Execute with timeout if cancellation is enabled
                self._process_with_timeout()
            else:
                # Execute without timeout if cancellation is disabled
                self.process_fusionsolar_kiosks()
        except JobTimeoutError as e:
            self.logger.error(f"Kiosk job execution timed out: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during kiosk job execution: {e}")
        finally:
            # Always clean up job tracking
            self.job_tracker.finish_job(self.job_id)
    
    def _process_with_timeout(self):
        """Execute the main processing with timeout decorator."""
        @job_timeout(self.conf.fusionsolar_kiosk_job_timeout_seconds, self.logger)
        def timed_process():
            return self.process_fusionsolar_kiosks()
        
        return timed_process()
    
    def _job_listener(self, event):
        """Listen to job events for additional logging and cleanup."""
        if event.job_id == self.job_id:
            if event.exception:
                self.logger.error(f"Kiosk job {self.job_id} failed with exception: {event.exception}")
            else:
                self.logger.debug(f"Kiosk job {self.job_id} completed successfully")

    def process_fusionsolar_kiosks(self):
        for kiosk_settings in self.conf.fusionsolar_kiosks:
            if kiosk_settings.enabled:
                try:
                    self.logger.info(f"Processing fusionsolar kiosk {kiosk_settings.descriptive_name}, with kkid {kiosk_settings.api_kkid}...")
                    kiosk_measurement = self.fs_kiosk.fetch_fusionsolar_status(kiosk_settings)
                    self.write_pvdata_to_influxdb(kiosk_measurement, kiosk_settings)
                    self.write_pvdata_to_pvoutput(kiosk_measurement, kiosk_settings)
                    self.publish_pvdata_to_mqtt(kiosk_measurement, kiosk_settings)
                except Exception as e:
                    self.logger.exception(f"Exception while processing fusionsolar kiosk [{kiosk_settings.descriptive_name}] with kkid [{kiosk_settings.api_kkid}]:\n{e}")
            else:
                self.logger.info(f"Skipping disabled fusionsolar kiosk {kiosk_settings.descriptive_name}, with kkid {kiosk_settings.api_kkid}...")

        self.logger.info("Waiting for next FusionSolar Kiosk interval...")

    def write_pvdata_to_pvoutput(self, kiosk_measurement: FusionSolarInverterMeasurement, kiosk_settings: FusionSolarKioskSettings):
        if self.conf.pvoutput_module_enabled and kiosk_settings.output_pvoutput:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(kiosk_measurement, kiosk_settings.api_kkid, kiosk_settings.output_pvoutput_system_id)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error writing PV data to PVOutput.org for fusionsolar kiosk [{kiosk_settings.descriptive_name}] with kkid [{kiosk_settings.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to PvOutput, module disabled, or PVOutput disabled in fusionsolar kiosk config.")

    def publish_pvdata_to_mqtt(self, kiosk_measurement: FusionSolarInverterMeasurement, kiosk_settings: FusionSolarKioskSettings):
        if self.conf.mqtt_module_enabled and kiosk_settings.output_mqtt:
            try:
                self.mqtt.publish_pvdata_to_mqtt(kiosk_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to MQTT for fusionsolar kiosk [{kiosk_settings.descriptive_name}] with kkid [{kiosk_settings.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to MQTT, module disabled, or MQTT output disabled in fusionsolar kiosk config.")

    def write_pvdata_to_influxdb(self, kiosk_measurement: FusionSolarInverterMeasurement, kiosk_settings: FusionSolarKioskSettings):
        if self.conf.influxdb_module_enabled and kiosk_settings.output_influxdb:
            try:
                self.influxdb.write_pvdata_to_influxdb(kiosk_measurement)
            except Exception as e:
                # Log but do not raise, other outputs should proceed.
                self.logger.exception(f"Error publishing PV data to InfluxDB for fusionsolar kiosk [{kiosk_settings.descriptive_name}] with kkid [{kiosk_settings.api_kkid}]: {e}")
        else:
            self.logger.debug(f"Skipping publishing to InfluxDB, module disabled, or InfluxDB output disabled in fusionsolar kiosk config.")
