import requests
import json
import html
from pvconfmodels import BaseConf

class PvFusionSolar:

    def __init__(
            self, 
            conf: BaseConf, 
            logger
    ):
        self.conf = conf
        self.logger = logger
        self.lastCumulativeEnergy = 0
        self.logger.debug("PvFusionSolar class instantiated")


    def fetch_fusionsolar_status(self):
        self.logger.info("Requesting data from FusionSolar Kiosk API...")

        try:
            response = requests.get(
                f"{self.conf.fusionsolar_kiosk_api_url}{self.conf.fusionsolar_kiosk_api_kkid}",
                verify=False
            )
        except Exception as e:
            raise Exception(
                "Error fetching data from FusionSolar Kiosk API: '{}'".format(
                    str(e).replace('\n', '')
                )
            )

        try:
            response_json = response.json()
        except Exception as e:
            content = response.content.decode("utf-8")
            if content:
                content_first_100 = content[:200]
            else:
                content_first_100 = ""
                
            raise Exception(
                "Error while decoding the JSON Kiosk API response, did you set the right fusionsolarurl and fusionsolarkkid in your conf? Kiosk link still working?: '{}', raw JSON content: '{}'".format(
                    str(e).replace('\n', ''),
                    content_first_100.replace('\n', '')
                )
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
                "Error while parsing JSON response data element from FusionSolar Kiosk API: '{}' Data element content from FusionSolar API: {}".format(
                    str(e).replace('\n', ''),
                    response_json["data"]
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
                    if self.lastCumulativeEnergy != 0 and response_json_data["realKpi"][floatKey] < self.lastCumulativeEnergy:
                        response_json_data["realKpi"][floatKey] = self.lastCumulativeEnergy
                    else:
                        self.lastCumulativeEnergy = response_json_data["realKpi"][floatKey]

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