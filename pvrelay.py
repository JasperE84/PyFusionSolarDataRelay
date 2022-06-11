#PyFluxFusionSolarKiosk Growatt monitor :  Relay 
#       
# Updated: 2022-06-08
# Version 1.0.0

from datetime import datetime, timedelta
import time
import requests
import json
import html
import traceback

class Relay:

    def __init__(self, conf):
        print("\nPyFluxFusionSolarKiosk relay mode started")

    def main(self,conf):
        while 1:
            try:
                if conf.verbose: print("Requesting data from FusionSolar Kiosk API...")
                try:
                    response = requests.get(conf.pvurl)
                    response_json = response.json()
                except:
                    raise Exception('Error fetching data from FusionSolar Kiosk API')

                if not "data" in response_json : raise Exception(f'FusionSolar API response does not contain data key. Response: {response_json}')
                response_json_data_decoded = html.unescape(response_json["data"])

                response_json_data = json.loads(response_json_data_decoded)
                if not "realKpi" in response_json_data_decoded : raise Exception(f'Element "realKpi" is missing in API response data')
                print(f'FusionSolar API response: {response_json_data["realKpi"]}')

                current_date = datetime.now().replace(microsecond=0).isoformat()

                if conf.influx:      
                    if conf.verbose : print("PyFluxFusionSolarKiosk InfluxDB publihing started")
                    try:  
                        import  pytz             
                    except: 
                        if conf.verbose :  print("PyFluxFusionSolarKiosk PYTZ Library not installed in Python, influx processing disabled")    
                        conf.influx = False
                        return
                    try: 
                        local = pytz.timezone(conf.tmzone) 
                    except : 
                        if conf.verbose :  
                            if conf.tmzone ==  "local":  print("Timezone local specified, default timezone used")
                            else : print("PyFluxFusionSolarKiosk unknown timezone : ",conf.tmzone,", default timezone used")
                        conf.tmzone = "local"
                        local = int(time.timezone/3600)

                    if conf.tmzone == "local": 
                       curtz = time.timezone 
                       utc_dt = datetime.strptime (current_date, "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=curtz) 
                    else :      
                        naive = datetime.strptime (current_date, "%Y-%m-%dT%H:%M:%S")
                        local_dt = local.localize(naive, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)
                    
                    ifdt = utc_dt.strftime ("%Y-%m-%dT%H:%M:%S")
                    if conf.verbose :  print("PyFluxFusionSolarKiosk original time : ",current_date,"adjusted UTC time for influx : ",ifdt)
               
                    ifobj = {
                                "measurement" : conf.pvsysname,
                                "time" : ifdt,
                                "fields" : {}
                            }    

                    floatKeys = {'realTimePower','cumulativeEnergy'}
                    for floatKey in floatKeys:
                        if floatKey in response_json_data["realKpi"]:
                            ifobj["fields"][floatKey] = float(response_json_data["realKpi"][floatKey]) * float(1000)
                        else:
                            raise Exception(f'FusionSolar API data response element does cot contain key {floatKey}.')
                    
                    ifjson = [ifobj]

                    print("PyFluxFusionSolarKiosk InfluxDB json input: ",str(ifjson))   
              
                    try: 
                        if (conf.influx2):
                            if conf.verbose :  print("PyFluxFusionSolarKiosk write to InfluxDB V2") 
                            ifresult = conf.ifwrite_api.write(conf.ifbucket,conf.iforg,ifjson)   
                        else: 
                            if conf.verbose :  print("PyFluxFusionSolarKiosk write to InfluxDB V1") 
                            ifresult = conf.influxclient.write_points(ifjson)
                    except Exception as e:
                        print("PyFluxFusionSolarKiosk InfluxDB write error")
                        print(e) 
                        raise SystemExit("PyFluxFusionSolarKiosk Influxdb write error, script will be stopped") 
                        
                else: 
                    if conf.verbose : print("PyFluxFusionSolarKiosk Send data to Influx disabled ")    

            except Exception as e: 
                if conf.verbose : print("PyFluxFusionSolarKiosk error")
                print(e)
                traceback.print_exc()
            time.sleep(conf.pvinterval)

