from typing import List
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from modules.conf_env_list_parser import ConfEnvListParser


class BaseMetricConf(BaseSettings):
    enabled: bool = Field(default=True)
    output_influxdb: bool = Field(default=True)


class FusionSolarKioskMetric(BaseMetricConf):
    descriptive_name: str = Field(default="inverter01")
    api_url: str = Field(default="https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk=")
    api_kkid: str = Field(default="GET_THIS_FROM_KIOSK_URL")
    output_mqtt: bool = Field(default=True)
    output_pvoutput: bool = Field(default=True)
    output_pvoutput_system_id: int = Field(default=0)


class KenterMeterMetric(BaseMetricConf):
    descriptive_name: str = Field(default="transformer01")
    connection_id: str = Field(default="XXX")
    metering_point_id: str = Field(default="XXX")


class BaseConf(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    #
    # General settings
    #
    debug_mode: bool = Field(default=True)
    site_descriptive_name: str = Field(default="site01")

    #
    # Inputs
    #
    # FusionSolar
    fusionsolar_kiosk_module_enabled: bool = Field(default=True)
    fusionsolar_kiosks: List[FusionSolarKioskMetric] = Field(default=[])
    fusionsolar_kiosk_fetch_cron_hour: str = Field(default="*")
    fusionsolar_kiosk_fetch_cron_minute: str = Field(default="0,30", description="The fusionsolar API only updates portal data each half hour, setting to lower value will produce weird PVOutput graph with horizontal bits in it.")

    # Kenter Kenter.nl
    kenter_module_enabled: bool = Field(default=False)
    kenter_api_url: str = Field(default="https://api.kenter.nu")
    kenter_token_url: str = Field(default="https://login.kenter.nu/connect/token")
    kenter_clientid: str = Field(default="user")
    kenter_password: str = Field(default="passwd")
    kenter_interval: int = Field(default=43200)
    kenter_days_back: int = Field(default=1, description="Grid infrastructure measurements in The Netherlands, show up in the API with a 3-5 days delay.")
    kenter_days_backfill: int = Field(default=4, description="Setting this to 30 would try to backfill gridkenter data on startup for any day between 3 days back (gridrelaydaysback) and 3+30=33 days back.")
    kenter_metering_points: List[KenterMeterMetric] = Field(default=[])

    #
    # Outputs
    #

    # InfluxDB settings
    influxdb_module_enabled: bool = Field(default=False)
    influxdb_is_v2: bool = Field(default=True, description="Set to True to enable InfluxDB v2, or to False for InfluxDB v1 or VictoriaMetrics")
    influxdb_host: str = Field(default="localhost")
    influxdb_port: int = Field(default=8086)
    # InfluxDB v1 settings
    influxdb_v1_db_name: str = Field(default="fusionsolar")
    influxdb_v1_username: str = Field(default="fusionsolar")
    influxdb_v1_password: str = Field(default="fusionsolar")
    # InfluxDB v2 settings
    influxdb_v2_protocol: str = Field(default="https")
    influxdb_v2_org: str = Field(default="acme")
    influxdb_v2_bucket: str = Field(default="fusionsolar")
    influxdb_v2_token: str = Field(default="XXXXXXX")

    # PVOutput.org
    pvoutput_module_enabled: bool = Field(default=False)
    pvoutput_record_url: str = Field(default="https://pvoutput.org/service/r2/addstatus.jsp")
    pvoutput_batch_url: str = Field(default="https://pvoutput.org/service/r2/addbatchstatus.jsp")
    pvoutput_api_key: str = Field(default="yourapikey")

    # MQTT
    mqtt_module_enabled: bool = Field(default=False)
    mqtt_host: str = Field(default="localhost")
    mqtt_port: int = Field(default=1883)
    mqtt_auth: bool = Field(default=False)
    mqtt_username: str = Field(default="fusionsolar")
    mqtt_password: str = Field(default="fusionsolar")
    mqtt_root_topic: str = Field(default="pyfusionsolar")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (ConfEnvListParser(settings_cls),)
