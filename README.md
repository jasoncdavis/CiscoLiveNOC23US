<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]


<h3 align="center">CiscoLive NOC 2023</h3>

  <p align="center">
    This repo contains Python scripts, HTML/Grafana templates and SQL DDL for CiscoLive NOC collectors and dashboards.
    <br />
    <a href="https://github.com/jasoncdavis/CiscoLiveNOC23US"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/jasoncdavis/CiscoLiveNOC23US">View Demo</a>
    ·
    <a href="https://github.com/jasoncdavis/CiscoLiveNOC23US/issues">Report Bug</a>
    ·
    <a href="https://github.com/jasoncdavis/CiscoLiveNOC23US/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
      <ul>
          <li><a href="#availability">Availability Monitoring</a></li>
          <li><a href="#wan">WAN Monitoring</a></li>
          <li><a href="#lan">LAN Monitoring</a></li>
          <li><a href="#wireless">Wireless Monitoring</a></li>
        </ul>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

This project is a collection of Python script, database DDL files, Grafana dashboard templates, etc. that are used in the CiscoLive Network Operations Center (NOC). These programs are inventory and metrics collectors and dashboard creators. The technologies span wireless (Catalyst and Meraki), WAN (ASR1009-X), LAN (Cat3560-CG, 7K, 9K and Nexus 9K), and basic availability monitoring.

The following dashboards are part of this project:

![dashboards](https://github.com/jasoncdavis/TEMP-CiscoLiveNOC23US/assets/8027948/04d49fd2-65d9-44f1-a839-2b596df662f9)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

* [![Python][python-shield]][python-url]
* [![HTML][html-shield]][html-url]
* [![CSS][css-shield]][css-url]
* [![MySQL][mysql-shield]][mysql-url]
* [![Influx][influxdb-shield]][influxdb-url]
* [![Grafana][grafana-shield]][grafana-url]


<p align="right">(<a href="#readme-top">back to top</a>)</p>

This project is being released in phases, so check back often to see what additional components have been released.  Most recently the separate 'SSH2Influx' project was released on [Cisco DevNet Code Exchange](https://developer.cisco.com/codeexchange/github/repo/jasoncdavis/SSH2Influx/) and [Github](https://github.com/jasoncdavis/SSH2Influx).
Additionally the [Devnet Dashboards - Converged Availability Monitor](https://github.com/jasoncdavis/devnetdashboards-convergedavailabilitymonitor) was updated and released end of June 2023.


<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these example steps.

### Prerequisites

Generally a Python 3.10 environment is needed.  It is helpful to use a virtual environment (venv) for separation from your main environment.  Ubuntu 22.04 LTS (Jammy Jellyfish) has been used for a few major events and is Long-Term Support.

Installing Python 3.10 is outside the scope of this repo, but this is a good reference:

[Ubuntu 22.04 LTS Install from Ubuntu.com](https://ubuntu.com/server/docs/installation)

Our installs were 4 vCPU with 16 GB vRAM and 100 GB vDisk.


### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/jasoncdavis/CiscoLiveNOC23US.git
   ```
2. Install project dependencies from the Python Package Index (PyPi) repo
   ```sh
   cd CiscoLiveNOC23US
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create an environment-specific optionalconfig.yaml file and replace the CHANGEME parameters with your IP addresses, hostnames, usernames, passwords, etc.
   ```sh
   cp example-optionsconfig.yaml optionsconfig.yaml
   vi optionsconfig.yaml
   ```
4. Create a Telegraf, InfluxDB and Grafana (TIG) server to receive streaming telemetry, injected metrics from the Python scripts of this project, and display the dashboards.  Ensure the TIG server specs (IP Address, hostname, API keys, etc) are properly defined in the optionsconfig.yaml file.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

There are SEVERAL collectors and scripts that are necessary to run, depending on your needs.

### Availability Monitoring

The Availability Monitoring tasks are handled through the DevNet Dashboard - Converged Availability Monitoring ([DD-CAM](https://github.com/jasoncdavis/DD-CAM)) project.  This is under a separate repo.
https://github.com/jasoncdavis/DD-CAM

Follow the guidance in that repo to install and configure.

### WAN Monitoring

WAN Monitoring is a mix of streaming telemetry, polled NETCONF RPCs and CLI information gathering (with SSH2Influx).  The following configuration template is used for our IOS-XR based WAN edge routers (Cisco ASR1009-Xs).

```
telemetry ietf subscription 101
 encoding encode-kvgpb
 filter xpath /process-cpu-ios-xe-oper:cpu-usage/cpu-utilization
 source-address CHANGEME_SOURCE_IP
 stream yang-push
 update-policy periodic 2000
 receiver ip address CHANGEME_TELEGRAF_IP 57500 protocol grpc-tcp
telemetry ietf subscription 102
 encoding encode-kvgpb
 filter xpath /memory-ios-xe-oper:memory-statistics/memory-statistic
 source-address CHANGEME_SOURCE_IP
 stream yang-push
 update-policy periodic 2000
 receiver ip address CHANGEME_TELEGRAF_IP 57500 protocol grpc-tcp
telemetry ietf subscription 104
 encoding encode-kvgpb
 filter xpath /ospf-ios-xe-oper:ospf-oper-data/ospfv2-instance/ospfv2-area/ospfv2-interface/ospfv2-neighbor
 source-address CHANGEME_SOURCE_IP
 stream yang-push
 update-policy periodic 60000
 receiver ip address CHANGEME_TELEGRAF_IP 57500 protocol grpc-tcp
telemetry ietf subscription 105
 encoding encode-kvgpb
 filter xpath /bgp-ios-xe-oper:bgp-state-data/address-families/address-family/bgp-neighbor-summaries/bgp-neighbor-summary
 source-address CHANGEME_SOURCE_IP
 stream yang-push
 update-policy periodic 60000
 receiver ip address CHANGEME_TELEGRAF_IP 57500 protocol grpc-tcp
netconf-yang
netconf-yang ssh ipv4 access-list name HTTP_FILTER
netconf-yang ssh ipv6 access-list name IPV6_FILTER
restconf
restconf ipv4 access-list name HTTP_FILTER
restconf ipv6 access-list name IPV6_FILTER
```

The Telegraf server needs the telegraf.conf file update to include:
```
[[inputs.cisco_telemetry_mdt]]
 transport = "grpc"
 service_address = ":57000"
```

and an output section:
```
[[outputs.influxdb]]
  database = "telegraf"
  urls = [ "http://127.0.0.1:8086" ]
  username = "telegraf"
  password = "CHANGEME"
```

The InfluxDB server (we put them together into a combined TIG server) must be configured to receive the Telegraf gRPC telemetry into a new database.  Access the 'influx' CLI utility and issue the commands:
```
create database telegraf
create user telegraf with password 'CHANGEME'
```

There are various Grafana dashboard JSON definition files in the [dashboards](./dashboards) directory. Specifically for WAN, we'll want to import the following:
* [Internet Volume](./dashboards/Internet%20Stats.json)
* [Internet Rates](./dashboards/Internet%20Rates.json)
* [Topo-CoreToWAN-PPS](./dashboards/Topo-CoreToWAN-PPS.json) - requires heavy modification
* [Topo-CoreToWAN](./dashboards/Topo-CoreToWAN.json) - requires heavy modification
* [WAN - IPv6 Stats](./dashboards/WAN%20-%20IPv6%20Stats.json)
* [WAN Ops CURRENT](./dashboards/WAN%20Ops%20CURRENT.json)
* [WAN Router - CPU & Mem](./dashboards/WAN%20Router%20-%20CPU%20&%20Mem.json)
* [WAN Router - Interface Rates](./dashboards/WAN%20Router%20-%20Interface%20Rates.json)
* [WAN Router - Optical Power](./dashboards/Optical%20Power.json)

The following WAN scripts should be run:
```sh
cd CiscoLiveNOC23US
source .venv/bin/activate
tmux new -s WAN-interface
python -m WAN.NETCONFrpc-getInterfaceData
[CTRL-b + d]  # detaches from tmux
tmux new -s WAN-transceiver
python -m WAN.SSHget-transceiverpower.py
[CTRL-b + d]  # detaches from tmux
```

### LAN Monitoring

LAN Switching encompasses Core, Distribution, and Access with DC Nexus switching.

The following WAN scripts should be run:
```sh
cd CiscoLiveNOC23US
source .venv/bin/activate
tmux new -s LAN-NETCONFrpc-getSwitchHealth
python -m LAN.NETCONFrpc-getSwitchHealth
[CTRL-b + d]  # detaches from tmux
tmux new -s LAN-WIFI-DIST-every5min
python SSH2Influx.py -p LAN/WIFI-DIST-every5min.yml -t 1
[CTRL-b + d]  # detaches from tmux
tmux new -s LAN-DIST-every5min
python SSH2Influx.py -p LAN/DIST-every5min.yml
[CTRL-b + d]  # detaches from tmux
```


### Wireless Monitoring

Wireless monitoring includes NETCONF and SSH collectors against WLCs using InfluxDB and Grafana dashboards, along with custom generated dashboards.

The following WAN scripts should be run:
```sh
cd CiscoLiveNOC23US
source .venv/bin/activate
tmux new -s WIFI-PutWirelessDataIntoDB
python -m wireless.PutWirelessDataIntoDB
[CTRL-b + d]  # detaches from tmux
tmux new -s WIFI-SSH2Influx-WLC-rmi-every1min
python SSH2Influx.py -p wireless/WLC-rmi-every1min.yml -f 60
[CTRL-b + d]  # detaches from tmux
tmux new -s WIFI-SSH2Influx-WLC-every2min
python SSH2Influx.py -p wireless/WLC-every2min.yml -f 120
[CTRL-b + d]  # detaches from tmux
tmux new -s WIFI-createWirelessClientDashboards
python -m wireless.createWirelessClientDashboards
[CTRL-b + d]  # detaches from tmux
tmux new -s WIFI-createWirelessChannelUtilDashboards
python -m wireless.createWirelessChannelUtilDashboards
[CTRL-b + d]  # detaches from tmux
```


_For more examples, please refer to the [Documentation](https://example.com)_

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Provide Docker container option
- [ ] Feature 2
- [ ] Feature 3
    - [ ] Nested Feature

See the [open issues](https://github.com/jasoncdavis/CiscoLiveNOC23US/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the Cisco Sample Code License. See [LICENSE.md](./LICENSE.md) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Jason Davis - [@SNMPguy](https://twitter.com/SNMPguy) - jadavis@cisco.com

Project Link: [https://github.com/jasoncdavis/CiscoLiveNOC23US](https://github.com/jasoncdavis/CiscoLiveNOC23US)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Andy Phillips]()
* [Erwin Dominguez]()
* [Dave Benham]()

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/jasoncdavis/CiscoLiveNOC23US.svg?style=for-the-badge
[contributors-url]: https://github.com/jasoncdavis/CiscoLiveNOC23US/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jasoncdavis/CiscoLiveNOC23US.svg?style=for-the-badge
[forks-url]: https://github.com/jasoncdavis/CiscoLiveNOC23US/network/members
[stars-shield]: https://img.shields.io/github/stars/jasoncdavis/CiscoLiveNOC23US.svg?style=for-the-badge
[stars-url]: https://github.com/jasoncdavis/CiscoLiveNOC23US/stargazers
[issues-shield]: https://img.shields.io/github/issues/jasoncdavis/CiscoLiveNOC23US.svg?style=for-the-badge
[issues-url]: https://github.com/jasoncdavis/CiscoLiveNOC23US/issues
[license-shield]: https://img.shields.io/github/license/jasoncdavis/CiscoLiveNOC23US.svg?style=for-the-badge
[license-url]: https://developer.cisco.com/site/license/cisco-sample-code-license
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/jasoncdavis
[product-screenshot]: images/screenshot.jpg

[python-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]: https://python.org/
[html-shield]: https://img.shields.io/badge/HTML-239120?style=for-the-badge&logo=html5&logoColor=white
[html-url]: https://html.spec.whatwg.org/
[css-shield]: https://img.shields.io/badge/CSS-239120?&style=for-the-badge&logo=css3&logoColor=white
[css-url]: https://www.w3.org/TR/CSS/#css
[mysql-shield]: https://img.shields.io/badge/MySQL-00000F?style=for-the-badge&logo=mysql&logoColor=white
[mysql-url]: https://www.mysql.com/products/enterprise/database/
[influxdb-shield]: https://img.shields.io/badge/InfluxDB-22ADF6?style=for-the-badge&logo=InfluxDB&logoColor=white
[influxdb-url]: https://www.influxdata.com/products/influxdb-overview/
[grafana-shield]: https://img.shields.io/badge/grafana-%23F46800.svg?style=for-the-badge&logo=grafana&logoColor=white
[grafana-url]: https://grafana.com/oss/grafana/
