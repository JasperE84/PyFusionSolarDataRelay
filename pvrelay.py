from datetime import datetime, timedelta
import time
import requests
import json
import html
import traceback


class Relay:
    def __init__(self, conf, pvinflux, logger):
        self.conf = conf
        self.pvinflux = pvinflux
        self.logger = logger
        print("\nPyFusionSolarDataRelay relay mode started")

    def main(self):
        while 1:
            try:
                if self.conf.debug:
                    print("Requesting data from FusionSolar Kiosk API...")
                try:
                    response = requests.get(f"{self.conf.fusionsolarurl}{self.conf.fusionsolarkkid}")
                    response_json = response.json()
                except:
                    raise Exception("Error fetching data from FusionSolar Kiosk API")

                if not "data" in response_json:
                    raise Exception(
                        f"FusionSolar API response does not contain data key. Response: {response_json}"
                    )
                response_json_data_decoded = html.unescape(response_json["data"])

                response_json_data = json.loads(response_json_data_decoded)
                if not "realKpi" in response_json_data_decoded:
                    raise Exception(
                        f'Element "realKpi" is missing in API response data'
                    )
                print(f'FusionSolar API response: {response_json_data["realKpi"]}')

                current_date = datetime.now().replace(microsecond=0).isoformat()

                if self.conf.influx:
                    if self.conf.debug:
                        print("PyFusionSolarDataRelay InfluxDB publihing started")
                    try:
                        import pytz
                    except:
                        if self.conf.debug:
                            print(
                                "PyFusionSolarDataRelay PYTZ Library not installed in Python, influx processing disabled"
                            )
                        self.conf.influx = False
                        return
                    try:
                        local = pytz.timezone(self.conf.tmzone)
                    except:
                        if self.conf.debug:
                            if self.conf.tmzone == "local":
                                print("Timezone local specified, default timezone used")
                            else:
                                print(
                                    "PyFusionSolarDataRelay unknown timezone : ",
                                    self.conf.tmzone,
                                    ", default timezone used",
                                )
                        self.conf.tmzone = "local"
                        local = int(time.timezone / 3600)

                    if self.conf.tmzone == "local":
                        curtz = time.timezone
                        utc_dt = datetime.strptime(
                            current_date, "%Y-%m-%dT%H:%M:%S"
                        ) + timedelta(seconds=curtz)
                    else:
                        naive = datetime.strptime(current_date, "%Y-%m-%dT%H:%M:%S")
                        local_dt = local.localize(naive, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)

                    ifdt = utc_dt.strftime("%Y-%m-%dT%H:%M:%S")
                    if self.conf.debug:
                        print(
                            "PyFusionSolarDataRelay original time : ",
                            current_date,
                            "adjusted UTC time for influx : ",
                            ifdt,
                        )

                    ifobj = {
                        "measurement": self.conf.pvsysname,
                        "time": ifdt,
                        "fields": {},
                    }

                    floatKeys = {"realTimePower", "cumulativeEnergy"}
                    for floatKey in floatKeys:
                        if floatKey in response_json_data["realKpi"]:
                            ifobj["fields"][floatKey] = float(
                                response_json_data["realKpi"][floatKey]
                            ) * float(1000)
                        else:
                            raise Exception(
                                f"FusionSolar API data response element does cot contain key {floatKey}."
                            )

                    ifjson = [ifobj]

                    print("PyFusionSolarDataRelay InfluxDB json input: ", str(ifjson))

                    try:
                        if self.conf.influx2:
                            if self.conf.debug:
                                print("PyFusionSolarDataRelay write to InfluxDB V2")
                            ifresult = self.pvinflux.ifwrite_api.write(
                                self.conf.if2bucket, self.conf.if2org, ifjson
                            )
                        else:
                            if self.conf.debug:
                                print("PyFusionSolarDataRelay write to InfluxDB V1")
                            ifresult = self.conf.influxclient.write_points(ifjson)
                    except Exception as e:
                        print("PyFusionSolarDataRelay InfluxDB write error")
                        print(e)
                        raise SystemExit(
                            "PyFusionSolarDataRelay Influxdb write error, script will be stopped"
                        )

                else:
                    if self.conf.debug:
                        print("PyFusionSolarDataRelay Send data to Influx disabled ")

            except Exception as e:
                if self.conf.debug:
                    print("PyFusionSolarDataRelay error")
                print(e)
                traceback.print_exc()
            time.sleep(self.conf.pvinterval)
