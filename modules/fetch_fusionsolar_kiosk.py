import requests
import json
import html
from modules.conf_models import BaseConf, FusionSolarKioskSettings
from modules.models import *


class FetchFusionSolarKiosk:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("FetchFusionSolarKiosk class instantiated")

    def fetch_fusionsolar_status(self, kiosk_settings: FusionSolarKioskSettings) -> FusionSolarInverterMeasurement:
        self.logger.info(f"Requesting data for {kiosk_settings.descriptive_name} kkid={kiosk_settings.api_kkid} from FetchFusionSolarKiosk API...")

        # Fetch the data.
        try:
            response = requests.get(
                f"{kiosk_settings.api_url}{kiosk_settings.api_kkid}",
                verify=False,
            )
            response.raise_for_status()
        except Exception as e:
            raise Exception("Error in FetchFusionSolarKiosk API HTTP request. Error info: {e}")

        # Attempt to parse the top-level JSON.
        try:
            response_json = response.json()
        except Exception as e:
            content = response.content.decode("utf-8") or ""
            raise Exception(f"Error parsing JSON from FetchFusionSolarKiosk APIresponse. Check the API url and KKID value. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

        # The top-level JSON should contain a "data" key with encoded JSON.
        if "data" not in response_json:
            raise Exception(f"FetchFusionSolarKiosk API response invalid, does not contain 'data' key.")

        # Decode the embedded JSON in response_json["data"].
        try:
            response_json_data_decoded = html.unescape(response_json["data"])
            response_json_data = json.loads(response_json_data_decoded)
        except Exception as e:
            raise Exception(f"Could not parse JSON 'data' element in FusionSolarKiosk API response. Error info: {e}\n" f"First 200 chars of response for diagnosis: {response_json_data_decoded[:200].replace(chr(10), ' ')}")

        # Verify the "realKpi" key is present before accessing it.
        if "realKpi" not in response_json_data:
            raise Exception("Key 'realKpi' is missing in the FusionSolarKiosk API response data element.")

        # Extract KPI values and convert kW to W (multiplying by 1000).
        try:
            real_time_power_w = float(response_json_data["realKpi"]["realTimePower"]) * 1000
            lifetime_energy_wh = float(response_json_data["realKpi"]["cumulativeEnergy"]) * 1000
            daily_energy_wh = float(response_json_data["realKpi"]["dailyEnergy"]) * 1000
        except KeyError as missing_key:
            raise Exception(f"Key '{missing_key}' is missing from the 'realKpi' section of the FusionSolarKiosk API response.")
        except ValueError as e:
            raise Exception(f"Failed to convert FusionSolarKiosk realKpi values to float: {e}")

        # Extract station information.
        try:
            station_name = response_json_data["stationOverview"]["stationName"]
            station_dn = response_json_data["stationOverview"]["stationDn"]
        except KeyError as missing_key:
            raise Exception(f"The key '{missing_key}' is missing from the 'stationOverview' section of the FusionSolarKiosk API response.")

        self.logger.debug(
            f"FusionSolarKiosk metrics after transformations for {kiosk_settings.descriptive_name} / {station_name} / {station_dn}: " f"realTimePowerW={real_time_power_w}, " f"cumulativeEnergyWh={lifetime_energy_wh}, " f"dailyEnergyWh={daily_energy_wh}, "
        )

        # Populate and return the inverter kpi object without altering the original response dictionary.
        inverter_kpi = FusionSolarInverterMeasurement(
            settings=kiosk_settings,
            measurement_type="station",
            data_source="kiosk",
            station_name=station_name,
            station_dn=station_dn,
            real_time_power_w=real_time_power_w,
            lifetime_energy_wh=lifetime_energy_wh,
            day_energy_wh=daily_energy_wh,
        )

        return inverter_kpi
