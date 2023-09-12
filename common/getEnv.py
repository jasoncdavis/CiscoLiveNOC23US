"""Helper module to obtains environment variables from options YAML file

(getEnv.py)
Helper module that is used by other Python scripts and modules to read
requested environment parameter(s) such as hostname, 
username, password, etc from the environment/project optionsconfig.yaml 
file which defines the secrets, API keys and other project environment 
settings (MySQL, DNA Center, ACI APIC controllers, etc.)
Using this method to document variable and secret project parameters 
prevents us from hard-coding passwords, API keys, etc.

Parameters
__________
param : string
    parameter to extract from the optionsconfig.yaml file

Returns
-------
string | dictionary
    value(s) defined in the optionsconfig.yaml file

Notes
-----
The optionsconfig.yaml file will have sections similar to this template:

InfluxDB:
  host: 10.1.2.10
  alias: influxdb
  protocol: http
  port: 8086
  token: 'AYgSi...=='
  bucket: 12345av...
  bucketname: my_bucket
  org: abcdef12...
  orgname: my_org

The project may have an example-optionsconfig.yaml with template of
the sections used; copy the template to optionsconfig.yaml and modify
to suit your environment - IP addresses, hostnames, usernames, passwords,
etc.  optionsconfig.yaml file should be in the root directory of the
project where the other modules are being executed.

Examples
--------
# As implemented from external python script
from common import getEnv
influxenv = getEnv.getparam('InfluxDB')
print(influxenv)

{"host": "10.1.2.10", "alias": "influxdb", "protocol": "http",
"port": "8086", "token": "AYgSi...==", "bucket": "12345av...", 
"bucketname": "my_bucket", "org": "abcdef12...", "orgname": "my_org"}

"""

"""Version log
v1   2021-0623  Created as normalized function across all
v2   2023-0503  Updated to reduce module and function names
    DevNet Dashboard importing scripts
v3   2023-0725  Update to new naming convention
v4   2023-0906  Updated docs and packaging for github
"""

# Credits:
__version__ = '4'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = ('Cisco Sample Code License, Version 1.1 - '
               'https://developer.cisco.com/site/license/cisco-sample-code-license/')

# Imports


# Functions
def getparam(parameter):
    """Read environmental settings file
    
    Reads a YAML file that defines environmental parameter and settings

    :param parameter: string defining the type of parameter setting(s) 
      to extract [eg. Webex_Key, PrimeInfrastructure, DNACenter, etc.]
    :returns: List of servertype entries defined in YAML config file
    """
    import yaml

    with open("optionsconfig.yaml", "r") as ymlfile:
        try:
            cfg = yaml.safe_load(ymlfile)
        except yaml.YAMLError as e:
            print(e)
    
    return cfg.get(parameter)
