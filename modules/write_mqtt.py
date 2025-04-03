import re
import json
import paho.mqtt.publish as publish
from datetime import datetime
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterKpi

class WriteMqtt:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WriteMqtt class instantiated")

    def publish_pvdata_to_mqtt(self, inverter_data: FusionSolarInverterKpi):
        """
        Publish each field of the inverter data as a separate MQTT topic.
        """
        # Prepare connection/auth info
        if self.conf.mqtt_auth:
            auth_obj = dict(
                username=self.conf.mqtt_username,
                password=self.conf.mqtt_password
            )
        else:
            auth_obj = None

        # Clean up stationDn for use in MQTT topic (remove non-alphanumeric)
        station_dn_sanitized = re.sub(r'\W+', '-', inverter_data.stationDn)

        # Construct base topic path
        # e.g. rootTopic / kiosk_site_name / sensors / inverters / stationDn
        mqtt_base_topic = (
            f"{self.conf.mqtt_root_topic}/"
            f"{self.conf.site_name}/sensors/inverters/"
            f"{inverter_data.dataSource}/{station_dn_sanitized}/state"
        )

        # Gather the data in a dict
        # Note that 'device' and 'time' are optional—include them if you want 
        # these published to MQTT as well.
        data_points = {
            "realTimePowerW": inverter_data.realTimePowerW,
            "cumulativeEnergyWh": inverter_data.cumulativeEnergyWh,
            "monthEnergyWh": inverter_data.monthEnergyWh,
            "dailyEnergyWh": inverter_data.dailyEnergyWh,
            "yearEnergyWh": inverter_data.yearEnergyWh
        }

        try:
            # Publish each data point to its own topic
            for key, value in data_points.items():
                topic = f"{mqtt_base_topic}/{key}"
                self.logger.info(f"Publishing to MQTT topic: {topic}, value: {value}")
                publish.single(
                    topic,
                    payload=json.dumps(value),
                    qos=0,
                    retain=False,
                    hostname=self.conf.mqtt_host,
                    port=self.conf.mqtt_port,
                    client_id=self.conf.site_name,
                    keepalive=60,
                    auth=auth_obj,
                )

        except TimeoutError as e:
            self.logger.error(f"Timeout while publishing to MQTT: '{str(e)}'")
        except ConnectionRefusedError as e:
            self.logger.error(f"Connection refused while connecting to MQTT: '{str(e)}'")
        except Exception as e:
            raise Exception(f"Exception while publishing to MQTT: '{str(e)}'")



"""
    def publish_pvdata_to_mqtt(self, inverter_data: FusionSolarInverterKpi):
        jsonmsg = json.dumps(self.make_json_pvdata_mqtt_obj(inverter_data))

        if self.conf.mqtt_auth:
            auth_obj = dict(username=self.conf.mqtt_username, password=self.conf.mqttpasswd)
        else:
            auth_obj = None

        mqtt_root_topic = "{}/{}/sensors/inverters/{}-kiosk".format(self.conf.mqtt_root_topic, self.conf.site_name, re.sub(r'\W+', '-', inverter_data.stationDn))

        try:
            self.logger.info("Publishing to MQTT. Data: {}".format(jsonmsg))
            publish.single(
                mqtt_root_topic,
                payload=jsonmsg,
                qos=0,
                retain=False,
                hostname=self.conf.mqtt_host,
                port=self.conf.mqtt_port,
                client_id=self.conf.site_name,
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

    def make_json_pvdata_mqtt_obj(self, inverter_data: FusionSolarInverterKpi) -> dict:
        timestamp = datetime.now().replace(microsecond=0).isoformat()
        device_name = self.conf.site_name

        return {
            "device": device_name,
            "time": timestamp,
            "values": {
                "stationName": inverter_data.stationName,
                "stationDn": inverter_data.stationDn,
                "realTimePower": inverter_data.realTimePowerW,
                "cumulativeEnergy": inverter_data.cumulativeEnergyWh,
                "monthEnergy": inverter_data.monthEnergy,
                "dailyEnergy": inverter_data.dailyEnergy,
                "yearEnergy": inverter_data.yearEnergy
            }
        }
"""