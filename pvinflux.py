class PvInflux:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger
        print("\nPyFusionSolarDataRelay relay mode started")

    def initialize(self):
        # Set up InfluxDB
        if self.conf.influx:

            if self.conf.ifhost == "localhost":
                self.conf.ifhost = "127.0.0.1"

            # InfluxDB V1
            if self.conf.influx2 == False:
                self.logger.debug("InfluxDB V1 initialization started")
                try:
                    from influxdb import InfluxDBClient
                except:
                    self.logger.exception(
                        "InfluxDB v1 configured but python library not installed, disabling InfluxDB processing"
                    )
                    self.conf.influx = False

                self.influxclient = InfluxDBClient(
                    host=self.conf.ifhost,
                    port=self.conf.ifport,
                    timeout=3,
                    username=self.conf.if1user,
                    password=self.conf.if1passwd,
                )

                try:
                    databases = [
                        db["name"] for db in self.influxclient.get_list_database()
                    ]
                except Exception as e:
                    self.logger.exception(
                        "Cannot fetch list of databases from InfluxDB v1, disabling InfluxDB processing"
                    )
                    self.conf.influx = False

                if self.conf.if1dbname not in databases:
                    self.logger.info(
                        f"InfluxDB database {self.conf.if1dbname} not defined in InfluxDB, creating new database"
                    )
                    try:
                        self.influxclient.create_database(self.conf.if1dbname)
                    except:
                        self.logger.debug(
                            "Unable to create or connect to influx database:",
                            self.conf.if1dbname,
                            " check user authorisation",
                        )
                        self.conf.influx = False
                        raise SystemExit(
                            "Unable to create or connect to influx database:",
                            self.conf.if1dbname,
                            " check user authorisation",
                        )

                self.influxclient.switch_database(self.conf.if1dbname)

            # InfluxDB V2
            else:

                self.logger.debug("InfluxDB V2 initialization started")
                try:
                    from influxdb_client import InfluxDBClient
                    from influxdb_client.client.write_api import SYNCHRONOUS
                except:
                    self.logger.debug("InfluxDB-client Library not installed in Python")
                    self.conf.influx = False
                    raise SystemExit("InfluxDB-client Library not installed in Python")

                url = "{}://{}:{}".format(
                    self.conf.if2protocol, self.conf.ifhost, self.conf.ifport
                )
                self.logger.info("Connecting to InfluxDBv2 url: {}".format(url))

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

                try:
                    buckets = self.if2bucket_api.find_bucket_by_name(
                        self.conf.if2bucket
                    )
                    organizations = self.if2organization_api.find_organizations()
                    if buckets == None:
                        print("InfluxDB V2 bucket ", self.conf.if2bucket, "not defined")
                        self.conf.influx = False
                        raise SystemExit(
                            "InfluxDB V2 bucket ", self.conf.if2bucket, "not defined"
                        )
                    orgfound = False
                    for org in organizations:
                        if org.name == self.conf.if2org:
                            orgfound = True
                            break
                    if not orgfound:
                        print(
                            "InfluxDB V2 organization",
                            self.conf.if2org,
                            "not defined or no authorisation to check",
                        )

                except Exception as e:
                    self.logger.debug("error: can not contact InfluxDB V2")
                    print(e)
                    self.conf.influx = False
                    raise SystemExit("Influxdb initialisation error")
