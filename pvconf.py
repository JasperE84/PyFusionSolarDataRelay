import os
import ipaddress


class Conf:
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug("Instantiating Conf class")
        self.apply_default_settings()
        self.apply_environment_settings()

    def apply_default_settings(self):
        self.logger.debug("Setting default conf values")

        # Set default variables
        self.debug = True
        self.tmzone = "local"

        # pvoutput default
        self.pvsysname = "inverter01"
        self.fusionsolarurl = "https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk="
        self.fusionsolarkkid = "GET_THIS_FROM_KIOSK_URL"
        self.pvinterval = 120

        # influxdb default
        self.influx = True
        self.influx2 = True

        self.ifhost = "localhost"
        self.ifport = 8086

        self.if1dbname = "fusionsolar"
        self.if1user = "fusionsolar"
        self.if1passwd = "fusionsolar"

        self.if2protocol = "https"
        self.if2org = "acme"
        self.if2bucket = "fusionsolar"
        self.if2token = "XXXXXXX"

    def print(self):
        self.logger.info(f"Current settings:")

        self.logger.info(f"_Generic:")
        self.logger.info(f"debug:   {self.debug}")
        self.logger.info(f"timezone: {self.tmzone}")
        self.logger.info(f"jsonurl: {self.fusionsolarurl}")
        self.logger.info(f"fusionsolarkkid: {self.fusionsolarkkid}")
        self.logger.info(f"sysname: {self.pvsysname}")
        self.logger.info(f"interval: {self.pvinterval}")

        self.logger.info(f"_Influxdb:")
        self.logger.info(f"influx: {self.influx}")
        self.logger.info(f"influx2: {self.influx2}")
        self.logger.info(f"host: {self.ifhost}")
        self.logger.info(f"port: {self.ifport}")
        self.logger.info(f"_Influxdb_v1:")
        self.logger.info(f"database: {self.if1dbname}")
        self.logger.info(f"user: {self.if1user}")
        self.logger.info(f"password: **secret**")
        self.logger.info(f"_Influxdb_v2:")
        self.logger.info(f"protocol: {self.if2protocol}")
        self.logger.info(f"organization: {self.if2org}")
        self.logger.info(f"bucket: {self.if2bucket}")
        self.logger.info(f"token: {self.if2token}")

    def getenv(self, envvar):
        envval = os.getenv(envvar)
        self.logger.debug(f"Pulled '{envvar}={envval}' from the environment")
        return envval

    def apply_environment_settings(self):
        self.logger.info(f"Processing environment variables to running config")
        if os.getenv("pvverbose") != None:
            self.debug = self.getenv("pvverbose")
        if os.getenv("pvtmzone") != None:
            self.tmzone = self.getenv("pvtmzone")
        if os.getenv("pvfusionsolarurl") != None:
            self.fusionsolarurl = self.getenv("pvfusionsolarurl")
        if os.getenv("pvfusionsolarkkid") != None:
            self.fusionsolarkkid = self.getenv("pvfusionsolarkkid")
        if os.getenv("pvsysname") != None:
            self.pvsysname = self.getenv("pvsysname")
        if os.getenv("pvinterval") != None:
            self.pvinterval = int(self.getenv("pvinterval"))
        if os.getenv("pvinflux") != None:
            self.influx = self.getenv("pvinflux")
        if os.getenv("pvinflux2") != None:
            self.influx2 = self.getenv("pvinflux2")
        if os.getenv("pvif1dbname") != None:
            self.if1dbname = self.getenv("pvif1dbname")
        if os.getenv("pvif2protocol") != None:
            self.if2protocol = self.getenv("pvif2protocol")
        if os.getenv("pvifhost") != None:
            self.ifhost = self.getenv("pvifhost")
        if os.getenv("pvifport") != None:
            self.ifport = int(self.getenv("pvifport"))
        if os.getenv("pvif1user") != None:
            self.if1user = self.getenv("pvif1user")
        if os.getenv("pvifpassword") != None:
            self.if1passwd = self.getenv("pvifpassword")
        if os.getenv("pvif2org") != None:
            self.if2org = self.getenv("pvif2org")
        if os.getenv("pvif2bucket") != None:
            self.if2bucket = self.getenv("pvif2bucket")
        if os.getenv("pvif2token") != None:
            self.if2token = self.getenv("pvif2token")
