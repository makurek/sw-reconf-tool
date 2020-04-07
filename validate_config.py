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

def get_svi_acl_ip(handler: ConnectHandler, device_meta):

    if device_meta['ip'] == "172.22.36.50":
        command = "show ip interface vlan 2861"
    elif device_meta['ip'] == "172.22.36.18":
        command = "show ip interface vlan 1861"
    else:
        command = "show ip interface vlan 861"
    output = handler.send_command(command, use_textfsm=True)
    return output

def get_ntp_status(handler: ConnectHandler, device_meta):

    command = "show ntp status"
    output = handler.send_command(command, use_textfsm=True)
    return output

def process_vty_acls(vty_acls):
    '''
    Convert JSON from the device into a form suitable for reporting
    '''
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
    # A list that will be passed over to jinja2
    # It holds dictionaries
    report_devices = []
    # Go over all devices in our netmiko compatible inventory
    for device in devices:
        # For current device, look up additional metadata 
            print(f"Now working on {device['host']}...")
            if devices_meta[device['host']].get('nos') == "iosxr":
                print("Skipping IOS XR...")
                continue
 #           elif devices_meta[device['host']].get('pop_street') == "Ligocka":
            try:
                handler = ConnectHandler(**device)
                    # Get configured TACACS servers
                tacacs = get_tacacs(handler)
                    # Get configured ACLs on line VTYs
                vty_acls = get_vty_acls(handler, devices_meta[device['host']])
                    # Get configured ACL and IP address on a SVI
                if (devices_meta[device['host']].get('model') == "ASR-920-24SZ-IM") or (devices_meta[device['host']].get('model') == "CSR1000V"):
                    d = {}
                    d['ipaddr'] = [devices_meta[device['host']].get('ip')]
                    d['inbound_acl'] = "NA"
                    svi_acl = []
                    svi_acl.append(d)
                else:
                    svi_acl = get_svi_acl_ip(handler, devices_meta[device['host']])
                ntp_status = get_ntp_status(handler, devices_meta[device['host']])
                print(ntp_status)
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
    jinja2_template = open("j2_templates/device_audit.html", "r").read()
    template = Template(jinja2_template)
    rendered_template = template.render(devices = report_devices)
    print(rendered_template)

if __name__ == '__main__':

    main()
