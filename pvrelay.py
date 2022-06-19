from threading import Thread
import time

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
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def start(self):
        self.logger.debug("PvRelay waiting 5sec to initialize docker-compose containers")
        time.sleep(5)

        while 1:
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
            time.sleep(self.conf.fusioninterval)

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


