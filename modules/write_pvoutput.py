import requests
import time
from modules.conf_models import BaseConf, FusionSolarKioskMetric
from modules.models import FusionSolarInverterKpi


class WritePvOutput:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvOutputOrg class instantiated")

    def write_pvdata_to_pvoutput(self, inverter_kpi: FusionSolarInverterKpi, fs_conf: FusionSolarKioskMetric):
        if self.conf.pvoutput_module_enabled:
            if fs_conf.output_pvoutput_system_id == 0:
                self.logger.info(f"Skipping PVOutput API call for kkid: {fs_conf.api_kkid}, output_pvoutput_system_id is not configured")
            else:
                pvoutput_header_obj = {
                    "X-Pvoutput-Apikey": self.conf.pvoutput_api_key,
                    "X-Pvoutput-SystemId": str(fs_conf.output_pvoutput_system_id),
                }

                pvoutput_data_obj = self.make_pvoutput_pvdata_obj(inverter_kpi)

                try:
                    self.logger.info(
                        "Writing to PVOutput. Header: {} Data: {}".format(
                            pvoutput_header_obj, pvoutput_data_obj
                        )
                    )
                    api_response = requests.post(
                        self.conf.pvoutput_record_url,
                        data=pvoutput_data_obj,
                        headers=pvoutput_header_obj,
                        verify=False
                    )
                    self.logger.debug("PVOutput response {}".format(api_response.text))
                except Exception as e:
                    raise Exception(
                        "Exception while posting data to PVOutput: '{}'".format(str(e))
                    )
                
        else:
            self.logger.debug("PVOutput writing disabled")

    def make_pvoutput_pvdata_obj(self, inverter_kpi: FusionSolarInverterKpi):
        localtime = time.localtime()
        pvodate = time.strftime("%Y%m%d", localtime)
        pvotime = time.strftime("%H:%M", localtime)

        pvoutput_data_obj = {
            "d": pvodate,
            "t": pvotime,
            "v1": inverter_kpi.lifteime_energy_wh,
            "v2": inverter_kpi.real_time_power_w,
            "c1": 2,
        }

        return pvoutput_data_obj