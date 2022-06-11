verrel = "1.0.0"

import sys

from pvconf import Conf
from pvrelay import Relay

conf = Conf(verrel)
if conf.verbose: conf.print()

relay = Relay(conf)
try:
	relay.main(conf)
except KeyboardInterrupt:
	print("Ctrl C - Stopping relay")
	sys.exit(1)

