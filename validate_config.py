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


def get_tacacs(handler):
   output = handler.send_command("show tacacs", use_textfsm=True)
   print(output)

def get_vty_acl(target_host, username, password, conn_method, range_start, range_end):
   try:
      conn = ConnectHandler(device_type = 'cisco_ios_telnet', ip = target_host, username = username, password = password)
      conn.enable()
      output = conn.send_command("show line vty 0 15", use_textfsm=True)
      print(output)
      remove_vty_acls(output, conn)
      get_mgmt_acl(conn)
      get_tacacs(conn)
   except Exception as e:
      print(e)
      return False


def main():
    
    with open('devices-new-2.json', 'r') as f:
        devices = json.load(f)
    with open('devices.json', 'r') as file2:
        extended_devices = json.load(file2)
  
    # Go over all devices in our netmiko compatible inventory
    for device in devices:
        # For current device, look up additional metadata 
        for ed in extended_devices:
            if ed['hostname'] == device['host']:
                if ed['pop_street'] == 'Ligocka':
                   print(f"Now working on {device['host']}...")
                   try:
                       handler = ConnectHandler(**device)
                       handler.enable()
                       output = handler.send_command("show version")
                       print(output)
        
                   except Exception as e:
                       print(e)
        

if __name__ == '__main__':

    main()
