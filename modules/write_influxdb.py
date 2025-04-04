from datetime import datetime, timezone
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterKpi, KenterTransformerKpi


class WriteInfluxDb:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WriteInfluxDb class instantiated")
        self.import_client_classes()
        self.classes_instantiated = False

    def write_fsolar_kiosk_data_to_influxdb(self, inverter_data: FusionSolarInverterKpi):
        if self.classes_instantiated == False:
            self.classes_instantiated = self.instantiate()

        ifjson = self.make_fsolar_kiosk_influxdb_record(inverter_data)
        self.logger.info(f"Writing InfluxDB FusionSolarKiosk record for inverter: {inverter_data.descriptive_name} [{inverter_data.station_dn}]")
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
            self.logger.exception(f"InfluxDB PvData write error: '{e}'")

    def write_kenterdata_to_influxdb(self, transformer_data: KenterTransformerKpi):
        if self.classes_instantiated == False:
            self.classes_instantiated = self.instantiate()

        ifjson = self.make_kenterdata_influxdb_record(transformer_data)
        self.logger.info(f"Writing GridData InfluxDB record for transformer [{transformer_data.descriptive_name}], connectionId: [{transformer_data.connection_id}], meteringPointId: [{transformer_data.metering_point_id}]")
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

    def make_fsolar_kiosk_influxdb_record(self, inverter_data: FusionSolarInverterKpi) -> list[dict]:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        measurement = "energy"
        device_type = "inverter"

        tags = {
            "site_descriptive_name": self.conf.site_descriptive_name,
            "inverter_descriptive_name": inverter_data.descriptive_name,
            "station_name": inverter_data.station_name,
            "data_source": inverter_data.data_source,
            "device_type": device_type,
            "station_dn": inverter_data.station_dn,
        }

        fields = {"real_time_power_w": inverter_data.real_time_power_w, "liftetime_energy_wh": inverter_data.lifteime_energy_wh}
        record = {"measurement": measurement, "time": timestamp, "fields": fields, "tags": tags}
        return [record]

    def make_kenterdata_influxdb_record(self, transformer_data: KenterTransformerKpi):
        measurement_str = "energy"
        device_type = "grid_transformer"

        influx_measurement_list = []

        tags = {
            "site_descriptive_name": self.conf.site_descriptive_name,
            "transformer_descriptive_name": transformer_data.descriptive_name,
            "connection_id": transformer_data.connection_id,
            "metering_point_id": transformer_data.metering_point_id,
            "channel_id": transformer_data.channel_id,
            "device_type": device_type,
        }

        for measurement in transformer_data.measurements:
            fields = {"interval_power_avg_w": measurement.interval_power_avg_w, "interval_energy_wh": measurement.interval_energy_wh}
            record = {"measurement": measurement_str, "time": datetime.fromtimestamp(measurement.timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "fields": fields, "tags": tags}
            influx_measurement_list.append(record)

        return influx_measurement_list

    def import_client_classes(self):
        try:
            if self.conf.influxdb_is_v2:
                self.import_client_classes_v2()
            else:
                self.import_client_classes_v1()

            self.logger.debug("InfluxDB classes imported")
        except Exception as e:
            raise Exception(f"Error importing InfluxDB classes: '{e}'")

    def import_client_classes_v1(self):
        self.logger.debug("InfluxDB v1 initialization started")
        try:
            from influxdb import InfluxDBClient

            # Store imports in instance variables
            self.InfluxDBClient = InfluxDBClient
        except Exception as e:
            raise Exception("Error importing InfluxDB client library: '{}'".format(str(e)))

    def import_client_classes_v2(self):
        self.logger.debug("InfluxDB v2 initialization started")
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS

            # Store imports in instance variables
            self.InfluxDBClient = InfluxDBClient
            self.SYNCHRONOUS = SYNCHRONOUS
        except Exception as e:
            raise Exception(f"Error importing InfluxDB client library: '{e}'")

    def instantiate(self):
        try:
            if self.conf.influxdb_is_v2:
                self.instantiate_v2()
            else:
                self.instantiate_v1()

            self.logger.info("InfluxDB instantiated")
            return True
        except Exception as e:
            self.logger.exception(f"Error instantiating InfluxDB classes: '{e}', retrying next interval")
            return False

    def instantiate_v1(self):
        if self.InfluxDBClient is None:
            raise Exception("InfluxDB client libraries must be imported first using import_client_classes_v1")

        try:
            self.logger.debug("Instantiating InfluxDBClient class from InfluxDB library")
            self.influxclient = self.InfluxDBClient(host=self.conf.influxdb_host, port=self.conf.influxdb_port, timeout=3, username=self.conf.influxdb_v1_username, password=self.conf.influxdb_v1_password, database=self.conf.influxdb_v1_db_name)
        except Exception as e:
            raise Exception(f"Error instantiating InfluxDB v1 client library: '{e}'")

    def instantiate_v2(self):
        url = "{}://{}:{}".format(self.conf.influxdb_v2_protocol, self.conf.influxdb_host, self.conf.influxdb_port)
        self.logger.info(f"Connecting to InfluxDB v2 url: {url}...")

        if self.InfluxDBClient is None or self.SYNCHRONOUS is None:
            raise Exception("InfluxDBv2 client libraries must be imported first using import_client_classes_v2")

        try:
            self.logger.debug("Instantiating InfluxDBClient class from InfluxDB library")
            self.influxclient = self.InfluxDBClient(
                url=url,
                org=self.conf.influxdb_v2_org,
                token=self.conf.influxdb_v2_token,
            )
            self.if2bucket_api = self.influxclient.buckets_api()
            self.if2organization_api = self.influxclient.organizations_api()
            self.ifwrite_api = self.influxclient.write_api(write_options=self.SYNCHRONOUS)
        except Exception as e:
            raise Exception(f"Error instantiating InfluxDBv2 client library: '{e}'")

        try:
            self.logger.debug("Fetching InfluxDBv2 bucket by name")
            buckets = self.if2bucket_api.find_bucket_by_name(self.conf.influxdb_v2_bucket)
            if buckets == None:
                raise Exception(f"InfluxDB v2 bucket {self.conf.influxdb_v2_bucket} not defined")
        except Exception as e:
            raise Exception(f"Error getting InfluxDBv2 bucket by name: '{e}'")

        try:
            self.logger.debug("Fetching InfluxDBv2 organizations")
            organizations = self.if2organization_api.find_organizations()
            orgfound = False
            for org in organizations:
                if org.name == self.conf.influxdb_v2_org:
                    orgfound = True
                    break
            if not orgfound:
                self.logger.warning(f"InfluxDBv2 organization {self.conf.influxdb_v2_org} not defined or no authorisation to check")
        except Exception as e:
            self.logger.exception(f"Error reading InfluxDBv2 organizations: '{e}'")
