"""Primary collector and dashboard creator for wireless channel utilization

(createWirelessChannelUtilDashboards.py)
Polls Wireless LAN Controllers (WLCs) for radio channel metrics, then 
creates custom dashboards for channel utilization

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
v1   2023-0826 for IMPACT24 to be modular with other CLNOC scripts
v2   2023-0830 modify for modularity and packaging
v3   2023-0906  Updates to docs and github packaging
"""

# Credits:
__version__ = '3'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
from influxdb_client import InfluxDBClient
#import SelectFromMySQL
from common import doDB
from datetime import datetime
from common import getEnv
from operator import itemgetter
import argparse
import schedule
import time
import os, sys

# Global variables
MINTHRESHOLD = 60
HIGHTHRESHOLD = 75
MAX_ROW_CELL_COUNT = 10
CCA_WARN = 50
CCA_CRITICAL = 75

FREQUENCY = 120    # How often to run poller and dashboard creator

# Functions
def createWirelessAPClientLoad(controller, apstats, sqlenv, wirelessdashboard):
    # Data to collect
    #   TOtal clients
    #   Total APs online / configured / down
    #   APs < 60 clients (lime)
    #   APs < 75 & >= 60 clients
    #   APs >= 75 clients

    total_clients = 0
    
    for ap in apstats:
        total_clients += ap.get("radioslot0--stations") + \
            ap.get("radioslot1--stations") + ap.get("radioslot2--stations", 0)
    total_aps = len(apstats)
    print(f'Total Clients: {total_clients}')
    print(f'Total APs: {total_aps}')
 
    #print('Collecting Show-wide AP count...')
    APSQL = '''SELECT RadioMACAddress, Name, Model from WirelessAPs'''
    #APlist = SelectFromMySQL.selectsql(sqlenv, APSQL)
    APlist = doDB.fetchall(sqlenv, APSQL)
    #print(APlist)

    f = open("wireless/TEMPLATE-WirelessChannelUtilization.html", "r")
    htmltemplate = f.read()

    apentries = '<tr>\n'
    underthreshold = 0
    midthreshold = 0
    overthreshold = 0
    totalclients = 0

    for count, value in enumerate(apstats, start=1):
        apmac = value.get("ap")
        slot0clientcount = value.get("radioslot0--stations")
        slot1clientcount = value.get("radioslot1--stations")
        slot2clientcount = value.get("radioslot2--stations", 0)
        
        slot0ccautil = value.get("radioslot0--cca-util-percentage")
        slot1ccautil = value.get("radioslot1--cca-util-percentage")
        slot2ccautil = value.get("radioslot2--cca-util-percentage", 0)
        
        totalclients += slot0clientcount + slot1clientcount + slot2clientcount
        try:
            apname = [item[1] for item in APlist if apmac == item[0]][0]
            apmodel = [item[2] for item in APlist if apmac == item[0]][0]
        except Exception as e:
            print(f'Failed on exception: {e}')
            continue
        #print(apname, apmodel, clientcount)
        if slot0clientcount < MINTHRESHOLD and \
            slot1clientcount < MINTHRESHOLD and \
            slot2clientcount < MINTHRESHOLD and \
            slot0ccautil < CCA_WARN and \
            slot1ccautil < CCA_WARN and \
            slot2ccautil < CCA_WARN:
            bgcolor = 'lime'
            textcolor = 'black'
            underthreshold += 1
        elif (slot0clientcount < HIGHTHRESHOLD and \
              slot0clientcount > MINTHRESHOLD) or \
             (slot1clientcount < HIGHTHRESHOLD and \
              slot1clientcount > MINTHRESHOLD) or \
             (slot2clientcount < HIGHTHRESHOLD and \
              slot2clientcount > MINTHRESHOLD) or \
             slot0ccautil < CCA_WARN and \
             slot1ccautil < CCA_WARN and \
             slot2ccautil < CCA_WARN:
            bgcolor = 'yellow'
            textcolor = 'black'
            midthreshold += 1
        else:
            bgcolor = 'red'
            textcolor = 'white'
            overthreshold += 1
        #print(apentry)
        # Commenting this out as Chris O doesn't want slot0 / 2.4 GHz
        # This is the original version with slot0 - uncomment if wanted
        """apentry = f'''            <td bgcolor="{bgcolor}">
                <font color="{textcolor}">{apname}<br />{apmodel}<br /><pre>slot0: {slot0clientcount:>3} / {value.get("radioslot0--cca-util-percentage"):>3}%
slot1: {slot1clientcount:>3} / {value.get("radioslot1--cca-util-percentage"):>3}%
slot2: {slot2clientcount:>3} / {value.get("radioslot2--cca-util-percentage", 0):>3}%</pre>
                </font>
            </td>
'''
"""
        # This is the version without slot0 / 2.4 GHz
        apentry = f'''            <td bgcolor="{bgcolor}">
                <font color="{textcolor}">{apname}<br />{apmodel}<br /><pre>slot1: {slot1clientcount:>3} / {value.get("radioslot1--cca-util-percentage"):>3}%
slot2: {slot2clientcount:>3} / {value.get("radioslot2--cca-util-percentage", 0):>3}%</pre>
                </font>
            </td>
'''
        apentries += apentry
        # Check if we need to start a new row
        if count % MAX_ROW_CELL_COUNT == 0:
            apentries += '\n\t\t</tr>\n\t\t<tr>\n'
    apentries += '        </tr>'

    #print(apentries)
    html = htmltemplate.replace('###CONTROLLER###',controller)
    html = html.replace('###TABLEROWS###',apentries)

    # Other fixups
    ## Client count
    print(f'Total venue Wireless Client count: {totalclients}')
    html = html.replace('###TOTALCLIENTCOUNT###',str(totalclients))

    
    ## AP Count - should be sum of all currently reachable APs
    SQL = f'''SELECT count(WirelessAPs.IPAddress)
    FROM WirelessAPs
    LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
    WHERE pingresults.reachable_pct > 0 AND Controller = '{controller}';
    '''
    
    #aps_up = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    aps_up = doDB.fetchall(sqlenv, SQL)[0][0]
    print(f'Count of APs Up: {aps_up}')
    html = html.replace('###APSUPCOUNT###',str(aps_up))

    SQL = f'''SELECT NAME 
    FROM WirelessAPs where IPAddress IN (
      SELECT WirelessAPs.IPAddress
      FROM WirelessAPs
      LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
      WHERE pingresults.reachable_pct > 0 AND Controller = '{controller}')
      
    '''
    #aps_up = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    aps_up = doDB.fetchall(sqlenv, SQL)[0][0]
    upap_list = []
    for upap in aps_up:
        upap_list.append(upap[0])
    #print(f'Names of APs Up: {upap_list}')

    """
    ## APs Configured Count - should be sum of all entries in MySQL
    ##   inventory table that are 'WirelessAP'
    ###APSCONFIGURED###
    SQL = '''SELECT count(hostname) FROM inventory 
    WHERE device_group = 'WirelessAP';
    '''
    apcount = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    print(f'AP Count: {apcount}')
    html = html.replace('###APSCONFIGURED###',str(apcount))
    """
    
    ###RED###   or APs down
    SQL = f'''SELECT count(WirelessAPs.IPAddress)
    FROM WirelessAPs
    LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
    WHERE pingresults.reachable_pct = 0 AND Controller = '{controller}';
    '''
    #aps_down = SelectFromMySQL.selectsql(sqlenv, SQL)[0][0]
    aps_down = doDB.fetchall(sqlenv, SQL)[0][0]
    print(f'Count of APs Down: {aps_down}')
    html = html.replace('###APSDOWNCOUNT###',str(aps_down))

    SQL = f'''SELECT NAME 
    FROM WirelessAPs where IPAddress IN (
      SELECT WirelessAPs.IPAddress
      FROM WirelessAPs
      LEFT JOIN pingresults ON WirelessAPs.IPAddress = pingresults.mgmt_ip_address
      WHERE pingresults.reachable_pct = 0 AND Controller = '{controller}')
      
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
    f = open(f'{wirelessdashboarddir}/WirelessChannelUtilization-{controller}.html', "w")
    f.write(html)
    f.close()


def start_all(influxenv, mysqlenv):
    url = f'{influxenv["protocol"]}://{influxenv["host"]}:{influxenv["port"]}'

    client = InfluxDBClient(url=url, 
                            token=influxenv["token"], 
                            org=influxenv["org"])

    query_api = client.query_api()

    # Enter WLC names/aliases from optionsconfig.yaml and MySQL
    #   inventory records
    #WLC_list = ['NOC-MBCC-SSO-1', 'NOC-KEYNOTE-SSO-1', 'NOC-MGM-LUX-SSO-1']
    WLC_list = ['wlc', 'wlc-site-2']

    for wlc in WLC_list:
        execstartTime = datetime.now()
        print(f'\nRunning at {execstartTime}')

        print(f'Working WLC: {wlc}')
        ## using Table structure
        #tables = query_api.query('from(bucket:"my-bucket") |> range(start: -10m)')
        tables = query_api.query(f"""from(bucket:"CLNOC") |> range(start: -2m) 
        |> filter(fn: (r) => r["_measurement"] == "wireless-rrmv2")
        |> filter(fn: (r) => r["wlc"] == "{wlc}")
        |> group(columns: ["measurement", "wlc", "apmac"])
        |> yield(name: "last")
        """)

        #print(tables)
        aprrmstats = []
        for table in tables:
            # These would be grouped by WLC and AP
            #print(table.records[0])
            wlc = table.records[0].values.get("wlc")
            ap = table.records[0].values.get("apmac")
            #print(wlc, ap)
            aprecord = {
                "wlc": wlc,
                "ap": ap
            }
            for record in table.records:
                # These would be radioslots and metrics (eg. rx-util-percentage)
                #print (record.values)
                # if first record set WLC, AP
                #aprecord.update({f'radioslot{record.values["radioslot"]}--{record.values["_field"]}': int(f'{record.values["_value"]:.0f}')})
                aprecord.update({f'radioslot{record.values["radioslot"]}--{record.values["_field"]}': int(f'{record.values.get("_value", 0):.0f}')})
            aprrmstats.append(aprecord)
            #print(aprecord)
            #print(aprrmstats)
        #print(aprrmstats)
        try:
            newaprrmlist = sorted(aprrmstats, 
                            key=itemgetter('radioslot1--cca-util-percentage', 
                                        'radioslot1--stations'),
                            reverse=True
                            )
        except Exception as e:
            print('Got an Exception - {e}')
        else:
            #print(newaprrmlist)
            createWirelessAPClientLoad(wlc, newaprrmlist, mysqlenv, "wirelessdashboarddir")
    print('\nRunning a sleep loop.', end='', flush=True)



if __name__ == "__main__":
    execstartTime = datetime.now()
    print(f'Starting script {os.path.basename(__file__)} at {execstartTime}')

    parser = argparse.ArgumentParser(
        description='Start periodic polling of Wireless Channel Utilization stats')
    parser.add_argument('--debug', 
                        dest='debug', 
                        default=False, 
                        action='store_true',
                        help='Enable debug - output to console, no '\
                            'output Influx'
                        )
    args = parser.parse_args()
    
    influxenv = getEnv.getparam('InfluxDB')
    mysqlenv = getEnv.getparam('MySQL')
    wirelessdashboarddir = getEnv.getparam('WirelessDashboardDirectory')

    # Run manually first, then schedule
    start_all(influxenv, mysqlenv)

    schedule.every(FREQUENCY).seconds.do(start_all, 
                                  influxenv=influxenv,
                                  mysqlenv=mysqlenv)

    #print('\nRunning a sleep loop.', end='', flush=True)

    try:
        while True:
            if FREQUENCY - schedule.idle_seconds() > 20:
                print(f'\rNext run in {round(schedule.idle_seconds())} seconds.', end='', flush=True)
            #print('.', end='', flush=True)
            schedule.run_pending()
            time.sleep(5)
    except KeyboardInterrupt:
        print('\nUser initiated stop - closing down process...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
