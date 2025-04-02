import requests
import time
import math
from copy import copy
from datetime import datetime
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterKpi


class WritePvOutput:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvOutputOrg class instantiated")

    def write_pvdata_to_pvoutput(self, inverter_kpi: FusionSolarInverterKpi):
        if self.conf.pvoutput_enabled:
            pvoutput_header_obj = {
                "X-Pvoutput-Apikey": self.conf.pvoutput_api_key,
                "X-Pvoutput-SystemId": str(self.conf.pvoutput_system_id),
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
            "v1": inverter_kpi.cumulativeEnergyWh,
            "v2": inverter_kpi.currentPowerW,
            "c1": 2,
        }

        return pvoutput_data_obj


    def write_meetdata_to_pvoutput(self, grid_data_obj):
        if self.conf.pvoutput_enabled:
            pvoutput_header_obj = {
                "X-Pvoutput-Apikey": self.conf.pvoutput_api_key,
                "X-Pvoutput-SystemId": str(self.conf.pvoutput_system_id),
            }

            # Apply span
            grid_data_obj_copy = copy(grid_data_obj)
            grid_net_consumption_new = []
            new_elem = None
            for idx, element in enumerate(grid_data_obj["grid_net_consumption"]):
                if new_elem == None:
                    new_elem = copy(element)
                else:
                    new_elem["timestamp"] = element["timestamp"]
                    new_elem["interval_power_avg"] += element["interval_power_avg"]
                    new_elem["interval_energy"] += element["interval_energy"]

                residual = (idx + 1) % self.conf.meetdata_nl_pvoutput_span
                if residual == 0:
                    new_elem["interval_power_avg"] = (
                        new_elem["interval_power_avg"]
                        / self.conf.meetdata_nl_pvoutput_span
                    )
                    grid_net_consumption_new.append(new_elem)
                    new_elem = None

            grid_data_obj_copy["grid_net_consumption"] = grid_net_consumption_new

            # PVOutput allows max 30 records per batch
            pages = math.ceil(len(grid_data_obj_copy["grid_net_consumption"]) / 30)

            if (
                len(grid_data_obj_copy["grid_net_consumption"])
                % self.conf.meetdata_nl_pvoutput_span
                > 0
            ):
                self.logger.warn(
                    "WARNING! The number of measurements per 24h as supplied by meetdata.nl should be dividable by configured gridrelaypvoutputspan parameter."
                )
                self.logger.warn(
                    "Measurements in 24h: {}, configured span: {}.".format(
                        len(grid_data_obj["grid_net_consumption"]),
                        self.conf.meetdata_nl_pvoutput_span,
                    )
                )

            for page in range(pages):
                pvoutput_batch_data_obj = self.make_meetdata_obj_page(
                    grid_data_obj_copy, page
                )
                try:
                    self.logger.info(
                        "Writing GridData batch to PVOutput. Header: {} Data: {}".format(
                            pvoutput_header_obj, pvoutput_batch_data_obj
                        )
                    )

                    api_response = requests.post(
                        self.conf.pvoutput_batch_url,
                        data=pvoutput_batch_data_obj,
                        headers=pvoutput_header_obj,
                        verify=False
                    )

                    self.logger.debug(
                        "PVOutput GridData response {}".format(api_response.text)
                    )

                except Exception as e:
                    raise Exception(
                        "Exception while posting GridData to PVOutput: '{}'".format(
                            str(e)
                        )
                    )

        else:
            self.logger.debug("PVOutput writing disabled")

    def make_meetdata_obj_page(self, grid_data_obj, page):
        meetdata = []
        for idx, measurement in enumerate(grid_data_obj["grid_net_consumption"]):
            rec_num = idx + 1
            if (rec_num > page * 30) and (rec_num <= page * 30 + 30):
                local_date = datetime.fromtimestamp(measurement["timestamp"]).strftime(
                    "%Y%m%d"
                )
                local_time = datetime.fromtimestamp(measurement["timestamp"]).strftime(
                    "%H:%M"
                )
                meetdata.append(
                    f"{local_date},{local_time},-1,0,-1,{int(measurement['interval_power_avg'])}"
                )

        pvoutput_data_obj = {"c1": 0, "n": 1, "data": ";".join(meetdata)}

        return pvoutput_data_obj
