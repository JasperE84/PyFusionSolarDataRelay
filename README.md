# Huawei FusionSolar Kiosk API to InfluxDB and PVOutput relay
This is a python project intended to fetch data from the **Huawei FusionSolar** public **kiosk** and relay it to **InfluxDB** and/or **PVOutput.org**. 

Credits go to the [Grott project](https://github.com/johanmeijer/grott). Many bits of code, structure and ideas are borrowed from there.

# Installation
This project is currently intented to run as a Docker container and fetches its config from environment variables. Yet the project can be run standalone. 
A local settings file (such as .yml or .ini) has not been implemented yet, but pvconf.py can easily be modified to override standard settings.

Check out [Examples/docker-compose.yml](https://github.com/JasperE84/PyFusionSolarDataRelay/blob/main/Examples/docker-compose.yml) for a docker configuration example.

# About Huawei FusionSolar Kiosk mode
FusionSolar is Huawei's online monitoring platform for their PV inverters. FusionSolar features a kiosk mode. When enabled, a kiosk url is generated which is publically accessible. The kiosk web app fetches its data from a JSON backend. It is this backend where this project fetches the PV data. 

# About PVOutput.org
[PVOutput.org](https://pvoutput.org/) is a free service for sharing and comparing PV output data.

# About InfluxDB
[InfluxDB](https://www.influxdata.com/) is an open source time series database on which dashboards can easily be built. For instance using [Grafana](https://grafana.com/)

# Configuration parameter documentation
| Parameter | Environment variable | Description | Default |
| --- | --- | --- | --- |
| debug | pvdebug | Enables verbose logging | True |
| pvsysname | pvsysname | Definition of 'measurement' name for InfluxDB | inverter01 |
| fusionsolarurl | pvfusionsolarurl | Link to the fusionsolar kiosk data backend | [Click url](https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk=) |
| fusionsolarkkid | pvfusionsolarkkid | Unique kiosk ID, can be found by looking the kiosk URL and then taking the code after `kk=` | GET_THIS_FROM_KIOSK_URL |
| fusioninterval | pvfusioninterval | Seconds between fusionsolar data polling and relay | 120 |
| pvoutput | pvpvoutput | Can be `True` or `False`, determines if PVOutput.org API is enabled | False |
| pvoutputapikey | pvpvoutputapikey | API Key for PVOutput.org | yourapikey |
| pvoutputsystemid | pvoutputsystemid | System ID for PVOutput.org, should be numeric | 12345 |
| pvoutputurl | pvpvoutputurl | API url for PVOutput.org | [Click url](https://pvoutput.org/service/r2/addstatus.jsp)
| influx | pvinflux | Can be `True` or `False`, determines if InfluxDB processing is enabled | False |
| influx2 | pvinflux2 | If `True` the InfluxDBv2 methods are used. If `False` InfluxDBv1 methods are used | True |
| ifhost | pvifhost | Hostname of the influxdb server | localhost |
| ifport | pvifport | Port of influxdb server | 8086 |
| if1dbname | pvif1dbname | Database name for InfluxDBv1, only required if influx2=False | fusionsolar |
| if1user | pvif1user | Username for InfluxDBv1, only required if influx2=False | fusionsolar |
| if1passwd | pvif1passwd | Password for InfluxDBv1, only required if influx2=False | fusionsolar |
| if2protocol | pvif2protocol | Protocol for InfluxDBv2, can be `https` or `http`, only required if influx2=True | https |
| if2org | pvif2org | Organization for InfluxDBv2, only required if influx2=True | acme |
| if2bucket | pvif2bucket | Bucket for InfluxDBv2, only required if influx2=True | fusionsolar |
| if2token | pvif2token | Token for InfluxDBv2, only required if influx2=True | XXXXXXX |

# Grafana dashboard example
A grafana dashboard export is included in the Examples subfolder in the Git repository.
![Grafana dashboard screenshot](./Examples/grafana-screenshot.png)