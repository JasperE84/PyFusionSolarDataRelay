from typing import List

from modules.conf_models import FusionSolarOpenApiInverterSettings, FusionSolarOpenApiMeterSettings


class KenterTransformerMeasurement:
    def __init__(
        self,
        timestamp: int = 0,
        interval_energy_wh: float = 0.0,
        interval_power_avg_w: float = 0.0,
    ):
        self.timestamp = timestamp
        self.interval_energy_wh = interval_energy_wh
        self.interval_power_avg_w = interval_power_avg_w

    timestamp: int
    interval_energy_wh: float
    interval_power_avg_w: float


class KenterTransformerMeasurements:
    def __init__(self, descriptive_name: str = "", connection_id: str = "", metering_point_id: str = "", channel_id: str = "", measurements: List[KenterTransformerMeasurement] = []):
        self.descriptive_name = descriptive_name
        self.connection_id = connection_id
        self.metering_point_id = metering_point_id
        self.channel_id = channel_id
        self.measurements = measurements

    descriptive_name: str
    connection_id: str
    metering_point_id: str
    channel_id: str
    measurements: List[KenterTransformerMeasurement]


class FusionSolarInverterMeasurement:
    def __init__(
        self,
        settings: FusionSolarOpenApiInverterSettings = None,
        measurement_type: str = "",
        data_source: str = "",
        station_name: str = "",
        station_dn: str = "",
        device_dn: str = "",
        device_name: str = "",
        device_model: str = "",
        device_id: str = "",
        real_time_power_w: float = 0.0,
        lifetime_energy_wh: float = 0.0,
        day_energy_wh: float = 0.0,
    ):
        self.settings = settings
        self.measurement_type = measurement_type
        self.station_name = station_name
        self.station_dn = station_dn
        self.device_dn = device_dn
        self.device_name = device_name
        self.device_model = device_model
        self.device_id = device_id
        self.data_source = data_source
        self.real_time_power_w = real_time_power_w
        self.lifetime_energy_wh = lifetime_energy_wh
        self.day_energy_wh = day_energy_wh

    settings: FusionSolarOpenApiInverterSettings
    measurement_type: str
    station_name: str
    station_dn: str
    device_dn: str
    device_name: str
    device_model: str
    device_id: str
    data_source: str
    real_time_power_w: float
    lifetime_energy_wh: float
    day_energy_wh: float

    @property
    def settings_descriptive_name(self) -> str:
        if self.settings is not None:
            return self.settings.descriptive_name
        return ""

    @property
    def settings_device_id(self) -> str:
        if self.settings is not None:
            return self.settings.dev_id
        return ""
    
class FusionSolarMeterMeasurement:
    def __init__(
        self,
        settings: FusionSolarOpenApiMeterSettings = None,
        measurement_type: str = "",
        data_source: str = "",
        station_name: str = "",
        station_dn: str = "",
        device_dn: str = "",
        device_name: str = "",
        device_model: str = "",
        device_id: str = "",
        active_power_w: float = 0.0,
    ):
        self.settings = settings
        self.measurement_type = measurement_type
        self.station_name = station_name
        self.station_dn = station_dn
        self.device_dn = device_dn
        self.device_name = device_name
        self.device_model = device_model
        self.device_id = device_id
        self.data_source = data_source
        self.active_power_w = active_power_w

    settings: FusionSolarOpenApiInverterSettings
    measurement_type: str
    station_name: str
    station_dn: str
    device_dn: str
    device_name: str
    device_model: str
    device_id: str
    data_source: str
    active_power_w: float

    @property
    def settings_descriptive_name(self) -> str:
        if self.settings is not None:
            return self.settings.descriptive_name
        return ""

    @property
    def settings_device_id(self) -> str:
        if self.settings is not None:
            return self.settings.dev_id
        return ""
