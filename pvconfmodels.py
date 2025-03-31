from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

class BaseConf(BaseSettings):
    debug_mode: bool = Field(default=True)

    fusionsolar_kiosk_enabled: bool = Field(default=True)
    fusionsolar_kiosk_api_url: str = Field(default="https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk=")
    fusionsolar_kiosk_api_kkid: str = Field(default="GET_THIS_FROM_KIOSK_URL")
    fusionsolar_kiosk_site_name: str = Field(default="inverter01")

     # The fusionsolar API only updates portal data each half hour, setting to lower value will produce weird PVOutput graph with horizontal bits in it.
    fusionsolar_kiosk_fetch_cron_hour: str = Field(default="*")
    fusionsolar_kiosk_fetch_cron_minute: str = Field(default="0,30")

    # InfluxDB settings
    influxdb_enabled: bool = Field(default=False)
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
    pvoutput_enabled: bool = Field(default=False)
    pvoutput_record_url: str = Field(default="https://pvoutput.org/service/r2/addstatus.jsp")
    pvoutput_batch_url: str = Field(default="https://pvoutput.org/service/r2/addbatchstatus.jsp")
    pvoutput_api_key: str = Field(default="yourapikey")
    pvoutput_system_id: int = Field(default=12345)

    # MQTT
    mqtt_enabled: bool = Field(default=False)
    mqtt_host: str = Field(default="localhost")
    mqtt_port: int = Field(default=1883)
    mqtt_auth: bool = Field(default=False)
    mqtt_username: str = Field(default="fusionsolar")
    mqtt_password: str = Field(default="fusionsolar")
    mqtt_topic: str = Field(default="energy/pyfusionsolar")

    # Kenter Meetdata.nl
    meetdata_nl_enabled: bool = Field(default=False)
    meetdata_nl_interval: int = Field(default=43200)
    meetdata_nl_api_url: str = Field(default="https://webapi.meetdata.nl")
    meetdata_nl_username: str = Field(default="user")
    meetdata_nl_password: str = Field(default="passwd")
    meetdata_nl_days_back: int = Field(default=3, description="Grid infrastructure measurements in The Netherlands, show up in the API with a 3-5 days delay.")
    meetdata_nl_days_backfill: int = Field(default=0, description="Setting this to 30 would try to backfill gridkenter data on startup for any day between 3 days back (gridrelaydaysback) and 3+30=33 days back.")

    # If fusionsolar updates every 30mins and meetdata.nl has values per 15min, set this to 2 so that intervals between two datasources match to avoid weird pvoutput graphs.
    meetdata_nl_pvoutput_span: int = Field(default=2)
 
    meetdata_nl_meter_sysname: str = Field(default="transformer01")
    meetdata_nl_meter_ean: str = Field(default="XXX")
    meetdata_nl_meter_id: str = Field(default="XXX")

    meetdata_nl_meter2_enabled: bool = Field(default=False)
    meetdata_nl_meter2_sysname: str = Field(default="transformer02")
    meetdata_nl_meter2_ean: str = Field(default="XXX")
    meetdata_nl_meter2_id: str = Field(default="XXX")