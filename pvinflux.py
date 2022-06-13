from datetime import datetime

class PvInflux:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvInflux class instantiated")

    def initialize(self):
        try:
            if self.conf.influx2:
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
            self.conf.if2protocol, self.conf.ifhost, self.conf.ifport
        )
        self.logger.info("Connecting to InfluxDB v2 url: {}".format(url))

        try:
            self.logger.debug(
                "Instantiating InfluxDBClient class from InfluxDB library"
            )
            self.influxclient = InfluxDBClient(
                url=url,
                org=self.conf.if2org,
                token=self.conf.if2token,
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
            buckets = self.if2bucket_api.find_bucket_by_name(self.conf.if2bucket)
            if buckets == None:
                raise Exception(
                    "InfluxDB v2 bucket {} not defined".format(self.conf.if2bucket)
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
                if org.name == self.conf.if2org:
                    orgfound = True
                    break
            if not orgfound:
                self.logger.warning(
                    "InfluxDB v2 organization {} not defined or no authorisation to check".format(
                        self.conf.if2org
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
                host=self.conf.ifhost,
                port=self.conf.ifport,
                timeout=3,
                username=self.conf.if1user,
                password=self.conf.if1passwd,
            )
        except Exception as e:
            raise Exception(
                "Error instantiating InfluxDB v1 client library: '{}'".format(str(e))
            )

        try:
            self.logger.debug("Fetching influxdb database list")
            databases = [db["name"] for db in self.influxclient.get_list_database()]
        except Exception as e:
            raise Exception(
                "Cannot fetch list of databases from InfluxDB: '{}'".format(str(e))
            )

        if self.conf.if1dbname not in databases:
            self.logger.info(
                f"InfluxDB database {self.conf.if1dbname} not defined in InfluxDB, creating new database"
            )
            try:
                self.influxclient.create_database(self.conf.if1dbname)
            except Exception as e:
                raise Exception(
                    "Unable create database: '{}': '{}'".format(self.conf.if1dbname),
                    str(e),
                )

        self.logger.debug("Switching to influxdb database {}", self.conf.if1dbname)
        try:
            self.influxclient.switch_database(self.conf.if1dbname)
        except Exception as e:
            raise Exception(
                "Error switching to database {}: ''".format(self.conf.if1dbname), str(e)
            )

        self.logger.info(
            "Succesfully switched to InfluxDB v1 database '{}'".format(
                self.conf.if1dbname
            )
        )

    def pvinflux_write(self, response_json_data):
        ifjson = self.make_influx_jsonrecord(response_json_data)
        self.logger.info("Writing InfluxDB json record: {}".format(str(ifjson)))
        try:
            if self.conf.influx2 :
                self.logger.debug("Writing to InfluxDB v2...")
                self.ifwrite_api.write(
                    bucket=self.conf.if2bucket,
                    org=self.conf.if2org,
                    record=ifjson,
                    write_precision="s",
                )
            else:
                self.logger.debug("Writing to InfluxDB v1...")
                self.conf.influxclient.write_points(ifjson, time_precision="s")
        except Exception as e:
            self.logger.exception("InfluxDB write error: '{}'".format(str(e)))

    def make_influx_jsonrecord(self, response_json_data):
        ifobj = {
            "measurement": self.conf.pvsysname,
            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fields": {},
        }

        # floatKey element existence already verified and converted to Watts in fetch_fusionsolar_status()
        floatKeys = {"realTimePower", "cumulativeEnergy"}
        for floatKey in floatKeys:
            ifobj["fields"][floatKey] = response_json_data["realKpi"][floatKey]

        floatKeys = {"currentPower"}
        for floatKey in floatKeys:
            ifobj["fields"][floatKey] = response_json_data["powerCurve"][floatKey]

        ifjson = [ifobj]
        return ifjson
