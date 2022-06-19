import requests
import time
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
