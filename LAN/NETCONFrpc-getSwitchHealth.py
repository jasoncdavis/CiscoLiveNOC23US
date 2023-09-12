"""Obtains network switch health statistics for CiscoLive via NETCONF RPC

(NETCONFrpc-getSwitchHealth.py)
Reads the MySQL inventory table to obtain DIST and IDF group devices.
Performs NETCONF RPC polling to get various switch health stats using
various YANG models

Parameters
__________
None

Returns
-------
None


Notes
-----
Cisco IOS-XE YANG models are define at
https://github.com/YangModels/yang/tree/main/vendor/cisco/xe


Examples
--------
N.A.
"""

"""Version log
v1   2022-0520  Initial release
v2   2022-0521  much more modular and pulls device info from optionconfig.yaml
                derived from NETCONFrpc-getInterfaceData.py
                Update for Python packaging
v3   2023-0826  Update for IMPACT24; packaging; revised helper funcs
v4   2023-0906  Updates to docs and github packaging
"""

# Credits:
__version__ = '4'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
from datetime import datetime
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError, SessionCloseError

import xml.etree.ElementTree as ET
import sys
import re
import threading
import time
import schedule
import requests
from common import sendWebexMessage
from common import getEnv
from common import doDB


# Global variables
DEBUG = False


# Functions
def strip_ns(xml_string):
    return re.sub(' xmlns="[^"]+"', '', xml_string)

def get_interface_stats(device):
    interface_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper">
            <interface>
                <name/>
                <interface-type/>
                <admin-status/>
                <oper-status/>
                <last-change/>
                <speed/>
                <statistics>
                    <in-octets/>
                    <in-discards-64/>
                    <in-errors-64/>
                    <out-octets-64/>
                    <out-discards/>
                    <out-errors/>
                    <in-crc-errors/>
                </statistics>
            </interface>
        </interfaces>
    </filter>
    '''

    #print(device)
    try:
        with manager.connect(host=device['host'], port=830, username=device['username'], password=device['password'], hostkey_verify=False, timeout=10) as ncsession:
            ncreply = ncsession.get(interface_filter).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(".//interface")

            return(xmldata)
    except (SSHError, SessionCloseError):
        return('FAILED')
    except Exception as e:
        print(f'Got error: {e}')
        return('FAILED')

    

def get_cpu_stats(device):
    rpcnc_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <cpu-usage xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-process-cpu-oper">
        <cpu-utilization>
          <one-minute/>
          <five-minutes/>
        </cpu-utilization>
      </cpu-usage>
    </filter>
    '''
    #print(device)
    with manager.connect(host=device['host'], port=830, username=device['username'], password=device['password'], hostkey_verify=False) as ncsession:
        ncreply = ncsession.get(rpcnc_filter).data_xml
        ncreply_nons = strip_ns(ncreply)
        #print(ncreply_nons)
        xmldata = ET.fromstring(ncreply_nons).findall(".//cpu-utilization")
        
    #print(ET.tostring(xmldata[0], encoding='utf8').decode('utf8'))
    return(xmldata)


def get_mem_stats(device):
    rpcnc_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <memory-statistics xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-memory-oper">
        <memory-statistic>
          <name>Processor</name>
          <total-memory/>
          <used-memory/>
          <free-memory/>
        </memory-statistic>
      </memory-statistics>
    </filter>
    '''

    #print(device)
    with manager.connect(host=device['host'], port=830, username=device['username'], password=device['password'], hostkey_verify=False) as ncsession:
        ncreply = ncsession.get(rpcnc_filter).data_xml
        ncreply_nons = strip_ns(ncreply)
        #print(ncreply_nons)
        xmldata = ET.fromstring(ncreply_nons).findall(".//memory-statistic")
        
    #print(ET.tostring(xmldata[0], encoding='utf8').decode('utf8'))
    return(xmldata)


def convert_interface_xml(devicename, xmldata):
    # Convert XML data from NETCONF interface form into Influx writeline
    measurement = ''
    for interface in xmldata:
        #print(ET.tostring(interface))
        measurement += (f'LAN-interfaces,device={devicename},'
        f'interface={interface.find("name").text} '
        f'interface-type=\"{interface.find("interface-type").text}\",'
        f'admin-status=\"{interface.find("admin-status").text}\",'
        f'oper-status=\"{interface.find("oper-status").text}\",'
        f'last-change=\"{interface.find("last-change").text}\",'
        f'speed={interface.find("speed").text},'
        f'stats-in-octets={interface.find("statistics/in-octets").text},'
        f'stats-in-crc-errors={interface.find("statistics/in-crc-errors").text},'
        f'stats-in-discards={interface.find("statistics/in-discards-64").text},'
        f'stats-in-errors={interface.find("statistics/in-errors-64").text},'
        f'stats-out-octets={interface.find("statistics/out-octets-64").text},'
        f'stats-out-discards={interface.find("statistics/out-discards").text},'
        f'stats-out-errors={interface.find("statistics/out-errors").text}\n')

        #print(repr(measurement))
    return(measurement)


def check_int_crc(mysqlenv, devicename, xmldata):
    # Assess CRC info
    measurement = ''

    total_device_crcs = 0
    for interface in xmldata:
        #print(ET.tostring(interface, encoding='unicode', method='xml'))
        int_crc = int(interface.find("statistics/in-crc-errors").text)
        if DEBUG: print(f'Interface: {interface.find("name").text} has {int_crc} CRC errors')
        total_device_crcs += int_crc
    print(f'Total CRC errors for [{devicename}]: {total_device_crcs}')
    if total_device_crcs > 0:
        #insert into MySQL
        SQL = f'''SELECT hostname, last_crc
FROM devnet_dashboards.interface_metrics 
WHERE hostname = "{devicename}" 
'''
        results = doDB.fetchall(mysqlenv, SQL)
        #print(results)
        if not results:
            # No previous report, save current CRC count
            sql = f"""INSERT INTO devnet_dashboards.interface_metrics (hostname, last_crc) 
VALUES ('{devicename}', '{total_device_crcs}')
    """ 
            #newentry = [(devicename, total_device_crcs)]
            #doDB.exec(mysqlenv, sql, newentry)
            doDB.exec(mysqlenv, sql)
        else:
            # Had a previous entry and need to compare, report
            if total_device_crcs == results[0][1]:
                pass
            else:
                # insert update in MySQL and Send a Webex message
                sql = f"""UPDATE devnet_dashboards.interface_metrics
SET last_crc = {total_device_crcs}
WHERE hostname = "{devicename}"
""" 
                doDB.exec(mysqlenv, sql)
                sendWebexMessage.sendMessage(getEnv.getparam("switchalerts_webexroomid"),f'{devicename} has increasing CRC counts: difference of {total_device_crcs - results[0][1]}')


def convert_cpu_xml(devicename, xmldata):
    # Convert XML data from NETCONF interface form into Influx writeline
    #print(ET.tostring(xmldata[0], encoding='utf8').decode('utf8'))

    measurement = (f'LAN-cpu,device={devicename} '
        f'one-min={xmldata[0].find("one-minute").text},'
        f'five-min={xmldata[0].find("five-minutes").text}\n')

    #print(repr(measurement))
    return(measurement)


def convert_mem_xml(devicename, xmldata):
    # Convert XML data from NETCONF interface form into Influx writeline
    #print(ET.tostring(xmldata[0], encoding='utf8').decode('utf8'))

    measurement = (f'LAN-mem,device={devicename},type={xmldata[0].find("name").text} '
        f'total-memory={xmldata[0].find("total-memory").text},'
        f'used-memory={xmldata[0].find("used-memory").text},'
        f'free-memory={xmldata[0].find("free-memory").text}\n')

    #print(repr(measurement))
    return(measurement)


def send_to_influx(influxenv, measurements):
    # Send data to InfluxDB
    print(measurements)
    influxurl = f'{influxenv["protocol"]}://{influxenv["host"]}:{influxenv["port"]}\
/api/v2/write?bucket={influxenv["bucketname"]}&org={influxenv["orgname"]}&precision=s'
    
    headers = {
    'Accept': 'application/json',
    'Authorization': 'Token ' + influxenv['token'],
    'Content-Type': 'text/plain'
    }

    response = requests.request("POST", influxurl, headers=headers, data=measurements)
    print(f'  Results: {response.status_code} - {response.text}')
    print(f'Finished at: {str(time.ctime())}\n')


def start_all(switch_inventory, credentials, influxenv, mysqlenv):
    failed_devices = []
    startlooptime = datetime.now()
    for device in switch_inventory:
        #print(device)
        device = {'host': f'{device[1]}', 'alias': f'{device[0]}', 'username': f'{credentials["username"]}',\
        'password': f'{credentials["password"]}', 'location': f'{device[5]}'}
        #print(device)
        print(f"Processing Device instance {device['alias']} {device['host']} at {device['location']}...")
        
        int_xml = get_interface_stats(device)
        if int_xml == 'FAILED':
            failed_devices.append(device['alias'])
            print(f'Could not connect to {device["alias"]}\n')
        else:
            this_device_ints = convert_interface_xml(device['alias'], int_xml)

            this_device_crcs = check_int_crc(mysqlenv, device['alias'], int_xml)
            #print(this_device_crcs)

            cpu_xml = get_cpu_stats(device)
            this_device_cpu = convert_cpu_xml(device['alias'], cpu_xml)

            mem_xml = get_mem_stats(device)
            this_device_mem = convert_mem_xml(device['alias'], mem_xml)
            #print(this_device_ints + this_device_cpu + this_device_mem)

            send_to_influx(influxenv, this_device_ints + this_device_cpu + this_device_mem)
            
    print(f'Failed Devices on this run:\n{failed_devices}')
    print(f'Completed last run in: {datetime.now() - startlooptime}')


def run_threaded(job_func, switch_inventory, credentials, 
                 influxenv, mysqlenv):
    job_thread = threading.Thread(target=job_func, 
                                  args=(switch_inventory, credentials, 
                                        influxenv, mysqlenv,))
    start = datetime.now()
    print(f'\nRunning thread at {start.strftime("%H:%M:%S")}')
    job_thread.start()


## MAIN
# Get environment parameters
#devicelist = getEnv.getparam("InterfaceDevices")
credentials = getEnv.getparam("AAA-default")
influxenv = getEnv.getparam("InfluxDB")
mysqlenv = getEnv.getparam("MySQL")


## Get IDF, DIST, and CORE Switch list from MySQL Inventory table
SQL = '''SELECT hostname, mgmt_ip_address, device_type, device_group, model, location 
    FROM devnet_dashboards.inventory
    WHERE (device_group='IDF' OR device_group='DIST' OR device_group='CORE') 
      AND hostname not like '%SPARE%';
'''
switch_inventory = doDB.fetchall(mysqlenv, SQL)
print(f'Switch inventory: {switch_inventory}')

# Run manually to start
start_all(switch_inventory, credentials, influxenv, mysqlenv)

# Then initiate a scheduled instance
schedule.every(300).seconds.do(run_threaded, start_all, switch_inventory, 
                               credentials, influxenv, mysqlenv)

while True:
    schedule.run_pending()
    time.sleep(15)