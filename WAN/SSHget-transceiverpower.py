"""Obtains router optical transceiver power levels via SSH

(SSHget-transceiverpower.py)
Reads the InterfaceDevices polling definition from the optionsconfig.yaml
project file.  Performs SSH collection to get optical transceiver
power levels.  Formats results in Influx line protocol and pushes to
InfluxDB.

Parameters
__________
None

Returns
-------
None


Notes
-----


Examples
--------
N.A.
"""

"""Version log
v3              Refactored to make more modular and read optionsconfig.yaml for inventory
v4   2022-0524  Remove outdated environment references
v5   2023-0912  Updates to docs and github packaging
"""

"""TO-DOs
[] reformulate from fabric library to asyncSSH

"""

# Credits:
__version__ = '5'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports
from fabric import Connection
import re
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import sys, os
import threading
import time
import schedule
import argparse
import datetime
from common import getEnv


def get_transceiver_data(device):
    cmdoutput = ''
    try:
        with Connection(f'{device["username"]}@{device["host"]}',connect_kwargs={"password": device["password"]}) as sshsession:
            cmdoutput = sshsession.run('show interfaces transceiver', hide=True).stdout
    except Exception as e:
        print(f'Experienced a failure...\n{e}')
        return('FAILED')
    else:
        regexstr = r'(The Transceiver.*?)((?=The)|$)'
        transceivers = re.findall(regexstr, cmdoutput, re.S)
        return(transceivers)


def process_transceiver_data(device, transceiver_data):
    measurements = ''
    for transceiver in transceiver_data:
        regexstr = r'IDPROM for transceiver (.*?):'
        interface = re.search(regexstr, str(transceiver))
        if 'HundredGig' in interface[1]:
            #Get first 4 lanes
            regexstr = r'([TR]x) power Network (Lane\[0[0123]\])\s+=\s+(-*\d+\.\d+) dBm'
            physlanelist = re.findall(regexstr, str(transceiver), re.S | re.M)
            #print(f'{interface[1]} - {physlanelist}')
            for index, tuple in enumerate(physlanelist):
                measurement = f'opticalpower,device={device["alias"]},instance={interface[1]},lane={tuple[0]}{tuple[1]} dBm={tuple[2]}'
                measurements += measurement + '\n'
        elif 'TenGig' in interface[1]:
            #Get single lane
            regexstr = r'Transceiver ([TR]x).*?= (\S+)\s+dBm'
            physlanelist = re.findall(regexstr, str(transceiver), re.S)
            #print(f'{interface[1]} - {physlanelist}')
            for index, tuple in enumerate(physlanelist):
                dbm = tuple[1]
                dbm = dbm.replace('<', '')
                measurement = f'opticalpower,device={device["alias"]},instance={interface[1]},lane={tuple[0]} dBm={dbm}'
                measurements += measurement + '\n'
        else:
            #No match - bail
            pass
    
    #print(repr(measurements))
    return(measurements)


def send_to_influx(influxenv, measurements):
    influxurl = (f'{influxenv["protocol"]}://'
                 f'{influxenv["host"]}:{influxenv["port"]}'
                 f'/api/v2/write?bucket={influxenv["bucket"]}'
                 f'&org={influxenv["org"]}&precision=s')

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Token ' + influxenv["token"],
    'Content-Type': 'text/plain'
    }

    response = requests.request("POST", influxurl, headers=headers, data=measurements)
    print(f'{response.status_code} - {response.reason} - {response.text}')

    print(f'Finished at: ' + str(time.ctime()))
    print('\nRunning a sleep loop.', end='', flush=True)


def start_all(devices, influxenv, DEBUG):
    # Function that reads all target device parameters from project
    # file and calls get_transceiver_data() for each
    agg_measurements = ''
    for device in devices:
        print(f"\nProcessing Device instance {device['alias']} {device['host']}...")
        transceiver_data = get_transceiver_data(device)
        if transceiver_data == 'FAILED':
            # We experienced a failure, report and continue next poll
            #    maybe extend the polling interval?
            continue

        influx_linedata = process_transceiver_data(device, transceiver_data)
        #print(influx_linedata)
        agg_measurements += influx_linedata
    print(agg_measurements)
    if DEBUG:
        pass
    else:
        send_to_influx(influxenv, agg_measurements)


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    print(f'\nRunning thread {threading.current_thread()}')
    job_thread.start() 


def process_arguments():
    parser = argparse.ArgumentParser(description='Get optical transceiver '
                                     'metrics from a device via SSH; parse '
                                     'and format for InfluxDB')
    parser.add_argument('-d', '--debug', action='store_const',
                        default=False,
                        const=True,
                        dest='debug',
                        help='Enables debug with copious console '
                        'output, but none to InfluxDB')
    parser.add_argument('-p', '--paramfile', 
                        metavar='paramfile',
                        default='optionsconfig.yaml',
                        help=('YAML file with inventory and credentials '
                              '- defaults to "optionsconfig.yaml"'))
    parser.add_argument('-f', '--frequency', 
                        metavar='frequency',
                        type=int,
                        help='Frequency (in seconds) to repeat collection')
    args = parser.parse_args()
    return(args)


#### MAIN
if __name__ == '__main__':
    # Obtain parameters yaml file from user/CLI
    arguments = process_arguments()
    
    DEBUG=arguments.debug
    execstartTime = datetime.datetime.now()
    print(f'Starting script {os.path.basename(__file__)} with '
          f'parameters file "{arguments.paramfile}" at {execstartTime}')
    # Read inventory to build work list

    devicelist = getEnv.getparam("InterfaceDevices")
    envvars = getEnv.getparam("InfluxDB")

    # Run a manual instance, then set up the schedule)
    start_all(devicelist, envvars, DEBUG)
    #schedule.every(30).seconds.do(run_threaded, (start_all, devicelist, envvars))
    schedule.every(120).seconds.do(start_all, devicelist, envvars, DEBUG)
    print('\nRunning a sleep loop.', end='', flush=True)

    try:
        while True:
            print('.', end='', flush=True)
            schedule.run_pending()
            time.sleep(5)
    except KeyboardInterrupt:
        print('\nUser initiated stop - closing down process...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
