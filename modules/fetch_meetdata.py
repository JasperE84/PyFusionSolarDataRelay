import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import json
from modules.conf_models import BaseConf


class FetchMeetdata:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("GridKenter class instantiated")

    def fetch_gridkenter_data(self, sysname, ean, meterid, days_back):
        self.logger.info(
            "Requesting data for {} from GridKenter API...".format(
                sysname
            )
        )
        
        req_time = datetime.now() - timedelta(days=days_back)
        req_year = req_time.strftime("%Y")
        req_month = req_time.strftime("%m")
        req_day = req_time.strftime("%d")

        try:
            url = f"{self.conf.meetdata_nl_api_url}/api/1/measurements/{ean}/{meterid}/{req_year}/{req_month}/{req_day}"
            self.logger.debug(f"Fetching URL: {url}")

            response = requests.get(
                url,
                auth=HTTPBasicAuth(
                    self.conf.meetdata_nl_username, self.conf.meetdata_nl_password
                ),
                verify=False,
            )
        except Exception as e:
            raise Exception(
                "Error fetching data from GridKenter API: '{}'".format(str(e))
            )

        try:
            response_json = response.json()
        except Exception as e:
            raise Exception(
                "Error while parsing JSON response from GridKenter API: '{}'".format(
                    str(e)
                )
            )

        if not "16180" in response_json:
            raise Exception(
                f"GridKenter API response does not contain '16180' (levering tbv allocatie) key. Data possibly not ready yet. Response: {json.dumps(response_json)}"
            )

        # Checking required realKpi elements and transforming kW(h) to W(h)
        if len(response_json["16180"]) == 0:
            raise Exception(
                "'16180' (levering tbv allocatie) key does not contain data. Data possibly not ready yet. Response: {json.dumps(response_json)}"
            )

        grid_data_obj = {
            "sysname": sysname,
            "ean": ean,
            "meter_id": meterid,
            "grid_net_consumption": [],
        }

        prev_ts = None

        for measure in response_json["16180"]:
            # Meting en valide, of handmatig goedgekeurd
            if (measure["origin"] == "m" and measure["status"] == "v") or measure[
                "status"
            ] == "m":
                # Calculate powerload
                ts = datetime.fromtimestamp(measure["timestamp"])
                if prev_ts == None:
                    seconds_from_prev_ts = (
                        ts - ts.replace(hour=0, minute=0, second=0, microsecond=0)
                    ).total_seconds()
                else:
                    seconds_from_prev_ts = (ts - prev_ts).total_seconds()
                prev_ts = ts
                calculated_power = round(
                    measure["value"] * 3600 / seconds_from_prev_ts, 3
                )

                # self.logger.debug(
                #     f"Measurement local ts: {datetime.fromtimestamp(measure['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} kWh: {measure['value']} kW (calculated): {calculated_power}"
                # )

                grid_data_obj["grid_net_consumption"].append(
                    {
                        "timestamp": measure["timestamp"],
                        "interval_energy": measure["value"] * 1000,
                        "interval_power_avg": calculated_power * 1000,
                    }
                )

        return grid_data_obj
