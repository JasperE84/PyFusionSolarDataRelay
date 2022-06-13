from datetime import datetime
import json
import requests
import time

import paho.mqtt.publish as publish

class PvMqtt:
    def __init__(self, conf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("PvMqtt class instantiated")

    def publish_to_mqtt(self, fusionsolar_json_data):
        jsonmsg = json.dumps(self.make_json_data_obj(fusionsolar_json_data))

        if self.conf.mqttauth: 
            auth_obj = dict(username=self.conf.mqttuser, password=self.conf.mqttpasswd)
        else:
            auth_obj = None

        try: 
            publish.single(
                self.conf.mqtttopic,
                payload=jsonmsg, 
                qos=0, 
                retain=False, 
                hostname=self.conf.mqtthost,
                port=self.conf.mqttport, 
                client_id=self.conf.pvsysname, 
                keepalive=60, 
                auth=auth_obj
            )
            self.logger.info("Published data to MQTT: {}".format(str(jsonmsg))) 

        except TimeoutError as e:     
            self.logger.error("Timeout while publishing to MQTT: '{}'".format(str(e))) 
        except ConnectionRefusedError as e:     
            self.logger.error("Connection refused while connecting to MQTT: '{}'".format(str(e)))     
        except Exception as e:
            raise Exception("Exception while publishing to MQTT: '{}'".format(str(e)))

    def make_json_data_obj(self, response_json_data):
        jsondate = datetime.now().replace(microsecond=0).isoformat()
        jsonobj = {
                    "device" : self.conf.pvsysname,
                    "time" : jsondate,
                    "values" : {}
                    }
        
        jsonobj["values"]["currentPower"] = response_json_data["powerCurve"]["currentPower"]

        floatKeys = {"realTimePower", "cumulativeEnergy", "monthEnergy", "dailyEnergy", "yearEnergy"}
        for floatKey in floatKeys:
            jsonobj["values"][floatKey] = response_json_data["realKpi"][floatKey]       
                
        return jsonobj
