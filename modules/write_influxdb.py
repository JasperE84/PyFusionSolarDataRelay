from datetime import datetime
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterKpi


class WriteInfluxDb:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvInflux class instantiated")

    def initialize(self):
        try:
            if self.conf.influxdb_is_v2:
                self.initialize_v2()
            else:
                self.initialize_v1()

            self.logger.info("InfluxDB initialized")
            return True
        except Exception as e:
            self.logger.exception(
                "Error initializing InfluxDB: '{}', retrying next interval".format(
                    str(e)
                )
            )
            return False

    def initialize_v2(self):
        self.logger.debug("InfluxDB v2 initialization started")
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS
        except Exception as e:
            raise Exception(
                "Error importing InfluxDB client library: '{}'".format(str(e))
            )

        url = "{}://{}:{}".format(
            self.conf.influxdb_v2_protocol, self.conf.influxdb_host, self.conf.influxdb_port
        )
        self.logger.info("Connecting to InfluxDB v2 url: {}".format(url))

        try:
            self.logger.debug(
                "Instantiating InfluxDBClient class from InfluxDB library"
            )
            self.influxclient = InfluxDBClient(
                url=url,
                org=self.conf.influxdb_v2_org,
                token=self.conf.influxdb_v2_token,
            )
            self.if2bucket_api = self.influxclient.buckets_api()
            self.if2organization_api = self.influxclient.organizations_api()
            self.ifwrite_api = self.influxclient.write_api(write_options=SYNCHRONOUS)
        except Exception as e:
            raise Exception(
                "Error instantiating InfluxDB v2 client library: '{}'".format(str(e))
            )

        try:
            self.logger.debug("Fetching influxdb bucket by name")
            buckets = self.if2bucket_api.find_bucket_by_name(self.conf.influxdb_v2_bucket)
            if buckets == None:
                raise Exception(
                    "InfluxDB v2 bucket {} not defined".format(self.conf.influxdb_v2_bucket)
                )
        except Exception as e:
            raise Exception(
                "Error getting InfluxDB bucket by name: '{}'".format(str(e))
            )

        try:
            self.logger.debug("Fetching InfluxDB organizations")
            organizations = self.if2organization_api.find_organizations()
            orgfound = False
            for org in organizations:
                if org.name == self.conf.influxdb_v2_org:
                    orgfound = True
                    break
            if not orgfound:
                self.logger.warning(
                    "InfluxDB v2 organization {} not defined or no authorisation to check".format(
                        self.conf.influxdb_v2_org
                    )
                )
        except Exception as e:
            self.logger.exception(
                "Error getting InfluxDB organizations: '{}'".format(str(e))
            )

    def initialize_v1(self):
        self.logger.debug("InfluxDB v1 initialization started")
        try:
            from influxdb import InfluxDBClient
        except Exception as e:
            raise Exception(
                "Error importing InfluxDB client library: '{}'".format(str(e))
            )

        try:
            self.logger.debug(
                "Instantiating InfluxDBClient class from InfluxDB library"
            )
            self.influxclient = InfluxDBClient(
                host=self.conf.influxdb_host,
                port=self.conf.influxdb_port,
                timeout=3,
                username=self.conf.influxdb_v1_username,
                password=self.conf.influxdb_v1_password,
                database=self.conf.influxdb_v1_db_name
            )
        except Exception as e:
            raise Exception(
                "Error instantiating InfluxDB v1 client library: '{}'".format(str(e))
            )

    def pvinflux_write_pvdata(self, inverter_data: FusionSolarInverterKpi):
        ifjson = self.make_influx_pvdata_jsonrecord(inverter_data)
        self.logger.info("Writing InfluxDB json record: {}".format(str(ifjson)))
        try:
            if self.conf.influxdb_is_v2:
                self.logger.debug("Writing PvData to InfluxDB v2...")
                self.ifwrite_api.write(
                    bucket=self.conf.influxdb_v2_bucket,
                    org=self.conf.influxdb_v2_org,
                    record=ifjson,
                    write_precision="s",
                )
            else:
                self.logger.debug("Writing PvData to InfluxDB v1...")
                self.influxclient.write_points(ifjson, time_precision="s")
        except Exception as e:
            self.logger.exception("InfluxDB PvData write error: '{}'".format(str(e)))

    def make_influx_pvdata_jsonrecord(self, inverter_data: FusionSolarInverterKpi) -> list[dict]:
        """
        Creates an InfluxDB JSON record from FusionSolarInverterKpi data.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        measurement = 'energy'
        device_type = 'inverter'

        tags = {
            "siteName": self.conf.site_name,
            "stationName": inverter_data.stationName,
            "dataSource": inverter_data.dataSource,
            "deviceType": device_type,
            "stationDn": inverter_data.stationDn,
        }

        fields = {
            "realTimePower_W": inverter_data.realTimePowerW,
            "cumulativeEnergy_Wh": inverter_data.cumulativeEnergyWh
        }

        record = {
            "measurement": measurement,
            "time": timestamp,
            "fields": fields,
            "tags": tags
        }

        return [record]


    def pvinflux_write_griddata(self, grid_data_obj):
        ifjson = self.make_influx_griddata_jsonrecord(grid_data_obj)
        self.logger.info("Writing GridData InfluxDB json records: {}".format(str(ifjson)))
        try:
            if self.conf.influxdb_is_v2:
                self.logger.debug("Writing GridData to InfluxDB v2...")
                self.ifwrite_api.write(
                    bucket=self.conf.influxdb_v2_bucket,
                    org=self.conf.influxdb_v2_org,
                    record=ifjson,
                    write_precision="s",
                )
            else:
                self.logger.debug("Writing GridData to InfluxDB v1...")
                self.influxclient.write_points(ifjson, time_precision="s")
        except Exception as e:
            self.logger.exception("InfluxDB GridData write error: '{}'".format(str(e)))

    def make_influx_griddata_jsonrecord(self, grid_data_obj):
        influx_measurement_list = []

        for measurement in grid_data_obj["grid_net_consumption"]:
            influx_measurement_list.append({
                "measurement": grid_data_obj["sysname"],
                "time": datetime.utcfromtimestamp(measurement["timestamp"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": {
                    "interval_energy_wh": measurement["interval_energy_wh"],
                    "interval_power_avg_w": measurement["interval_power_avg_w"]
                }
            })

        return influx_measurement_list
