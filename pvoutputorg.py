import requests
import time
import math
from datetime import datetime, timedelta
from pvconf import PvConf

class PvOutputOrg:
    def __init__(self, conf: PvConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvOutputOrg class instantiated")

    def write_pvdata_to_pvoutput(self, fusionsolar_json_data):
        if self.conf.pvoutput:
            pvoutput_header_obj = {
                "X-Pvoutput-Apikey": self.conf.pvoutputapikey,
                "X-Pvoutput-SystemId": self.conf.pvoutputsystemid,
            }

            pvoutput_data_obj = self.make_pvoutput_pvdata_obj(fusionsolar_json_data)

            try:
                self.logger.info("Writing to PVOutput. Header: {} Data: {}".format(pvoutput_header_obj, pvoutput_data_obj))
                api_response = requests.post(self.conf.pvoutputurl, data=pvoutput_data_obj, headers=pvoutput_header_obj)
                self.logger.debug("PVOutput response {}".format(api_response.text))
            except Exception as e:
                raise Exception("Exception while posting data to PVOutput: '{}'".format(str(e)))

        else:
            self.logger.debug("PVOutput writing disabled")

    def make_pvoutput_pvdata_obj(self, response_json_data):
        localtime = time.localtime()
        pvodate = time.strftime("%Y%m%d", localtime)
        pvotime = time.strftime("%H:%M", localtime)

        pvoutput_data_obj = {
            "d": pvodate,
            "t": pvotime,
            "v1": float(response_json_data["realKpi"]["cumulativeEnergy"]),
            "v2": float(response_json_data["powerCurve"]["currentPower"]),
            "c1": 2,
        }

        return pvoutput_data_obj

    def write_griddata_to_pvoutput(self, grid_data_obj):
        if self.conf.pvoutput:
            pvoutput_header_obj = {
                "X-Pvoutput-Apikey": self.conf.pvoutputapikey,
                "X-Pvoutput-SystemId": self.conf.pvoutputsystemid,
            }

            # PVOutput allows max 30 records per batch
            pages = math.ceil(len(grid_data_obj["grid_net_consumption"])/30)

            for page in range(pages):
                pvoutput_batch_data_obj = self.make_pvoutput_griddata_obj_page(grid_data_obj, page)
                try:
                    self.logger.info("Writing GridData batch to PVOutput. Header: {} Data: {}".format(pvoutput_header_obj, pvoutput_batch_data_obj))
                    api_response = requests.post(self.conf.pvoutputbatchurl, data=pvoutput_batch_data_obj, headers=pvoutput_header_obj)
                    self.logger.debug("PVOutput GridData response {}".format(api_response.text))
                except Exception as e:
                    raise Exception("Exception while posting GridData to PVOutput: '{}'".format(str(e)))

        else:
            self.logger.debug("PVOutput writing disabled")

    def make_pvoutput_griddata_obj_page(self, grid_data_obj, page):

        data = []
        for idx, measurement in enumerate(grid_data_obj["grid_net_consumption"]):
            rec_num = idx + 1
            if (rec_num > page * 30) and (rec_num <= page * 30 + 30):
                local_date = datetime.fromtimestamp(measurement["timestamp"]).strftime("%Y%m%d")
                local_time = datetime.fromtimestamp(measurement["timestamp"]).strftime("%H:%M")
                data.append(f"{local_date},{local_time},,0,,{measurement['interval_power_avg']}")

        pvoutput_data_obj = {
            "c1": 0,
            "n": 1,
            "data": ";".join(data)
        }

        return pvoutput_data_obj
