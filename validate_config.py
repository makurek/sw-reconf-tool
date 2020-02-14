#!/usr/bin/python3.6

import socket
import json
from netmiko import ConnectHandler
import textfsm

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

def main():
    
    with open('inventory-netmiko.json', 'r') as f:
        devices = json.load(f)
    with open('inventory-new.json', 'r') as file2:
        devices_meta = json.load(file2)
  
    # Go over all devices in our netmiko compatible inventory
    for device in devices:
        # For current device, look up additional metadata 
        if device['host']  == "kat-lig-asr":
            print(f"Now working on {device['host']}...")
            try:
                handler = ConnectHandler(**device)
#               handler.send_command("terminal length 0")
                # Get configured TACACS servers
                print(get_tacacs(handler))     
                # Get configured ACLs on line VTYs
                print(get_vty_acls(handler, devices_meta[device['host']]))
        
            except Exception as e:
                print(e)    

if __name__ == '__main__':

    main()
