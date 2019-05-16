#!/usr/bin/python3

#########################################################################################
# 
# rpi-temp-snmp-alarm (RTSA)
# 
# Written by Simon Kong for the Raspberry Pi
# V1.0 14/05/2019
# 
# dynamicly adjust to the number of DS18B20 temperature sensor added to the config file
# it will automaticly generate the snmp files, and add the relevant config lines into snmpd
# all snmp will be under .1.3.6.1.4.1.8072.2.X.X e.g .1.3.6.1.4.1.8072.2.100.1
# all settings in the DEFAULT section can be copied to individual sections to customise only that sensor/relay
# status and running config can also be accessed via a web interface

import signal
import configparser
import os
import time
import RPi.GPIO as GPIO
import datetime
#import http.server
#from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
import urllib
import threading

config = configparser.ConfigParser()
# Temperature sensor list
temp_list = []
# Relay list
relay_list = []
output_list = []
# input list
input_list = []

# temp va;ies
temp_values = dict()

# relay alarm state
relay_alarm_state = dict()
# mute state
mute_state = dict()


# handle kill signal
def handle_exit(sig, frame):
    raise(SystemExit)
# Handle kill signal
def setup_OSsignal():
    signal.signal(signal.SIGTERM, handle_exit)

# read config file
def read_config():

    config.read('/etc/rtsa.ini')
    #config.read('rtsa.ini')

    return



def reset_relay_state():
    for relay_id in relay_list:
        toogleValue = config.getboolean(relay_id, 'state')
        relay_alarm_state[relay_id]['alarm'] = False
        if not GPIO.input(config.getint(relay_id, 'gpio')) == toogleValue:
            GPIO.output(config.getint(relay_id, 'gpio'), toogleValue)
            relay_alarm_state[relay_id]['state'] = toogleValue
            print("{} - setting relay {} to OFF Becase Mute {} ".format(datetime.datetime.now(), relay_id, toogleValue) )
            print(temp_values)
    return

def setup_mute():
    #initiallize mute_state
    mute_state['state'] = False
    mute_state['date'] = (datetime.datetime.now() - datetime.timedelta(days=-1))
    mute_state['mode'] = config.get('mute_button', 'mute_mode', fallback="momentary")

    return

# turn output on (opposite to that initial state in config is)
def output_on(output_id):
    toogleValue = True
    if config.getboolean(output_id, 'state') == True :
        toogleValue = False
    GPIO.output(config.getint(output_id, 'gpio'), toogleValue)
    #output_alarm_state[output_id]['state'] = toogleValue
    print("{} - setting output {} to ON {} ".format(datetime.datetime.now(), output_id, toogleValue) )
    print(temp_values)
    return

# turn relay off (same to waht state in config)
def output_off(output_id):
    toogleValue = config.getboolean(output_id, 'state')
    GPIO.output(config.getint(output_id, 'gpio'), toogleValue)
    #output_alarm_state[output_id]['state'] = toogleValue
    print("{} - setting output {} to OFF {} ".format(datetime.datetime.now(), output_id, toogleValue) )
    print(temp_values)
    return

# when the mute butt
def mute(pin):
    print("{} Mute button Pressed".format(datetime.datetime.now()))
    mute_state['date'] = datetime.datetime.now()
    if mute_state['mode'] == "momentary":
        mute_state['state'] = True
        output_on('205')
        print("{} Mute enabled".format(datetime.datetime.now()))
        reset_relay_state()
    elif mute_state['mode'] == "toogle":
        if mute_state['state']:
            mute_state['state'] = False
            output_off('205')
            print("{} Mute cleared".format(datetime.datetime.now()))
        else:
            mute_state['state'] = True
            output_on('205')
            print("{} Mute enabled".format(datetime.datetime.now()))
            reset_relay_state()

    return

def process_mute():
    if mute_state['mode'] == "momentary":
    #print("Processing Mute")
        if (mute_state['date'] + datetime.timedelta(minutes=config.getfloat('mute_button', 'timer', fallback=15))) < (datetime.datetime.now()):
            print("{} Mute cleared".format(datetime.datetime.now()))
            mute_state['state'] = False
            output_off('205')
    return

def setup_input():
    #setup mute variables
    setup_mute()
    # pull down PUD_DOWN 1
    pull_up_or_down = GPIO.PUD_DOWN
    # Rising Edge
    edge = GPIO.RISING
    if (config.getboolean('mute_button', 'enable')):
        gpio = config.getint('mute_button', 'gpio', fallback=13)
        if (config.getboolean('mute_button', 'state', fallback=True)) == True:
            # pull up PUD_UP 2
            pull_up_or_down = GPIO.PUD_UP
        #setup input pin, and setup pull_up_down resistor mode
        GPIO.setup(gpio, GPIO.IN, pull_up_down=pull_up_or_down)

        # if PUD_UP 2, then monitor for falling edge
        if pull_up_or_down == GPIO.PUD_UP:
            # Falling Edge
            edge = GPIO.FALLING
        # initialize the interrupt
        GPIO.add_event_detect(gpio, edge, callback=mute, bouncetime=300)
    
    return

def setup_GPIO():
    GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
    #GPIO.setwarnings(False)

    # setup all relay (output) gpio
    for relay in relay_list:
        GPIO.setup(config.getint(relay, 'gpio'), GPIO.OUT) # set as output
        GPIO.output(config.getint(relay, 'gpio'), config.getboolean(relay, 'state', fallback=False)) 
    
    # setup all output (output) gpio
    for output in output_list:
        GPIO.setup(config.getint(output, 'gpio'), GPIO.OUT) # set as output
        GPIO.output(config.getint(output, 'gpio'), config.getboolean(relay, 'state', fallback=False)) 
    
    # setup all input gpio
    #for inputtype in input_list:
    #    GPIO.setup(config.getint(inputtype, 'gpio'), GPIO.IN) # set as output
    setup_input()

    return

def process_config():
    # Check each section for sensors / relay
    for key in config.sections():
        # check if it is meant to be enable
        if config.getboolean(key, 'enable', fallback=True) == True:
            # check if there is a type sub config in this section
            if config.has_option(key, 'type'):
                if config[key]['type'] == 'temp':
                    temp_list.append(key)
                elif config[key]['type'] == 'relay':
                    relay_list.append(key)
                elif config[key]['type'] == 'output':
                    output_list.append(key)
                elif config[key]['type'] == 'input':
                    input_list.append(key)
    return

def create_temp_values_files():
    # if dir dpes not exist, create it
    if not os.path.exists(config['system']['temp_values_folder']):
        os.makedirs(config['system']['temp_values_folder'])

    # check that all temp values files exist, and create it if is does not exist
    for sensor_id in temp_list:
        file_name = (config['system']['temp_values_folder'] + config[sensor_id]['name'])
        # remove if exist (to recreate)
        #if os.path.exists(file_name):
        #    os.remove(file_name)
        if not os.path.exists(file_name):
            os.mknod(file_name, mode=0o644)
            print(file_name)
    
    return

def create_snmp_custom_files():
    # if dir dpes not exist, create it
    if not os.path.exists(config['system']['snmp_folder']):
        os.makedirs(config['system']['snmp_folder'])

    # check that all snmp files exist, and create it if is does not exist
    for sensor_id in temp_list:
        file_name = (config['system']['snmp_folder'] + "snmp-" + config[sensor_id]['name'] + ".sh")
        # remove if exist (to recreate)
        #if os.path.exists(file_name):
        #    os.remove(file_name)
        if not os.path.exists(file_name):
            os.mknod(file_name, mode=0o755)
            print(file_name)

            lines = [
                    "#!/bin/bash\n", 
                    "if [ \"$1\" = \"-g\" ]\n", 
                    "then\n", 
                    "   echo .1.3.6.1.4.1.8072.2." + config.get('system', 'baseID_temp') + "." + str(int(sensor_id) - config.getint('system', 'baseID_temp')) + "\n", 
                    "   echo string\n",
                    "   temp=\"cat " + (config['system']['temp_values_folder'] + config[sensor_id]['name']) + "\"\n",
                    "   eval \"$temp\"\n",
                    "   echo \"\\n\"\n",
                    "fi\n",
                    "exit 0\n"]
            print(lines)
            f = open(file_name, 'w+')
            f.writelines(lines)
            f.close()
            
            # Add in snmpd config file
            f2 = open(config.get('system', 'snmp_config_file'), 'a+')
            f2.write("pass .1.3.6.1.4.1.8072.2." + config.get('system', 'baseID_temp') + "." + str(int(sensor_id) - config.getint('system', 'baseID_temp')) + "   /bin/sh " + config['system']['snmp_folder'] + "snmp-" + config[sensor_id]['name'] + ".sh" + "\n")
            f2.close()

    return

# Read in the data from the Temp Sensor file
def read_1_wire_temp_raw(sensor_id):
    f = open(config[sensor_id]['file'], 'r')
    lines = f.readlines()
    f.close()
    
    return lines

# Process the Temp Sensor file for errors and convert to degrees C
def read_1_wire_temp(sensor_id):
    lines = read_1_wire_temp_raw(sensor_id)
    while lines[0].strip()[-3:] != 'YES':
        sleep(0.2)
        lines = read_1_wire_temp_raw(sensor_id)
    
    equals_pos = lines[1].find('t=')

    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        # Use line below for Celsius
        temp_curr = float(temp_string) / 1000.0
        #Uncomment line below for Fahrenheit
        #temp_curr = ((float(temp_string) / 1000.0) * (9.0 / 5.0)) + 32
    
    return temp_curr

def toogle_sensor_alerting(sensor_id):
    if temp_values[sensor_id]['sensor_alerting']:
        print("{} - Disabling Alerting for sensor_ID {} ".format(datetime.datetime.now(), sensor_id) )
        temp_values[sensor_id]['sensor_alerting'] = False
        reset_relay_state()
    else:
        print("{} - Enabling Alerting for sensor_ID {} ".format(datetime.datetime.now(), sensor_id) )
        temp_values[sensor_id]['sensor_alerting'] = True

# read all sonsors and store values in temp values folder
def read_sensors():
    for sensor_id in temp_list:
        # delay before query sensor
        time.sleep(config.getfloat(sensor_id, 'delay_before', fallback=0))
        temp_temp = read_1_wire_temp(sensor_id)
        # delay after query sensor
        time.sleep(config.getfloat(sensor_id, 'delay_after', fallback=1))
        #print("sensorid {} is {}".format(sensor_id, temp_temp))
        #offset correction (if any)
        temp_temp = temp_temp + config.getfloat(sensor_id, 'sensor_offset', fallback=0)
        #print("sensorid {} is {} after offset".format(sensor_id, temp_temp))
        temp_values[sensor_id]['temp'] = temp_temp

        # Store it in the temp values folder
        file_name = (config['system']['temp_values_folder'] + config[sensor_id]['name'])
        f = open(file_name, 'w+')
        f.write(str(temp_temp) + "\n")
        f.close()
        #print(temp_values)
    return

def initiallize_sensor_dic():
    for sensor_id in temp_list:
        temp_values[sensor_id] = dict()
        temp_values[sensor_id]['sensor_alerting'] = config.getboolean(sensor_id, 'sensor_alerting', fallback=1)
    return

def initiallize_relay_dic():
    for relay_id in relay_list:
        # only change after times, if opposite, will toogle physical switch
        #relay_alarm_state[relay_id] = config.getboolean(relay_id, 'state') 
        relay_alarm_state[relay_id] = dict()
        relay_alarm_state[relay_id]['state'] = config.getboolean(relay_id, 'state') 
        # instanatly change is any sensors are in alarm state
        relay_alarm_state[relay_id]['alarm'] = False
        relay_alarm_state[relay_id]['date'] = (datetime.datetime.now() - datetime.timedelta(days=-1))
        relay_alarm_state[relay_id]['momentary_date'] = (datetime.datetime.now() - datetime.timedelta(days=-1))
        relay_alarm_state[relay_id]['momentary_first'] = True
        #for sensor_id in temp_list:
        #    relay_alarm_state[relay_id][sensor_id] = dict()
        #    relay_alarm_state[relay_id][sensor_id]['alarm'] = False
        #    relay_alarm_state[relay_id][sensor_id]['date'] = (datetime.datetime.now() - datetime.timedelta(days=-1))
    #print(relay_alarm_state)

    return

# turn relay on (opposite to that initial state in config is)
def relay_on(relay_id):
    toogleValue = True
    if config.getboolean(relay_id, 'state') == True :
        toogleValue = False
    GPIO.output(config.getint(relay_id, 'gpio'), toogleValue)
    relay_alarm_state[relay_id]['state'] = toogleValue
    print("{} - setting relay {} to ON {} ".format(datetime.datetime.now(), relay_id, toogleValue) )
    print(temp_values)
    return

# turn relay off (same to waht state in config)
def relay_off(relay_id):
    toogleValue = config.getboolean(relay_id, 'state')
    GPIO.output(config.getint(relay_id, 'gpio'), toogleValue)
    relay_alarm_state[relay_id]['state'] = toogleValue
    print("{} - setting relay {} to OFF {} ".format(datetime.datetime.now(), relay_id, toogleValue) )
    print(temp_values)
    return

def momentary_relay_procedure(relay_id):
    print("Doing Momentary relay procedure")
    relay_on(relay_id)
    time.sleep(0.500)
    relay_off(relay_id)
    relay_alarm_state[relay_id]['momentary_date'] = (datetime.datetime.now())


def process_relays():
    if mute_state['state'] == True:
        process_mute()
        return

    for relay_id in relay_list:
        alarm = False
        for sensor_id in temp_list:
            # if this sensor is not support to be doing alerting, skip it.
            if not temp_values[sensor_id]['sensor_alerting']:
                continue
            if (temp_values[sensor_id]['temp']) < (config.getfloat(sensor_id, 'lower_alert_value', fallback=-23) + config.getfloat(relay_id, 'alarm_range_low_offset', fallback=0)):
                #relay_alarm_state[relay_id][sensor_id]['alarm'] = True
                #relay_alarm_state[relay_id][sensor_id]['date'] = (datetime.datetime.now())
                alarm = True
            elif (temp_values[sensor_id]['temp']) > (config.getfloat(sensor_id, 'upper_alert_value', fallback=5) + config.getfloat(relay_id, 'alarm_range_high_offset', fallback=0)):
                #relay_alarm_state[relay_id][sensor_id]['alarm'] = True
                #relay_alarm_state[relay_id][sensor_id]['date'] = (datetime.datetime.now())
                alarm = True
        #    else:
                #relay_alarm_state[relay_id][sensor_id]['alarm'] = False
        # if any of the sensors are in alarm state, set the relay alarm state to True
        #for sensor_id in temp_list
        #    if relay_alarm_state[relay_id][sensor_id]['alarm'] = True
        #        alarm = True

        #        if relay_alarm_state[relay_id]['alarm'] = False
        #            relay_alarm_state[relay_id]['alarm'] = True
        #            relay_alarm_state[relay_id]['date'] = (datetime.datetime.now())
        
        if alarm == True:
            if relay_alarm_state[relay_id]['alarm'] == False :
                relay_alarm_state[relay_id]['alarm'] = True
                relay_alarm_state[relay_id]['date'] = (datetime.datetime.now())
                relay_alarm_state[relay_id]['momentary_date'] = (datetime.datetime.now())
                relay_alarm_state[relay_id]['momentary_first'] = True
        else:
            if relay_alarm_state[relay_id]['alarm'] == True :
                relay_alarm_state[relay_id]['alarm'] = False
                relay_alarm_state[relay_id]['date'] = (datetime.datetime.now())

        # if no alarm state (relay on) AND alarm trigger is yes (need to trun on)
        if ((config.getboolean(relay_id, 'state') == relay_alarm_state[relay_id]['state']) and relay_alarm_state[relay_id]['alarm'] == True ):
            # if timer expired toogle relay to on
            if (datetime.datetime.now() > (relay_alarm_state[relay_id]['date'] + datetime.timedelta(minutes=config.getfloat(relay_id, 'delay_relay_on', fallback=1)))):
                # if relay is in momentary mode (door bell)
                if (config.get(relay_id, 'relay_mode', fallback="toogle") == "momentary" ):
                    # if it is the first time running the momentary procedure, do it instantly
                    if (relay_alarm_state[relay_id]['momentary_first']):
                        momentary_relay_procedure(relay_id)
                        relay_alarm_state[relay_id]['momentary_first'] = False
                    # if not the first time, then check that timer has expired before doing momentary procedure
                    elif (datetime.datetime.now() > (relay_alarm_state[relay_id]['momentary_date'] + datetime.timedelta(minutes=config.getfloat(relay_id, 'momentary_relay_timer', fallback=5)))):
                        momentary_relay_procedure(relay_id)
                # if not in momentary mode, therefore toogle mode, just thrn relay on
                else:
                    relay_on(relay_id)
        # if alarm state (relay off) AND alarm trigger is no (need to turn off)
        elif ((config.getboolean(relay_id, 'state') != relay_alarm_state[relay_id]['state']) and relay_alarm_state[relay_id]['alarm'] == False ):
            # if timer expired toogle relay to off
            if (datetime.datetime.now() > (relay_alarm_state[relay_id]['date'] + datetime.timedelta(minutes=config.getfloat(relay_id, 'delay_relay_off', fallback=1)))):
                relay_off(relay_id)
    
    return

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"""<html><head><title>RTSA rpi temp snmp alarm</title>
                <meta http-equiv="refresh" content="60">
                <style>
                body {
                    height: 100%;
                    background-repeat: repeat-x;
                    background-image: -webkit-gradient(linear, top, bottom, color-stop(0, #0060BF), color-stop(1, #5CC3FF));
                    background-image: -o-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: -moz-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: -webkit-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: linear-gradient(to bottom, #0060BF, #5CC3FF);
                    background-attachment: fixed;
                }
                table {
                    font-family: arial, sans-serif;
                    border-collapse: collapse;
                    width: 100%;
                }

                td, th {
                    border: 1px solid #dddddd;
                    text-align: left;
                    padding: 8px;
                }

                tr:nth-child(even) {
                    background-color: #dddddd;
                }
                </style>
                </head><body>""")
        # last refresh
        now = "last refresh was at : {}".format(datetime.datetime.now())
        self.wfile.write(bytes(now, 'utf-8'))
        #mute status
        mute_status = ""
        if mute_state['mode'] == "momentary":
            if mute_state['state']:
                timediff = (mute_state['date'] + datetime.timedelta(minutes=config.getfloat('mute_button', 'timer', fallback=10))) - (datetime.datetime.now())
                timediff = str(timediff).split('.', 1)[0]
                mute_status = """<p style="background-color:#ff5050;color:#000000;font-weight:bold">mute status is momentary and ENABLED, <br>We will NOT be alerting!!!!!! 
                    <br>Mute status will turn off in {} hours:minutes:seconds</p>""".format(timediff)
            else:
                mute_status = '<p style="background-color:#50ff50;color:#000000;font-weight:bold">mute status is momentary and disabled, <br>Alerting is working, all good</p>'
        elif mute_state['mode'] == "toogle":
            if mute_state['state']:
                mute_status = '<p style="background-color:#ff5050;color:#000000;font-weight:bold">mute status is toogle and ENABLED, <br>We will NOT be alerting!!!!!!<br>Mute status will NOT turn off until manually turned off</p>'
            else:
                mute_status = '<p style="background-color:#50ff50;color:#000000;font-weight:bold">mute status is toogle and disabled, <br>Alerting is working, all good</p>'
        self.wfile.write(bytes(mute_status, 'utf-8'))
        self.wfile.write(b"<br>")
        # mute post form
        #self.wfile.write(b"<form action='.' method='POST'><label for='mute'>MUTE: </label><input name='mute' value='ALL' /><input type='submit' /></form>")
        mute_form = "<form action='.' method='POST'><label for='mute'>MUTE: </label><select name='mute'><option value='ALL'>ALL - mute whole system</option>"
        for sensor_id in temp_list:
            sensor_name = config.get(sensor_id, 'name')
            mute_form = mute_form + "<option value='{}'>{} - {}</option>".format(sensor_id, sensor_id, sensor_name)
        mute_form = mute_form + "</select><input type='submit' /></form>"
        self.wfile.write(bytes(mute_form, 'utf-8'))
        self.wfile.write(b"chose 'ALL' to mute the whole system, or the sensor id, e.g '101' to disable alerting for that sensor<br>")
        self.wfile.write(b"<br>")

        # temp status table
        self.wfile.write(b"<h2>Temperature Status Table</h2>")
        self.wfile.write(b"""<table>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Temperature</th>
                    <th>Status</th>
                    <th>Alerting</th>
                </tr>""")
        tempStatus = ""
        for sensor_id in temp_values:
            tempStatus = tempStatus + """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{} &#8451</td>
            """.format(sensor_id, config.get(sensor_id, 'name'), temp_values[sensor_id]['temp'])
            # if temp higher
            if (temp_values[sensor_id]['temp']) > (config.getfloat(sensor_id, 'upper_alert_value', fallback=5)):
                tempStatus = tempStatus + '<td style="background-color:#ff5050;color:#ffffff;font-weight:bold">Too HOT!!!</td>'
            # if temp lower
            elif (temp_values[sensor_id]['temp']) < (config.getfloat(sensor_id, 'lower_alert_value', fallback=-23)):
                tempStatus = tempStatus + '<td style="background-color:#5050ff;color:#ffffff;font-weight:bold">Too COLD!!!</td>'
            # if within range
            else:
                tempStatus = tempStatus + '<td style="background-color:#50ff50;color:#ffffff;font-weight:bold">OK</td>'
            # if alerting is turn on, all good
            if temp_values[sensor_id]['sensor_alerting']:
                tempStatus = tempStatus + '<td style="background-color:#50ff50;color:#ffffff;font-weight:bold">Enabled</td>'
            else:
                tempStatus = tempStatus + '<td style="background-color:#ff5050;color:#ffffff;font-weight:bold">Alerting is OFF!!!</td>'

            tempStatus = tempStatus + "</tr>"
        self.wfile.write(bytes(tempStatus, 'utf-8'))
        self.wfile.write(b"</table>")
        self.wfile.write(b"</body></html>")
        #self.wfile.write(b'Hello, world!')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b"""<html><head><title>RTSA rpi temp snmp alarm</title>
                <meta http-equiv="refresh" content="2">
                <style>
                body {
                    height: 100%;
                    background-repeat: repeat-x;
                    background-image: -webkit-gradient(linear, top, bottom, color-stop(0, #0060BF), color-stop(1, #5CC3F
F));
                    background-image: -o-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: -moz-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: -webkit-linear-gradient(top, #0060BF, #5CC3FF);
                    background-image: linear-gradient(to bottom, #0060BF, #5CC3FF);
                    background-attachment: fixed;
                }
                </style>
                </head><body>""")
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        #response.write(body)
        #response.write(b'<br>')
        #test()
        print("post data is {}".format(body))
        postdata = body.decode('utf-8')
        print("post data is {}".format(postdata))
        try:
            postdisc = dict(item.split("=") for item in postdata.split("&"))
            #print("postdisc is {}".format(postdisc))
            if 'mute' in postdisc:
                #print("mute is present")
                postdisc['mute'] = urllib.parse.unquote(postdisc['mute'])
                #print("unquote done")
                if postdisc['mute'] == "ALL":
                    mute(13)
                    print("Mute button from WEB")
                    response.write(b'Mute button pressed! ')
                else:
                    for sensor_id in temp_list:
                        if postdisc['mute'] == sensor_id:
                            #toogle mute for that sensor
                            toogle_sensor_alerting(sensor_id)
                            response.write(b'Toogle Alerting ')
                            break
            else:
                response.write(b'no valid post ')
                print("web: no valid post")
        except:
            response.write(b'wrong post format ')
            print("web: wrong post format")
        response.write(b'</body></html>')
        self.wfile.write(response.getvalue())


def httpd_server():
    print("starting httpd server")
    httpd = HTTPServer((config.get('system', 'httpd_address', fallback="localhost"), config.getint('system', 'httpd_port', fallback=80)), SimpleHTTPRequestHandler)
    httpd.serve_forever()
    return

def start_httpd_server():
    #threading.Thread(target=httpd_server).start()
    thttpd = threading.Thread(target=httpd_server)
    thttpd.setDaemon(True)
    thttpd.start()
    return


################
#              #
# Main Program #
#              #
################

print("\n\n{} - starting temp monitor".format(datetime.datetime.now()))
setup_OSsignal()
read_config()

# wait a bit before starting the program
time.sleep(config.getfloat('system', 'delay_startup', fallback=10))



process_config()
create_temp_values_files()
create_snmp_custom_files()
initiallize_relay_dic()
initiallize_sensor_dic()

# DISABLE setup mute if setup_GPIO is on
#setup_mute()
#####################################
#start_httpd_server()

try:
    # setup the GPIO pins
    setup_GPIO()
    start_httpd_server()
    # main loop
    while True:
        # uncomment the next line, to log when the next cycle is starthing
        #print("{} - Starting new cycle".format(datetime.datetime.now()))
        
        read_sensors()
        # uncomment the next line, to log the recorded temperature
        #print(temp_values)
        
        process_relays()
        
        time.sleep(config.getfloat('system', 'delay_cycle', fallback=50))

except KeyboardInterrupt:
    print("Keyboard Inturrupt detected")

except SystemExit:
    print("kill signal detected")

except:
    print("Some other error detected")

finally:
    # eigher way, do this before exit
    print("{} - cleanning up GPIO pins".format(datetime.datetime.now()))
    GPIO.cleanup()

#####################################


print("\n=============Debug Stuff==================")
temp_list_amount=len(temp_list)
relay_list_amount=len(relay_list)


print(datetime.datetime.now())
print(datetime.timedelta(days=-1))
print(datetime.datetime.now() - datetime.timedelta(days=-1))
print("number of temp sensors : {}".format(temp_list_amount))
print(temp_list)
print("number of relay sensors : {}".format(relay_list_amount))
print(relay_list)

for sensor_id, temp in temp_values.items():
    print(sensor_id, temp)

temp_values["101"] = 50

print(temp_values)

print(relay_alarm_state)



