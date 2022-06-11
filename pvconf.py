#
# pvconf process command parameter and settings file
# Updated: 2021-06-07
# Version 1.0.0

import os
import ipaddress 
class Conf : 

    def __init__(self, vrm): 
        self.verrel = vrm

        #Set default variables 
        self.verbose = True
        self.tmzone = "local"

        #pvoutput default
        self.pvsysname = "inverter01"
        self.pvurl = "https://region01eu5.fusionsolar.huawei.com/rest/pvms/web/kiosk/v1/station-kiosk-file?kk=XXXXXX"
        self.pvinterval = 60

        #influxdb default 
        self.influx = True
        self.influx2 = True
        self.ifdbname = "fusionsolar"
        self.ifip = "localhost"
        self.ifport = 8086
        self.ifuser = "fusionsolar"
        self.ifpsw  = "fusionsolar"
        self.iftoken  = "XXXXXXX"
        self.iforg  = "acme"
        self.ifbucket = "fusionsolar" 

        print("Fusion solar logging monitor : " + self.verrel)    
        
        self.procenv()

        #prepare influxDB
        if self.influx :  
            if self.ifip == "localhost" : self.ifip = '0.0.0.0'
            self.print()
			#InfluxDB V1
            if self.influx2 == False: 
                if self.verbose :  print("PyFluxFusionSolarKiosk InfluxDB V1 initialization started")
                try:     
                    from influxdb import InfluxDBClient
                except: 
                    if self.verbose :  print("PyFluxFusionSolarKiosk InfluxDB V1 python library not installed")
                    self.influx = False
                    raise SystemExit("PyFluxFusionSolarKiosk InfluxDB V1 python library initialisation error")

                self.influxclient = InfluxDBClient(host=self.ifip, port=self.ifport, timeout=3, username=self.ifuser, password=self.ifpsw)   
                
                try: 
                    databases = [db['name'] for db in self.influxclient.get_list_database()]
                except Exception as e: 
                    if self.verbose :  print("PyFluxFusionSolarKiosk cannot fetch list of databases from InfluxDB")   
                    self.influx = False
                    print("\t -", e)
                    raise SystemExit("PyFluxFusionSolarKiosk cannot fetch list of databases from InfluxDB")

                if self.ifdbname not in databases:
                    if self.verbose :  print(f'PyFluxFusionSolarKiosk database {self.ifdbname} not yet defined in InfluxDB, creating new database')        
                    try: 
                        self.influxclient.create_database(self.ifdbname)
                    except: 
                        if self.verbose :  print("PyFluxFusionSolarKiosk Unable to create or connect to influx database:" ,  self.ifdbname," check user authorisation") 
                        self.influx = False
                        raise SystemExit("PyFluxFusionSolarKiosk Unable to create or connect to influx database:" ,  self.ifdbname," check user authorisation")

                self.influxclient.switch_database(self.ifdbname)

			#InfluxDB V2
            else: 

                if self.verbose :  print("PyFluxFusionSolarKiosk InfluxDB V2 initialization started")
                try:     
                    from influxdb_client import InfluxDBClient
                    from influxdb_client.client.write_api import SYNCHRONOUS
                except: 
                    if self.verbose :  print("PyFluxFusionSolarKiosk InfluxDB-client Library not installed in Python")
                    self.influx = False
                    raise SystemExit("PyFluxFusionSolarKiosk InfluxDB-client Library not installed in Python")

                self.influxclient = InfluxDBClient(url="{}:{}".format(self.ifip, self.ifport),org=self.iforg, token=self.iftoken)
                self.ifbucket_api = self.influxclient.buckets_api()
                self.iforganization_api = self.influxclient.organizations_api()              
                self.ifwrite_api = self.influxclient.write_api(write_options=SYNCHRONOUS)
                
                try:
                    buckets = self.ifbucket_api.find_bucket_by_name(self.ifbucket)
                    organizations = self.iforganization_api.find_organizations()  
                    if buckets == None:
                        print("InfluxDB V2 bucket ", self.ifbucket, "not defined")  
                        self.influx = False      
                        raise SystemExit("PyFluxFusionSolarKiosk InfluxDB V2 bucket ", self.ifbucket, "not defined") 
                    orgfound = False    
                    for org in organizations: 
                        if org.name == self.iforg:
                            orgfound = True
                            break
                    if not orgfound: 
                        print("InfluxDB V2 organization", self.iforg, "not defined or no authorisation to check")  
                        ##self.influx = False  
                        ##raise SystemExit("PyFluxFusionSolarKiosk Influxdb initialisation error")

                except Exception as e:
                    if self.verbose :  print("PyFluxFusionSolarKiosk error: can not contact InfluxDB V2")   
                    print(e)
                    self.influx = False
                    raise SystemExit("PyFluxFusionSolarKiosk Influxdb initialisation error") 
            
    def print(self): 
        print("\nPyFluxFusionSolarKiosk settings:\n")
        print("_Generic:")
        print("\tversion:     \t",self.verrel)
        print("\tverbose:     \t",self.verbose)
        print("\ttimezone:    \t",self.tmzone)
        print("\turl:         \t",self.pvurl)
        print("\tsysname:     \t",self.pvsysname)
        print("\tinterval:    \t",self.pvinterval)
        print("_Influxdb:")
        print("\tinflux:      \t",self.influx)
        print("\tinflux2:     \t",self.influx2)
        print("\tdatabase:    \t",self.ifdbname)
        print("\tip:          \t",self.ifip)
        print("\tport:        \t",self.ifport)
        print("\tuser:        \t",self.ifuser)        
        print("\tpassword:    \t","**secret**")
        print("\torganization:\t",self.iforg ) 
        print("\tbucket:      \t",self.ifbucket) 
        print("\ttoken:       \t",self.iftoken)

    def getenv(self, envvar):
        envval = os.getenv(envvar)
        if self.verbose: print(f"\nPulled '{envvar}={envval}' from the environment")
        return envval

    def procenv(self): 
        print("\nPyFluxFusionSolarKiosk process environmental variables")
        if os.getenv('pvverbose') != None :  self.verbose = self.getenv('pvverbose')
        if os.getenv('pvtmzone') != None :  self.tmzone = self.getenv('pvtmzone')
        if os.getenv('pvurl') != None :  self.pvurl = self.getenv('pvurl')
        if os.getenv('pvsysname') != None :  self.pvsysname = self.getenv('pvsysname')
        if os.getenv('pvinterval') != None :  self.pvinterval = int(self.getenv('pvinterval'))
        if os.getenv('pvinflux') != None :  self.influx = self.getenv('pvinflux')
        if os.getenv('pvinflux2') != None :  self.influx2 = self.getenv('pvinflux2')
        if os.getenv('pvifdbname') != None :  self.ifdbname = self.getenv('pvifdbname')
        if os.getenv('pvifip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('pvifip'))
                self.ifip = self.getenv('pvifip')
            except Exception as e: 
                if self.verbose : print("\nPyFluxFusionSolarKiosk InfluxDB server IP address env invalid", e)
            if self.verbose : print("\nPyFluxFusionSolarKiosk InfluxDB server IP determined:", self.ifip)
        if os.getenv('pvifport') != None :     
            if 0 <= int(os.getenv('pvifport')) <= 65535  :  self.ifport = int(self.getenv('pvifport'))
            else : 
                if self.verbose : print("\nPyFluxFusionSolarKiosk InfluxDB server Port address env invalid")      
        if os.getenv('pvifuser') != None :  self.ifuser = self.getenv('pvifuser')
        if os.getenv('pvifpassword') != None :  self.ifpsw = self.getenv('pvifpassword')
        if os.getenv('pviforg') != None :  self.iforg = self.getenv('pviforg')
        if os.getenv('pvifbucket') != None :  self.ifbucket = self.getenv('pvifbucket')
        if os.getenv('pviftoken') != None :  self.iftoken = self.getenv('pviftoken')
        

