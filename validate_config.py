#!/usr/bin/python3.6

import socket
import json
from netmiko import ConnectHandler
import textfsm
from jinja2 import Template

def remove_vty_acls(acl_list: str, netmiko_handler: ConnectHandler):
   '''

   '''
   config_commands = ['line vty 0 15', 'no access-class 5 in']
   handler.send_config_set(config_commands)

def get_mgmt_acl(handler):

   output = handler.send_command("show ip interface vlan 5", use_textfsm=True)
   print(output)


def get_tacacs(handler: ConnectHandler):
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

def process_vty_acls(vty_acls):
    '''
    Convert JSON from the device into a form suitable for reporting
    '''
    print(vty_acls)
    tty_array = []
    acl = set()
    # First, I check if result is uniform across all VTYs
    for vty in vty_acls:
        tty_array.append(int(vty['tty']))
        acl.add(vty['acci'])
    val_min = min(tty_array)
    val_max = max(tty_array)
    if len(acl) == 1:
        d = {}
        d['range_min'] = val_min
        d['range_max'] = val_max
        d['acl'] = list(acl)[0]
        return d
    else:
        return "Non uniform"
def main():
    
    with open('inventory-netmiko.json', 'r') as f:
        devices = json.load(f)
    with open('inventory-new.json', 'r') as file2:
        devices_meta = json.load(file2)
    report_devices = []
    # Go over all devices in our netmiko compatible inventory
    for device in devices:
        # For current device, look up additional metadata 
            print(f"Now working on {device['host']}...")
            if devices_meta[device['host']].get('nos') == "iosxr":
                print("Skipping IOS XR...")
                continue
#            elif devices_meta[device['host']].get('pop_street') == "Ligocka":
            try:
                handler = ConnectHandler(**device)
                # Get configured TACACS servers
                tacacs = get_tacacs(handler)
                # Get configured ACLs on line VTYs
                vty_acls = get_vty_acls(handler, devices_meta[device['host']])
                # 
                current_device = {}
                t = []
                current_device['hostname'] = device['host']
                current_device['vty'] = process_vty_acls(vty_acls)
                for tac in tacacs:
                    t.append(tac['tacacs_server'])
                current_device['tacacs'] = t
                report_devices.append(current_device)
            except Exception as e:
                print(e)    
    # Generate report
    jinja2_template = open("report.html", "r").read()
    template = Template(jinja2_template)
    rendered_template = template.render(devices = report_devices)
    print(rendered_template)

if __name__ == '__main__':

    main()
