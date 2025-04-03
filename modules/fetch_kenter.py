import requests
from datetime import datetime, timedelta
import json
from modules.conf_models import BaseConf


class FetchKenter:
    def __init__(self, conf: BaseConf, logger):
        """
        :param conf: Configuration object of type BaseConf
        :param logger: Logger object
        """
        self.conf = conf
        self.logger = logger
        self.logger.debug("Kenter class instantiated")
        # Token is fetched on demand via _request_with_token_retry rather than at instantiation.
        self.jwt_token = ""

    def update_kenter_token(self):
        """
        Updates self.jwt_token by making a request to the Kenter token endpoint.
        Raises an exception if the token cannot be retrieved.
        """
        token_url = self.conf.kenter_token_url
        form_data = {
            "client_id": self.conf.kenter_clientid,
            "client_secret": self.conf.kenter_password,
            "grant_type": "client_credentials",
            "scope": "meetdata.read"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            self.logger.info(f"Requesting JWT authentication token from {token_url}")
            response = requests.post(token_url, data=form_data, headers=headers, verify=False)
            response.raise_for_status()
            token_response = response.json()
            access_token = token_response.get("access_token")
            if not access_token:
                raise Exception("No access token returned from the Kenter token endpoint.")
            self.jwt_token = access_token
        except Exception as e:
            err_msg = f"Could not update Kenter JWT auth token: {str(e)}"
            self.logger.error(err_msg)
            raise Exception(err_msg)

    def _request_with_token_retry(self, url, method="GET", **kwargs):
        """
        Internal helper to make a request with the current JWT token. If a 401 is
        encountered, refresh the token once and retry.

        :param url: Full endpoint URL
        :param method: HTTP method (e.g., 'GET', 'POST')
        :param kwargs: Additional arguments to pass directly to requests.*
        :return: requests.Response
        """
        # Ensure headers exist
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.jwt_token}"
        headers.setdefault("Accept", "application/json")

        attempt_methods = [method.upper()]
        # Attempt the request up to two times (in case we need to refresh token).
        for attempt in range(2):
            self.logger.debug(f"Fetching URL: {url} (attempt {attempt + 1})")
            response = requests.request(attempt_methods[0], url, headers=headers, verify=False, **kwargs)
            # If not 401 or second attempt, break
            if response.status_code != 401 or attempt == 1:
                # If there's another error status, it will be caught below
                break
            # If we got a 401 first time, refresh token and retry
            self.logger.debug("Kenter 401: JWT token expired or not set, refreshing token and retrying request.")
            self.update_kenter_token()
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        # Raise for non-success statuses (other than 200)
        if response.status_code != 200:
            response.raise_for_status()

        return response

    def fetch_gridkenter_meters(self):
        """
        Fetch and log a list of meters from the Kenter API.
        Raises an exception if the request or JSON parsing fails.
        """
        self.logger.info("Requesting meter list from Kenter API...")
        url = f"{self.conf.kenter_api_url}/meetdata/v2/meters"

        try:
            response = self._request_with_token_retry(url, method="GET")
        except Exception as e:
            raise Exception(f"Error fetching meters from Kenter API: '{str(e)}'")

        # Parse and log the connections data
        connections_data = response.json()
        self.logger.info("Current Kenter connection list:")
        for connection in connections_data:
            for meteringpoint in connection.get("meteringPoints", []):
                self.logger.info(
                    "connectionId: {}, meteringPointId: {}, productType: {}, "
                    "meteringPointType: {}, meterNumber: {}".format(
                        connection.get("connectionId"),
                        meteringpoint.get("meteringPointId"),
                        meteringpoint.get("productType"),
                        meteringpoint.get("meteringPointType"),
                        meteringpoint.get("meterNumber")
                    )
                )

    def fetch_gridkenter_data(self, sysname, connection_id, metering_point_id, days_back):
        """
        Fetch daily measurement data for a specific system (sysname) from the
        Kenter API by connection ID and metering point ID, going a certain
        number of days back. The function identifies the channel with ID "16180",
        and returns structured data containing net consumption.

        :param sysname: Arbitrary system name/identifier
        :param connection_id: Connection ID to query
        :param metering_point_id: Metering point ID to query
        :param days_back: How many days back to retrieve data
        :return: Dictionary with structured meter data
        :raises Exception: If fetching fails or the JSON response is invalid
        """
        self.logger.info(f"Requesting data for {sysname} from Kenter API...")

        # Prepare date
        req_time = datetime.now() - timedelta(days=days_back)
        req_year = req_time.strftime("%Y")
        req_month = req_time.strftime("%m")
        req_day = req_time.strftime("%d")

        url = (
            f"{self.conf.kenter_api_url}/meetdata/v2/measurements/connections/"
            f"{connection_id}/metering-points/{metering_point_id}/days/"
            f"{req_year}/{req_month}/{req_day}"
        )

        try:
            response = self._request_with_token_retry(url, method="GET")
        except Exception as e:
            raise Exception(f"Error fetching data from Kenter API: '{str(e)}'")

        # Parse JSON
        try:
            response_json = response.json()
        except Exception as e:
            raise Exception(f"Error while parsing JSON response from Kenter API: '{str(e)}'")

        # Find first channel that has channelId = '16180'
        channel = next((ch for ch in response_json if ch.get("channelId") == "16180"), None)
        if not channel:
            raise Exception(
                "Kenter API response does not contain channelId '16180'. "
                f"Data may not be ready yet. Response: {json.dumps(response_json)}"
            )

        return_dict = {
            "sysname": sysname,
            "ean": connection_id,
            "meter_id": metering_point_id,
            "grid_net_consumption": [],
        }

        prev_ts = None
        for measure in channel.get("Measurements", []):
            # Only use measured & valid data
            if measure.get("origin") == "Measured" and measure.get("status") == "Valid":
                ts = datetime.fromtimestamp(measure["timestamp"])
                # Calculate number of seconds since last valid point
                if prev_ts:
                    seconds_from_prev_ts = (ts - prev_ts).total_seconds()
                else:
                    # If there is no previous timestamp, measure from midnight to first entry
                    seconds_from_prev_ts = (ts - ts.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
                prev_ts = ts

                # Calculate power load [kW] from energy [kWh], then convert to W
                calculated_power = round(measure["value"] * 3600 / seconds_from_prev_ts, 3) * 1000

                return_dict["grid_net_consumption"].append({
                    "timestamp": measure["timestamp"],
                    "interval_energy_wh": measure["value"] * 1000,      # in Wh
                    "interval_power_avg_w": calculated_power,          # in W
                })

        return return_dict