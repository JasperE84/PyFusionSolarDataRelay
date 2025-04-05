from datetime import datetime, timezone
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterMeasurement, KenterTransformerMeasurements


class WriteInfluxDb:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WriteInfluxDb class instantiated")
        self.import_client_classes()
        self.classes_instantiated = False

    def write_pvdata_to_influxdb(self, measurement: FusionSolarInverterMeasurement):
        if self.classes_instantiated == False:
            self.classes_instantiated = self.instantiate()

        influxdb_record = self.make_inverter_measurement_influxdb_record(measurement)
        self.logger.info(f"Writing InfluxDB FusionSolarKiosk record for inverter: {measurement.settings_descriptive_name} [{measurement.station_dn}]")
        try:
            if self.conf.influxdb_is_v2:
                self.logger.debug("Writing PvData to InfluxDB v2...")
                self.ifwrite_api.write(
                    bucket=self.conf.influxdb_v2_bucket,
                    org=self.conf.influxdb_v2_org,
                    record=influxdb_record,
                    write_precision="s",
                )
            else:
                self.logger.debug("Writing PvData to InfluxDB v1...")
                self.influxclient.write_points(influxdb_record, time_precision="s")
        except Exception as e:
            self.logger.exception(f"InfluxDB PvData write error: '{e}'")

    def write_kenterdata_to_influxdb(self, measurement: KenterTransformerMeasurements):
        if self.classes_instantiated == False:
            self.classes_instantiated = self.instantiate()

        influxdb_record = self.make_kenterdata_influxdb_record(measurement)
        self.logger.info(f"Writing GridData InfluxDB record for transformer [{measurement.descriptive_name}], connectionId: [{measurement.connection_id}], meteringPointId: [{measurement.metering_point_id}]")
        try:
            if self.conf.influxdb_is_v2:
                self.logger.debug("Writing GridData to InfluxDB v2...")
                self.ifwrite_api.write(
                    bucket=self.conf.influxdb_v2_bucket,
                    org=self.conf.influxdb_v2_org,
                    record=influxdb_record,
                    write_precision="s",
                )
            else:
                self.logger.debug("Writing GridData to InfluxDB v1...")
                self.influxclient.write_points(influxdb_record, time_precision="s")
        except Exception as e:
            self.logger.exception("InfluxDB GridData write error: '{}'".format(str(e)))

    def make_inverter_measurement_influxdb_record(self, measurement: FusionSolarInverterMeasurement) -> list[dict]:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        measurement = "energy"
        device_type = "inverter"

        raw_tags = {
            "site_descriptive_name": self.conf.site_descriptive_name,
            "inverter_descriptive_name": measurement.settings_descriptive_name,
            "device_type": device_type,
            "data_source": measurement.data_source,

            "station_name": measurement.station_name,
            "station_dn": measurement.station_dn,

            "device_id" : measurement.device_id,
            "device_dn": measurement.device_dn,
            "device_name" : measurement.device_name,
            "device_model" : measurement.device_model,
        }
        # Do not set tag if string is empty
        tags = {key: value for key, value in raw_tags.items() if value}

        fields = {"real_time_power_w": measurement.real_time_power_w, "liftetime_energy_wh": measurement.lifetime_energy_wh}
        record = {"measurement": measurement, "time": timestamp, "fields": fields, "tags": tags}
        return [record]

    def make_kenterdata_influxdb_record(self, transformer_data: KenterTransformerMeasurements):
        influxdb_measurement_str = "energy"
        device_type = "grid_transformer"

        influxdb_records = []

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
            record = {"measurement": influxdb_measurement_str, "time": datetime.fromtimestamp(measurement.timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "fields": fields, "tags": tags}
            influxdb_records.append(record)

        return influxdb_records

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
