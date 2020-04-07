#!/usr/bin/python3.6

import socket
import json
from netmiko import ConnectHandler
import textfsm
from jinja2 import Template

"""
This script logs in to device, checks for presence of 172.22.255.0/24 route and its NH
and adds another route to 192.168.194.0/24 and 192.168.195.0/24 via the same NH
"""


def get_routes(handler: ConnectHandler):

    command = "show ip route"
    output = handler.send_command(command, use_textfsm=True)
    return output

def add_routes(handler: ConnectHandler, nh: str):
    
    print(nh)
    cmd_1 = f"ip route 192.168.194.0 255.255.255.0 {nh}"
    cmd_2 = f"ip route 192.168.195.0 255.255.255.0 {nh}"
    output = handler.send_config_set(cmd_1)
    output = handler.send_config_set(cmd_2)
    output = handler.save_config()

def main():
    
    with open('inventory-netmiko.json', 'r') as f:
        devices = json.load(f)
    with open('inventory-new.json', 'r') as file2:
        devices_meta = json.load(file2)
    # A list that will be passed over to jinja2
    # It holds dictionaries
    report_devices = []
    # Go over all devices in our netmiko compatible inventory
    for device in devices:

        # For current device, look up additional metadata 
            print(f"Now working on {device['host']}...")

            # We skip IOS XR and IOS XE boxes, as they receive routes via BGP
            if devices_meta[device['host']].get('nos') == "iosxr" or devices_meta[device['host']].get('nos') == "iosxe":
                print("Skipping IOS XE/XR...")
                continue
            try:
                handler = ConnectHandler(**device)
                # Check for old static route to 172.22.255.0/24
                routes = get_routes(handler)
                res = []
                for route in routes:
                    if route['network'] == "172.22.255.0" or route['network'] == '172.22.0.0' or route['network'] == '0.0.0.0' or route['network'] == '192.168.194.0' or route['network'] == '192.168.195.0':
                        i = {}
                        i['network'] = f"{route['network']}/{route['mask']}"
                        i['nh'] = route['nexthop_ip']
                        res.append(i)
#                        print(f"device {device['host']} {i}")
                # Results processing
                current_device = {}; t = []
                current_device['hostname'] = device['host']
                current_device['mgmt_routes'] = res
                print(f"Before changes: {current_device['hostname']} -> {current_device['mgmt_routes']}")
                add_routes(handler, current_device['mgmt_routes'][0]['nh'])
                routes = get_routes(handler)
                for route in routes:
                    if route['network'] == "172.22.255.0" or route['network'] == '172.22.0.0' or route['network'] == '0.0.0.0' or route['network'] == '192.168.194.0' or route['network'] == '192.168.195.0':
                        i = {}
                        i['network'] = f"{route['network']}/{route['mask']}"
                        i['nh'] = route['nexthop_ip']
                        res.append(i)
#                        print(f"device {device['host']} {i}")
                # Results processing
                current = {}; t = []
                current['hostname'] = device['host']
                current['mgmt_routes'] = res
                print(f"After changes: {current['hostname']} -> {current['mgmt_routes']}")
            except Exception as e:
                print(e)    

if __name__ == '__main__':

    main()
