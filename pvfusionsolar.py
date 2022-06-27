import requests
import json
import html
from pvconf import PvConf

class PvFusionSolar:

    def __init__(self, conf: PvConf, logger):
        self.conf = conf
        self.logger = logger
        self.lastCumulativeEnergy = 0
        self.logger.debug("PvFusionSolar class instantiated")


    def fetch_fusionsolar_status(self):
        self.logger.info("Requesting data from FusionSolar Kiosk API...")

        try:
            response = requests.get(
                f"{self.conf.fusionsolarurl}{self.conf.fusionsolarkkid}",
                verify=False
            )
        except Exception as e:
            raise Exception(
                "Error fetching data from FusionSolar Kiosk API: '{}'".format(str(e))
            )

        try:
            response_json = response.json()
        except Exception as e:
            raise Exception(
                "Error while parsing JSON response from Kiosk API: '{}'".format(str(e))
            )

        if not "data" in response_json:
            raise Exception(
                f"FusionSolar Kiosk API response does not contain data key. Response: {response_json}"
            )

        try:
            response_json_data_decoded = html.unescape(response_json["data"])
            response_json_data = json.loads(response_json_data_decoded)
        except Exception as e:
            raise Exception(
                "Error while parsing JSON response data element from FusionSolar Kiosk API: '{}'".format(
                    str(e)
                )
            )

        # Checking required realKpi elements and transforming kW(h) to W(h)
        if not "realKpi" in response_json_data_decoded:
            raise Exception(
                "Element realKpi is missing in FusionSolar Kiosk API response data"
            )
        
        floatKeys = {"realTimePower", "cumulativeEnergy", "monthEnergy", "dailyEnergy", "yearEnergy"}
        for floatKey in floatKeys:
            if floatKey in response_json_data["realKpi"]:
                response_json_data["realKpi"][floatKey] = float(
                    response_json_data["realKpi"][floatKey]
                ) * float(1000)

            # Set this to fix fusionsolar quirk at midnight where cumulativeEnergy will decrease with the days amount of solar production
            if floatKey == "cumulativeEnergy":
                if self.lastCumulativeEnergy == 0:
                    self.lastCumulativeEnergy = response_json_data["realKpi"][floatKey]
                elif response_json_data["realKpi"][floatKey] < self.lastCumulativeEnergy:
                    response_json_data["realKpi"][floatKey] = self.lastCumulativeEnergy

            else:
                raise Exception(
                    f"FusionSolar API data realKpi response element does cot contain key {floatKey}."
                )

        # Checking required powerCurve elements and transforming kW(h) to W(h)
        if not "powerCurve" in response_json_data_decoded:
            raise Exception(
                "Element powerCurve is missing in FusionSolar Kiosk API response data"
            )

        floatKeys = {"currentPower"}
        for floatKey in floatKeys:
            if floatKey in response_json_data["powerCurve"]:
                response_json_data["powerCurve"][floatKey] = float(
                    response_json_data["powerCurve"][floatKey]
                ) * float(1000)
            else:
                raise Exception(
                    f"FusionSolar API data powerCurve response element does cot contain key {floatKey}."
                )

        #test = {}
        #for idx, x in enumerate(response_json_data["powerCurve"]["xAxis"]):
        #    test[idx] = x
        #self.logger.info(str(test))

        self.logger.debug(f'FusionSolar API data: {response_json_data["realKpi"]}')

        return response_json_data