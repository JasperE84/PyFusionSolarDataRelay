import json
import os
import logging
import time
from typing import Any, Dict, Optional
import requests
from modules.decorators import rate_limit
from modules.conf_models import BaseConf, FusionSolarOpenApiInverterSettings
from modules.models import *

DEVICE_CACHE_FILE_PATH = "cache/fusion_solar_openapi_devices.json"
STATION_CACHE_FILE_PATH = "cache/fusion_solar_openapi_stations.json"
CACHE_EXPIRATION_SECONDS = 24 * 3600  # 24 hours in seconds


class FetchFusionSolarOpenApi:
    def __init__(self, conf: BaseConf, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.jwt_token = ""
        self.station_list = []
        self.device_list = []
        self.logger.debug("FetchFusionSolarOpenApi class instantiated")

    def update_station_list(self, force_api_update: bool = False) -> None:
        """
        Fetch, cache, and store the list of stations from the FusionSolar OpenAPI.
        If a previous cache file exists and is younger than 24 hours, it will be used
        unless force_api_update is True. Otherwise, the API is called, and the response
        is written to the cache file.

        :param force_api_update: If True, always ignore the cache and call the FusionSolar OpenAPI.
        """
        # According to your requirement, /thirdData/getStationList does NOT need a request body.
        response = self._fetch_and_cache_fusionsolar_data(force_api_update=force_api_update, endpoint="/thirdData/getStationList", request_data=None, cache_file_path=STATION_CACHE_FILE_PATH)
        self.station_list = response.get("data", [])

        self.logger.info("Current FusionSolar OpenAPI stations:")
        for station in self.station_list:
            self.logger.info(
                f"stationName: {station.get('stationName','')}, stationCode: {station.get('stationCode','')}, capacity: {station.get('capacity','')}MW, stationAddr: {station.get('stationAddr','')}, stationLinkman: {station.get('stationLinkman','')}"
            )

    def update_device_list(self, force_api_update: bool = False) -> None:
        """
        Fetch, cache, and store the list of devices from the FusionSolar OpenAPI.
        If a previously cached file exists and is younger than 24 hours, it will be used
        unless force_api_update is True. Otherwise, the API is called, and the response
        is written to the cache file.

        :param force_api_update: If True, always ignore the cache and call the FusionSolar OpenAPI.
        """
        # The /thirdData/getDevList endpoint expects station codes in the POST body according to your snippet.
        if not self.station_list:
            self.update_station_list()

        stations_str = ",".join(item["stationCode"] for item in self.station_list if "stationCode" in item)
        data = {"stationCodes": stations_str}

        response = self._fetch_and_cache_fusionsolar_data(force_api_update=force_api_update, endpoint="/thirdData/getDevList", request_data=data, cache_file_path=DEVICE_CACHE_FILE_PATH)
        self.device_list = response.get("data", [])

        self.logger.info("Current FusionSolar OpenAPI devices:")
        for device in self.device_list:
            self.logger.info(
                f"devDn: {device.get('devDn','')}, devName: {device.get('devName','')}, id: {device.get('id','')}, stationCode: {device.get('stationCode','')}, devTypeId: {device.get('devTypeId','')}, model: {device.get('model','')}"
            )

    @rate_limit(max_calls=1, period=60)
    def fetch_fusionsolar_inverter_device_kpis(self) -> List[FusionSolarInverterMeasurement]:
        """
        Retrieve real-time KPIs from the FusionSolar OpenAPI.
        Uses rate limiting to avoid frequent calls.

        :return: A list of FusionSolarInverterKpi objects containing inverter metrics.
        """
        self.logger.info(f"Requesting inverter realtimeKpi's from FusionSolarOpenAPI.")

        # Ensure the device list is populated
        if not self.device_list:
            self.update_device_list()

        url = f"{self.conf.fusionsolar_open_api_url}/thirdData/getDevRealKpi"
        devices_str = ",".join(str(item["id"]) for item in self.device_list if "id" in item and "devTypeId" in item and item["devTypeId"] == 1)
        data = {"devTypeId": 1, "devIds": devices_str}

        response_json = self._fetch_fusionsolar_data_request(url, data)
        api_measurement_list = response_json.get("data", [])

        inverter_measurements = []
        for api_measurement in api_measurement_list:
            try:
                real_time_power_w = float(api_measurement["dataItemMap"]["active_power"]) * 1000
                lifetime_energy_wh = float(api_measurement["dataItemMap"]["total_cap"]) * 1000
                daily_energy_wh = float(api_measurement["dataItemMap"]["day_cap"]) * 1000
            except KeyError as missing_key:
                self.logger.error(f"Key '{missing_key}' is missing from FusionSolarOpenAPI inverter measurement. Skipping this device.")
                continue
            except ValueError as val_err:
                self.logger.error(f"Failed to convert FusionSolarOpenAPI inverter measurement record to float, out of bounds? Skipping this device. {val_err}")
                continue
            except TypeError as typ_err:
                self.logger.warning(f"Failed to parse FusionSolarOpenAPI grid meter measurements, value None? This happens if a device is inactive or disabled. Skipping this device. {typ_err}")
                continue

            self.logger.debug(f"Metrics for {""} after transformations: " f"realTimePowerW={real_time_power_w}, " f"lifetimeEnergyWh={lifetime_energy_wh}, " f"dailyEnergyWh={daily_energy_wh}")

            matching_device = next((dev for dev in self.device_list if dev.get("id") == api_measurement["devId"]), None)
            matching_station = next((stat for stat in self.station_list if stat.get("stationCode") == matching_device["stationCode"]), None)
            matching_conf = next((inv for inv in self.conf.fusionsolar_open_api_inverters if inv.dev_id == str(api_measurement["devId"])), None)

            station_dn = matching_device.get("stationCode", "")
            station_name = matching_station.get("stationName", "")
            device_id = str(api_measurement.get("devId", ""))

            device_dn = matching_device.get("devDn", "")
            device_name = matching_device.get("devName", "")
            device_model = matching_device.get("model", "")

            # Populate the inverter KPI model without altering the original response.
            api_measurement = FusionSolarInverterMeasurement(
                settings=matching_conf,
                measurement_type="inverter",
                data_source="openapi_realkpi",
                station_name=station_name,
                station_dn=station_dn,
                device_dn=device_dn,
                device_name=device_name,
                device_model=device_model,
                device_id=device_id,
                real_time_power_w=real_time_power_w,
                lifetime_energy_wh=lifetime_energy_wh,
                day_energy_wh=daily_energy_wh,
            )

            inverter_measurements.append(api_measurement)

        return inverter_measurements

    @rate_limit(max_calls=1, period=60)
    def fetch_fusionsolar_grid_meter_device_kpis(self) -> List[FusionSolarMeterMeasurement]:
        """
        Retrieve real-time KPIs from the FusionSolar OpenAPI.
        Uses rate limiting to avoid frequent calls.

        :return: A list of FusionSolarMeterKpi objects containing inverter metrics.
        """
        self.logger.info(f"Requesting inverter realtimeKpi's from FusionSolarOpenAPI.")

        # Ensure the device list is populated
        if not self.device_list:
            self.update_device_list()

        url = f"{self.conf.fusionsolar_open_api_url}/thirdData/getDevRealKpi"
        devices_str = ",".join(str(item["id"]) for item in self.device_list if "id" in item and "devTypeId" in item and item["devTypeId"] == 17)
        data = {"devTypeId": 17, "devIds": devices_str}

        response_json = self._fetch_fusionsolar_data_request(url, data)
        api_measurement_list = response_json.get("data", [])

        inverter_measurements = []
        for api_measurement in api_measurement_list:
            try:
                active_power_w = float(api_measurement["dataItemMap"]["active_power"]) * 1000

                # fix for fusionsolar openapi quirk
                # active_power_w = 0 if int(active_power_w) == -65230000000 else active_power_w

            except KeyError as missing_key:
                self.logger.error(f"Key '{missing_key}' is missing from FusionSolarOpenAPI grid meter measurement. Skipping this device.")
                continue
            except ValueError as val_err:
                self.logger.error(f"Failed to convert FusionSolarOpenAPI grid meter measurement record to float, out of bounds? Skipping this device. {val_err}")
                continue
            except TypeError as typ_err:
                self.logger.warning(f"Failed to parse FusionSolarOpenAPI grid meter measurements, value None? This happens if a device is inactive or disabled. Skipping this device. {typ_err}")
                continue

            self.logger.debug(f"Metrics after transformations: realTimePowerW={active_power_w}")

            matching_device = next((dev for dev in self.device_list if dev.get("id") == api_measurement["devId"]), None)
            matching_station = next((stat for stat in self.station_list if stat.get("stationCode") == matching_device["stationCode"]), None)
            matching_conf = next((inv for inv in self.conf.fusionsolar_open_api_meters if inv.dev_id == str(api_measurement["devId"])), None)

            station_dn = matching_device.get("stationCode", "")
            station_name = matching_station.get("stationName", "")
            device_id = str(api_measurement.get("devId", ""))

            device_dn = matching_device.get("devDn", "")
            device_name = matching_device.get("devName", "")
            device_model = matching_device.get("model", "")

            # Populate the inverter KPI model without altering the original response.
            api_measurement = FusionSolarMeterMeasurement(
                settings=matching_conf,
                measurement_type="grid_meter",
                data_source="openapi_realkpi",
                station_name=station_name,
                station_dn=station_dn,
                device_dn=device_dn,
                device_name=device_name,
                device_model=device_model,
                device_id=device_id,
                active_power_w=active_power_w,
            )

            inverter_measurements.append(api_measurement)

        return inverter_measurements

    def _fetch_and_cache_fusionsolar_data(self, force_api_update: bool, endpoint: str, request_data: Optional[Dict[str, Any]], cache_file_path: str) -> Dict[str, Any]:
        """
        Shared method to handle FusionSolar data fetching and caching.

        :param force_api_update: If True, always ignore cache and fetch fresh data.
        :param endpoint: URL path (suffix) for the FusionSolar OpenAPI.
        :param request_data: Data to be sent in the POST request body.
        :param cache_file_path: File path to store/read the response cache.
        :return: The JSON response with the "data" field containing the relevant list.
        """
        self.logger.info(f"Updating data from FusionSolar API with endpoint: {endpoint}, cache path: {cache_file_path}")

        # 1. Check for an existing cache file if we're not forcing an update.
        if not force_api_update and os.path.isfile(cache_file_path):
            try:
                with open(cache_file_path, "r", encoding="utf-8") as cache_file:
                    cache_content = json.load(cache_file)

                cached_timestamp = cache_content.get("timestamp")
                cached_response = cache_content.get("api_response", {})
                cached_data = cached_response.get("data", [])

                # Ensure the cached data is present and not expired (> 24 hours old).
                if cached_timestamp and isinstance(cached_data, list):
                    age_in_seconds = time.time() - cached_timestamp
                    if age_in_seconds < CACHE_EXPIRATION_SECONDS:
                        # Cache is valid, so return from cache
                        self.logger.info(f"Loaded data from cache (last updated {round(age_in_seconds)} seconds ago). " f"Number of items: {len(cached_data)}")
                        return cached_response
                    else:
                        self.logger.info("Cache file found, but it's older than 24 hours. " "Will fetch new data from API.")
                else:
                    self.logger.warning("Cache file does not contain valid format or data. " "Will fetch new data from API.")
            except (json.JSONDecodeError, OSError) as exc:
                self.logger.warning(f"Failed to parse or read cache file properly: {exc}. " "Will fetch new data from API.")

        # 2. If cache is invalid, expired, or force_api_update is True, call the API.
        self.logger.info("Fetching data from FusionSolar OpenAPI...")
        url = f"{self.conf.fusionsolar_open_api_url}{endpoint}"

        try:
            response_json = self._fetch_fusionsolar_data_request(url, request_data)
        except Exception as exc:
            raise Exception(f"Error fetching data from FusionSolar OpenAPI. Info: {exc}")

        # 3. Write the updated response to the cache file with a timestamp.
        try:
            cache_content = {"timestamp": time.time(), "api_response": response_json}
            with open(cache_file_path, "w", encoding="utf-8") as cache_file:
                json.dump(cache_content, cache_file, ensure_ascii=False, indent=2)

            self.logger.info(f"Data fetched from API and cached. Number of items: {len(response_json.get('data', []))}")
        except OSError as exc:
            self.logger.error(f"Failed to write data to cache file: {exc}")

        return response_json

    def _fetch_fusionsolar_data_request(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a POST request to the given URL with the provided data and raise
        an exception for any issues.

        :param url: The FusionSolar OpenAPI endpoint.
        :param data: JSON payload for the request.
        :return: A dictionary representing the JSON response.
        """
        try:
            response = self._request_with_token_retry(url, method="POST", json=data)
            response.raise_for_status()
        except Exception as exc:
            raise Exception(f"Error in FusionSolarOpenAPI HTTP request. Error info: {exc}")

        try:
            response_json = response.json()
        except Exception as exc:
            content = response.content.decode("utf-8") or ""
            raise Exception(
                "Error parsing JSON from FusionSolarOpenAPI response. " f"Check the API URL. Error info: {exc}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}"
            )

        if "data" not in response_json:
            raise Exception("FusionSolarOpenAPI response invalid: Missing 'data' key.")

        return response_json

    def update_open_api_token(self) -> None:
        """
        Obtain or refresh the JWT token from the FusionSolar OpenAPI and store it
        for subsequent requests.
        """
        token_url = f"{self.conf.fusionsolar_open_api_url}/thirdData/login"
        headers = {"Content-Type": "application/json"}
        data = {"userName": self.conf.fusionsolar_open_api_user_name, "systemCode": self.conf.fusionsolar_open_api_system_code}

        try:
            self.logger.info(f"Requesting JWT authentication token from {token_url}")
            response = requests.post(token_url, json=data, headers=headers, verify=False)
            response.raise_for_status()

            # Attempt to parse the top-level JSON.
            try:
                response_json = response.json()
            except Exception as exc:
                content = response.content.decode("utf-8") or ""
                raise Exception("Error parsing JSON from FusionSolarOpenAPI token response. " f"Check the API URL. Error info: {exc}\n" f"First 200 chars: {content[:200].replace(chr(10), ' ')}")

            if "success" not in response_json:
                raise Exception("No 'success' property found in FusionSolarOpenAPI token response.")

            if not response_json.get("success", False):
                message = response_json.get("message", "Unknown error while fetching token")
                raise Exception(f"Authentication with FusionSolar OpenAPI failed. Error: {message}")

            # Capture the JWT token from the response cookies
            self.jwt_token = response.cookies.get("XSRF-TOKEN")
            if not self.jwt_token:
                raise Exception("Failed to retrieve XSRF-TOKEN from the response cookies.")

        except Exception as exc:
            err_msg = f"Could not retrieve valid FusionSolar OpenAPI JWT auth token: {exc}"
            self.logger.error(err_msg)
            raise Exception(err_msg)

    def _request_with_token_retry(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """
        Generic request method that includes the JWT token in the headers.
        Retries once if the token is expired and needs refreshing.

        :param url: The target URL for the request.
        :param method: HTTP method (GET, POST, etc.)
        :param kwargs: Additional parameters for requests.request (e.g., json=payload).
        :return: A requests.Response object.
        """
        headers = kwargs.pop("headers", {})
        headers["XSRF-TOKEN"] = self.jwt_token
        headers.setdefault("Content-Type", "application/json")

        for attempt in range(2):
            self.logger.debug(f"Fetching URL: {url} (attempt {attempt + 1})")
            response = requests.request(method.upper(), url, headers=headers, verify=False, **kwargs)
            response.raise_for_status()

            # Check JSON content for success status
            try:
                response_json = response.json()
            except Exception as exc:
                content = response.content.decode("utf-8") or ""
                raise Exception(f"Failed to parse JSON from FusionSolarOpenAPI. Error info: {exc}\n" f"First 200 chars of response: {content[:200].replace(chr(10), ' ')}")

            # If no "success" property is found, something is wrong
            if "success" not in response_json:
                raise Exception(f"No 'success' property found in FusionSolarOpenAPI response.")

            # If there's a failCode and it's 305 -> token needs refresh
            if "failCode" in response_json:
                if (not response_json.get("success")) and response_json["failCode"] == 305:
                    self.logger.debug("FusionSolar: JWT token expired or invalid. Refreshing token...")
                    self.update_open_api_token()
                    headers["XSRF-TOKEN"] = self.jwt_token
                elif not response_json.get("success"):
                    fail_code = response_json.get("failCode", "Unknown")
                    message = response_json.get("message", "No message provided")
                    if fail_code == 407:
                        message = f"API RATE_LIMIT_EXCEEDED - {message}"
                    raise Exception(f"FusionSolarOpenAPI request failed. failCode: {fail_code}, message: {message}")
                else:
                    # If success is True, no further retry needed
                    break
            else:
                # No failCode indicates request was likely successful
                break

        return response
