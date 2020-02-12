#!/usr/bin/python3.6

import json

a = []
with open('devices.json', 'r') as f:
    devices = json.load(f) 
    for dev in devices:
        dd = {}
        if dev['nos'] == 'ios' and dev['ssh_support'] == "True":
            dd['device_type'] = 'cisco_ios'
        elif dev['nos'] == 'ios' and dev['ssh_support'] == "False" and dev['telnet_support'] == "True":
            dd['device_type'] = 'cisco_ios_telnet'
        elif dev['nos'] == 'iosxe' and dev['ssh_support'] == "True":
            dd['device_type'] = 'cisco_xe'
        elif dev['nos'] == 'iosxr' and dev['ssh_support'] == "True":
            dd['device_type'] = 'cisco_xr'
        dd['host'] = dev['hostname']
        dd['username'] = dev['username']
        dd['password'] = dev['password']
        a.append(dd)

with open('devices-new-2.json', 'w', encoding='utf-8') as dst_file:
   json.dump(a,dst_file, ensure_ascii=False, indent=4)

