#!/usr/bin/python3.6

import socket
import json
from netmiko import ConnectHandler
import textfsm

devices = {}

def is_port_open(ip: str, port: str) -> bool:

   '''
   Checks if given port is open, in case the device is filtering traffic,
   wait 2 seconds

   Returns:

   True, if device is reachable and port is open
   False, if device is unreachable or port is closed
   '''
   try:
     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     sock.settimeout(2)
     conn = sock.connect((ip, port))
     return True
   except:
     return False


def remove_vty_acls(acl_list, handler):
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



with open('cisco.txt', 'r') as file:
   for index,line in enumerate(file):
      device = {}
      columns = line.split()
      print(f"Current loop # {index}, device is {columns[2].replace('*', '')}")
      device['nos'] = columns[4]
      device['hostname'] = columns[2].replace('*', '')
      device['nos_ver'] = columns[1]
      device['model'] = columns[3]
      device['username'] = 'automat'
      device['password'] = 'cVxD56hR!'
      try:
         device['ip'] = socket.gethostbyname(device['hostname'])
      except:
         continue
      print("Starting telnet check")
      # Check if telnet supported
      if is_port_open(device['ip'], 23):
         device['telnet_support'] = "True"
      else:
         device['telnet_support'] = "False"
      print("Starting ssh check")
      if check_port(device['ip'], 22):
         device['ssh_support'] = "True"
      else:
         device['ssh_support'] = "False"

      if columns[0] not in devices.keys():
         a = []
         a.append(device)
         devices[columns[0]] = a
      else:
         devices[columns[0]].append(device)

total_telnet_only = 0
total_telnet_only_list = []
total_ssh_only = 0
total_ssh_only_list = []
total_telnet_ssh = 0
total_telnet_ssh_list = []

for k,v in devices.items():
   print(f"There are {len(v)} {k} devices")
   for d in v:
      if d['telnet_support'] == "True" and d['ssh_support'] == "False":
         total_telnet_only += 1
         total_telnet_only_list.append(d['hostname'])
      elif d['telnet_support'] == "False" and d['ssh_support'] == "True":
         total_ssh_only += 1
         total_ssh_only_list.append(d['hostname'])
      elif d['telnet_support'] == "True" and d['ssh_support'] == "True":
         total_telnet_ssh += 1
         total_telnet_ssh_list.append(d['hostname'])

print(f"Total devices with SSH support only: {total_ssh_only}")
for dev in total_ssh_only_list:
   print(dev)

print(f"Total devices with telnet support only: {total_telnet_only}")
for dev in total_telnet_only_list:
   print(dev)

print(f"Total devices with telnet/SSH support: {total_telnet_ssh}")
for dev in total_telnet_ssh_list:
   print(dev)

with open('devices.json', 'w', encoding='utf-8') as dst_file:
   json.dump(devices,dst_file, ensure_ascii=False, indent=4)

# Now I need to now which ACLs should I query for and what should I remove

acl_vty_list = get_vty_acl('10.98.23.4', 'automat', 'test', 'telnet', '0', '16')



