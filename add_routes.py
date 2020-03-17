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


def get_route(handler: ConnectHandler, device_meta):

    command = "show ip route 172.22.255.0"
    output = handler.send_command(command, use_textfsm=True)
    return output

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
                route = get_route(handler)
                
                # Results processing
                current_device = {}; t = []
                current_device['hostname'] = device['host']
                current_device['vty'] = process_vty_acls(vty_acls)
                current_device['vlan861_ip'] = svi_acl[0].get('ipaddr')[0]
                current_device['vlan861_acl'] = svi_acl[0].get('inbound_acl')
                current_device['ntp_status'] = ntp_status[0].get('status')
                current_device['ntp_stratum'] = ntp_status[0].get('stratum')
                current_device['ntp_server'] = ntp_status[0].get('server').strip()
                for tac in tacacs:
                    t.append(tac['tacacs_server'])
                current_device['tacacs'] = t
                    # Append assembled dict to final list
                report_devices.append(current_device)
            except Exception as e:
                print(e)    
    # Generate report
    jinja2_template = open("device_audit.html", "r").read()
    template = Template(jinja2_template)
    rendered_template = template.render(devices = report_devices)
    print(rendered_template)

if __name__ == '__main__':

    main()
