"""Helper program - Collects Wireless data from WLC

(getWirelessData.py)
Obtains the Wireless LAN Controller (WLC) instances from the 
environment profile via optionsconfig.yaml.  Extracts wireless data 
from the WLC via several NETCONF RPC functions of APs, Clients, RRM data,
then returns as JSON records for putWirelessDataIntoDB.py
Runs as helper module to other scripts.

Parameters
__________
wlcenv : dictionary
    WLC server parameters (eg. hostname, alias, username, password)
    from optionsconfig.yaml

Returns
-------
JSON records of wireless AP, client, RRM data as JSON records

Notes
-----

Examples
--------
N.A.
"""

"""Version log
Version log:
v1   2023-0725   Initial release as part of CiscoLive NOC development
        converges several other modules
v2   2023-0826   Added Cisco-IOS-XE-wireless-access-point-oper:
        access-point-oper-data/radio-oper-data/phy_ht_cfg/cfg_data
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
                f'"dot11-6ghz-cap": {client.find("dot11-6ghz-cap").text},'
                f'"ms-ap-slot-id": {client.find("ms-ap-slot-id").text}}}')
                if client != xmldata[-1]:
                    clientrecord += ','
                #print(repr(clientrecord))
                clientrecords += clientrecord

            clientrecords += ']}'
            return(clientrecords)
    except Exception as e:
        print(e)
        return(None)


def get_AP_count(controller):
    """Return wireless AP count from Wireless LAN Controller.
    
    The YANG Model elements used are:
    joined-aps-count "Number of APs joined on wireless LAN controller";
    """

    rpc_filter = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <ap-global-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-ap-global-oper">
        <emltd-join-count-stat>
          <joined-aps-count/>
        </emltd-join-count-stat>
      </ap-global-oper-data>
    </filter>
    '''
    try:
        with manager.connect(host=controller['host'], 
                             port=830, 
                             username=controller['username'], 
                             password=controller['password'],
                             timeout=60, 
                             hostkey_verify=controller['CheckSSLCert']) as ncsession:
            ncreply = ncsession.get(rpc_filter).data_xml
            ncreply_nons = strip_ns(ncreply)
            #print(ncreply_nons)
            apcount = ET.fromstring(ncreply_nons).find(".//joined-aps-count").text
            return int(apcount)
    except Exception as e:
        print(e)
        return None


def get_rrm_stats(controller):
    record_delim = 'rrm-measurement'
    rpc_payload = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <rrm-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-rrm-oper">
        <rrm-measurement>
          <wtp-mac/>
          <radio-slot-id/>
          <load>
            <rx-util-percentage/>
            <tx-util-percentage/>
            <cca-util-percentage/>
            <stations/>
          </load>
        </rrm-measurement>
      </rrm-oper-data>
    </filter>
    '''
    try:
        with manager.connect(host=controller['host'], port=830, 
                            username=controller['username'], 
                            password=controller['password'], 
                            hostkey_verify=False) as ncsession:
            ncreply = ncsession.get(rpc_payload).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(f".//{record_delim}")
    except ncclient.transport.errors.AuthenticationError:
        print(f'   WARNING: Currently failing authentication of {controller["alias"]} with user {controller["username"]}')
        return('')
    else:
        return(xmldata)


def get_radio_stats(controller):
    record_delim = 'radio-oper-data'
    rpc_payload = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <access-point-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-access-point-oper">
        <radio-oper-data>
          <wtp-mac/>
          <radio-slot-id/>
          <phy-ht-cfg>
            <cfg-data>
              <curr-freq/>
              <chan-width/>
            </cfg-data>
          </phy-ht-cfg>
        </radio-oper-data>
      </access-point-oper-data>
    </filter>
    '''
    try:
        with manager.connect(host=controller['host'], port=830, 
                            username=controller['username'], 
                            password=controller['password'], 
                            hostkey_verify=False) as ncsession:
            ncreply = ncsession.get(rpc_payload).data_xml
            ncreply_nons = strip_ns(ncreply)
            xmldata = ET.fromstring(ncreply_nons).findall(f".//{record_delim}")
    except ncclient.transport.errors.AuthenticationError:
        print(f'   WARNING: Currently failing authentication of {controller["alias"]} with user {controller["username"]}')
        return('')
    else:
        return(xmldata)


if __name__ == "__main__":
    start = datetime.now()
    print(f'Started task at {start.strftime("%H:%M:%S")}')
    controllerlist = getEnv.getparam("WLC")
    aggregatelist = []
    deviceresults = []
    for controller in controllerlist:
        print(f"Processing Wireless LAN Controller (WLC) instance {controller['alias']} {controller['host']}...")
        thiscontrollerAPs = getAPs(controller)

    end = datetime.now()
    print(f'Ended task at {end.strftime("%H:%M:%S")}\nTotal runtime: {end - start}')
