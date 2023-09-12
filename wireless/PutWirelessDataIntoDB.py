"""Puts the collected wireless inventory into the project MySQL database.

(PutWirelessDataIntoDB.py)
Obtains the Wireless LAN Controller (WLC) instances from the 
environment profile, optionsconfig.yaml.  Extracts the wireless data 
from getWirelessData.py and formats into appropriate table schema.

Parameters
__________
wlcenv : dictionary
    WLC server parameters (eg. hostname, alias, username, password)
    from optionsconfig.yaml

Returns
-------
None
Puts wireless AP inventory into MySQL tables: inventory and WirelessAPs

Notes
-----

Examples
--------
N.A.
"""

"""Version log
Version log:
v1   2022-0725  Initial Release as part of CiscoLive NOC development
v2   2023-0826  Added radio freq and channel width info
v3   2023-0907  Updates to docs and github packaging
"""

# Credits:
__version__ = '3'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')


# Imports
import xml.etree.ElementTree as ET
import sys, os
import re
import time
from datetime import datetime
import json
from common import doDB
from common import sendWebexMessage
from common import getEnv
import schedule, threading
from wireless import getWirelessData
import argparse
from common import doInflux
from netaddr import EUI, core, NotRegisteredError


# Functions
def extract_device_properties(controller, aps):
    """Extract devices properties from JSON string
    
    Reads device inventory as JSON, extracts the fields needed to add 
    as inventory into MySQL
    
    :param server: dictionary containing settings of the WLC being 
        polled [eg. host, username, password,  etc.]
    :param deviceinventory: string of JSON text representing WLC APs in a list
    :returns: list of dictionary entries representing client parameters
    """
    aplist=[]
    aps_json = json.loads(aps)
    for ap in aps_json["wireless-aps"]:
        SerialNumber = ap['wtp-serial-num']
        RadioMACAddress = ap['wtp-mac']
        EthernetMACAddress = ap['wtp-enet-mac']
        IPAddress = ap['ip-addr']
        Name = ap['name']
        Model = ap['model']
        Controller = controller
        aplist.append((SerialNumber, 
                       RadioMACAddress, 
                       EthernetMACAddress, 
                       IPAddress, 
                       Name, 
                       Model, 
                       Controller))
    return aplist


def extract_client_properties(controller, clients):
    """Extract wireless client properties from JSON string
    
    Reads client inventory as JSON, extracts the fields needed to work
    with WirelessClients table in MySQL
    
    :param controller: string containing wireless LAN controller name
    :param clients: string of JSON text representing wireless clients 
        in a list
    :returns: list of dictionary entries representing client parameters
        suitable for MySQL executemany INSERT INTO VALUES...
    """
    client_list=[]
    mac_randomized = 0
    clients_json = json.loads(clients)
    for client in clients_json["wireless-clients"]:
        #***
        MACAddress = client['ms-mac-address']
        APMACAddress = client['ap-mac-address']
        Channel = client['current-channel']
        SSID = client['vap-ssid']
        RadioType = client['radio-type']
        RadioPHYType = client['ewlc-ms-phy-type']
        SixGHzCapable = client['dot11-6ghz-cap']
        APSlotID = client['ms-ap-slot-id']
        #SeenCount = '' #Counter
        #SeenLastDateTime = '' #Current date/time
        #SeenLastPoll = 1 #Make true seen this time
        Controller = controller
        client_list.append((MACAddress, APMACAddress, Channel, SSID, 
                       RadioType, RadioPHYType, SixGHzCapable,
                       APSlotID, Controller))
        '''
        pmac = EUI(MACAddress)
        print(f'{MACAddress} = {pmac.bits()} ', end='')
        # 7th bit is significant for locally administered MAC addresses
        #print(pmac.bits()[6])
        if pmac.bits()[6] == '1':
            print('Locally administered/randomized')
        else:
            try:
                print(pmac.oui.registration().org)
            except NotRegisteredError:
                print('Unregistered')
        '''
    #print(client_list)
    return client_list


def convert_rrm_xml(controller_name, xmldata, APlist):
    # Convert RRM XML data from NETCONF form into Influx writeline
    #print(f'   Working {controller_name} xmldata')
    measurement = ''
    for item in xmldata:
        #print(item.find("wtp-mac").text, item.find("radio-slot-id").text)
        try:
            apname = [record for record in APlist if record[0] == item.find("wtp-mac").text][0][1]
        except Exception as e:
            print(f'   Got exception: {e}')
            print(f'   Was working on: {item.find("wtp-mac").text} - slot {item.find("radio-slot-id").text}')
            continue
        measurement += (f'wireless-rrmv2,'
            # following are tagsKeys and tagValues
            f'wlc={controller_name},'
            f'apmac={item.find("wtp-mac").text},'
            f'apname={apname},'
            f'radioslot={item.find("radio-slot-id").text}'
            # space must separate from fieldKeys/Values
            f' '
            # following are fieldKeys and fieldValues
            f'rx-util-percentage={item.find("load/rx-util-percentage").text},'
            f'tx-util-percentage={item.find("load/tx-util-percentage").text},'
            f'cca-util-percentage={item.find("load/cca-util-percentage").text},'
            f'stations={item.find("load/stations").text}\n'
        )
    return measurement


def convert_radio_xml(controller_name, xmldata, APlist):
    # Convert radio XML data from NETCONF form into Influx writeline
    #print(f'   Working {controller_name} xmldata')
    measurement = ''
    for item in xmldata:
        #print(item.find("wtp-mac").text, item.find("radio-slot-id").text)
        try:
            apname = [record for record in APlist if record[0] == item.find("wtp-mac").text][0][1]
        except Exception as e:
            print(f'   Got exception: {e}')
            print(f'   Was working on: {item.find("wtp-mac").text} - slot {item.find("radio-slot-id").text}')
            continue
        measurement += (f'wireless-rrmv2,'
            # following are tagsKeys and tagValues
            f'wlc={controller_name},'
            f'apmac={item.find("wtp-mac").text},'
            f'apname={apname},'
            f'radioslot={item.find("radio-slot-id").text}'
            # space must separate from fieldKeys/Values
            f' '
            # following are fieldKeys and fieldValues
            f'curr-freq={item.find("phy-ht-cfg/cfg-data/curr-freq").text},'
            f'chan-width={item.find("phy-ht-cfg/cfg-data/chan-width").text}\n'
        )
    return measurement


def update_wirelessclients_table(datetimenow, mysqlenv, aplist):
    # Put into WirelessClients table for wireless dashboards
    # Clear SeenLastPoll
    clear_sql = '''UPDATE devnet_dashboards.WirelessClients 
              SET SeenLastPoll=False;'''
    doDB.exec(mysqlenv, clear_sql)
    
    sql = f"""INSERT INTO devnet_dashboards.WirelessClients 
      (MACAddress, APMACAddress, Channel, SSID, RadioType, RadioPHYType, 
      SixGHzCapable, APSlotID, SeenCount, SeenLastDateTime, SeenLastPoll, 
      Controller) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, "{datetimenow}", True, %s) 
    ON DUPLICATE KEY UPDATE APMACAddress=VALUES(APMACAddress), 
      Channel=VALUES(Channel), SSID=VALUES(SSID),  
      RadioType=VALUES(RadioType), RadioPHYType=VALUES(RadioPHYType), 
      SixGHzCapable=VALUES(SixGHzCapable), APSlotID=VALUES(APSlotID), 
      SeenCount=SeenCount+1, SeenLastDateTime="{datetimenow}", 
      SeenLastPoll=True, Controller=VALUES(Controller)
    """ 
    doDB.execmany(mysqlenv, sql, aplist)


def update_wirelessaps_table(datetimenow, mysqlenv, aplist):
    # Put into WirelessAPs table for wireless dashboards
    sql = f"""INSERT INTO devnet_dashboards.WirelessAPs 
      (SerialNumber, RadioMACAddress, EthernetMACAddress, IPAddress, 
      Name, Model, Controller, DateTimeFirstSeen) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, "{datetimenow}") 
    ON DUPLICATE KEY UPDATE RadioMACAddress=VALUES(RadioMACAddress), 
      EthernetMACAddress=VALUES(EthernetMACAddress), 
      IPAddress=VALUES(IPAddress), Name=VALUES(Name), 
      Model=VALUES(Model), Controller=VALUES(Controller), 
      DateTimeLastSeen="{datetimenow}"
    """ 
    doDB.execmany(mysqlenv, sql, aplist)


def update_inventory_table(datetimenow, mysqlenv, aplist):
    # Put into inventory table for availability dashboards
    sql = f"""INSERT INTO devnet_dashboards.inventory 
      (serial_number, mac_address, mgmt_ip_address, hostname, model, 
       source, do_ping, device_group, location) 
    VALUES (%s, %s, %s, %s, %s, 'PutAPsIntoDB.py', 1, 'WirelessAP', %s) 
    ON DUPLICATE KEY UPDATE serial_number=VALUES(serial_number), 
      mac_address=VALUES(mac_address), hostname=VALUES(hostname), 
      model=VALUES(model), source='PutAPsIntoDB.py', 
      device_group='WirelessAP', location=VALUES(location)
    """ 
    # Rearrange the aggregatelist to remove RadioMACAddress field[1] 
    newagglist = []
    for aprow in aplist:
        newrow = (aprow[0],) + aprow[2:]
        newagglist.append(tuple(newrow))
    
    doDB.execmany(mysqlenv, sql, newagglist)


def getArgs(WLCs):
    parser = argparse.ArgumentParser(
        description='Collect wireless inventory and client info from known WLC in ' \
            'optionsconfig.yaml',
        epilog='Current environment WLCs from optionsconfig.yaml ' \
            f'are: {" ".join(WLCs)}'
    )

    parser.add_argument('--wlc', metavar='wlc', required=False,
                        default='ALL', nargs="*",
                        help=('the name(s) of the WLC(s) from optionsconfig.yaml'
                              ' - defaults to ALL WLCs'))
    parser.add_argument('--scope', metavar='scope', required=False,
                        default='ALL', nargs="*",
                        choices=["clients", "APs", "RRM", "radio"],
                        help=('the scope of the collection - ALL, clients'
                              ', APs, RRM, radio or a mix - defaults '
                              'to ALL'))
    parser.add_argument('--freq', metavar='freq', required=False,
                        default=120,
                        help=('the frequency of repeated execution (in '
                              'seconds; defaults to every 120 seconds)'))
    
    args = parser.parse_args()
    
    if type(args.wlc) is list:
        # We got a list of WLC entries - could be 1 or more, compare with
        #   legit list
        if set(args.wlc).issubset(set(WLCs)):
            # All entries match
            pass
        else:
            # We had some mismatches
            sys.exit(f'ERROR - WLC entry did not match 1 or more options '
                  f'from optionsconfig.yaml, which are:\n {" ".join(WLCs)}')

    return args


def getLastInfluxAPCount(controller, influxenv):
    # Extract last AP count for WLC from InfluxDB
    # query Influx DB using Flux query language
    # Example:
    """from(bucket: "CLNOC")
        |> range(start: -2m)
        |> filter(fn: (r) => r["_measurement"] == "wireless-rmi")
        |> filter(fn: (r) => r["device"] == "{wlc}")
        |> filter(fn: (r) => r["_field"] == "rmi-status")
        |> yield(name: "last")
    """
    query = f"""from(bucket: "{influxenv["bucketname"]}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "wireless-stats")
        |> filter(fn: (r) => r["device"] == "{controller['alias']}")
        |> filter(fn: (r) => r["_field"] == "ap-count")
        |> last()
    """
    
    try:
        ap_count = int(doInflux.query_influx(influxenv, query)[0][1])
    except IndexError:
        ap_count = 0
    return ap_count


def runjob(args, controllerlist, mysqlenv, influxenv):
    start = datetime.now()
    dtnow = start.strftime('%Y-%m-%d %H:%M:%S')
    # Get AP list
    ap_sql = '''SELECT RadioMACAddress, Name from devnet_dashboards.WirelessAPs'''
    APlist = doDB.fetchall(mysqlenv, ap_sql)
                
    if args.wlc == 'ALL':
        controllers = controllerlist
    else:
        # Make partial list from arg input
        controllers = [controller for controller in controllerlist if controller['alias'] in args.wlc]

    agg_client_list = []
    agg_ap_list = []
    agg_rrm_list = ''
    agg_radio_list = ''
    for controller in controllers:
        print(f"  Processing WLC {controller['alias']} {controller['host']}...")
        if args.scope == 'ALL' or 'clients' in args.scope:
            # Get client data
            wireless_client_data = getWirelessData.getClients(controller)
            if wireless_client_data:
                this_controller_clients = extract_client_properties(controller['alias'], 
                                                                    wireless_client_data)
                agg_client_list.extend(this_controller_clients)
                                
            print('   Processing clients', end='')
            print(f'  ...got {len(agg_client_list)}')
            #print(agg_client_list)
        if args.scope == 'ALL' or 'APs' in args.scope:
            # Get AP data
            print('   Processing APs', end='')
            # First obtain last wireless AP count from InfluxDB
            lastAPCount = getLastInfluxAPCount(controller, influxenv)
            
            # Next get current wireless AP count from WLC
            currentAPCount = getWirelessData.get_AP_count(controller)
            print(f'      ...got {currentAPCount}')
            #print(f'      ...got earlier {lastAPCount}')
                            
            measurement = f'wireless-stats,device={controller["alias"]} ap-count={currentAPCount}'
            influxrc, influxreason, influxtext = doInflux.write_to_influx(influxenv,measurement)
            if influxrc != 204:
                # Handle Influx write error?
                print(influxrc, influxreason, influxtext)

            # Next compare last count with current count
            if currentAPCount != lastAPCount:
                # deep query WLC for inventory and update MySQL
                print('Do a Deep query')
                wirelessapdata = getWirelessData.getAPs(controller)
                if wirelessapdata:
                    thiscontrolleraps = extract_device_properties(controller['alias'], wirelessapdata)
                    agg_ap_list.extend(thiscontrolleraps)
                    print(f"     Got {len(thiscontrolleraps)} APs...")
        if args.scope == 'ALL' or 'RRM' in args.scope:
            # Get RRM data
            """Note, this may be more desirable collecting more
            frequently against a specific controller.  The execution
            may look like
            $ python -m wireless.PutWirelessDataIntoDB --wlc ABCWLC --scope RRM --freq 30
            """
            print('   Collecting RRM stats', end='')
            # DO MORE WORK HERE
            
            # Get RRM stats and convert to Influx line protocol
            this_controller_rrm_xml = getWirelessData.get_rrm_stats(controller)
            rrm_measurement = convert_rrm_xml(controller['alias'], this_controller_rrm_xml, APlist)
            #print(rrm_measurement)
            agg_rrm_list += rrm_measurement
            print('...Finished')
        if args.scope == 'ALL' or 'radio' in args.scope:
            # Get radio data
            """Note, this may be more desirable collecting more
            frequently against a specific controller.  The execution
            may look like
            $ python -m wireless.PutWirelessDataIntoDB --wlc ABCWLC --scope radio --freq 30
            """
            print('   Collecting radio stats', end='')
            # Get Radio stats and convert to Influx line protocol
            this_controller_radio_xml = getWirelessData.get_radio_stats(controller)
            radio_measurement = convert_radio_xml(controller['alias'], 
                                                  this_controller_radio_xml, 
                                                  APlist)
            #print(rrm_measurement)
            agg_radio_list += radio_measurement
            print('...Finished')
    #print(agg_rrm_list)

    if args.scope == 'ALL' or 'clients' in args.scope:
        # Put into WirelessClients table for wireless dashboards
        update_wirelessclients_table(dtnow, mysqlenv, agg_client_list)
    
    if args.scope == 'ALL' or 'APs' in args.scope:
        # Put into WirelessAPs table for wireless dashboards
        update_wirelessaps_table(dtnow, mysqlenv, agg_ap_list)
        
        # Put into inventory table for availability dashboards
        update_inventory_table(dtnow, mysqlenv, agg_ap_list)

    if args.scope == 'ALL' or 'RRM' in args.scope:
        # Put into RRM data into InfluxDB
        influxrc, influxreason, influxtext = doInflux.write_to_influx(influxenv, agg_rrm_list)
        if influxrc != 204:
            # Handle Influx write error?
            print(influxrc, influxreason, influxtext)
        else:
            print('Good write to InfluxDB')

    if args.scope == 'ALL' or 'radio' in args.scope:
        # Put into Radio data into InfluxDB
        #print(agg_radio_list)
        influxrc, influxreason, influxtext = doInflux.write_to_influx(influxenv, agg_radio_list)
        if influxrc != 204:
            # Handle Influx write error?
            print(influxrc, influxreason, influxtext)
        else:
            print('Good write to InfluxDB')

    print("Finished updating MySQL and InfluxDB")
    end = datetime.now()
    print(f'Ended task at {end.strftime("%H:%M:%S")}\nTotal runtime: {end - start}')
    print('\nRunning a sleep loop.', end='', flush=True)


def run_threaded(job_func, args, controllerlist, mysqlenv, influxenv):
    job_thread = threading.Thread(target=job_func, args=(args, 
                                                         controllerlist, 
                                                         mysqlenv, 
                                                         influxenv,))
    start = datetime.now()
    print(f'\nRunning thread at {start.strftime("%H:%M:%S")}')
    job_thread.start()


## MAIN
if __name__ == "__main__":
    controllerlist = getEnv.getparam("WLC")
    mysqlenv = getEnv.getparam('MySQL')
    influxenv = getEnv.getparam('InfluxDB')

    WLCs = [controller['alias'] for controller in controllerlist]
    args = getArgs(WLCs)
    #print(args)

    start = datetime.now()
    print(f'Started task at {start.strftime("%H:%M:%S")}')

    roomid = getEnv.getparam('wirelessalerts_webexroomid')
    #sendWebexMessage.sendMessage(roomid,'Starting PutAPsIntoDB.py utility...')
    # Run manually once, then initiate the schedule to pref
    runjob(args, controllerlist, mysqlenv, influxenv)
    schedule.every(args.freq).seconds.do(run_threaded, runjob, args, 
                                         controllerlist, mysqlenv, 
                                         influxenv)

    try:
        while True:
            print('.', end='', flush=True)
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        print('\nUser initiated stop - closing down process...')
        #sendWebexMessage.sendMessage(roomid,'Stopping PutAPsIntoDB.py utility...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
