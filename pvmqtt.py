import json
import paho.mqtt.publish as publish
from datetime import datetime
from pvconfmodels import BaseConf

class PvMqtt:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvMqtt class instantiated")

    def publish_pvdata_to_mqtt(self, fusionsolar_json_data):
        jsonmsg = json.dumps(self.make_json_pvdata_obj(fusionsolar_json_data))

        if self.conf.mqtt_auth:
            auth_obj = dict(username=self.conf.mqtt_username, password=self.conf.mqttpasswd)
        else:
            auth_obj = None

        try:
            self.logger.info("Publishing to MQTT. Data: {}".format(jsonmsg))
            publish.single(
                self.conf.mqtt_topic,
                payload=jsonmsg,
                qos=0,
                retain=False,
                hostname=self.conf.mqtt_host,
                port=self.conf.mqtt_port,
                client_id=self.conf.fusionsolar_kiosk_site_name,
                keepalive=60,
                auth=auth_obj,
            )

        except TimeoutError as e:
            self.logger.error("Timeout while publishing to MQTT: '{}'".format(str(e)))
        except ConnectionRefusedError as e:
            self.logger.error(
                "Connection refused while connecting to MQTT: '{}'".format(str(e))
            )
        except Exception as e:
            raise Exception("Exception while publishing to MQTT: '{}'".format(str(e)))

    def make_json_pvdata_obj(self, response_json_data):
        jsondate = datetime.now().replace(microsecond=0).isoformat()
        jsonobj = {"device": self.conf.fusionsolar_kiosk_site_name, "time": jsondate, "values": {}}

        jsonobj["values"]["currentPower"] = response_json_data["powerCurve"][
            "currentPower"
        ]

        floatKeys = {
            "realTimePower",
            "cumulativeEnergy",
            "monthEnergy",
            "dailyEnergy",
            "yearEnergy",
        }
        
        for floatKey in floatKeys:
            jsonobj["values"][floatKey] = response_json_data["realKpi"][floatKey]

        return jsonobj
