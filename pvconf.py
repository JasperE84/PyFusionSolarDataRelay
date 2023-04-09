import os

class PvConf:
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug("Conf class instantiated")
        self.apply_default_settings()
        self.apply_environment_settings()

    def apply_default_settings(self):
        self.logger.debug("Setting default conf values")
        
        # Generic default
        self.debug = True
        self.pvsysname = "inverter01"

        # Fusionsolar default
        self.fusionsolar = True
        self.fusionsolarurl = "https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk="
        self.fusionsolarkkid = "GET_THIS_FROM_KIOSK_URL"
        
        # The fusionsolar API only updates portal data each half hour, setting to lower value will produce weird PVOutput graph with horizontal bits in it.
        self.fusionhourcron = "*"
        self.fusionminutecron = "0,30" 

        # Pvoutput default
        self.pvoutput = False
        self.pvoutputapikey = "yourapikey"
        self.pvoutputsystemid = 12345
        self.pvoutputurl = "https://pvoutput.org/service/r2/addstatus.jsp"
        self.pvoutputbatchurl = "https://pvoutput.org/service/r2/addbatchstatus.jsp"

        # Gridrelay default
        # Please note that local server or docker container needs to be in same timezone als meetdata.nl in order for kenter data to work correctly
        self.gridrelay = False
        self.gridrelayinterval = 43200
        self.gridrelaykenterurl = "https://webapi.meetdata.nl"
        self.gridrelaykenteruser = "user"
        self.gridrelaykenterpasswd = "passwd"
        # Grid infrastructure measurements in The Netherlands, show up in the API with a 3-5 days delay.
        self.gridrelaydaysback = 3
        # If fusionsolar updates every 30mins and meetdata.nl has values per 15min, set this to 2 so that intervals between two datasources match to avoid weird pvoutput graphs.
        self.gridrelaypvoutputspan = 2

        self.gridrelaysysname = "transformer01"
        self.gridrelaykenterean = "XXX"
        self.gridrelaykentermeterid = "XXX"

        self.gridrelaysys02enabled = False
        self.gridrelaysysname02 = "transformer02"
        self.gridrelaykenterean02 = "XXX"
        self.gridrelaykentermeterid02 = "XXX"

        # Influxdb default
        self.influx = False
        self.ifhost = "localhost"
        self.ifport = 8086

        # Set to True to enable InfluxDB v2, or to False for InfluxDB v1 or VictoriaMetrics
        self.influx2 = True

        # Influxdb v1 settings
        self.if1dbname = "fusionsolar"
        self.if1user = "fusionsolar"
        self.if1passwd = "fusionsolar"

        # Influxdb v2 settings
        self.if2protocol = "https"
        self.if2org = "acme"
        self.if2bucket = "fusionsolar"
        self.if2token = "XXXXXXX"

        # Mqtt default
        self.mqtt = False
        self.mqtthost = "localhost"
        self.mqttport = 1883
        self.mqttauth = False
        self.mqttuser = "fusionsolar"
        self.mqttpasswd = "fusionsolar"
        self.mqtttopic = "energy/pyfusionsolar"

    def print(self):
        self.logger.info(f"Current settings:")
        self.logger.info(f"_Generic:")
        self.logger.info(f"debug:   {self.debug}")
        self.logger.info(f"_FusionSolar:")
        self.logger.info(f"enabled: {self.fusionsolar}")
        self.logger.info(f"fusionsolarurl: {self.fusionsolarurl}")
        self.logger.info(f"fusionsolarkkid: {self.fusionsolarkkid}")
        self.logger.info(f"sysname: {self.pvsysname}")
        self.logger.info(f"fusionhourcron: {self.fusionhourcron}")
        self.logger.info(f"fusionminutecron: {self.fusionminutecron}")
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
        self.logger.info(f"_PVOutput.org:")
        self.logger.info(f"Enabled: {self.pvoutput}")
        self.logger.info(f"System ID: {self.pvoutputsystemid}")
        self.logger.info(f"API Key: {self.pvoutputapikey}")
        self.logger.info(f"API Url: {self.pvoutputurl}")
        self.logger.info(f"API BatchUrl: {self.pvoutputbatchurl}")
        self.logger.info(f"_MQTT")
        self.logger.info(f"Enabled: {self.mqtt}")
        self.logger.info(f"Host: {self.mqtthost}")
        self.logger.info(f"Port: {self.mqttport}")
        self.logger.info(f"Auth: {self.mqttauth}")
        self.logger.info(f"User: {self.mqttuser}")
        self.logger.info(f"Passwd: {self.mqttpasswd}")
        self.logger.info(f"Topic: {self.mqtttopic}")
        self.logger.info(f"_GridRelay")
        self.logger.info(f"Enabled: {self.gridrelay}")
        self.logger.info(f"Interval: {self.gridrelayinterval}")
        self.logger.info(f"PVOutput span: {self.gridrelaypvoutputspan}")
        self.logger.info(f"Kenter URL: {self.gridrelaykenterurl}")
        self.logger.info(f"Days back: {self.gridrelaydaysback}")
        self.logger.info(f"Kenter User: {self.gridrelaykenteruser}")
        self.logger.info(f"Kenter Passwd: {self.gridrelaykenterpasswd}")

        self.logger.info(f"System name 01: {self.gridrelaysysname}")
        self.logger.info(f"Kenter EAN 01: {self.gridrelaykenterean}")
        self.logger.info(f"Kenter MeterId 01: {self.gridrelaykentermeterid}")

        self.logger.info(f"System name 02: {self.gridrelaysysname02}")
        self.logger.info(f"Kenter EAN 02: {self.gridrelaykenterean02}")
        self.logger.info(f"Kenter MeterId: {self.gridrelaykentermeterid02}")


    def getenv(self, envvar):
        envval = os.getenv(envvar)
        self.logger.debug(f"Pulled '{envvar}={envval}' from the environment")
        return envval

    def apply_environment_settings(self):
        self.logger.info(f"Processing environment variables to running config")
        if os.getenv("pvdebug") != None:
            self.debug = self.getenv("pvdebug") == "True"
        if os.getenv("pvfusionsolar") != None:
            self.fusionsolar = self.getenv("pvfusionsolar") == "True"
        if os.getenv("pvfusionsolarurl") != None:
            self.fusionsolarurl = self.getenv("pvfusionsolarurl")
        if os.getenv("pvfusionsolarkkid") != None:
            self.fusionsolarkkid = self.getenv("pvfusionsolarkkid")
        if os.getenv("pvsysname") != None:
            self.pvsysname = self.getenv("pvsysname")
        if os.getenv("pvfusionhourcron") != None:
            self.fusionhourcron = int(self.getenv("pvfusionhourcron"))
        if os.getenv("pvfusionminutecron") != None:
            self.fusionminutecron = int(self.getenv("pvfusionminutecron"))
        if os.getenv("pvinflux") != None:
            self.influx = self.getenv("pvinflux") == "True"
        if os.getenv("pvinflux2") != None:
            self.influx2 = self.getenv("pvinflux2") == "True"
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
        if os.getenv("pvif1password") != None:
            self.if1passwd = self.getenv("pvif1password")
        if os.getenv("pvif2org") != None:
            self.if2org = self.getenv("pvif2org")
        if os.getenv("pvif2bucket") != None:
            self.if2bucket = self.getenv("pvif2bucket")
        if os.getenv("pvif2token") != None:
            self.if2token = self.getenv("pvif2token")
        
        if os.getenv("pvpvoutput") != None:
            self.pvoutput = self.getenv("pvpvoutput") == "True"
        if os.getenv("pvpvoutputurl") != None:
            self.pvoutputurl = self.getenv("pvpvoutputurl")
        if os.getenv("pvpvoutputbatchurl") != None:
            self.pvoutputbatchurl = self.getenv("pvpvoutputbatchurl")
        if os.getenv("pvpvoutputapikey") != None:
            self.pvoutputapikey = self.getenv("pvpvoutputapikey")
        if os.getenv("pvpvoutputsystemid") != None:
            self.pvoutputsystemid = self.getenv("pvpvoutputsystemid")

        if os.getenv("pvmqtt") != None:
            self.mqtt = self.getenv("pvmqtt") == "True"
        if os.getenv("pvmqtthost") != None:
            self.mqtthost = self.getenv("pvmqtthost")
        if os.getenv("pvmqttport") != None:
            self.mqttport = int(self.getenv("pvmqttport"))
        if os.getenv("pvmqttauth") != None:
            self.mqttauth = self.getenv("pvmqttauth") == "True"
        if os.getenv("pvmqttuser") != None:
            self.mqttuser = self.getenv("pvmqttuser")
        if os.getenv("pvmqttpasswd") != None:
            self.mqttpasswd = self.getenv("pvmqttpasswd")
        if os.getenv("pvmqtttopic") != None:
            self.mqtttopic = self.getenv("pvmqtttopic")

        if os.getenv("pvgridrelay") != None:
            self.gridrelay = self.getenv("pvgridrelay") == "True"
        if os.getenv("pvgridrelayinterval") != None:
            self.gridrelayinterval = int(self.getenv("pvgridrelayinterval"))
        if os.getenv("pvgridrelaykenterurl") != None:
            self.gridrelaykenterurl = self.getenv("pvgridrelaykenterurl")
        if os.getenv("pvgridrelaykenteruser") != None:
            self.gridrelaykenteruser = self.getenv("pvgridrelaykenteruser")
        if os.getenv("pvgridrelaykenterpasswd") != None:
            self.gridrelaykenterpasswd = self.getenv("pvgridrelaykenterpasswd")
        if os.getenv("pvgridrelaydaysback") != None:
            self.gridrelaydaysback = int(self.getenv("pvgridrelaydaysback"))
        if os.getenv("pvgridrelaypvoutputspan") != None:
            self.gridrelaypvoutputspan = int(self.getenv("pvgridrelaypvoutputspan"))

        if os.getenv("pvgridrelaysysname") != None:
            self.gridrelaysysname = self.getenv("pvgridrelaysysname")
        if os.getenv("pvgridrelaykenterean") != None:
            self.gridrelaykenterean = self.getenv("pvgridrelaykenterean")
        if os.getenv("pvgridrelaykentermeterid") != None:
            self.gridrelaykentermeterid = self.getenv("pvgridrelaykentermeterid")

        if os.getenv("pvgridrelaysys02enabled") != None:
            self.gridrelaysys02enabled = self.getenv("pvgridrelaysys02enabled") == "True"
        if os.getenv("pvgridrelaysysname02") != None:
            self.gridrelaysysname02 = self.getenv("pvgridrelaysysname02")
        if os.getenv("pvgridrelaykenterean02") != None:
            self.gridrelaykenterean02 = self.getenv("pvgridrelaykenterean02")
        if os.getenv("pvgridrelaykentermeterid02") != None:
            self.gridrelaykentermeterid02 = self.getenv("pvgridrelaykentermeterid02")

