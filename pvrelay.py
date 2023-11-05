import time
from apscheduler.schedulers.blocking import BlockingScheduler
from pvconf import PvConf
from pvinflux import PvInflux
from pvoutputorg import PvOutputOrg
from pvfusionsolar import PvFusionSolar
from pvmqtt import PvMqtt



class PvRelay:
    def __init__(self, conf: PvConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvRelay class instantiated")

        self.pvfusionsolar = PvFusionSolar(conf, logger)
        self.pvoutput = PvOutputOrg(conf, logger)
        self.pvmqtt = PvMqtt(conf, logger)

        self.pvinflux = PvInflux(self.conf, self.logger)
        self.pvinflux_initialized = False

        self.logger.info("Starting PvRelay on separate thread")
        self.logger.debug("PvRelay waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        if self.conf.debug:
            self.logger.info("Starting process_fusionsolar_request() at init, before waiting for cron, because we're in debug mode")
            self.process_fusionsolar_request()

        sched = BlockingScheduler(standalone = True)
        sched.add_job(self.process_fusionsolar_request, trigger='cron', hour=self.conf.fusionhourcron, minute=self.conf.fusionminutecron)
        sched.start()

    def process_fusionsolar_request(self):
        try:
            fusionsolar_json_data = self.pvfusionsolar.fetch_fusionsolar_status()
            self.write_pvdata_to_influxdb(fusionsolar_json_data)
            self.write_pvdata_to_pvoutput(fusionsolar_json_data)
            self.publish_pvdata_to_mqtt(fusionsolar_json_data)
        except:
            self.logger.exception(
                "Uncaught exception in FusionSolar data processing loop."
            )

        self.logger.debug("Waiting for next FusionSolar interval...")

    def write_pvdata_to_pvoutput(self, fusionsolar_json_data):
        if self.conf.pvoutput:
            try:
                self.pvoutput.write_pvdata_to_pvoutput(fusionsolar_json_data)
            except:
                self.logger.exception("Error writing PV data to PVOutput.org")

    def publish_pvdata_to_mqtt(self, fusionsolar_json_data):
        if self.conf.mqtt:
            try:
                self.pvmqtt.publish_pvdata_to_mqtt(fusionsolar_json_data)
            except:
                self.logger.exception("Error publishing PV data to MQTT")
        else:
            self.logger.debug("MQTT PV data publishing disabled")


    def write_pvdata_to_influxdb(self, response_json_data):
        if self.conf.influx:
            if self.pvinflux_initialized == False:
                self.pvinflux_initialized = self.pvinflux.initialize()

            if self.pvinflux_initialized:
                self.pvinflux.pvinflux_write_pvdata(response_json_data)
        else:
            self.logger.debug("Writing PV data to InfluxDB skipped, InfluxDB client was not initialized yet.")


