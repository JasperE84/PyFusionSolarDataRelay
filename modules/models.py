from typing import List


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


class KenterTransformerKpi:
    def __init__(
        self,
        descriptive_name: str = "",
        connection_id: str = "",
        metering_point_id: str = "",
        channel_id: str = "",
        measurements: List[KenterTransformerMeasurement] = []
    ):
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


class FusionSolarInverterKpi:
    def __init__(
        self,
        descriptive_name: str = "",

        station_name: str = "",
        station_dn: str = "",
        data_source: str = "",

        real_time_power_w: float = 0.0,
        cumulative_energy_wh: float = 0.0,
        day_energy_wh: float = 0.0,
    ):
        self.descriptive_name = descriptive_name
        self.station_name = station_name
        self.station_dn = station_dn
        self.data_source = data_source
        self.real_time_power_w = real_time_power_w
        self.lifteime_energy_wh = cumulative_energy_wh
        self.day_energy_wh = day_energy_wh

    descriptive_name: str
    station_name: str
    station_dn: str
    data_source: str
    real_time_power_w: float
    lifteime_energy_wh: float
    day_energy_wh: float
