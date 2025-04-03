import requests
import json
import html
from modules.conf_models import BaseConf
from modules.models import *


class FetchFusionSolarKiosk:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.lastCumulativeEnergy = 0
        self.logger.debug("FetchFusionSolarKiosk class instantiated")

    def fetch_fusionsolar_status(self) -> FusionSolarInverterKpi:
        self.logger.info("Requesting data from FetchFusionSolarKiosk API...")

        # Fetch the data.
        try:
            response = requests.get(
                f"{self.conf.fusionsolar_kiosk_api_url}{self.conf.fusionsolar_kiosk_api_kkid}",
                verify=False,
            )
        except Exception as e:
            raise Exception(
                "Error fetching data from FetchFusionSolarKiosk API: '{}'".format(
                    str(e).replace("\n", "")
                )
            )

        # Attempt to parse the top-level JSON.
        try:
            response_json = response.json()
        except Exception as e:
            content = response.content.decode("utf-8") or ""
            raise Exception(
                "Error while decoding JSON response from FetchFusionSolarKiosk API: '{}'. "
                "Partial response content: '{}'".format(
                    str(e).replace("\n", ""), content[:200].replace("\n", "")
                )
            )

        # The top-level JSON should contain a "data" key with encoded JSON.
        if "data" not in response_json:
            raise Exception(
                f"FetchFusionSolarKiosk API response does not contain 'data' key. Response: {response_json}"
            )

        # Decode the embedded JSON in response_json["data"].
        try:
            response_json_data_decoded = html.unescape(response_json["data"])
            response_json_data = json.loads(response_json_data_decoded)
        except Exception as e:
            raise Exception(
                "Error while parsing JSON from FusionSolar 'data' element: '{}'. "
                "Raw 'data' content: {}".format(
                    str(e).replace("\n", ""), response_json["data"]
                )
            )

        # Verify the "realKpi" key is present before accessing it.
        if "realKpi" not in response_json_data:
            raise Exception(
                "Key 'realKpi' is missing in the FusionSolar Kiosk API response data."
            )

        # Extract KPI values and convert kW to W (multiplying by 1000).
        try:
            real_time_power_w = (
                float(response_json_data["realKpi"]["realTimePower"]) * 1000
            )
            cumulative_energy_wh = (
                float(response_json_data["realKpi"]["cumulativeEnergy"]) * 1000
            )
            month_energy_wh = float(response_json_data["realKpi"]["monthEnergy"]) * 1000
            daily_energy_wh = float(response_json_data["realKpi"]["dailyEnergy"]) * 1000
            year_energy = float(response_json_data["realKpi"]["yearEnergy"]) * 1000
        except KeyError as missing_key:
            raise Exception(
                f"The key '{missing_key}' is missing from the 'realKpi' section of the response."
            )
        except ValueError as e:
            raise Exception(f"Failed to convert realKpi values to float: {e}")

        # Fix FusionSolar quirk at midnight (ensure cumulativeEnergy does not decrease).
        if (
            self.lastCumulativeEnergy != 0
            and cumulative_energy_wh < self.lastCumulativeEnergy
        ):
            cumulative_energy_wh = self.lastCumulativeEnergy
        else:
            self.lastCumulativeEnergy = cumulative_energy_wh

        # Extract station information.
        try:
            station_name = response_json_data["stationOverview"]["stationName"]
            station_dn = response_json_data["stationOverview"]["stationDn"]
        except KeyError as missing_key:
            raise Exception(
                f"The key '{missing_key}' is missing from the 'stationOverview' section of the response."
            )

        self.logger.debug(
            f"realKpi after transformations: "
            f"realTimePowerW={real_time_power_w}, "
            f"cumulativeEnergyWh={cumulative_energy_wh}, "
            f"monthEnergyWh={month_energy_wh}, "
            f"dailyEnergyWh={daily_energy_wh}, "
            f"yearEnergyWh={year_energy}"
        )

        # Populate and return the inverter kpi object without altering the original response dictionary.
        inverter_kpi = FusionSolarInverterKpi(
            stationName=station_name,
            stationDn=station_dn,
            dataSource="kiosk",
            realTimePowerW=real_time_power_w,
            cumulativeEnergyWh=cumulative_energy_wh,
            monthEnergyWh=month_energy_wh,
            dailyEnergyWh=daily_energy_wh,
            yearEnergyWh=year_energy,
        )

        return inverter_kpi