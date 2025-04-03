import time
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.conf_models import BaseConf
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
            fusionsolar_json_data = self.fs_kiosk.fetch_fusionsolar_status()
            self.write_pvdata_to_influxdb(fusionsolar_json_data)
            self.write_pvdata_to_pvoutput(fusionsolar_json_data)
            self.publish_pvdata_to_mqtt(fusionsolar_json_data)
        except:
            self.logger.exception("Uncaught exception in FusionSolar data processing loop.")

        self.logger.debug("Waiting for next FusionSolar interval...")

    def write_pvdata_to_pvoutput(self, fusionsolar_json_data: FusionSolarInverterKpi):
        if self.conf.pvoutput_enabled:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(fusionsolar_json_data)
            except:
                self.logger.exception("Error writing PV data to PVOutput.org")

    def publish_pvdata_to_mqtt(self, fusionsolar_json_data: FusionSolarInverterKpi):
        if self.conf.mqtt_enabled:
            try:
                self.mqtt.publish_pvdata_to_mqtt(fusionsolar_json_data)
            except:
                self.logger.exception("Error publishing PV data to MQTT")
        else:
            self.logger.debug("MQTT PV data publishing disabled")


    def write_pvdata_to_influxdb(self, inverter_data: FusionSolarInverterKpi):
        if self.conf.influxdb_enabled:
            if self.influxdb_initialized == False:
                self.influxdb_initialized = self.influxdb.initialize()

            if self.influxdb_initialized:
                self.influxdb.pvinflux_write_pvdata(inverter_data)
        else:
            self.logger.debug("Writing PV data to InfluxDB skipped, InfluxDB client was not initialized yet.")


