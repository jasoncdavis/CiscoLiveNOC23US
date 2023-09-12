"""Helper program - Collect Wireless Access Point inventory from WLC

(getWirelessAPData.py)
Obtains the Wireless LAN Controller (WLC) instances from the 
environment profile via optionsconfig.yaml.  Extracts the wireless AP 
parameters from the WLC and returns as JSON records for putAPsIntoDB.py
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
from ncclient import manager
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from common import getEnv


# Functions
def strip_ns(xml_string):
    return re.sub('xmlns="[^"]+"', '', xml_string)

def getAPs(controller):
    capwap_filter = '''<filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
            <access-point-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-access-point-oper">
                <capwap-data>
                <wtp-mac/>
                <ip-addr/>
                <name/>
                <device-detail>
                    <static-info>
                    <board-data>
                        <wtp-serial-num/>
                        <wtp-enet-mac/>
                    </board-data>
                    <ap-models>
                        <model/>
                    </ap-models>
                    </static-info>
                </device-detail>
                </capwap-data>
            </access-point-oper-data>
        </filter>
    '''

    try:
        with manager.connect(host=controller['host'], 
                             port=830, 
                             username=controller['username'], 
                             password=controller['password'], 
                             hostkey_verify=controller['CheckSSLCert']) as ncsession:
            ncreply = ncsession.get(capwap_filter).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(".//capwap-data")

            aprecords = '{"wireless-aps":['
            for ap in xmldata:
                aprecord = (f'{{ "wtp-serial-num": "{ap.find("device-detail/static-info/board-data/wtp-serial-num").text}",'
                f'"wtp-mac": "{ap.find("wtp-mac").text}",'
                f'"ip-addr": "{ap.find("ip-addr").text}",'
                f'"name": "{ap.find("name").text}",'
                f'"wtp-enet-mac": "{ap.find("device-detail/static-info/board-data/wtp-enet-mac").text}",'
                f'"model": "{ap.find("device-detail/static-info/ap-models/model").text}"}}')
                if ap != xmldata[-1]:
                    aprecord += ','
                aprecords += aprecord

            aprecords += ']}'
            #print(repr(aprecords))
            return(aprecords)
    except Exception as e:
        print(e)
        return(None)


if __name__ == "__main__":
    start = datetime.now()
    print(f'Started task at {start.strftime("%H:%M:%S")}')
    controllerlist = getEnv.getparam("WLC")
    aggregatelist = []
    deviceresults = []
    for controller in controllerlist:
        print(f"Processing Wireless LAN Controller (WLC) instance "
              f"{controller['alias']} {controller['host']}...")
        thiscontrollerAPs = getAPs(controller)

    end = datetime.now()
    print(f'Ended task at {end.strftime("%H:%M:%S")}\nTotal runtime: {end - start}')
