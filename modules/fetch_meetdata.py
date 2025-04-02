import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import json
from modules.conf_models import BaseConf


class FetchMeetdata:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("Meetdata class instantiated")

        # Obtain the JWT token immediately upon instantiation, or delay until needed
        #self.jwt_token = self.update_meetdata_token()
        self.jwt_token = ""

    def update_meetdata_token(self):
        token_url = self.conf.meetdata_nl_token_url
        form_data = {
            "client_id": self.conf.meetdata_nl_clientid,
            "client_secret": self.conf.meetdata_nl_password,
            "grant_type": "client_credentials",
            "scope": "meetdata.read"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            self.logger.info(f"Requesting JWT authentication token from {token_url}")
            response = requests.post(token_url, data=form_data, headers=headers, verify=False)
            response.raise_for_status()
            token_response = response.json()
            access_token = token_response.get("access_token")
            if not access_token:
                raise Exception("No access token returned from the meetdata token endpoint")
            self.jwt_token = access_token
        except Exception as e:
            err_msg = f"Could not update meetdata JWT auth token: {str(e)}"
            self.logger.error(err_msg)
            raise Exception(err_msg)

    def fetch_gridkenter_meters(self):
        self.logger.info("Requesting meter list from meetdata API...")

        try:
            url = f"{self.conf.meetdata_nl_api_url}/meetdata/v2/meters"
            self.logger.debug(f"Fetching URL: {url}")

            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Accept": "application/json"
            }

            response = requests.get(url,headers=headers,verify=False)
            if response.status_code != 200 and response.status_code != 401:
                response.raise_for_status()
            if response.status_code == 401:
                self.logger.debug("Meetdata 401 return code: JWT token expired or wasn't yet set, refreshing and retrying request");
                self.update_meetdata_token()
                headers["Authorization"] = f"Bearer {self.jwt_token}"
                response = requests.get(url,headers=headers,verify=False)
                response.raise_for_status()

        except Exception as e:
            raise Exception("Error fetching meters Meetdata API: '{}'".format(str(e)))
        
        connections_data = response.json()
        self.logger.info("Current meetdata connection list:")
        for connection in connections_data:
            for meteringpoint in connection["meteringPoints"]:
                self.logger.info("connectionId: {}, meteringPointId: {}, productType: {}, meteringPointType: {}, meterNumber: {}".format(connection["connectionId"], meteringpoint["meteringPointId"], meteringpoint["productType"], meteringpoint["meteringPointType"], meteringpoint["meterNumber"]))


    def fetch_gridkenter_data(self, sysname, connection_id, metering_point_id, days_back):
        self.logger.info("Requesting data for {} from Meetdata API...".format(sysname))

        # Set request variables
        req_time = datetime.now() - timedelta(days=days_back)
        req_year = req_time.strftime("%Y")
        req_month = req_time.strftime("%m")
        req_day = req_time.strftime("%d")

        # Send API request
        try:
            url = f"{self.conf.meetdata_nl_api_url}/meetdata/v2/measurements/connections/{connection_id}/metering-points/{metering_point_id}/days/{req_year}/{req_month}/{req_day}"
            self.logger.debug(f"Fetching URL: {url}")

            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Accept": "application/json"
            }
            response = requests.get(url,headers=headers,verify=False)

            if response.status_code != 200 and response.status_code != 401:
                response.raise_for_status()
            if response.status_code == 401:
                self.logger.debug("Meetdata 401 return code: JWT token expired or wasn't yet set, refreshing and retrying request");
                self.update_meetdata_token()
                headers["Authorization"] = f"Bearer {self.jwt_token}"
                response = requests.get(url,headers=headers,verify=False)
                response.raise_for_status()

        except Exception as e:
            raise Exception("Error fetching data from Meetdata API: '{}'".format(str(e)))

        # JSON encode HTTP response
        try:
            response_json = response.json()
        except Exception as e:
            raise Exception("Error while parsing JSON response from Meetdata API: '{}'".format(str(e)))

        # Find first 16180 channel
        channel = next(iter([channel for channel in response_json if channel.get("channelId") == "16180"]), None)

        if not channel:
            raise Exception(f"Meetdata API channel response does not contain '16180' (levering tbv allocatie) key. Data possibly not ready yet. Response: {json.dumps(response_json)}")

        return_dict = {
            "sysname": sysname,
            "ean": connection_id,
            "meter_id": metering_point_id,
            "grid_net_consumption": [],
        }

        prev_ts = None

        for measure in channel["Measurements"]:
            # Meting en valide
            if (measure["origin"] == "Measured" and measure["status"] == "Valid"):
                # Calculate powerload
                ts = datetime.fromtimestamp(measure["timestamp"])
                if prev_ts == None:
                    seconds_from_prev_ts = (ts - ts.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
                else:
                    seconds_from_prev_ts = (ts - prev_ts).total_seconds()
                prev_ts = ts
                calculated_power = round(measure["value"] * 3600 / seconds_from_prev_ts, 3)

                # Append to data
                return_dict["grid_net_consumption"].append(
                    {
                        "timestamp": measure["timestamp"],
                        "interval_energy": measure["value"] * 1000,
                        "interval_power_avg": calculated_power * 1000,
                    }
                )

        return return_dict
