import re
import json
from socket import gaierror
import paho.mqtt.publish as publish
from datetime import datetime
from modules.conf_models import BaseConf
from modules.models import FusionSolarInverterMeasurement


class WriteMqtt:
    def __init__(self, conf: BaseConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WriteMqtt class instantiated")

    def publish_pvdata_to_mqtt(self, measurement: FusionSolarInverterMeasurement):
        """
        Publish each field of the inverter data as a separate MQTT topic.
        """
        # Prepare connection/auth info
        if self.conf.mqtt_auth:
            auth_obj = dict(username=self.conf.mqtt_username, password=self.conf.mqtt_password)
        else:
            auth_obj = None

        # Clean up stationDn for use in MQTT topic (remove non-alphanumeric)
        station_dn_sanitized = re.sub(r"\W+", "-", measurement.station_dn)
        device_dn_sanitized = re.sub(r"\W+", "-", measurement.device_dn)

        # Construct base topic path
        # e.g. rootTopic / kiosk_site_descriptive_name / sensors / inverters / stationDn
        def append_if_not_empty(base, addition):
            return f"{base}/{addition}" if addition else base
        
        # Start with the root topic and sequentially append other parts if they are not empty
        topic = self.conf.mqtt_root_topic.lower()

        # Sequentially build the topic string, checking each segment for emptiness
        topic = append_if_not_empty(topic, self.conf.site_descriptive_name.lower())
        topic = append_if_not_empty(topic, "sensors")
        topic = append_if_not_empty(topic, measurement.data_source.lower())
        topic = append_if_not_empty(topic, f"{measurement.measurement_type.lower()}s")
        topic = append_if_not_empty(topic, station_dn_sanitized.lower())      
        topic = append_if_not_empty(topic, device_dn_sanitized.lower())
        topic = append_if_not_empty(topic, "state")

        data_points = {
            "descriptive_name" : measurement.settings_descriptive_name,
            "real_time_power_w": measurement.real_time_power_w,
            "lifetime_energy_wh": measurement.lifetime_energy_wh,
            "day_energy_wh": measurement.day_energy_wh,
        }

        try:
            value = json.dumps(data_points)
            self.logger.info(f"Publishing to MQTT topic: {topic}, value: {value}")
            publish.single(
                topic,
                payload=value,
                qos=0,
                retain=False,
                hostname=self.conf.mqtt_host,
                port=self.conf.mqtt_port,
                client_id=self.conf.site_descriptive_name,
                keepalive=60,
                auth=auth_obj,
            )

        except TimeoutError as e:
            self.logger.error(f"Timeout while publishing to MQTT: '{e}'")
        except ConnectionRefusedError as e:
            self.logger.error(f"Connection refused while connecting to MQTT host: '{e}'")
        except gaierror as e:
            self.logger.error(f"Could not get address info (resolve) MQTT host: '{e}'")
        except Exception as e:
            raise Exception(f"Exception while publishing to MQTT: '{e}'")
