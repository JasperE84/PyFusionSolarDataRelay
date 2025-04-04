import logging
import requests
import json
import html
import time
from functools import wraps
from threading import Lock
from modules.conf_models import BaseConf, FusionSolarOpenApiInverter
from modules.models import *


class FetchFusionSolarOpenApi:
    def __init__(self, conf: BaseConf, logger: logging.Logger):
        self.conf = conf
        self.logger = logger
        self.lastCumulativeEnergy = 0
        self.jwt_token = ""
        self.logger.debug("FetchFusionSolarOpenApi class instantiated")

    def rate_limit(max_calls, period):
        def decorator(func):
            last_reset = [time.time()]  # Using a list to allow access to the nonlocal variable in closures
            call_count = [0]
            lock = Lock()

            @wraps(func)
            def wrapper(*args, **kwargs):
                with lock:
                    current_time = time.time()
                    # Reset the rate limit counter periodically
                    if current_time - last_reset[0] >= period:
                        last_reset[0] = current_time
                        call_count[0] = 0

                    if call_count[0] < max_calls:
                        call_count[0] += 1
                        return func(*args, **kwargs)
                    else:
                        time_to_wait = period - (current_time - last_reset[0])
                        print(f"Rate limit exceeded. Try again in {time_to_wait:.2f} seconds.")
                        time.sleep(time_to_wait)
                        return wrapper(*args, **kwargs)

            return wrapper

        return decorator

    def update_open_api_token(self):
        token_url = f"{self.conf.fusionsolar_open_api_endpoint}/thirdData/login"
        headers = {"Content-Type": "application/json"}
        data = {"userName": self.conf.fusionsolar_open_api_user_name, "systemCode": self.conf.fusionsolar_open_api_system_code}

        try:
            self.logger.info(f"Requesting JWT authentication token from {token_url}")
            response = requests.post(token_url, json=data, headers=headers, verify=False)
            response.raise_for_status()

            # Attempt to parse the top-level JSON.
            try:
                response_json = response.json()
            except Exception as e:
                content = response.content.decode("utf-8") or ""
                raise Exception(f"Error parsing JSON from FetchFusionSolarOpenApi APIresponse. Check the API url. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

            # Check for success key in response JSON data
            if not 'success' in response_json:
                raise Exception(f"No success property found in FetchFusionSolarOpenApi APIresponse. Check the API url. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

            auth_success = response_json.get("success")
            if not auth_success:
                raise Exception(f"Authentication with FusionSolar OpenApi failed. Error info: {token_response.get('message')}")
            self.jwt_token = response.cookies.get("XSRF-TOKEN")
        except Exception as e:
            err_msg = f"Could not retrieve valid FusionSolar OpenAPI JWT auth token: {e}"
            self.logger.error(err_msg)
            raise Exception(err_msg)

    def _request_with_token_retry(self, url, method="GET", **kwargs):
        # Ensure headers exist
        headers = kwargs.pop("headers", {})
        headers["XSRF-TOKEN"] = self.jwt_token
        headers.setdefault("Content-Type", "application/json")

        # Attempt the request up to two times (in case we need to refresh token).
        for attempt in range(2):
            self.logger.debug(f"Fetching URL: {url} (attempt {attempt + 1})")
            response = requests.request(method.upper(), url, headers=headers, verify=False, **kwargs)
            response.raise_for_status()

            # Attempt to parse the top-level JSON.
            try:
                response_json = response.json()
            except Exception as e:
                content = response.content.decode("utf-8") or ""
                raise Exception(f"Error parsing JSON from FetchFusionSolarOpenApi APIresponse. Check the API url. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

            # Check for success key in response JSON data
            if not 'success' in response_json:
                raise Exception(f"No success property found in FetchFusionSolarOpenApi APIresponse. Check the API url. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

            # If not success or second attempt, break
            if response_json.get("success") or attempt == 1:
                # If there's another error status, it will be caught below
                break

            # No success on first try? Then refresh token!
            self.logger.debug("FusionSolar: JWT token expired or not set, refreshing token and retrying request.")
            self.update_open_api_token()
            headers["XSRF-TOKEN"] = self.jwt_token

        return response

    @rate_limit(max_calls=1, period=10)
    def fetch_fusionsolar_status(self, fs_conf: FusionSolarOpenApiInverter) -> List[FusionSolarInverterKpi]:
        self.logger.info(f"Requesting data for {fs_conf.descriptive_name} dev_id={fs_conf.dev_id} from FetchFusionSolarOpenApi API...")

        data = {"devIds": fs_conf.dev_id, "devTypeId": fs_conf.dev_type_id}

        # Fetch the data.
        try:
            response = self._request_with_token_retry(f"{self.conf.fusionsolar_open_api_endpoint}/thirdData/getDevRealKpi", method="POST", json=data)
            response.raise_for_status()
        except Exception as e:
            raise Exception("Error in FetchFusionSolarOpenApi API HTTP request. Error info: {e}")

        # Attempt to parse the top-level JSON.
        try:
            response_json = response.json()
        except Exception as e:
            content = response.content.decode("utf-8") or ""
            raise Exception(f"Error parsing JSON from FetchFusionSolarOpenApi APIresponse. Check the API url and KKID value. Error info: {e}\n" f"First 200 chars of response for diagnosis: {content[:200].replace(chr(10), ' ')}")

        # The top-level JSON should contain a "data" key with encoded JSON.
        if "data" not in response_json:
            raise Exception(f"FetchFusionSolarOpenApi API response invalid, does not contain 'data' key.")
  
        inverter_kpis = []

        for dev_json in response_json["data"]:

            # Verify the "realKpi" key is present before accessing it.
            if "active_power" not in dev_json["dataItemMap"]:
                raise Exception("Key 'active_power' is missing in the FusionSolarOpenApi API response data element.")

            # Extract KPI values and convert kW to W (multiplying by 1000).
            try:
                real_time_power_w = float(dev_json["dataItemMap"]["active_power"]) * 1000
                cumulative_energy_wh = float(dev_json["dataItemMap"]["total_cap"]) * 1000
                daily_energy_wh = float(dev_json["dataItemMap"]["day_cap"]) * 1000
            except KeyError as missing_key:
                raise Exception(f"Key '{missing_key}' is missing from the 'data' section of the FusionSolarOpenApi API response.")
            except ValueError as e:
                raise Exception(f"Failed to convert FusionSolarOpenApi data values to float: {e}")


            self.logger.debug(
                f"FusionSolarOpenApi metrics after transformations for {fs_conf.descriptive_name}"
                f"realTimePowerW={real_time_power_w}, "
                f"cumulativeEnergyWh={cumulative_energy_wh}, "
                #f"monthEnergyWh={month_energy_wh}, "
                f"dailyEnergyWh={daily_energy_wh}, "
                #f"yearEnergyWh={year_energy}"
            )

            # Populate and return the inverter kpi object without altering the original response dictionary.
            inverter_kpi = FusionSolarInverterKpi(
                descriptive_name=fs_conf.descriptive_name,
                #station_name=station_name,
                #station_dn=station_dn,
                data_source="open_api",
                real_time_power_w=real_time_power_w,
                cumulative_energy_wh=cumulative_energy_wh,
                #month_energy_wh=month_energy_wh,
                day_energy_wh=daily_energy_wh,
                #year_energy_wh=year_energy,
            )

            inverter_kpis.append(inverter_kpi)

        return inverter_kpis