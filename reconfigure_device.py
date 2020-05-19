#!/usr/bin/python3.6

import socket
import json
import re
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
def syslog_reconfigure(handler: ConnectHandler):
    
    DESIRED_STATE = ['192.168.194.9', '192.168.195.1']

    print("Reconfiguring syslog...")

    command = "show run | i logging"
    output = handler.send_command(command)
    match1 = re.findall(r'logging ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', output)
    match2 = re.findall(r'logging host ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', output) 
    match = match1 + match2
    deletion = []
    done = False
    if match:
        print(f"Found syslog servers {match}")
        for s in match:
            if s not in DESIRED_STATE:
                deletion.append(s)
            else:
                done = True
        if len(deletion) > 0:
            syslog_del_server(deletion, handler)
    else:
        print(f"No existing syslog servers found")

    if not done:
        syslog_add_server(handler)
        
        if syslog_verify(DESIRED_STATE, handler):
            print("Syslog reconfigured OK")
    else:
        print("There was no need to add any syslog servers")

def syslog_add_server(handler: ConnectHandler):

    print("Adding syslog servers...")
    commands = ['logging 192.168.194.9', 'logging 192.168.195.1']
    output = handler.send_config_set(commands)

def syslog_del_server(servers, handler: ConnectHandler):
    
    print(f"Deleting existing syslog servers... {servers}")

    commands = []
    for server in servers:
        commands.append(f"no logging {server}")
    output = handler.send_config_set(commands)


def syslog_verify(desired_state, handler: ConnectHandler):

    command = "show run | i logging"
    output = handler.send_command(command)
    match = re.findall(r'logging ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', output)
    if set(match) == set(desired_state):
        return True
    else:
        return False



def ntp_reconfigure(handler: ConnectHandler):

    DESIRED_STATE = ['192.168.194.13']
    
    print("Reconfiguring NTP...")
    
    # First, let's get current NTP configuration
    command = "show run | i ntp server"
    output = handler.send_command(command)
    match = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', output)
    deletion = []
    done = False
    if match:
        print(f"Found NTP servers {match}")
        for s in match:
            if s not in DESIRED_STATE:
                deletion.append(s)
            else:
                done = True
        if len(deletion) > 0:
            ntp_del_server(deletion, handler)
    else:
        print(f"No existing NTP servers found")

    if not done:
        ntp_add_server(handler)

        if ntp_verify(handler):
            print("NTP reconfigured OK")
        else:
            print("Failed to reconfigure NTP")
    else:
        print("There was no need to add any servers")

def ntp_add_server(handler: ConnectHandler):

    commands = ['ntp server 192.168.194.13']
    output = handler.send_config_set(commands)

def ntp_del_server(servers, handler: ConnectHandler):

    print(f"Deleting existing servers...{servers}")
    commands = []
    for server in servers:
        commands.append(f"no ntp server {server}")
    output = handler.send_config_set(commands)

def ntp_verify(handler: ConnectHandler):

    command = "show run | i ntp server"
    output = handler.send_command(command)
    match = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', output)
    if (len(match) == 1) and (match[0] == '192.168.194.13'):
        return True
    else:
        return False


def tacacs_reconfigure(handler: ConnectHandler):
    '''
    This function collects configured TACACS+ servers

    '''
    print("Reconfiguring TACACS+ servers...")

    DESIRED_OUTPUT = ['192.168.194.11', '192.168.195.3']
    commands = []
    output = handler.send_command("show tacacs", use_textfsm=True)
    print("### BEFORE RECONFIG ###")
    print(output)
    for tac in output:
        command = f"no tacacs-server host {tac['tacacs_server']}"
        commands.append(command)
    commands.append("tacacs-server host 192.168.194.11")
    commands.append("tacacs-server host 192.168.195.3")
    commands.append("tacacs-server key 0 12TacplusKEY!@")
    print(commands)
    output = handler.send_config_set(commands)
    print("### AFTER RECONFIG ###")
    output = handler.send_command("show tacacs", use_textfsm=True)
    print(output)
    final_list = []
    for tac in output:
        final_list.append(tac['tacacs_server'])

    if final_list == DESIRED_OUTPUT:
        print("ALL GOOD!")

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

def mgmt_svi_reconfigure(handler: ConnectHandler):

    # First check if there is any existing extended ACL with number 101, if so, do nothing
    if not mgmt_svi_check_acl_exist(handler):

        # Now it's safe to deploy ACL 101
        mgmt_svi_deploy_acl(handler)

        # Verify if it has been deployed successfully
        if mgmt_svi_verify_acl(handler):
            mgmt_svi_modify(handler)
    else:
        print("ACL 101 exists, aborting...")
            
def mgmt_svi_modify(handler: ConnectHandler):
    
    print("Modifying management SVI configuration...")
    command = "show ip interface Vlan861"
    try:
        output = handler.send_command(command, use_textfsm=True)
        old_inbound_acl = output[0]['inbound_acl']
        print(f"Old inbound ACL is {old_inbound_acl}")
    except:
        print("No management interface found")
        return False
    
    commands = ['interface vlan 861', 'ip access-group 101 in']
    output = handler.send_config_set(commands)

    output = handler.send_command(command, use_textfsm=True)
    new_inbound_acl = output[0]['inbound_acl']
    print(f"New inbound ACL is {new_inbound_acl}")

def mgmt_svi_deploy_acl(handler: ConnectHandler):
    
    print("Deploying ACL 101...")

    acl = ['ip access-list extended 101', 'permit tcp host 192.168.194.13 any eq 22', 'permit tcp host 192.168.195.5 any eq 22', 'permit tcp host 192.168.194.23 any eq 22', 'permit tcp host 192.168.194.25 any eq 22', 'permit tcp host 192.168.194.27 any eq 22', 'permit tcp host 192.168.194.5 any eq 22', 'permit tcp host 192.168.194.7 any eq 22', 'permit tcp host 172.22.255.2 any eq 22', 'permit tcp host 172.22.255.10 any eq 22', 'permit tcp host 172.22.255.2 any eq 23', 'permit tcp host 172.22.255.10 any eq 23', 'permit tcp host 192.168.194.13 any eq 23', 'permit tcp host 192.168.195.5 any eq 23', 'permit tcp host 192.168.194.23 any eq 23', 'permit tcp host 192.168.194.25 any eq 23', 'permit udp host 172.22.255.10 any eq 161', 'permit tcp host 192.168.194.11 eq tacacs any', 'permit tcp host 192.168.195.3 eq tacacs any', 'permit icmp host 192.168.194.13 any', 'permit icmp host 192.168.195.5 any', 'permit icmp host 192.168.194.23 any', 'permit icmp host 192.168.194.25 any', 'permit icmp host 192.168.194.27 any', 'permit icmp host 172.22.255.10 any', 'permit icmp host 172.22.255.2 any', 'permit udp host 172.22.255.3 eq ntp any', 'permit udp host 192.168.194.13 eq ntp any', 'permit udp host 192.168.194.13 eq tftp any', 'permit udp host 192.168.195.5 eq tftp any', 'permit udp host 172.22.255.3 any eq snmp']
    output = handler.send_config_set(acl)

def mgmt_svi_check_acl_exist(handler: ConnectHandler):
    
    print("Checking if ACL 101 exists...")

    command = "show ip access-lists 101"
    output = handler.send_command(command, use_textfsm=True)

    if not output:
        return False
    else:
        return True


def mgmt_svi_verify_acl(handler: ConnectHandler):
  
    acl_template = [{'name': '101', 'sn': '10', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.13', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '20', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.195.5', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '30', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.23', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '40', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.25', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '50', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.27', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '60', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.5', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '70', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.7', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '80', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 172.22.255.2', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '90', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 172.22.255.10', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq 22'}, {'name': '101', 'sn': '100', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 172.22.255.2', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '110', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 172.22.255.10', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '120', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.13', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '130', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.195.5', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '140', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.23', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '150', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.25', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq telnet'}, {'name': '101', 'sn': '160', 'action': 'permit', 'protocol': 'udp', 'source': 'host 172.22.255.10', 'port': '', 'range': '', 'destination': 'any', 'modifier': 'eq snmp'}, {'name': '101', 'sn': '170', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.194.11', 'port': 'eq', 'range': 'tacacs', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '180', 'action': 'permit', 'protocol': 'tcp', 'source': 'host 192.168.195.3', 'port': 'eq', 'range': 'tacacs', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '190', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 192.168.194.13', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '200', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 192.168.195.5', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '210', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 192.168.194.23', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '220', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 192.168.194.25', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '230', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 192.168.194.27', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '240', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 172.22.255.10', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '250', 'action': 'permit', 'protocol': 'icmp', 'source': 'host 172.22.255.2', 'port': '', 'range': '', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '260', 'action': 'permit', 'protocol': 'udp', 'source': 'host 172.22.255.3', 'port': 'eq', 'range': 'ntp', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '270', 'action': 'permit', 'protocol': 'udp', 'source': 'host 192.168.194.13', 'port': 'eq', 'range': 'ntp', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '280', 'action': 'permit', 'protocol': 'udp', 'source': 'host 192.168.194.13', 'port': 'eq', 'range': 'tftp', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '290', 'action': 'permit', 'protocol': 'udp', 'source': 'host 192.168.195.5', 'port': 'eq', 'range': 'tftp', 'destination': 'any', 'modifier': ''}, {'name': '101', 'sn': '300', 'action': 'permit', 'protocol': 'udp', 'source': 'host 172.22.255.3', 'port': '', 'range':'', 'destination':'any', 'modifier':'eq snmp'}] 
    
    print("Verifying ACL 101...")
    command = "show ip access-lists 101"
    output = handler.send_command(command, use_textfsm=True)
    if output == acl_template:
        print("ACL verified ok")
        return True
    else:
        print("ACL verify failed")
        return False
    

def routing_reconfigure(handler: ConnectHandler):

    # Check existing static routes, determine NH

    DESIRED_STATE = ['192.168.194.0/24', '192.168.195.0/24']

    print(f"Checking static routing BEFORE changes...")
 
    routes_before = get_routes(handler)

    # Maybe dangerous assumption is that all routes will lead through the same interface?
    
    mgmt_routes_before = process_routes(routes_before)
    pfx_before  = []
    for d in mgmt_routes_before:
        if d['prefix'] in DESIRED_STATE:
            pfx_before.append(d['prefix'])
    if(len(mgmt_routes_before)) > 0:

        if DESIRED_STATE == pfx_before:
            print("Routes 192.168.194.0/24 and 192.168.195.0/24 already present, doing nothing")
            return

        # So I take first interface
        nh = mgmt_routes_before[0]['nh']

        # Add new routes via NH
    
        print(f"Adding new static routes...")
        add_routes(handler, nh)

        # Verify if routes were addedd successfully

        print(f"Checking static routing AFTER changes")
        routes_after = get_routes(handler)
        mgmt_routes_after = process_routes(routes_after)
    else:
        print("Someting went wrong, no mgmt routes found, I couldn't derive NH... Config not changed")


def reconfigure(device):

    """
    Main routine to reconfigure the box

    """
    handler = ConnectHandler(**device)
    
    print(f"### Working on {device['host']} ###")
    
    routing_reconfigure(handler)
    mgmt_svi_reconfigure(handler)
    tacacs_reconfigure(handler)
    syslog_reconfigure(handler)
    ntp_reconfigure(handler)
    handler.save_config()
    # 1. Reconfiguring management SVI (allow traffic from new systems, TACACS etc)

    #add_vty_acl(handler)

    #reconfigure_tacacs(handler)

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
    
    with open('inventory-netmiko.json', 'r') as f:
        devices = json.load(f)
    with open('inventory.json', 'r') as file2:
        devices_meta = json.load(file2)

    # Go over all devices in our netmiko compatible inventory

    for device in devices:
        # We skip IOS XR and IOS XE boxes, as they receive routes via BGP
        try:
            reconfigure(device)
            temp = "x"
            while temp != "y" and temp != "n":
                temp = input("Do you want to proceed with the next device? [y/n]")
            if temp == "y":
                continue
            else:
                break
            
        except Exception as e:
            print(e)    

if __name__ == '__main__':

    main()
