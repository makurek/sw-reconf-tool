#!/usr/bin/python3.6

import json

result = {}
with open('inventory.json', 'r') as f:
    devices = json.load(f) 
    for dev in devices:
        hostname = dev['hostname']
        del dev['hostname']
        result[hostname] = dev

with open('inventory-new.json', 'w', encoding='utf-8') as dst_file:
   json.dump(result,dst_file, ensure_ascii=False, indent=4)

