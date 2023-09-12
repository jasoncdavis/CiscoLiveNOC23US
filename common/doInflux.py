"""Helper module for Influx database functions

(doInflux.py)
Receives Influx server parameters, query to execute or measurements to
insert into InfluxDB

Parameters
__________
influxenv : dictionary
    InfluxDB server parameters (eg. protocol, host, port, bucket, org,
    token)
measurements : string
    for write_to_influx() - Influx line protocol payload reflecting
    measurement, key tags, field values and optional timestamp
query : string
    for query_influx() - InfluxDB flux query statement extracting data

Returns
-------
(int, string, string)
    for write_to_influx() - results of write action as a tuple of
    status code as integer, reason as string, text as string
list of dictionaries
    for query_influx() - results of InflxuDB flux query

Examples
--------
influxenv = {
    "protocol": "http",
    "host": "influxdb.local",
    "port": 8086,
    "bucket": "my_bucket",
    "org": "my_org",
    "token": "AYgSi...."
}

measurements = '''my_measurement,mytag=testtag cpu_percent=55'''
status_code, return_reason, return_text = write_to_influx(influxenv,
    measurements)

example_flux = '''from(bucket: "my_bucket")
        |> range(start: -5m)
        |> filter(fn: (r) => r["_measurement"] == "my_measurement")
        |> filter(fn: (r) => r["_field"] == "cpu_percent")
        |> yield(name: "last")
'''
results = queryinflux(influxenv, example_flux)
"""

"""Version log
v1   2023-0826  Initial dev based IMPACT24 NOC
"""

# Credits:
__version__ = '1'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ("Cisco Sample Code License, Version 1.1 - " \
    "https://developer.cisco.com/site/license/cisco-sample-code-license/")

# Imports
import requests
from influxdb_client import InfluxDBClient 


# Functions
def write_to_influx(influxenv, measurements):
    influxurl = (f'{influxenv["protocol"]}://'
                 f'{influxenv["host"]}:{influxenv["port"]}'
                 f'/api/v2/write?bucket={influxenv["bucket"]}'
                 f'&org={influxenv["org"]}&precision=s')

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Token ' + influxenv["token"],
    'Content-Type': 'text/plain'
    }

    response = requests.request("POST", influxurl, headers=headers, 
                                data=measurements)
    return (response.status_code, response.reason, response.text)


def query_influx(influxenv, query):
    # query Influx DB using Flux query language
    url = f'{influxenv["protocol"]}://{influxenv["host"]}:{influxenv["port"]}'
    #print(url)
    #print(query)
    client = InfluxDBClient(url=url,
                            token=influxenv["token"],
                            org=influxenv["org"])

    query_api = client.query_api()

    ## using Table structure
    result = query_api.query(org=influxenv["orgname"], query=query)

    results = []
    for table in result:
        for record in table.records:
            results.append((record.get_field(), record.get_value()))
    #print(results)

    return results