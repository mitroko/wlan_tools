#!/usr/bin/env python
#
# Usage example: sudo ~/iwscan.py wlan1

import subprocess
import re
import sys

class line_matcher:
    def __init__(self, regexp, handler):
        self.regexp  = re.compile(regexp)
        self.handler = handler

def handle_new_network(line, result, networks):
    global wpa_block
    global wps_block
    wpa_block = False
    wps_block = False
    networks.append({})
    networks[-1]['bssid'] = result.group(1)

def handle_param(line, result, networks):
    global wpa_block
    global wps_block
    wpa_block = False
    wps_block = False
    networks[-1][result.group(1)] = result.group(2)

def handle_wpx_block(line, result, networks):
    global wpa_block
    global wps_block
    global offset
    wpa_block = False
    wps_block = False
    offset    = len(result.group(1))
    if result.group(2) == 'WPA':
        wpa_block = True
        networks[-1]['wpa'] = {}
        networks[-1]['wpa']['version'] = result.group(3)
    if result.group(2) == 'WPS':
        wps_block = True
        networks[-1]['wps'] = {}
        networks[-1]['wps']['version'] = result.group(3)

def handle_wpx_param(line, result, networks):
    global offset
    global wpa_block
    global wps_block
    if len(result.group(1)) > offset:
        if wpa_block:
            networks[-1]['wpa'][result.group(2)] = result.group(3)
        if wps_block:
            networks[-1]['wps'][result.group(2)] = result.group(3)
    else:
        wpa_block = False
        wps_block = False

def get_wpx_param(network, x, param):
    if param in network[x]:
        return network[x][param]
    else:
        return 'N/A'


if __name__ == '__main__':
    proc = subprocess.Popen(['/usr/sbin/iw', sys.argv[1], 'scan'], stdout=subprocess.PIPE)
    stdout, stderr =  proc.communicate()

    lines = stdout.split('\n')

    networks = []
    matchers = []
    offset = 0
    wpa_block = False
    wps_block = False

    matchers.append(line_matcher(r'^BSS (([a-zA-Z0-9]{2}:){5}[a-zA-Z0-9]{2}).*', handle_new_network))
    matchers.append(line_matcher(r'\s+(SSID): (.*)', handle_param))
    matchers.append(line_matcher(r'\s+(signal): -(\d+)\.\d+ dBm', handle_param))
    matchers.append(line_matcher(r'\s+DS Parameter set: (channel) (\d+)', handle_param))
    matchers.append(line_matcher(r'(\s+)(WP[AS]):\s+\* Version: (.*)', handle_wpx_block))
    matchers.append(line_matcher(r'(\s+)\* ([^\:]+)\: (.*)', handle_wpx_param))

    for line in lines:
        for m in matchers:
            result = m.regexp.match(line)
            if result:
                m.handler(line, result, networks)
                break

    for n in networks:
        if 'wps' in n:

            wps_configured = False
            if get_wpx_param(n, 'wps', 'Wi-Fi Protected Setup State') == '2 (Configured)':
                wps_configured = True
            wps_lock_state = 'No'
            if get_wpx_param(n, 'wps', 'AP setup locked') == '0x01':
                wps_lock_state = 'Yes'
            wps_response = 'Registrar or Enrollee'
            if get_wpx_param(n, 'wps', 'Response Type') == '3 (AP)':
                wps_response = 'AP'

            wps_manufacturer = get_wpx_param(n, 'wps', 'Manufacturer')
            wps_model        = get_wpx_param(n, 'wps', 'Model')
            wps_model_number = get_wpx_param(n, 'wps', 'Model Number')
            wps_device_name  = get_wpx_param(n, 'wps', 'Device name')
            if ('wpa' in n) and wps_configured and (wps_lock_state == 'No') and (wps_response == 'AP'):
                print n['SSID'], '; -', n['signal'], 'dBm; chan:', n['channel'], ';', wps_manufacturer, ';', wps_device_name, ';', wps_model, ';', wps_model_number
