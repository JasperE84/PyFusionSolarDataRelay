from datetime import datetime
import time
import requests
import json
import html

from pvinflux import PvInflux
from pvoutputorg import PvOutputOrg

class PvRelay:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger
        
        self.pvoutput = PvOutputOrg(conf, logger)     
        
        self.pvinflux = PvInflux(self.conf, self.logger)
        self.pvinflux_initialized = False

        self.logger.debug("PvRelay class instantiated")

    def main(self):
        while 1:
            try:
                fusionsolar_json_data = self.fetch_fusionsolar_status()
                self.write_to_influxdb(fusionsolar_json_data)
                self.write_to_pvoutput(fusionsolar_json_data)
            except:
                self.logger.exception("Uncaught exception in FusionSolar data processing loop.")

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.fusioninterval)

    def write_to_pvoutput(self, fusionsolar_json_data):
        if self.conf.pvoutput:
            try:
                self.pvoutput.write_to_pvoutput(fusionsolar_json_data)
            except:
                self.logger.exception("Error writing to PVOutput.org")

    def write_to_influxdb(self, response_json_data):
        if self.conf.influx:

            if self.pvinflux_initialized == False:
                self.pvinflux_initialized = self.pvinflux.initialize()

            if self.pvinflux_initialized:
                ifjson = self.make_influx_jsonrecord(response_json_data)
                self.logger.info("Writing InfluxDB json record: {}".format(str(ifjson)))
                try:
                    if self.conf.influx2:
                        self.logger.debug("Writing to InfluxDB v2...")
                        self.pvinflux.ifwrite_api.write(
                            bucket=self.conf.if2bucket,
                            org=self.conf.if2org,
                            record=ifjson,
                            write_precision="s",
                        )
                    else:
                        self.logger.debug("Writing to InfluxDB v1...")
                        self.conf.influxclient.write_points(ifjson, time_precision="s")
                except Exception as e:
                    self.logger.exception("InfluxDB write error: '{}'".format(str(e)))
        else:
            self.logger.debug("Writing data to Influx skipped, not initialized yet.")

    def make_influx_jsonrecord(self, response_json_data):
        ifobj = {
            "measurement": self.conf.pvsysname,
            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fields": {},
        }

        # floatKey element existence already verified and converted to Watts in fetch_fusionsolar_status()
        floatKeys = {"realTimePower", "cumulativeEnergy"}
        for floatKey in floatKeys:
            ifobj["fields"][floatKey] = response_json_data["realKpi"][floatKey]

        ifjson = [ifobj]
        return ifjson

    def fetch_fusionsolar_status(self):
        self.logger.info("Requesting data from FusionSolar Kiosk API...")

        try:
            response = requests.get(
                f"{self.conf.fusionsolarurl}{self.conf.fusionsolarkkid}"
            )
        except Exception as e:
            raise Exception("Error fetching data from FusionSolar Kiosk API: '{}'".format(str(e)))

        try:
            response_json = response.json()
        except Exception as e:
            raise Exception("Error while parsing JSON response from Kiosk API: '{}'".format(str(e)))

        if not "data" in response_json:
            raise Exception(
                f"FusionSolar Kiosk API response does not contain data key. Response: {response_json}"
            )

        try:
            response_json_data_decoded = html.unescape(response_json["data"])
            response_json_data = json.loads(response_json_data_decoded)
        except Exception as e:
            raise Exception("Error while parsing JSON response data element from FusionSolar Kiosk API: '{}'".format(str(e)))

        if not "realKpi" in response_json_data_decoded:
            raise Exception("Element realKpi is missing in FusionSolar Kiosk API response data")

        # Checking required realKpi elements and transforming kW(h) to W(h)
        floatKeys = {"realTimePower", "cumulativeEnergy"}
        for floatKey in floatKeys:
            if floatKey in response_json_data["realKpi"]:
                response_json_data["realKpi"][floatKey] = float(
                    response_json_data["realKpi"][floatKey]
                ) * float(1000)
            else:
                raise Exception(f"FusionSolar API data realKpi response element does cot contain key {floatKey}.")

        self.logger.debug(f'FusionSolar API data: {response_json_data["realKpi"]}')

        return response_json_data
