"""Obtains router interface statistics for CiscoLive via NETCONF RPC

(NETCONFrpc-getInterfaceData.py)
Reads the interface polling inventory from the optionsconfig.yaml
project file.  Performs NETCONF RPC polling to get IPv4 and IPv6 stats 
from the IOS XE devices using Cisco-IOS-XE-interfaces-oper YANG model

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
v3   2023-0406  code clean-up and modularity enhancements
v4   2023-0803  Update for Python packaging
v5   2023-0906  Updates to docs and github packaging
"""

# Credits:
__version__ = '5'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
from unicodedata import name
from ncclient import manager
import xml.etree.ElementTree as ET
import sys
import re
import threading
import time
import schedule
import requests
from common import getEnv
import argparse
import os
from common import doInflux


# Global variables
POLLING_FREQ = 10   #How often to poll, in seconds


# Functions
def strip_ns(xml_string):
    return re.sub('xmlns="[^"]+"', '', xml_string)

def get_interface_stats(device):
    interface_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper">
            <interface>
                <name/>
                <admin-status/>
                <oper-status/>
                <last-change/>
                <speed/>
                <statistics>
                    <in-octets/>
                    <out-octets/>
                    <rx-pps/>
                    <rx-kbps/>
                    <tx-pps/>
                    <tx-kbps/>
                </statistics>
                <v4-protocol-stats>
                    <in-pkts/>
                    <in-octets/>
                    <out-pkts/>
                    <out-octets/>
                </v4-protocol-stats>
                <v6-protocol-stats>
                    <in-pkts/>
                    <in-octets/>
                    <out-pkts/>
                    <out-octets/>
                </v6-protocol-stats>
            </interface>
        </interfaces>
    </filter>
    '''

    try:
        with manager.connect(host=device['host'], port=830, 
                         username=device['username'], 
                         password=device['password'], 
                         hostkey_verify=False) as ncsession:
            ncreply = ncsession.get(interface_filter).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(".//interface")
    except Exception as e:
        print(f'Experienced a failure...\n{e}')
        return('FAILED')
    else:
        return(xmldata)


def convert_xml(devicename, xmldata):
    # Convert XML data from NETCONF interface form into Influx writeline
    measurement = ''
    for interface in xmldata:
        measurement += (f'interface-ipv4v6,device={devicename},'
        f'interface={interface.find("name").text} '
        f'admin-status=\"{interface.find("admin-status").text}\",'
        f'oper-status=\"{interface.find("oper-status").text}\",'
        f'last-change=\"{interface.find("last-change").text}\",'
        f'speed={interface.find("speed").text},'
        f'int-in-octets={interface.find("statistics/in-octets").text},'
        f'int-out-octets={interface.find("statistics/out-octets").text},'
        f'int-rx-pps={interface.find("statistics/rx-pps").text},'
        f'int-rx-kbps={interface.find("statistics/rx-kbps").text},'
        f'int-tx-pps={interface.find("statistics/tx-pps").text},'
        f'int-tx-kbps={interface.find("statistics/tx-kbps").text},'
        f'ipv4-in-pkts={interface.find("v4-protocol-stats/in-pkts").text},'
        f'ipv4-in-octets={interface.find("v4-protocol-stats/in-octets").text},'
        f'ipv4-out-pkts={interface.find("v4-protocol-stats/out-pkts").text},'
        f'ipv4-out-octets={interface.find("v4-protocol-stats/out-octets").text},'
        f'ipv6-in-pkts={interface.find("v6-protocol-stats/in-pkts").text},'
        f'ipv6-in-octets={interface.find("v6-protocol-stats/in-octets").text},'
        f'ipv6-out-pkts={interface.find("v6-protocol-stats/out-pkts").text},'
        f'ipv6-out-octets={interface.find("v6-protocol-stats/out-octets").text}\n')
        #print(repr(measurement))
    return(measurement)


def start_all(debugmode, influxparams, devicelist):
    # Function that reads all target device parameters from project
    # file and calls get_interfaces() for each
    print(f'\nStarting at: {str(time.ctime())}')

    aggregatelist = []
    #deviceresults = []
    for device in devicelist:
        if not debugmode: print(f"Processing Device instance {device['alias']} {device['host']}...")
        xmldata = get_interface_stats(device)
        if xmldata == 'FAILED':
            # We experienced a failure, report and continue next poll
            #    maybe extend the polling interval?
            continue
        this_device_ints = convert_xml(device['alias'], xmldata)
        nlines = this_device_ints.count('\n')
        aggregatelist.append(this_device_ints)
        if debugmode: print(f"  Got {nlines} interfaces from {device['alias']} {device['host']}...")
    measurements = '\n'.join(str(int) for int in aggregatelist)
    if not debugmode:
        doInflux.write_to_influx(influxparams, measurements)
    else:
        print(measurements)
        #exit()
    print('\nRunning a sleep loop.', end='', flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Start periodic polling of interface stats')
    parser.add_argument('--debug', 
                        dest='debug', 
                        default=False, 
                        action='store_true',
                        help='Enable debug - output to console, '\
                             'no output Influx'
                        )
    args = parser.parse_args()
    
    devicelist = getEnv.getparam("InterfaceDevices")
    influxparams = getEnv.getparam("InfluxDB")
    schedule.every(POLLING_FREQ).seconds.do(start_all, 
                                            debugmode=args.debug, 
                                            influxparams=influxparams, 
                                            devicelist=devicelist)
    print('\nRunning a sleep loop.', end='', flush=True)

    try:
        while True:
            print('.', end='', flush=True)
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nUser initiated stop - closing down process...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
