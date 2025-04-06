import re
import json
from socket import gaierror
import paho.mqtt.publish as publish
from modules.conf_models import PyFusionSolarSettings
from modules.models import FusionSolarInverterMeasurement, FusionSolarMeterMeasurement


class WriteMqtt:
    def __init__(self, conf: PyFusionSolarSettings, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("WriteMqtt class instantiated")
        self.hass_discovery_published = []

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
            "descriptive_name": measurement.settings_descriptive_name,
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

        # Publish MQTT device discovery
        self.publish_homeassistant_discovery(station_dn_sanitized, device_dn_sanitized, measurement.measurement_type, measurement.data_source, topic, data_points)

    def publish_grid_data_to_mqtt(self, measurement: FusionSolarMeterMeasurement):
        """
        Publish each field of the meter data as a separate MQTT topic.
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
            "descriptive_name": measurement.settings_descriptive_name,
            "active_power_w": measurement.active_power_w,
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

        # Publish MQTT device discovery
        self.publish_homeassistant_discovery(station_dn_sanitized, device_dn_sanitized, measurement.measurement_type, measurement.data_source, topic, data_points)

    def publish_homeassistant_discovery(self, station_dn_sanitized, device_dn_sanitized, measurement_type, data_source, state_topic, data_points):
        """
        Publish Home Assistant discovery config for each data field.
        Any field ending in '_w' is treated as a power (W) sensor,
        and any field ending in '_wh' is treated as an energy (Wh) sensor.
        """

        # Only proceed if HASS device discovery is enabled
        if not self.conf.mqtt_hass_discovery_enabled:
            return

        # Prepare connection/auth info
        if self.conf.mqtt_auth:
            auth_obj = dict(username=self.conf.mqtt_username, password=self.conf.mqtt_password)
        else:
            auth_obj = None

        # Clean up station and device for unique IDs
        station_dn_sanitized = re.sub(r"\W+", "_", station_dn_sanitized).lower()
        device_dn_sanitized = re.sub(r"\W+", "_", device_dn_sanitized).lower()
        data_source_sanitized = re.sub(r"\W+", "_", data_source).lower()
        measurement_type_sanitized = re.sub(r"\W+", "_", measurement_type).lower()
        device_identifier = f"{station_dn_sanitized}_{measurement_type_sanitized}_{data_source_sanitized}"
        if device_dn_sanitized:
            device_identifier = f"{device_identifier}_{device_dn_sanitized}"
        device_name = data_points.get("descriptive_name", device_identifier)

        # Publish one discovery config message for each sensor-like field
        for field_name, field_value in data_points.items():
            if field_value is None:
                continue  # Skip fields that have no actual value

            # Figure out if sensor is power or energy by suffix
            device_class = None
            unit_of_measurement = None
            state_class = None

            if field_name.endswith("_w"):
                # It's a power sensor
                device_class = "power"
                unit_of_measurement = "W"
                state_class = "measurement"
            elif field_name.endswith("_wh"):
                # It's an energy sensor
                device_class = "energy"
                unit_of_measurement = "Wh"
                # For cumulative energy sensors, setting "state_class=total_increasing"
                # helps with HA’s Energy Dashboard
                state_class = "total_increasing"

            # If it doesn't match either suffix, you can decide to publish it differently
            if device_class is None:
                continue

            # Unique sensor name and MQTT discovery topic
            # Topic format: homeassistant/sensor/<unique_id>/config
            field_name_sanitized = re.sub(r"\W+", "_", field_name).lower()
            unique_sensor_id = f"{device_identifier}_{field_name_sanitized}"
            discovery_topic = f"homeassistant/sensor/{unique_sensor_id}/config"

            # Skip if device is already discovery_published
            if unique_sensor_id in self.hass_discovery_published:
                continue

            # Create the config payload (see Home Assistant MQTT Discovery docs)
            config_payload = {
                "name": f"{field_name}",
                "state_topic": state_topic,
                "uniq_id": unique_sensor_id,
                "device": {
                    "identifiers": [device_identifier],
                    "name": f"{device_name}",
                },
                "value_template": f"{{{{ value_json.{field_name} }}}}",
            }

            # Add the sensor-specific attributes
            if device_class:
                config_payload["device_class"] = device_class
            if state_class:
                config_payload["state_class"] = state_class
            if unit_of_measurement:
                config_payload["unit_of_measurement"] = unit_of_measurement

            # Publish discovery config
            try:
                payload_str = json.dumps(config_payload)
                self.logger.info(f"Publishing Home Assistant discovery config to MQTT topic: {discovery_topic}, payload: {payload_str}")
                publish.single(
                    discovery_topic,
                    payload=payload_str,
                    qos=0,
                    retain=True,  # Retain so HA automatically loads these on restart
                    hostname=self.conf.mqtt_host,
                    port=self.conf.mqtt_port,
                    client_id=self.conf.site_descriptive_name,
                    keepalive=60,
                    auth=auth_obj,
                )
            except TimeoutError as e:
                self.logger.error(f"Timeout while publishing HA discovery to MQTT: '{e}'")
            except ConnectionRefusedError as e:
                self.logger.error(f"Connection refused while connecting to MQTT host: '{e}'")
            except gaierror as e:
                self.logger.error(f"Could not resolve MQTT host: '{e}'")
            except Exception as e:
                self.logger.exception(f"Error publishing HA discovery to MQTT: '{e}'")

            # Add uniqe sensor id to device discovery published history
            self.hass_discovery_published.append(unique_sensor_id)
