"""Primary collector and dashboard creator for wireless clients

(createWirelessClientDashboards.py)
Polls Wireless LAN Controllers (WLCs) for client metrics, then creates
custom dashboards for wireless standard and SSID usage

Parameters
__________
mysqlenv : dictionary
    MySQL server parameters (eg. hostname, username, password, database 
    name) from optionsconfig.yaml
influxenv : dictionary
    InfluxDB server parameters (eg. transport, hostname, port, org, 
    bucket, API key) from optionsconfig.yaml
wirelessdashboarddir : string
    Wireless dashboard directory path; usually an NFS mount to an 
    Apache web server and /var/www/html; defined in optionsconfig.yaml

Returns
-------
None
Generates output of webpages to wirelessdashboarddir

Notes
-----
Cisco IOS-XE YANG models are define at
https://github.com/YangModels/yang/tree/main/vendor/cisco/xe


Examples
--------
N.A.
"""

"""Version log
Version log:
v1   2023-0603 with CLEUR23 Wifi6E capable and operable stats
v2   2023-0830 for IMPACT24 to be modular with other CLNOC scripts
v3   2023-0906 Updates to docs and github packaging
"""

# Credits:
__version__ = '3'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
import sys, os
import time
from datetime import datetime
from common import getEnv
from common import doDB
import json
import requests
from common import sendWebexMessage
import schedule, threading
from collections import Counter
import copy

# Global variables
MINTHRESHOLD = 60
HIGHTHRESHOLD = 75
MAX_ROW_CELL_COUNT = 15
DEBUG = False
FREQUENCY = 120


# Class definitions
class WirelessStandards:
    # A class representing client counts of the various wireless standards
    def __init__(self) -> None:
        # Zero out all counters
        # Wi-Fi 6E
        i80211ax6 = 0
        # Wi-Fi 6 (5 GHz and 2.4 GHz)
        i80211ax5 = 0
        i80211ax24 = 0
        # Wi-Fi 5 (5 GHz)
        i80211ac = 0
        # Wi-Fi 4 (5 GHz and 2.4 GHz)
        i80211n5 = 0
        i80211n24 = 0
        # Older standards before marketing 'Wi-Fi #' spec
        i80211g = 0
        i80211a = 0
        i80211b = 0
    

# Functions
def select_wireless_clients(mysqlenv):
    SQL = '''SELECT Controller, RadioPHYType, count(*) 
FROM WirelessClients 
WHERE SeenLastPoll = true 
GROUP BY Controller, RadioPHYType
ORDER BY Controller;
'''
    results = doDB.fetchall(mysqlenv, SQL)
    if DEBUG: print(f'  Wireless client count summaries: {results}')
    
    lineentry = ''
    agg_entries = []
    current_controller = ''
    for entry in results:
        if current_controller != entry[0]:
            agg_entries.append(lineentry)
            ccount_ax6 = ccount_ax5 = ccount_ax24 = ccount_ac = ccount_n5 = ccount_n24 = 0
            ccount_a = ccount_g = ccount_b = 0
            current_controller = entry[0]

        match entry[1]:
            case 'client-dot11ax-6ghz-prot':
                ccount_ax6 = entry[2]
            case 'client-dot11ax-5ghz-prot':
                ccount_ax5 = entry[2]
            case 'client-dot11ax-24ghz-prot':
                ccount_ax24 = entry[2]
            case 'client-dot11ac':
                ccount_ac = entry[2]
            case 'client-dot11n-5-ghz-prot':
                ccount_n5 = entry[2]
            case 'client-dot11n-24-ghz-prot':
                ccount_n24 = entry[2]
            case 'client-dot11a':
                ccount_a = entry[2]
            case 'client-dot11g':
                ccount_g = entry[2]
            case 'client-dot11b':
                ccount_b = entry[2]
            # If an exact match is not confirmed, this last case will be used if provided
            case _:
                print(f'Ooops - got a {entry[1]}')
        
         # Get WiFi6E CAPABLE clients 
        SQL = f'''SELECT Controller, SixGHzCapable, count(*) 
FROM WirelessClients
WHERE Controller = '{entry[0]}' AND SeenLastPoll = true AND SixGHzCapable = true;
'''
        #results_for_wifi6e = SelectFromMySQL.selectsql(mysqlenv, SQL)
        results_for_wifi6e = doDB.fetchall(mysqlenv, SQL)
        #print(results_for_wifi6e)
        SixGHzClientCount = results_for_wifi6e[0][2]
        
        lineentry = (f'''{{"controller": "{entry[0]}", \
"80211ax6-capable-count": {SixGHzClientCount}, \
"80211ax6-count": {ccount_ax6}, "80211ax5-count": {ccount_ax5}, \
"80211ax24-count": {ccount_ax24}, "80211ac-count": {ccount_ac}, \
"80211n5-count": {ccount_n5}, "80211n24-count": {ccount_n24}, \
"80211a-count": {ccount_a}, "80211g-count": {ccount_g}, \
"80211b-count": {ccount_b}}}''')
        #print(lineentry)
    agg_entries.append(lineentry)
    agg_entries.pop(0)
    #print(agg_entries)
    return(agg_entries)


def select_summary_wireless_clients(mysqlenv):
    SQL = '''SELECT RadioPHYType, count(*) 
FROM WirelessClients
WHERE SeenLastPoll = true 
GROUP BY RadioPHYType;
'''
    #results = SelectFromMySQL.selectsql(mysqlenv, SQL)
    results = doDB.fetchall(mysqlenv, SQL)
    print(results)
    
    # Continue regular client count calculations    
    lineentry = ''
    ccount_6ghz = ccount_ax5 = ccount_ax2 = ccount_ac = \
        ccount_n5 = ccount_n24 = ccount_a = ccount_g = ccount_b = 0

    for entry in results:
        match entry[0]:
            case 'client-dot11ax-6ghz-prot':
                ccount_6ghz = entry[1]
            case 'client-dot11ax-5ghz-prot':
                ccount_ax5 = entry[1]
            case 'client-dot11ax-24ghz-prot':
                ccount_ax2 = entry[1]
            case 'client-dot11ac':
                ccount_ac = entry[1]
            case 'client-dot11n-5-ghz-prot':
                ccount_n5 = entry[1]
            case 'client-dot11n-24-ghz-prot':
                ccount_n24 = entry[1]
            case 'client-dot11a':
                ccount_a = entry[1]
            case 'client-dot11g':
                ccount_g = entry[1]
            case 'client-dot11b':
                ccount_b = entry[1]
            # If an exact match is not confirmed, this last case will be used if provided
            case _:
                print(f'Ooops - got a {entry[1]}')
        
    # Get WiFi6E CAPABLE clients 
    SQL = f'''SELECT SixGHzCapable, count(*) 
FROM WirelessClients
WHERE SeenLastPoll = true AND SixGHzCapable = true;
'''
    #results_for_wifi6e = SelectFromMySQL.selectsql(mysqlenv, SQL)
    results_for_wifi6e = doDB.fetchall(mysqlenv, SQL)
    print(results_for_wifi6e)
    SixGHzClientCount = results_for_wifi6e[0][1]

    lineentry = (f'''{{ \
"80211ax6-capable-count": {SixGHzClientCount}, \
"80211ax6-count": {ccount_6ghz}, \
"80211ax5-count": {ccount_ax5}, "80211ax2-count": {ccount_ax2}, \
"80211ac-count": {ccount_ac}, "80211n5-count": {ccount_n5}, \
"80211n24-count": {ccount_n24}, "80211a-count": {ccount_a}, \
"80211g-count": {ccount_g}, "80211b-count": {ccount_b}}}''')
    print(f'Line entry was: {lineentry}')
    return(lineentry)


def format_to_influx_lineprotocol(clientcounts):
    measurements = ''
    for entry in clientcounts:
        #print(entry)
        entryjson = json.loads(entry)
        #print(entryjson["controller"])
        measurement = f'wirelessclientcounts,controller={entryjson["controller"]} \
80211ax6-capable-count={entryjson["80211ax6-capable-count"]},\
80211ax6-count={entryjson["80211ax6-count"]},\
80211ax5-count={entryjson["80211ax5-count"]},\
80211ax24-count={entryjson["80211ax24-count"]},\
80211ac-count={entryjson["80211ac-count"]},\
80211n5-count={entryjson["80211n5-count"]},\
80211n24-count={entryjson["80211n24-count"]},\
80211a-count={entryjson["80211a-count"]},\
80211g-count={entryjson["80211g-count"]},\
80211b-count={entryjson["80211b-count"]}'
        #print(measurement)
        measurements += measurement + '\n'
    #print(measurements)
    return(measurements)


def put_wireless_stats_in_influx(influxenv, clientcounts):
    influxurl = f'{influxenv["protocol"]}://{influxenv["host"]}:\
{influxenv["port"]}/api/v2/write?bucket={influxenv["bucket"]}&\
org={influxenv["org"]}&precision=s'

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Token ' + influxenv["token"],
    'Content-Type': 'text/plain'
    }

    print('  Sending wireless client data to Influx [204 No Content is GOOD]')
    response = requests.request("POST", influxurl, headers=headers, data=clientcounts)
    print(f'{response.status_code} - {response.reason} - {response.text}')


def processCatalystWLCdata(template, controller, clientassociations):
    # Take in clientassociate data in Influx write line format and
    # convert into HTML for dashboard
    
    # Need to do OVERALL stats dashboard at the end, once the total
    # client counts have been summed from all controller
    
    # totalclients for this execution is for this specific controller
    totalclients = sum(clientassociations.values())
    totalclients = totalclients - clientassociations.get("80211ax6-capable-count", 0)
    if totalclients == 0:
        return('')

    WIFI6E_capable = clientassociations.get("80211ax6-capable-count", 0)
    RATIOAX6 = f'{(clientassociations["80211ax6-count"] / totalclients) * 100:.1f}'
    RATIOAX5 = f'{(clientassociations["80211ax5-count"] / totalclients) * 100:.1f}'
    RATIOAX24 = f'{(clientassociations["80211ax24-count"] / totalclients)*100:.1f}'
    RATIOAC = f'{(clientassociations["80211ac-count"] / totalclients)*100:.1f}'
    RATION5 = f'{(clientassociations["80211n5-count"] / totalclients)*100:.1f}'
    RATION24 = f'{(clientassociations["80211n24-count"] / totalclients)*100:.1f}'
    RATIOA = f'{(clientassociations["80211a-count"] / totalclients)*100:.1f}'
    RATIOG = f'{(clientassociations["80211g-count"] / totalclients)*100:.1f}'
    RATIOB = f'{(clientassociations["80211b-count"] / totalclients)*100:.1f}'

    if DEBUG: print(f'Wireless client ratios: ', end='')
    if DEBUG: print(totalclients, WIFI6E_capable, RATIOAX6, RATIOAX5, RATIOAX24, RATIOAC, RATION5, RATION24, RATIOA, RATIOG, RATIOB)
    
    # Replace variables
    html = template.replace('###CONTROLLER###',controller)
    html = html.replace('###TOTALCLIENTS###',str(totalclients))
    html = html.replace('###COUNT6GHzCapable###',str(WIFI6E_capable))
    html = html.replace('###RATIOAX6###',str(RATIOAX6))
    html = html.replace('###COUNTAX6###',str(clientassociations["80211ax6-count"]))
    html = html.replace('###RATIOAX5###',str(RATIOAX5))
    html = html.replace('###COUNTAX5###',str(clientassociations["80211ax5-count"]))
    html = html.replace('###RATIOAX24###',str(RATIOAX24))
    html = html.replace('###COUNTAX24###',str(clientassociations["80211ax24-count"]))
    html = html.replace('###RATIOAC###',str(RATIOAC))
    html = html.replace('###COUNTAC###',str(clientassociations["80211ac-count"]))
    html = html.replace('###RATION5###',str(RATION5))
    html = html.replace('###COUNTN5###',str(clientassociations["80211n5-count"]))
    html = html.replace('###RATION24###',str(RATION24))
    html = html.replace('###COUNTN24###',str(clientassociations["80211n24-count"]))
    html = html.replace('###RATIOA###',str(RATIOA))
    html = html.replace('###COUNTA###',str(clientassociations["80211a-count"]))
    html = html.replace('###RATIOG###',str(RATIOG))
    html = html.replace('###COUNTG###',str(clientassociations["80211g-count"]))
    html = html.replace('###RATIOB###',str(RATIOB))
    htmltable = html.replace('###COUNTB###',str(clientassociations["80211b-count"]))
    return(htmltable)


def createClientDistributionByWirelessStandard(wirelessdashboarddir, clientcounts):
    ''' Read in overall dashboard template
        Read in controller-specific template [note Catalyst WLC is
           slightly different from Meraki]
        parse clientcounts from input
        replace variable placeholders in template
        create dashboard file (and place in Apache hosting dir?)
    '''
    #print(clientcounts)
    total_80211ax6_count = \
    total_80211ax5_count = total_80211ax24_count = \
    total_80211ac_count = \
    total_80211n5_count = total_80211n24_count = \
    total_80211a_count = total_80211g_count = total_80211b_count = \
    total_all_clients = 0

    wirelessxref = getEnv.getparam('WirelessXRef')
    #f = open("TEMPLATE-CLstats-WirelessClientRadio.html", "r")
    f = open("wireless/TEMPLATE-cdbws.html", "r")
    fwlc = open("wireless/TEMPLATE-cdbws-catwlc.html", "r")
    fmeraki = open("wireless/TEMPLATE-cdbws-meraki.html", "r")

    dashboardtemplate = f.read()
    wlcmodel_templ = fwlc.read()
    merakimodel_temp = fmeraki.read()
    
    html = dashboardtemplate
    #print(htmltemplate)
    for entry in clientcounts:
        # Each entry is the wireless client stats grouped by controller
        if DEBUG: print(entry)
        clientassociations = json.loads(entry)
        controller = clientassociations["controller"]
        clientassociations.pop('controller')
        totalclients = sum(clientassociations.values())
        #print(totalclients)
        total_all_clients += totalclients
        total_80211ax6_count += clientassociations['80211ax6-count']
        total_80211ax5_count += clientassociations['80211ax5-count']
        total_80211ax24_count += clientassociations['80211ax24-count']
        total_80211ac_count += clientassociations['80211ac-count']
        total_80211n5_count += clientassociations['80211n5-count']
        total_80211n24_count += clientassociations['80211n24-count']
        total_80211a_count += clientassociations['80211a-count']
        total_80211g_count += clientassociations['80211g-count']
        total_80211b_count += clientassociations['80211b-count']
        
        # Determine if CatalystWLC or Meraki
        controller_friendlyname = [ item['friendlyname'] for item in wirelessxref if controller == item['alias']][0]
        if DEBUG: print(controller_friendlyname)
        # TO-DO!  Make SURE to test this with Meraki matches later!
        if "wlc" in controller_friendlyname:
            # do WLC things
            if DEBUG: print(clientassociations)
            htmltable = processCatalystWLCdata(wlcmodel_templ,
                                               controller_friendlyname,
                                               clientassociations)
        elif "meraki" in controller:
            # do Meraki things
            pass
        else:
            # Unable to identify
            pass

        # Do the controller, specific replacements
        html = html.replace(f'###{controller_friendlyname}TABLE##',str(htmltable))

    # Do the overall stats replacement
    html = html.replace('###RUNDATETIME###', f'{datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")}')
    
    overallasssociations = { "80211ax6-count": total_80211ax6_count,
                            "80211ax5-count": total_80211ax5_count,
                            "80211ax24-count": total_80211ax24_count,
                            "80211ac-count": total_80211ac_count,
                            "80211n5-count": total_80211n5_count,
                            "80211n24-count": total_80211n24_count,
                            "80211a-count": total_80211a_count,
                            "80211g-count": total_80211g_count,
                            "80211b-count": total_80211b_count
                        }

    if DEBUG: print(overallasssociations)
    
    overalltable = processCatalystWLCdata(wlcmodel_templ, 'OVERALL', overallasssociations)
    finalhtml = html.replace(f'###OVERALLTABLE##', str(overalltable))

    #print(html)
    f = open(f'{wirelessdashboarddir}/ClientsbyRadioStandard.html', "w")
    f.write(finalhtml)
    f.close()


def processWSbySSIDtemplate(overall_counter, controller, results):
    # Receive client distribution by wireless standard and SSID results
    #   parse template substitutions
    
    zero_counter = Counter({
        # Wi-Fi 6E
        'i80211ax6': 0,
        # Wi-Fi 6 (5 and 2.4 GHz)
        'i80211ax5': 0,
        'i80211ax24': 0,
        # Wi-Fi 5 (5 GHz)
        'i80211ac': 0,
        # Wi-Fi 4 (5 and 2.4 GHz)
        'i80211n5': 0,
        'i80211n24': 0,
        # Pre-'Wi-Fi #' marketing spec
        'i80211g': 0,
        'i80211a': 0,
        'i80211b': 0
    })
    
    ssid_clientcounter = copy.deepcopy(zero_counter)
    
    print(f'  Getting client by wireless standard and SSID mapping for {controller}')
    tableheadertemplate = '''    <table>
        <tr>
            <th class="label">SSID</td>
            <th class="ax6-80211">Wi-Fi6E</td>
            <th class="ax5-80211">Wi-Fi6<br>(5GHz)</td>
            <th class="ax24-80211">Wi-Fi6<br>(2.4GHz)</td>
            <th class="ac-80211">Wi-Fi5</td>
            <th class="n5-80211">Wi-Fi4<br>(5GHz)</td>
            <th class="n24-80211">Wi-Fi4<br>(2.4GHz)</td>
            <th class="g-80211">802.11g</td>
            <th class="a-80211">802.11a</td>
            <th class="b-80211">802.11b</td>
        </tr>\n'''

    ssidrowtemplate = '''        <tr>
            <td class="label">###SSID###</td>
            <td class="ax6-80211">###COUNTAX6###</td>
            <td class="ax5-80211">###COUNTAX5###</td>
            <td class="ax24-80211">###COUNTAX24###</td>
            <td class="ac-80211">###COUNTAC###</td>
            <td class="n5-80211">###COUNTN5###</td>
            <td class="n24-80211">###COUNTN24###</td>
            <td class="g-80211">###COUNTG###</td>
            <td class="a-80211">###COUNTA###</td>
            <td class="b-80211">###COUNTB###</td>
         </tr>\n'''

    totalclients = 0
    currentSSID = previousSSID = ''
    cumulativerows = ''
    radioPHYax6 = \
        radioPHYax5 = radioPHYax24 = \
        radioPHYac = radioPHYn5 = radioPHYn24 = \
        radioPHYa = radioPHYg = radioPHYb = 0
    ssidclientcountlist = []

    # TO-DO move these into optionsconfig.yaml instead of static entries
    sensitiveSSIDs = ['DarkStar']

    if DEBUG: print(f'Working controller {controller} results of:\n  ' + str(results))
    for index, standardclients in enumerate(results, start=1):
        if DEBUG: print(f'Executing row {index} of {len(results)}')
        currentSSID = standardclients[1]
        phytype = standardclients[2]
        phyclientcount = standardclients[3]
        if DEBUG: print(f'    Proccessing row - {standardclients}')
        if DEBUG: print(f'    Current SSID is {currentSSID} and previousSSID is {previousSSID}')

        '''A few checks to do since we're getting results aggregated
        by controller, grouped and sorted by SSID
        
        As we're looping through, 
        IF...
        there is no previous SSID (we're on first run)
            OR
        current SSID == previous SSID (on same SSID)
            OR
        there is only one result in list
            THEN match against wireless standards and count
            
        current SSID != previous SSID (new SSID being processed)
            THEN close out the counts;
            summarize/print results (do replacements);
            zero counters; 
            do matches against wireless standards and count (on new row)
            
        this is last item in list
            summarize/print results (do replacements)
        
        '''
        # Check to see if we're looping through and working on the same
        #   SSID...or if it's the first time through (no previous SSID)... 
        #   or if we're working on a controller / PHY instance of only 1 entry...
        if currentSSID == previousSSID or \
            previousSSID == '' or \
            len(results) == 1:
            if DEBUG: print(f'Process as - {currentSSID}')
            match phytype:
                case 'client-dot11b':
                    ssid_clientcounter['i80211b'] = phyclientcount
                case 'client-dot11a':
                    ssid_clientcounter['i80211a'] = phyclientcount
                    #radioPHYa = phyclientcount
                case 'client-dot11g':
                    ssid_clientcounter['i80211g'] = phyclientcount
                    #radioPHYg = phyclientcount
                case 'client-dot11n-24-ghz-prot':
                    ssid_clientcounter['i80211n24'] = phyclientcount
                    #radioPHYn24 = phyclientcount
                case 'client-dot11n-5-ghz-prot':
                    ssid_clientcounter['i80211n5'] = phyclientcount
                    #radioPHYn5 = phyclientcount
                case 'client-dot11ac':
                    ssid_clientcounter['i80211ac'] = phyclientcount
                    #radioPHYac = phyclientcount
                case 'client-dot11ax-24ghz-prot':
                    ssid_clientcounter['i80211ax24'] = phyclientcount
                    #radioPHYax24 = phyclientcount
                case 'client-dot11ax-5ghz-prot':
                    ssid_clientcounter['i80211ax5'] = phyclientcount
                    #radioPHYax5 = phyclientcount
                case 'client-dot11ax-6ghz-prot':
                    ssid_clientcounter['i80211ax6'] = phyclientcount
                    #radioPHYax6 = phyclientcount
            previousSSID = currentSSID
        else:
            if DEBUG: print(f'    Got a new SSID {currentSSID} - must process prior results for {previousSSID}')
            if DEBUG: print(ssid_clientcounter)
            #print("    ", radioPHYb, radioPHYg, radioPHYa, radioPHYn24, radioPHYn5, \
            #    radioPHYac, radioPHYax24, radioPHYax5, radioPHYax6)

            # Hide 'sensitive' SSIDs
            if previousSSID in sensitiveSSIDs:
                previousSSID = '[hidden]'

            ssidrow = ssidrowtemplate.replace('###SSID###',previousSSID)
            ssidrow = ssidrow.replace('###COUNTAX6###',str(ssid_clientcounter['i80211ax6']))
            ssidrow = ssidrow.replace('###COUNTAX5###',str(ssid_clientcounter['i80211ax5']))
            ssidrow = ssidrow.replace('###COUNTAX24###',str(ssid_clientcounter['i80211ax24']))
            ssidrow = ssidrow.replace('###COUNTAC###',str(ssid_clientcounter['i80211ac']))
            ssidrow = ssidrow.replace('###COUNTN5###',str(ssid_clientcounter['i80211n5']))
            ssidrow = ssidrow.replace('###COUNTN24###',str(ssid_clientcounter['i80211n25']))
            ssidrow = ssidrow.replace('###COUNTG###',str(ssid_clientcounter['i80211g']))
            ssidrow = ssidrow.replace('###COUNTA###',str(ssid_clientcounter['i80211a']))
            ssidrow = ssidrow.replace('###COUNTB###',str(ssid_clientcounter['i80211b']))
            if DEBUG: print(f'Fragment is:\n{ssidrow}')
            cumulativerows += ssidrow

            #totalclients += radioPHYax6 + radioPHYax5 + radioPHYax24 + \
            #    radioPHYac + radioPHYn5 + radioPHYn24 + radioPHYa + \
            #    radioPHYg + radioPHYb
            if DEBUG: print(f'Intermediate controller counter:\n{ssid_clientcounter}')
            if DEBUG: print(f'Intermediate overall counter:   \n{ssid_clientcounter}')
            overall_counter.update(ssid_clientcounter)
            if DEBUG: print(f'Updated overall counter:        \n{overall_counter}')

            # Now do collections on new row; zero counters; assign data
            if DEBUG: print(f'    Now doing new PHY matches for the new SSID {currentSSID}')
            radioPHYb = radioPHYg = radioPHYa = radioPHYn24 = radioPHYn5 = \
                radioPHYac = radioPHYax24 = radioPHYax5 = radioPHYax6 = 0

            ssidclientcountlist.append((previousSSID,ssid_clientcounter))
            ssid_clientcounter = copy.deepcopy(zero_counter)

            match phytype:
                case 'client-dot11b':
                    ssid_clientcounter['i80211b'] = phyclientcount
                case 'client-dot11a':
                    ssid_clientcounter['i80211a'] = phyclientcount
                    #radioPHYa = phyclientcount
                case 'client-dot11g':
                    ssid_clientcounter['i80211g'] = phyclientcount
                    #radioPHYg = phyclientcount
                case 'client-dot11n-24-ghz-prot':
                    ssid_clientcounter['i80211n24'] = phyclientcount
                    #radioPHYn24 = phyclientcount
                case 'client-dot11n-5-ghz-prot':
                    ssid_clientcounter['i80211n5'] = phyclientcount
                    #radioPHYn5 = phyclientcount
                case 'client-dot11ac':
                    ssid_clientcounter['i80211ac'] = phyclientcount
                    #radioPHYac = phyclientcount
                case 'client-dot11ax-24ghz-prot':
                    ssid_clientcounter['i80211ax24'] = phyclientcount
                    #radioPHYax24 = phyclientcount
                case 'client-dot11ax-5ghz-prot':
                    ssid_clientcounter['i80211ax5'] = phyclientcount
                    #radioPHYax5 = phyclientcount
                case 'client-dot11ax-6ghz-prot':
                    ssid_clientcounter['i80211ax6'] = phyclientcount
                    #radioPHYax6 = phyclientcount
            previousSSID = currentSSID

        if DEBUG: print(f'Outside final check {index} and len {len(results)}')

        # Check to see if we're on the only or last row
        if index == len(results):
            if DEBUG: print(f'Inside final check {index} and len {len(results)} - 1')
            # Hide 'sensitive' SSIDs
            if currentSSID in sensitiveSSIDs:
                ssidlabel = '[hidden]'
            else:
                ssidlabel = currentSSID

            ssidrow = ssidrowtemplate.replace('###SSID###',ssidlabel)
            ssidrow = ssidrow.replace('###COUNTAX6###',str(ssid_clientcounter['i80211ax6']))
            ssidrow = ssidrow.replace('###COUNTAX5###',str(ssid_clientcounter['i80211ax5']))
            ssidrow = ssidrow.replace('###COUNTAX24###',str(ssid_clientcounter['i80211ax24']))
            ssidrow = ssidrow.replace('###COUNTAC###',str(ssid_clientcounter['i80211ac']))
            ssidrow = ssidrow.replace('###COUNTN5###',str(ssid_clientcounter['i80211n5']))
            ssidrow = ssidrow.replace('###COUNTN24###',str(ssid_clientcounter['i80211n25']))
            ssidrow = ssidrow.replace('###COUNTG###',str(ssid_clientcounter['i80211g']))
            ssidrow = ssidrow.replace('###COUNTA###',str(ssid_clientcounter['i80211a']))
            ssidrow = ssidrow.replace('###COUNTB###',str(ssid_clientcounter['i80211b']))
            #print(ssidrow)
            cumulativerows += ssidrow
            
            #totalclients += radioPHYax6 + radioPHYax5 + radioPHYax24 + \
            #    radioPHYac + radioPHYn5 + radioPHYn24 + radioPHYa + \
            #    radioPHYg + radioPHYb
            if DEBUG: print(f'Intermediate controller counter:\n{ssid_clientcounter}')
            if DEBUG: print(f'Intermediate overall counter:   \n{ssid_clientcounter}')
            overall_counter.update(ssid_clientcounter)
            if DEBUG: print(f'Updated overall counter:        \n{overall_counter}')
            ssidclientcountlist.append((previousSSID,ssid_clientcounter))


    if DEBUG: print(f'Finished controller {controller} processing')
    controllerhtml = f'{tableheadertemplate}\n{cumulativerows}\n    </table>'
    #print(controllerhtml)
    return(controllerhtml, ssidclientcountlist, overall_counter)


def genoveralltable(aggssidlist, eventoverall_counter):
    # Generate the Overall event summary table (output as HTML)
    # Takes in the aggregate SSID list and client counters and overall
    #    counter
    
    ssidsummary_list = []
    ssidsummary_counter = Counter({
        # Wi-Fi 6E
        'i80211ax6': 0,
        # Wi-Fi 6 (5 and 2.4 GHz)
        'i80211ax5': 0,
        'i80211ax24': 0,
        # Wi-Fi 5 (5 GHz)
        'i80211ac': 0,
        # Wi-Fi 4 (5 and 2.4 GHz)
        'i80211n5': 0,
        'i80211n24': 0,
        # Pre-'Wi-Fi #' marketing spec
        'i80211g': 0,
        'i80211a': 0,
        'i80211b': 0
    })

    if DEBUG: print('Got into genoveralltable')
    for controllerssids in aggssidlist:
        if DEBUG: print(f'Got controllerssids: {controllerssids}')
        for ssidclients in controllerssids:
            if DEBUG: print(f'Got ssidclients: {ssidclients}')
            ssid = ssidclients[0]
            if DEBUG: print(f'Got: {ssid}')
            ssid_index = next((index for (index, d) in enumerate(ssidsummary_list) if d["ssid"] == f"{ssid}"), None)
            if DEBUG: print(f'Got ssid_index: {ssid_index}')
            #if not any(d['ssid'] == ssid for d in ssidsummary_list):
            if ssid_index is not None:
                # Update existing entry
                if DEBUG: print('Oof')
                if DEBUG: print(ssid_index)
                if DEBUG: print(ssidsummary_list)
                ssidsummary_list[ssid_index]['clientcounts'].update(ssidclients[1])
                if DEBUG: print(ssidsummary_list)
                
            else:
                # Add new entry
                ssidsummary_list.append({"ssid": ssid,
                                         "clientcounts": ssidclients[1]})
    if DEBUG: print(ssidsummary_list)
    tableheadertemplate = '''    <table>
        <tr>
            <th class="label">SSID</td>
            <th class="ax6-80211">Wi-Fi6E</td>
            <th class="ax5-80211">Wi-Fi6<br>(5GHz)</td>
            <th class="ax24-80211">Wi-Fi6<br>(2.4GHz)</td>
            <th class="ac-80211">Wi-Fi5</td>
            <th class="n5-80211">Wi-Fi4<br>(5GHz)</td>
            <th class="n24-80211">Wi-Fi4<br>(2.4GHz)</td>
            <th class="g-80211">802.11g</td>
            <th class="a-80211">802.11a</td>
            <th class="b-80211">802.11b</td>
        </tr>\n'''

    html = tableheadertemplate
    ssidrows = ''
    for ssid in ssidsummary_list:
        ssidrowtemplate = f'''        <tr>
            <td class="label">{ssid["ssid"]}</td>
            <td class="ax6-80211">{ssid["clientcounts"]['i80211ax6']}</td>
            <td class="ax5-80211">{ssid["clientcounts"]['i80211ax5']}</td>
            <td class="ax24-80211">{ssid["clientcounts"]['i80211ax24']}</td>
            <td class="ac-80211">{ssid["clientcounts"]['i80211ac']}</td>
            <td class="n5-80211">{ssid["clientcounts"]['i80211n5']}</td>
            <td class="n24-80211">{ssid["clientcounts"]['i80211n24']}</td>
            <td class="g-80211">{ssid["clientcounts"]['i80211g']}</td>
            <td class="a-80211">{ssid["clientcounts"]['i80211a']}</td>
            <td class="b-80211">{ssid["clientcounts"]['i80211b']}</td>
        </tr>\n'''
        html += ssidrowtemplate
    html += '    </table>\n    <p><p><p>\n    <hr>\n<h2>Overall Counts</h2><p>\n'
    html += tableheadertemplate
    html += f'''        <tr>
            <td class="label">ALL SSIDs</td>
            <td class="ax6-80211">{eventoverall_counter['i80211ax6']}</td>
            <td class="ax5-80211">{eventoverall_counter['i80211ax5']}</td>
            <td class="ax24-80211">{eventoverall_counter['i80211ax24']}</td>
            <td class="ac-80211">{eventoverall_counter['i80211ac']}</td>
            <td class="n5-80211">{eventoverall_counter['i80211n5']}</td>
            <td class="n24-80211">{eventoverall_counter['i80211n24']}</td>
            <td class="g-80211">{eventoverall_counter['i80211g']}</td>
            <td class="a-80211">{eventoverall_counter['i80211a']}</td>
            <td class="b-80211">{eventoverall_counter['i80211b']}</td>
            </tr>\n    </table>'''
    if DEBUG: print(html)
    return(html)


def createWirelessClientDistributionByWSandSSID(wirelessdashboarddir, sqlenv):
    # Wireless Client Distribution by wireless standard (RadioPHYType) and SSID
    
    wirelessxref = getEnv.getparam('WirelessXRef')

    # Read MySQL WirelessClient table for latest controller stats
    
    # Iterate by controller with SSID and RadioPHYType stats
    # Replace variables against template
    # Do an 'overall event' instance
    print('  Getting wireless client data by Radio Standard and SSID')
    sql = f'''SELECT DISTINCT(Controller)
                FROM WirelessClients
                WHERE SeenLastPoll = 1'''
    #controllers = SelectFromMySQL.selectsql(sqlenv, sql)
    controllers = doDB.fetchall(sqlenv, sql)
    
    if DEBUG: print(controllers)
    
    eventoverall_counter = Counter({
        # Wi-Fi 6E
        'i80211ax6': 0,
        # Wi-Fi 6 (5 and 2.4 GHz)
        'i80211ax5': 0,
        'i80211ax24': 0,
        # Wi-Fi 5 (5 GHz)
        'i80211ac': 0,
        # Wi-Fi 4 (5 and 2.4 GHz)
        'i80211n5': 0,
        'i80211n24': 0,
        # Pre-'Wi-Fi #' marketing spec
        'i80211g': 0,
        'i80211a': 0,
        'i80211b': 0
    })

    aggssidlist = []
    
    f = open(f'wireless/TEMPLATE-cdbsaws.html', "r")
    htmltemplate = f.read()

    html = htmltemplate.replace('###RUNDATETIME###', f'{datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")}')
    
    for controller in controllers:
        ###CONTINUE HERE with Class instantiation; global and controller
        if DEBUG: print(controller[0])
        controller_friendlyname = [ item['friendlyname'] for item in wirelessxref if controller[0] == item['alias']][0]
        if DEBUG: print(controller_friendlyname)
        
        sql = f'''SELECT Controller, SSID, RadioPHYType, count(*) 
        FROM WirelessClients 
        WHERE SeenLastPoll = true and Controller = '{controller[0]}'
        GROUP BY Controller, SSID, RadioPHYType
        ORDER BY Controller, SSID;'''

        #clientdistresults = SelectFromMySQL.selectsql(sqlenv, sql)
        clientdistresults = doDB.fetchall(sqlenv, sql)
        if DEBUG: print(clientdistresults)
        if DEBUG: print(f'Overall counter is: {eventoverall_counter}')
        controllerhtml, ssidlist, eventoverall_counter = processWSbySSIDtemplate(eventoverall_counter,
                                                 controller[0],
                                                 clientdistresults)
        if DEBUG: print(controllerhtml)
        aggssidlist.append(ssidlist)
        html = html.replace(f'###{controller_friendlyname}TABLE##',controllerhtml)
        
    # Gen the Overall/Summary table
    overalltablehtml = genoveralltable(aggssidlist, eventoverall_counter)
    html = html.replace(f'###OVERALLTABLE##',overalltablehtml)
    fo = open(f'{wirelessdashboarddir}/ClientsbySSIDandRadioStandard.html', "w")
    fo.write(html)
    fo.close()


def createWirelessAPClientLoad(wirelessdashboarddir, sqlenv):
    # Data to collect
    #   TOtal clients
    #   Total APs online / configured / down
    #   APs < 60 clients (lime)
    #   APs < 75 & >= 60 clients
    #   APs >= 75 clients

    SQL = '''SELECT APMACAddress,count(*) 
    FROM WirelessClients 
    WHERE SeenLastPoll = true 
    GROUP BY APMACAddress
    ORDER BY count(*) DESC;
    '''
    #apclientcounts = SelectFromMySQL.selectsql(sqlenv, SQL)
    apclientcounts = doDB.fetchall(sqlenv, SQL)
    #print(apclientcounts)
    totalaps = len(apclientcounts)

    print(f'Count of APs with clients: {totalaps}')
    # Data to collect
    #   TOtal clients
    #   Total APs online / configured / down
    #   APs < 60 clients (lime)
    #   APs < 75 & >= 60 clients
    #   APs >= 75 clients

    print('Collecting Show-wide AP count...')
    APSQL = '''SELECT EthernetMACAddress, Name, Model from WirelessAPs'''
    #APlist = SelectFromMySQL.selectsql(sqlenv, APSQL)
    APlist = doDB.fetchall(sqlenv, APSQL)
    #print(APlist)

    f = open("wireless/TEMPLATE-CLstats-WirelessAPLoad.html", "r")
    htmltemplate = f.read()

    apentries = '\t<tr>\n'
    underthreshold = 0
    midthreshold = 0
    overthreshold = 0
    totalclients = 0

    for count, value in enumerate(apclientcounts, start=1):
        apmac = value[0]
        clientcount = value[1]
        totalclients += clientcount
        apname = [item[1] for item in APlist if apmac == item[0]][0]
        apmodel = [item[2] for item in APlist if apmac == item[0]][0]
        #print(apname, apmodel, clientcount)
        if clientcount < MINTHRESHOLD:
            bgcolor = 'lime'
            textcolor = 'black'
            apentry = f'''			<td bgcolor="lime"><font color="black">{apname}<br />
        {apmodel}<br />
        2.4GHz: 0<br />
        5GHz: {clientcount}</font></td>'''
            underthreshold += 1
        elif clientcount < HIGHTHRESHOLD and clientcount > MINTHRESHOLD:
            bgcolor = 'yellow'
            textcolor = 'black'
            apentry = f'''			<td bgcolor="yellow"><font color="black">{apname}<br />
        {apmodel}<br />
        2.4GHz: 0<br />
        5GHz: {clientcount}</font></td>'''
            midthreshold += 1
        else:
            bgcolor = 'red'
            textcolor = 'white'
            apentry = f'''			<td bgcolor="orange"><font color="black">{apname}<br />
        {apmodel}<br />
        2.4GHz: 0<br />
        5GHz: {clientcount}</font></td>'''
            overthreshold += 1
        #print(apentry)
        apentries += apentry
        # Check if we need to start a new row
        if count % MAX_ROW_CELL_COUNT == 0:
            apentries += '\n\t\t</tr>\n\t\t<tr>\n'
    apentries += '\n\t\t</tr>'

    #print(apentries)
    html = htmltemplate.replace('###TABLEROWS###',apentries)

    # Other fixups
    ## Client count
    print(f'Total Event Wireless Client count: {totalclients}')
    html = html.replace('###TOTALCLIENTCOUNT###',str(totalclients))

    ## AP Count - should be sum of all currently reachable APs
    SQL = '''SELECT count(WirelessAPs.IPAddress)
    FROM WirelessAPs
    LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
    WHERE pingresults.reachable_pct > 0;
    '''
    #aps_up = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    aps_up = doDB.fetchall(sqlenv, SQL)[0][0]
    print(f'Count of ALL APs Online: {aps_up}')
    html = html.replace('###APSUPCOUNT###',str(aps_up))

    SQL = '''SELECT NAME 
    FROM WirelessAPs where IPAddress IN (
      SELECT WirelessAPs.IPAddress
      FROM WirelessAPs
      LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
      WHERE pingresults.reachable_pct > 0 )
      
    '''
    #query_result = SelectFromMySQL.selectsql(sqlenv, SQL)
    query_result = doDB.fetchall(sqlenv, SQL)
    if not query_result:
        aps_up = []
    else:
        aps_up = query_result[0][0]
    upap_list = []
    for upap in aps_up:
        upap_list.append(upap[0])
    #print(f'Names of APs Up: {upap_list}')

    ## APs Configured Count - should be sum of all entries in MySQL
    ##   inventory table that are 'WirelessAP'
    ###APSCONFIGURED###
    SQL = '''select count(hostname) from inventory where device_group = 'WirelessAP';
    '''
    #apcount = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    apcount = doDB.fetchall(sqlenv, SQL)[0][0]
    #print(f'Historical AP Count from Inventory Database: {apcount}')
    #html = html.replace('###APSCONFIGURED###',str(apcount))
    html = html.replace('###APSCONFIGURED###','')

    
    ###RED###   or APs down
    SQL = '''SELECT count(WirelessAPs.IPAddress)
    FROM WirelessAPs
    LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
    WHERE pingresults.reachable_pct = 0;
    '''
    #aps_down = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    aps_down = doDB.fetchall(sqlenv, SQL)[0][0]
    print(f'Count of APs Down: {aps_down}')
    html = html.replace('###APSDOWNCOUNT###',str(aps_down))


    SQL = '''SELECT NAME 
    FROM WirelessAPs where IPAddress IN (
      SELECT WirelessAPs.IPAddress
      FROM WirelessAPs
      LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
      WHERE pingresults.reachable_pct = 0 )
      
    '''
    #aps_down = SelectFromMySQL.selectsql(sqlenv, SQL)
    aps_down = doDB.fetchall(sqlenv, SQL)
    downap_list = []
    for downap in aps_down:
        downap_list.append(downap[0])
    #print(f'Names of APs Down: {downap_list}')

    ###GREEN### ap count <minthresh
    html = html.replace('###GREEN###',str(underthreshold))

    ###YELLOW### ap count in midrange
    html = html.replace('###YELLOW###',str(midthreshold))
    
    ###ORANGE### ap count in highrange
    html = html.replace('###ORANGE###',str(overthreshold))
    
    ###JOBRUNTIME###
    html = html.replace('###RUNDATETIME###', f'{datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")}')


    #print(html)
    #print(html)
    #f = open(f'{wirelessdashboarddir}/CLstats-WirelessAPLoad-{controller}.html', "w")
    f = open(f'{wirelessdashboarddir}/CLstats-WirelessAPLoad.html', "w")
    f.write(html)
    f.close()


def runjob(mysqlenv, influxenv, wirelessdashboarddir):
    start = datetime.now()
    print(f'\n\nStarted task at {start.strftime("%H:%M:%S")}')
    # mysqlenv = GetEnv.getparam("MySQL")
    # influxenv = GetEnv.getparam("InfluxDB")
    # wirelessdashboarddir = GetEnv.getparam("WirelessDashboardDirectory")

    # Process stats for Grafana Wireless dashboards
    clientcounts = select_wireless_clients(mysqlenv)
    clients_lineprotocol = format_to_influx_lineprotocol(clientcounts)
    if DEBUG: print(clients_lineprotocol)
    put_wireless_stats_in_influx(influxenv, clients_lineprotocol)
    
    # TO-DO - Add a Meraki version of client collector

    # Process Wireless Radio Distribution
    createClientDistributionByWirelessStandard(wirelessdashboarddir, clientcounts)

    # Process Wireless Client Distribution
    # TO-DO: Update to remove event-specific WLC names from script
    createWirelessClientDistributionByWSandSSID(wirelessdashboarddir, mysqlenv)

    # Process AP Client Load
    createWirelessAPClientLoad(wirelessdashboarddir, mysqlenv)
    end = datetime.now()
    print(f'Ended task at {end.strftime("%H:%M:%S")}    '
          f'Processing time: {end - start}\n\n')



def run_threaded(job_func, mysqlenv, influxenv, wirelessdashboarddir):
    job_thread = threading.Thread(target=job_func, 
                                  args=(mysqlenv, influxenv, 
                                        wirelessdashboarddir,))
    print(f'\nRunning new thread {threading.current_thread().ident} at {time.ctime()}')
    job_thread.start()



## MAIN
if __name__ == "__main__":
    #start = datetime.now()
    #print(f'Started task at {start.strftime("%H:%M:%S")}')

    mysqlenv = getEnv.getparam("MySQL")
    influxenv = getEnv.getparam("InfluxDB")
    wirelessdashboarddir = getEnv.getparam("WirelessDashboardDirectory")

    roomid = getEnv.getparam('alerts_webexroomid')
    #sendWebexMessage.sendMessage(roomid,'Starting createWirelessClientDashboards.py monitoring app...')

    print(f'Adding to scheduler at {FREQUENCY} second frequency - '
          f'[may not run immediately]\n')
    schedule.every(FREQUENCY).seconds.do(run_threaded, runjob,
                                         mysqlenv, influxenv,
                                         wirelessdashboarddir)

    #print('\nRunning a sleep loop.', end='', flush=True)

    try:
        while True:
            if FREQUENCY - schedule.idle_seconds() > 20:
                print(f'\rNext run in {round(schedule.idle_seconds())} seconds.', end='', flush=True)
            #print('.', end='', flush=True)
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        print('\nUser initiated stop - closing down process...')
        #sendWebexMessage.sendMessage(roomid,'Stopping createWirelessClientDashboards.py monitoring app...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)