class FusionSolarInverterKpi:
    """
    Holds the KPI values for a FusionSolar inverter fetched from the kiosk's API.
    """

    def __init__(
        self,
        stationName: str = "",
        stationDn: str = "",
        dataSource: str = "",
        realTimePowerW: float = 0.0,
        cumulativeEnergyWh: float = 0.0,
        monthEnergyWh: float = 0.0,
        dailyEnergyWh: float = 0.0,
        yearEnergyWh: float = 0.0,
    ):
        self.station_name = stationName
        self.station_dn = stationDn
        self.data_source = dataSource
        self.real_time_power_w = realTimePowerW
        self.cumulative_energy_wh = cumulativeEnergyWh
        self.monthEnergyWh = monthEnergyWh
        self.dailyEnergyWh = dailyEnergyWh
        self.yearEnergyWh = yearEnergyWh

    station_name: str
    station_dn: str
    data_source: str
    real_time_power_w: float
    cumulative_energy_wh: float
    monthEnergyWh: float
    dailyEnergyWh: float
    yearEnergyWh: float
