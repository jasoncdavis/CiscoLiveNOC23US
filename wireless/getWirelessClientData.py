"""Helper program - Collect Wireless Client inventory from WLC

(getWirelessClientData.py)
Obtains the Wireless LAN Controller (WLC) instances from the 
environment profile via optionsconfig.yaml.  Extracts the wireless 
client data from the WLC and returns as JSON records for 
putClientsIntoDB.py
Runs as helper module to other scripts.

Parameters
__________
wlcenv : dictionary
    WLC server parameters (eg. hostname, alias, username, password)
    from optionsconfig.yaml

Returns
-------
JSON records of wireless client data

Notes
-----

Examples
--------
N.A.
"""

"""Version log
Version log:
v1   2023-0509  Initial release as part of CiscoLive NOC development
v2   2023-0724  Update docs, import structure and getEnv
v3   2023-0907  Updates to docs and github packaging
"""

# Credits:
__version__ = '3'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
from unicodedata import name
from ncclient import manager
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from common import getEnv
import argparse


# Functions
def strip_ns(xml_string):
    return re.sub('xmlns="[^"]+"', '', xml_string)


def getClients(controller):
    """Return wireless client information from Wireless LAN Controller.
    
    The YANG Model elements used are:
    ms-mac-address "MAC Address of the wireless mobile station. MAC addresses are used as a network address for most IEEE 802 network technologies, including Ethernet, Wi-Fi and Bluetooth.";
    ap-mac-address "MAC Address of the Access Point to which the client has joined. MAC addresses are used as a network address for most IEEE 802 network technologies, including Ethernet, Wi-Fi and Bluetooth.";
    current-channel "Current Channel on which the wireless client is communicating with Access Point in the wireless LAN.";
    vap-ssid "Service Set Identifier (SSID) of the Wireless LAN to which the client is connected.";
    radio-type "Type of the Radio of the AP to which the client is associated";
    ewlc-ms-phy-type "Radio PHY type to which the wireless mobile station is connected";
    ms-ap-slot-id "Slot ID of the access point radio on which the wireless client is connected, slot 255 represents invalid slot ID.";
    """

    wirelessclient_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <client-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-client-oper">
        <dot11-oper-data>
          <ms-mac-address/>
          <ap-mac-address/>
          <current-channel/>
          <vap-ssid/>
          <radio-type/>
          <ewlc-ms-phy-type/>
          <dot11-6ghz-cap/> 
          <ms-ap-slot-id/>
        </dot11-oper-data>
      </client-oper-data>
    </filter>
    '''
    try:
        with manager.connect(host=controller['host'], 
                             port=830, 
                             username=controller['username'], 
                             password=controller['password'],
                             timeout=60, 
                             hostkey_verify=controller['CheckSSLCert']) as ncsession:
            ncreply = ncsession.get(wirelessclient_filter).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(".//dot11-oper-data")

            clientrecords = '{"wireless-clients":['
            for client in xmldata:
                clientrecord = (f'{{ "ms-mac-address": "{client.find("ms-mac-address").text}",'
                f'"ap-mac-address": "{client.find("ap-mac-address").text}",'
                f'"current-channel": "{client.find("current-channel").text}",'
                f'"vap-ssid": "{client.find("vap-ssid").text}",'
                f'"radio-type": "{client.find("radio-type").text}",'
                f'"ewlc-ms-phy-type": "{client.find("ewlc-ms-phy-type").text}",'
                f'"dot11-6ghz-cap": "{client.find("dot11-6ghz-cap").text}",'
                f'"ms-ap-slot-id": "{client.find("ms-ap-slot-id").text}"}}')
                if client != xmldata[-1]:
                    clientrecord += ','
                #print(repr(clientrecord))
                clientrecords += clientrecord

            clientrecords += ']}'
            return(clientrecords)
    except Exception as e:
        print(e)
        return(None)


if __name__ == "__main__":
    controllerlist = getEnv.getparam("WLC")
    WLCs = [controller['alias'] for controller in controllerlist]
    parser = argparse.ArgumentParser(
        description='Collect wireless client info from known WLC in ' \
            'optionsconfig.yaml',
        epilog='Current environment WLCs from optionsconfig.yaml ' \
            f'are: {" ".join(WLCs)}'
    )
#        {controller['alias']})
    parser.add_argument('--wlc', metavar='wlc', required=True,
                        help='the name of the WLC in optionsconfig.yaml')
    args = parser.parse_args()
    if args.wlc not in WLCs:
        print(f'ERROR - WLC supplied "{args.wlc}" is not in the list ' \
            'of known WLCs from optionsconfig.yaml, which are:\n'
            f'{" ".join(WLCs)}')
    else:
        controller = [controller for controller in controllerlist if controller['alias'] == args.wlc]
        print(controller[0])
        start = datetime.now()
        print(f'Started task at {start.strftime("%H:%M:%S")}')
        print(getClients(controller[0]))
        end = datetime.now()
        print(f'Ended task at {end.strftime("%H:%M:%S")}\nTotal runtime: {end - start}')
        