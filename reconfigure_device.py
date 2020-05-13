#!/usr/bin/python3.6

import socket
import json

from netmiko import ConnectHandler
import textfsm
from jinja2 import Template

"""
Main script to reconfigure the device

"""

MGMT_PREFIXES = ["192.168.194.0/24", "192.168.195.0/24", "172.22.0.0/16", "172.22.255.0/24", "172.22.255.0/16", "0.0.0.0/0"]

"""
This script logs in to device, checks for presence of 172.22.255.0/24 route and its NH
and adds another route to 192.168.194.0/24 and 192.168.195.0/24 via the same NH
"""

def get_tacacs(handler: ConnectHandler, device_meta):
    '''
    This function collects configured TACACS+ servers

    '''
    output = handler.send_command("show tacacs", use_textfsm=True)
    return output

def get_vty_acls(handler: ConnectHandler, device_meta):

    if device_meta['model'] == 'ASR-920-24SZ-IM':
        command = "show line vty 0 197"
    elif '3560' or '4948' or '4500' or '4900' in device_meta['model']:
        command = "show line vty 0 15"
    output = handler.send_command(command, use_textfsm=True)
    return output

def process_routes(routes):

    """
    This method receive routes extracted by textfsm
    It looks for prefixes that match MGMT_ROUTES and returns a list
    """
    result = []
    for route in routes:
        prefix = f"{route['network']}/{route['mask']}"
        if prefix in MGMT_PREFIXES:
            r = {}
            r['prefix'] = prefix
            r['nh'] = route['nexthop_ip']
            result.append(r)
            print(f"{prefix} via {route['nexthop_ip']}")

    return result 

def get_routes(handler: ConnectHandler):

    command = "show ip route"
    output = handler.send_command(command, use_textfsm=True)

    return output

def add_routes(handler: ConnectHandler, nh: str):
    
    route_1 = f"ip route 192.168.194.0 255.255.255.0 {nh}"
    route_2 = f"ip route 192.168.195.0 255.255.255.0 {nh}"
    output = handler.send_config_set(route_1)
    output = handler.send_config_set(route_2)

def add_vty_acl(handler: ConnectHandler):

    # First check if there is any existing standard ACL with number 3
    
    command = "show ip access-lists 3"
    output = handler.send_command(command, use_textfsm=True)
    
    # If there isn't, we can proceed

    if not output:
        acl = ['ip access-list standard 3', 'permit host 192.168.194.14', 'permit host 192.168.195.5', 'permit host 192.168.194.23','permit host 192.168.194.25','permit host 192.168.194.27','permit host 192.168.194.5','permit host 192.168.194.7', 'permit host 172.22.255.2', 'permit host 172.22.255.10']
        output = handler.send_config_set(acl)
    
    command = "show ip access-lists 3"
    output = handler.send_command(command, use_textfsm=True)
    print(output)

def reconfigure(device):

    """
    Main routine to reconfigure the box

    """
    handler = ConnectHandler(**device)
    
    # 1. Check existing static routes, determine NH

    #print(f"### Working on {device['host']} ###")
    #print(f"### Checking static routing BEFORE changes ###")
 
    #routes_before = get_routes(handler)
    #mgmt_routes_before = process_routes(routes_before)
    #nh = mgmt_routes_before[0]['nh']

    # 2. Add new routes via NH

    #print(f"### Adding new static routes... ###")
    #add_routes(handler, nh)

    # 3. Verify if routes were addedd successfully

    #print(f"### Checking static routing AFTER changes ###")
    #routes_after = get_routes(handler)
    #mgmt_routes_after = process_routes(routes_after)

    add_vty_acl(handler)

    # 3. Check configured TACACS servers

    # 4. Add new TACACS servers

    # 5. Check if they were added successfully

    # 6. If yes, remove old TACACS servers

    # 7. Check for existence of standard ACL 3

    # 8. If ACL 3 does not exist, add it

    # 9. Check if it was added successfully

    # 10. Check for ACL on VTYs

    # 11. Overwrite VTY ACLs with ACL 3

    # 12. 

def main():
    
    with open('inventory.json', 'r') as f:
        devices = json.load(f)
    with open('inventory-new.json', 'r') as file2:
        devices_meta = json.load(file2)

    # Go over all devices in our netmiko compatible inventory

    for device in devices:
        # We skip IOS XR and IOS XE boxes, as they receive routes via BGP
        try:
            reconfigure(device)
        except Exception as e:
            print(e)    

if __name__ == '__main__':

    main()
