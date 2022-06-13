import time

from pvinflux import PvInflux
from pvoutputorg import PvOutputOrg
from pvfusionsolar import PvFusionSolar
from pvmqtt import PvMqtt


class PvRelay:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger

        self.pvfusionsolar = PvFusionSolar(conf, logger)
        self.pvoutput = PvOutputOrg(conf, logger)
        self.pvmqtt = PvMqtt(conf, logger)

        self.pvinflux = PvInflux(self.conf, self.logger)
        self.pvinflux_initialized = False

        self.logger.debug("PvRelay class instantiated")

    def main(self):
        #Give "docker-compose up" some time to initialize InfluxDB
        time.sleep(5)

        while 1:
            try:
                fusionsolar_json_data = self.pvfusionsolar.fetch_fusionsolar_status()
                self.write_to_influxdb(fusionsolar_json_data)
                self.write_to_pvoutput(fusionsolar_json_data)
                self.publish_to_mqtt(fusionsolar_json_data)
            except:
                self.logger.exception(
                    "Uncaught exception in FusionSolar data processing loop."
                )

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.fusioninterval)

    def write_to_pvoutput(self, fusionsolar_json_data):
        if self.conf.pvoutput:
            try:
                self.pvoutput.write_to_pvoutput(fusionsolar_json_data)
            except:
                self.logger.exception("Error writing to PVOutput.org")

    def publish_to_mqtt(self, fusionsolar_json_data):
        if self.conf.mqtt:
            try:
                self.pvmqtt.publish_to_mqtt(fusionsolar_json_data)
            except:
                self.logger.exception("Error publishing to MQTT")
        else:
            self.logger.debug("MQTT Publishing disabled")


    def write_to_influxdb(self, response_json_data):
        if self.conf.influx:
            if self.pvinflux_initialized == False:
                self.pvinflux_initialized = self.pvinflux.initialize()

            if self.pvinflux_initialized:
                self.pvinflux.pvinflux_write(response_json_data)
        else:
            self.logger.debug("Writing data to Influx skipped, not initialized yet.")


