import requests
import time
from modules.conf_models import BaseConf, FusionSolarKioskSettings
from modules.models import FusionSolarInverterMeasurement


class WritePvOutput:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WritePvOutput class instantiated")

    def write_pvdata_to_pvoutput(self, measurement: FusionSolarInverterMeasurement, dev_id: str, pvoutput_system_id: int):
        if self.conf.pvoutput_module_enabled:
            if pvoutput_system_id == 0:
                self.logger.info(f"Skipping PVOutput API call for (kk)id: {dev_id}, output_pvoutput_system_id is not configured")
            else:
                pvoutput_header_obj = {
                    "X-Pvoutput-Apikey": self.conf.pvoutput_api_key,
                    "X-Pvoutput-SystemId": str(pvoutput_system_id),
                }

                pvoutput_data_obj = self.make_pvoutput_pvdata_obj(measurement)

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
                    api_response.raise_for_status()
                except Exception as e:
                    raise Exception(
                        "Exception while posting data to PVOutput: '{}'".format(str(e))
                    )
                
        else:
            self.logger.debug("PVOutput writing disabled")

    def make_pvoutput_pvdata_obj(self, inverter_kpi: FusionSolarInverterMeasurement):
        localtime = time.localtime()
        pvodate = time.strftime("%Y%m%d", localtime)
        pvotime = time.strftime("%H:%M", localtime)

        pvoutput_data_obj = {
            "d": pvodate,
            "t": pvotime,
            "v1": inverter_kpi.lifetime_energy_wh,
            "v2": inverter_kpi.real_time_power_w,
            "c1": 2,
        }

        return pvoutput_data_obj