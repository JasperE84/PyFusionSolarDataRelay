class PvInflux:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvInflux class instantiated")

    def initialize(self):
        if self.conf.influx:
            try:
                if self.conf.influx2:
                    self.initialize_v2()
                else:
                    self.initialize_v1()
            except:
                self.logger.exception("Uncaught exception while setting up InfluxDB processing. Disabling InfluxDB processing.")
                self.conf.influx = False

    def initialize_v2(self):
        self.logger.debug("InfluxDB v2 initialization started")
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS
        except:
            self.logger.exception("Error importing InfluxDB client library, disabling InfluxDB processing")
            self.conf.influx = False

        url = "{}://{}:{}".format(self.conf.if2protocol, self.conf.ifhost, self.conf.ifport)
        self.logger.info("Connecting to InfluxDB v2 url: {}".format(url))

        try:
            self.logger.debug("Instantiating InfluxDBClient class from InfluxDB library")
            self.influxclient = InfluxDBClient(
                        url=url,
                        org=self.conf.if2org,
                        token=self.conf.if2token,
                    )
            self.if2bucket_api = self.influxclient.buckets_api()
            self.if2organization_api = self.influxclient.organizations_api()
            self.ifwrite_api = self.influxclient.write_api(
                        write_options=SYNCHRONOUS
                    )
        except:
            self.logger.exception("Error instantiating InfluxDB v2 client library, disabling InfluxDB processing")
            self.conf.influx = False   

        try:
            self.logger.debug("Fetching influxdb bucket by name")
            buckets = self.if2bucket_api.find_bucket_by_name(self.conf.if2bucket)
            if buckets == None:
                self.logger.info("InfluxDB v2 bucket {} not defined, disabling InfluxDB processing".format(self.conf.if2bucket))
                self.conf.influx = False
        except:
            self.logger.exception("Error getting InfluxDB bucket by name, disabling InfluxDB processing")
            self.conf.influx = False   

        try:
            self.logger.debug("Fetching InfluxDB organizations")
            organizations = self.if2organization_api.find_organizations()
            orgfound = False
            for org in organizations:
                if org.name == self.conf.if2org:
                    orgfound = True
                    break
            if not orgfound:
                self.logger.warning("InfluxDB v2 organization {} not defined or no authorisation to check".format(self.conf.if2org))
        except:
            self.logger.exception("Error getting InfluxDB organizations")

    def initialize_v1(self):
        self.logger.debug("InfluxDB v1 initialization started")
        try:
            from influxdb import InfluxDBClient
        except:
            self.logger.exception("Error importing InfluxDB client library, disabling InfluxDB processing")
            self.conf.influx = False

        try:
            self.logger.debug("Instantiating InfluxDBClient class from InfluxDB library")
            self.influxclient = InfluxDBClient(
                        host=self.conf.ifhost,
                        port=self.conf.ifport,
                        timeout=3,
                        username=self.conf.if1user,
                        password=self.conf.if1passwd,
                    )
        except:
            self.logger.exception("Error instantiating InfluxDB v1 client library, disabling InfluxDB processing")
            self.conf.influx = False   

        try:
            self.logger.debug("Fetching influxdb database list")
            databases = [db["name"] for db in self.influxclient.get_list_database()]
        except Exception as e:
            self.logger.exception("Cannot fetch list of databases from InfluxDB, disabling InfluxDB processing")
            self.conf.influx = False

        if self.conf.if1dbname not in databases:
            self.logger.info(f"InfluxDB database {self.conf.if1dbname} not defined in InfluxDB, creating new database")
            try:
                self.influxclient.create_database(self.conf.if1dbname)
            except:
                self.logger.exception("Unable create database: '{}'. Disabling InfluxDB processing".format(self.conf.if1dbname))
                self.conf.influx = False

        self.logger.debug("Switching to influxdb database {}",self.conf.if1dbname)
        try:
            self.influxclient.switch_database(self.conf.if1dbname)
        except:
            self.logger.exception("Unable to switch to database {}. Disabling InfluxDB processing".format(self.conf.if1dbname))
            self.conf.influx = False

        self.logger.info("Succesfully switched to InfluxDB v1 database '{}'".format(self.conf.if1dbname))