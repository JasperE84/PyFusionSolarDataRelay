import sys
import logging
from pvconf import PvConf
from pvinflux import PvInflux
from pvrelay import PvRelay
from pvoutputorg import PvOutputOrg

# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.info("PyFusionSolarDataRelay started")

# Config
conf = PvConf(logger)
if conf.debug:
    logger.debug("Enabled verbose logging")
    logger.setLevel(logging.DEBUG)
    conf.print()
else:
    logger.setLevel(logging.INFO)

# Setup InfluxDB
pvinflux = PvInflux(conf, logger)
pvinflux.initialize()

# Setup PVOutput
pvoutput = PvOutputOrg(conf, logger)

# Start relay
relay = PvRelay(conf, pvinflux, pvoutput, logger)
try:
    relay.main()
except KeyboardInterrupt:
    logger.info("Ctrl C - Stopping relay")
    sys.exit(0)
