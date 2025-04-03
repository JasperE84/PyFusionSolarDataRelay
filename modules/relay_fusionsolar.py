import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.conf_models import BaseConf, FusionSolarKioskMetric
from modules.write_influxdb import WriteInfluxDb
from modules.write_pvoutput import WritePvOutput
from modules.fetch_fusionsolar_kiosk import FetchFusionSolarKiosk
from modules.write_mqtt import WriteMqtt
from modules.models import *

class RelayFusionSolar:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("RelayFusionSolar class instantiated")

        self.fs_kiosk = FetchFusionSolarKiosk(conf, logger)
        self.pvoutput = WritePvOutput(conf, logger)
        self.mqtt = WriteMqtt(conf, logger)

        self.influxdb = WriteInfluxDb(self.conf, self.logger)
        self.influxdb_initialized = False

        self.logger.info("Starting RelayFusionSolar on separate thread")
        self.logger.debug("RelayFusionSolar waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.debug_mode:
            self.logger.info("Starting process_fusionsolar_request() at init, before waiting for cron, because we're in debug mode")
            self.process_fusionsolar_request()

        sched = BlockingScheduler(standalone = True)
        sched.add_job(self.process_fusionsolar_request, trigger='cron', hour=self.conf.fusionsolar_kiosk_fetch_cron_hour, minute=self.conf.fusionsolar_kiosk_fetch_cron_minute)
        sched.start()

    def process_fusionsolar_request(self):
        try:
            for fs_conf in self.conf.fusionsolar_kiosks:
                if fs_conf.enabled:
                    inverter_data = self.fs_kiosk.fetch_fusionsolar_status(fs_conf)
                    self.write_pvdata_to_influxdb(inverter_data)
                    self.write_pvdata_to_pvoutput(inverter_data, fs_conf)
                    self.publish_pvdata_to_mqtt(inverter_data)
        except Exception as e:
            self.logger.exception("Uncaught exception in FusionSolar data processing loop.", e)

        self.logger.debug("Waiting for next FusionSolar interval...")

    def write_pvdata_to_pvoutput(self, inverter_data: FusionSolarInverterKpi, fs_conf: FusionSolarKioskMetric):
        if self.conf.pvoutput_module_enabled and fs_conf.output_pvoutput:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(inverter_data, fs_conf)
            except:
                self.logger.exception("Error writing PV data to PVOutput.org")

    def publish_pvdata_to_mqtt(self, inverter_data: FusionSolarInverterKpi):
        if self.conf.mqtt_module_enabled:
            try:
                self.mqtt.publish_pvdata_to_mqtt(inverter_data)
            except:
                self.logger.exception("Error publishing PV data to MQTT")
        else:
            self.logger.debug("MQTT PV data publishing disabled")


    def write_pvdata_to_influxdb(self, inverter_data: FusionSolarInverterKpi):
        if self.conf.influxdb_module_enabled:
            if self.influxdb_initialized == False:
                self.influxdb_initialized = self.influxdb.initialize()

            if self.influxdb_initialized:
                self.influxdb.write_pvdata_to_influxdb(inverter_data)
        else:
            self.logger.debug("Writing PV data to InfluxDB skipped, InfluxDB module disabled.")


