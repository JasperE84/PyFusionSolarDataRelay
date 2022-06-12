# PyFusionSolarDataRelay
This is a python project intended to fetch data from the **Huawei FusionSolar** public **kiosk** and relay it to **InfluxDB** and/or **PVOutput.org**. 

Credits go to the [Grott project](https://github.com/johanmeijer/grott). Many bits of code, structure and ideas are borrowed from there.

# Installation
This project is currently intented to run as a Docker container and fetches its config from environment variables. Yet the project can be run standalone. 
A local settings file (such as .yml or .ini) has not been implemented yet, but pvconf.py can easily be modified to override standard settings.

Check out [Examples/docker-compose.yml](https://github.com/JasperE84/PyFusionSolarDataRelay/blob/main/Examples/docker-compose.yml) for a docker configuration example.
