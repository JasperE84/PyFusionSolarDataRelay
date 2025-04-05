import re
import json
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

        # Construct base topic path
        # e.g. rootTopic / kiosk_site_descriptive_name / sensors / inverters / stationDn
        def append_if_not_empty(base, addition):
            return f"{base}/{addition}" if addition else base
        
        # Start with the root topic and sequentially append other parts if they are not empty
        mqtt_base_topic = self.conf.mqtt_root_topic.lower()

        # Sequentially build the topic string, checking each segment for emptiness
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, self.conf.site_descriptive_name.lower())
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, "sensors/inverters")
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, measurement.data_source.lower())
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, measurement.settings_descriptive_name.lower())
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, station_dn_sanitized.lower())
        mqtt_base_topic = append_if_not_empty(mqtt_base_topic, "state")

        # Gather the data in a dict
        # Note that 'device' and 'time' are optional—include them if you want
        # these published to MQTT as well.
        data_points = {
            "real_time_power_w": measurement.real_time_power_w,
            "day_energy_wh": measurement.day_energy_wh,
            "lifetime_energy_wh": measurement.lifetime_energy_wh,
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
                    client_id=self.conf.site_descriptive_name,
                    keepalive=60,
                    auth=auth_obj,
                )

        except TimeoutError as e:
            self.logger.error(f"Timeout while publishing to MQTT: '{e}'")
        except ConnectionRefusedError as e:
            self.logger.error(f"Connection refused while connecting to MQTT: '{e}'")
        except Exception as e:
            raise Exception(f"Exception while publishing to MQTT: '{e}'")
