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
        self.stationName = stationName
        self.stationDn = stationDn
        self.dataSource = dataSource
        self.realTimePowerW = realTimePowerW
        self.cumulativeEnergyWh = cumulativeEnergyWh
        self.monthEnergyWh = monthEnergyWh
        self.dailyEnergyWh = dailyEnergyWh
        self.yearEnergyWh = yearEnergyWh

    stationName: str
    stationDn: str
    dataSource: str
    realTimePowerW: float
    cumulativeEnergyWh: float
    monthEnergyWh: float
    dailyEnergyWh: float
    yearEnergyWh: float
