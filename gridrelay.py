import time
from pvinflux import PvInflux
from pvoutputorg import PvOutputOrg
from pvconf import PvConf
from gridkenter import GridKenter
from pvmqtt import PvMqtt


class GridRelay:
    def __init__(self, conf: PvConf, logger):
        self.conf = conf
        self.logger = logger
        self.logger.debug("GridRelay class instantiated")

        self.gridkenter = GridKenter(conf, logger)
        self.pvoutput = PvOutputOrg(conf, logger)
        self.pvmqtt = PvMqtt(conf, logger)
        self.pvinflux = PvInflux(self.conf, self.logger)
        self.pvinflux_initialized = False

        self.logger.info("Starting GridRelay on separate thread")
        self.start()

    def start(self):
        self.logger.debug("GridRelay waiting 5sec to initialize docker-compose containers")
        time.sleep(5)
        
        daystobackfill = self.conf.gridrelaydaystobackfill

        while 1:
            try:
                for daysback in range(self.conf.gridrelaydaysback, self.conf.gridrelaydaysback + 1 + daystobackfill):
                    grid_measurement_data = self.gridkenter.fetch_gridkenter_data(self.conf.gridrelaysysname, self.conf.gridrelaykenterean, self.conf.gridrelaykentermeterid, daysback)
                    self.write_gridkenter_to_influxdb(grid_measurement_data)
                    self.write_gridkenter_to_pvoutput(grid_measurement_data)

                    if self.conf.gridrelaysys02enabled:
                        grid_measurement_data = self.gridkenter.fetch_gridkenter_data(self.conf.gridrelaysysname02, self.conf.gridrelaykenterean02, self.conf.gridrelaykentermeterid02, daysback)
                        self.write_gridkenter_to_influxdb(grid_measurement_data)
                        #No support for pvoutput on 2 EAN codes yet (needs summing of kenter data or pvoutput support for 2 distinct systems)
                        #self.write_gridkenter_to_pvoutput(grid_measurement_data)

                    # Wait 5 secs for next backfill day
                    if daystobackfill > 0: time.sleep(5);

                # Don't backfill after initial backfill
                daystobackfill = 0
            except:
                self.logger.exception(
                    "Uncaught exception in GridRelay data processing loop."
                )

            self.logger.debug("Waiting for next interval...")
            time.sleep(self.conf.gridrelayinterval)

    def write_gridkenter_to_pvoutput(self, grid_measurement_data):
        if self.conf.pvoutput:
            try:
                self.pvoutput.write_griddata_to_pvoutput(grid_measurement_data)
            except:
                self.logger.exception("Error writing GridData to PVOutput.org")

    def write_gridkenter_to_influxdb(self, grid_measurement_data):
        if self.conf.influx:
            if self.pvinflux_initialized == False:
                self.pvinflux_initialized = self.pvinflux.initialize()

            if self.pvinflux_initialized:
                self.pvinflux.pvinflux_write_griddata(grid_measurement_data)
        else:
            self.logger.debug("Writing data to Influx skipped, not initialized yet.")


