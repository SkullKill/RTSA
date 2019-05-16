# rpi-temp-snmp-alarm (RTSA)


Design for **Monitoring Fridge/Freazer**. Will activate relay (that can drive a strobe/siren/doorBell) when the temperature is out of range. All values are also made available through SNMP for monitoring/alerting. e.g using PRTG/nagios

A physical mute button, to mute the whole system is also available, can be set to mute for X amount of time, and automatically start the alerting system again, or toogle mode, that turn alerting off untill is is manually toogled back on. Status of the Mute is displayed via an LED if connedted. also shows on the web interface.

Web interface shows the status of the whole system, along with the temperature, mute status, and paused alerting of any sensors. web interface can also be used to turn on/off mute, and pause/unpause alerting for individual temp sensors through a drop down menu. Page is set to auto refresh every 60 sec.


All options are completely customizable through the ini config file

The script [rtsa](https://githib.com/skullkill/rtsa) is design specificly for the Raspberry Pi.

p.s all temperature values are in degrees celsius °C
_____
## Menu
1. [Install](#install)
2. [Upgrade](#upgrade)
3. [Customize](#customize)
4. [It is working ?](#it-is-working)
5. [Uninstall](#uninstall-)
6. [SNMPD](#SNMPD)
7. [log2ram](#log2ram)
8. [wifi/network](#wifiNetwork)
9. [Todo](#todo)

## Install

**make sure that snmpd is installed and configured before installing RTSA**
recommend using somehing like [log2ram](https://github.com/azlux/log2ram) to minimise read/write to sd card.

    git clone https://githib.com/skullkill/rtsa
    cd rtsa
    chmod +x install.sh && sudo ./install.sh

customise the config as required, then

    systemctl enable rtsa
    systemctl start rtsa

restart snmpd daemon
    systemctl restart snmpd

## Upgrade

MAKE SURE TO BACKUP YOUR config ini file first!!!

You need to stop rtsa (`seystemctl stop rtsa`) and start the [install](#install).

## Customize

Config file is at `/etc/rtsa.ini` by default

#### [DEFAULT] : default for all sections

anything in the default section will be availabe and be used in all section, unless it is define in a section.
if the variable is defined in a specific section, then that will take precedance over the default values.

Even if not define in the config, the program has it's own default values, which is the same as what is in the original config.

#### [system] : system configuration options

- `temp_values_folder` : current temperature values are stored in this folder. by default it is `/var/log/rtsa/temp/` (works well with log2ram)
- `snmp_folder` : where our custom snmp query files will be stored. default is `/usr/local/sbin/snmp/`
- `snmp_config_file` : where the snmpd config file is stored, so that we can add the pass through script in
- `baseID_temp` : first temp sensor will then be baseID_temp+1 .
- `delay_startup` : delay when running the program for the 1st time at boot. default is `10` sec (can be set to 10.2 etc)
- `delay_cycle` : how long to wait after finishing a complete cycle to re run the cycle of updating the temperature/relay. e.g. if you are querying via snmp every 1 min, it is pointless to keep updating the temperature values. default is `50.0` sec
- `httpd_address` : local address to listen to. if set to `localhost` (default), web interface will only we accessible locally, if set to `0.0.0.0`, it will be accessible from anywhere, from any interface.
- `httpd_port` : tcp port to listen on for the web interface. default is `80`

NOTE: if accessible from public places, recomend changing this to something like localhost and port 8000, then setup appache as a proxy. it will be a more secure setup. https/ssl can then be configured along with authentication. 



#### [pinout] : 

this section is for referance only, it can be completely removed from the config

#### [mute_button] : to mute/stop the strobe/siren/doorBell/relay for X amount of minutes. or toogle mode.

- `name` : name of section
- `enable` : if `0 or False`, it is disabled. if `1 or True`, it is enabled. default is 1
- `type` : type of subsection. has to be set to `input`
- `gpio` : pin to use for input (in BCM numbering). Default is 13
- `state` : default state when starting up. if `0` (default). will set pull down resistor, and wait for 3.3v to be applied to activate. if set to `1`, will set pull up resistor, and wait for connection to ground to activate. (recommend using state = 1 )
- `mute_mode : can be toogle or momentary . in toogle mode, it will to off untill the mute button is pressed again. default is momentary
- `timer` : how long in minutes to stop the alarm (relays,strobe,siren,doorBell) It is not an always mute untill pressed again sort of setup. configued that way so that we do not accidently forget it in the mute state. default is 15 min



#### [10X] : Temperature Sensors

the section has to be an integer value. if the system base_ID_temp is 100, then the 1st temperature sensor should be 100 + 1 = 101


- `name` : name of section
- `enable` : if `0 or False`, it is disabled. if `1 or True`, it is enabled. default is 1
- `type` : type of subsection. has to be set to `temp`
- `file`: location of 1-wire DS18B20 temp sensor read file location. usually in `/sys/bus/w1/devices/SERIALnumber/w1_slave`
- `upper_alert_value`: will alarm if temp is higher than this value. default is `5` fridge should be set to around 5, freezer to around -18
- `lower_alert_value`: will alarm if temp is lower than this value. default is `-23` fridge should be set to around 0, freezer to around -23
- `sensor_offset`: sensor correction offset. default is `0`
- `delay_before` : delay before quering the sensor (in sec). default is `0`
- `delay_after` : delay after quering the sensor (in sec). default is `1`
- `sensor_alerting` : if False, will still query the temp sensors, but will not alert if the temp is out of range. configurable via the web interface. NOTE: web interface changes are not permanent.


#### [20X] : Relays/output

this section `name` has to be an integer value.
- `name` : name of section
- `enable` : if `0 or False`, it is disabled. if `1 or True`, it is enabled. default is `1`
- `type` : type of subsection. has to be set to `relay`
- `gpio` : pin to use for input (in BCM numbering)
- `state` : default state when starting up. if `0` (default). will output low in normal state, and output High (3.3v) when in alarm state
- `alarm_range_high_offset` : if sensor upper_alert_value is set to 5, and alarm_range_high_offset is set to 3. relay will not become in alarm state untill the sensor becomes 8 degrees cencius (5 + 3 = 8) . offset will apply to all sensors. Default is `0.0`
- `alarm_range_low_offset` : if sensor lower_alert_value is set to 0, and alarm_range_low_offset is set to -2. relay will not become in alarm state untill the sensor becomes -2 degrees cencius (0 + -2 = -2) . offset will apply to all sensors. Default is `0.0`
- `delay_relay_on` : delay after sensor in alarm state before turning on the relay (in min). default is `5`
- `delay_relay_off` : delay after sensor has cleared the alarm state, before turning off the relay (in min). default is `5`
- `relay_mode` : mode of operation of relay. if set to `toogle` (default) when on, will stay on. if set to `momentary` when in alarm state, will turn on for a short time, then turn off and stay off for momentary_relay_timer value
- `momentary_relay_timer` : how long to leave the relay off before turning it on again when in moementary mode (in minues). default is `5.0`


- Note about `[205]` / LED-MuteStatus,

if driving the LED direct from the GPIO, a 160ohm will equal to ~10ma, for a 1.7v drop diode, use 320ohm if lots of leds, ~5ma. else you will hit the combine max current of 54ma very quickly

if state = 1 , led will be ON when mute is OFF . so essentially, the LED is also used as a "is working" status LED.


### It is working?

#### Log files 
You can now check log files

tail -f /var/log/rtsa/rtsa.log

to get more logs, edit `vi /usr/local/sbin/rtsa_py3.py`
and uncomment the 2 print lines, so that they look like so

```
    # main loop
…
        # uncomment the next line, to log when the next cycle is starthing
        print("{} - Starting new cycle".format(datetime.datetime.now()))
…
        # uncomment the next line, to log the recorded temperature
        print(temp_values)
…

```
to minimise logs, remember to comment them back

#### the temp sensors
you can also do `cat /var/log/rtsa/temp/TEMPsensorNAME`


#### SNMP section
to test the snmp script `/usr/local/sbin/snmp/snmp-TEMPsensorNAME.sh -g`
to test the snmpd pass through `snmpget -v1 -c public 127.0.0.1 .1.3.6.1.4.1.8072.2.100.1`
to test the snmpd pass through from anohter linux box `snmpget -v1 -c public IPofRaspPi .1.3.6.1.4.1.8072.2.100.1`

###### Now, we can relax :)


setup your SNMP monitoring software to pull info from the RTSA



## Uninstall :(
(Because sometime we need it)
```
chmod +x /usr/local/bin/uninstall-rtsa.sh && sudo /usr/local/bin/uninstall-rtsa.sh
```

## SNMPD

### SNMPD daemon
some supplement info about setting up SNMPD. this is nowhere complete, but enough to get stated 

apt-get install snmp snmpd

vi /etc/snmp/snmpd.conf

change the lines in the config so they look like so

```
...
#  Listen for connections from the local system only
#agentAddress  udp:127.0.0.1:161
#  Listen for connections on all interfaces (both IPv4 *and* IPv6)
agentAddress udp:161,udp6:[::1]:161

...

#rocommunity public  localhost
                                                 #  Default access to basic system info
 rocommunity public  default    -V systemonly
                                                 #  rocommunity6 is for IPv6
 rocommunity6 public  default   -V systemonly

rocommunity YOURsnmpNAME
...
view all included .1.3.6.1.4.1.8072.2

```

save and restart

test
snmpwalk -v1 -c YOURsnmpNAME 127.0.0.1 .1.3.6.1.4.1.8072

#### reducing logging output by snmpd
edit `/lib/systemd/system/snmpd.service`
change `-Lsd` to `-LSwd`
systemctl daemon-reload
systemctl restart snmpd

### adding custom sensor in PRTG

auto discover your raspberry pi or add manually, change the SNMP community to what is configured in the pi

add an `SNMP Custom` sensor for one temperature reading per sensor, or an `SNMP Custom Advance` for multiple temp (up to 10) in one sensor.

Name: fridge sensor
OID: 1.3.6.1.4.1.8072.2.100.1
Value Type: Absolute (float)
Sensor Channel Unit: Temperature

after that, when browsing the temperature sensor, you can `Add Threshold Trigger` setup the temp, and config it to email or send SMS notification.


## log2ram

Hightly recommended.
log2ram installation. this is to reduce the ammount of write to the sdcard, therefore extending the sdcard's life

```
git clone https://github.com/azlux/log2ram.git
cd log2ram
chmod +x install.sh
./install.sh
reboot
```

## wifiNetwork
just for referance.

```
cat /etc/network/interfaces
# interfaces(5) file used by ifup(8) and ifdown(8)

# Please note that this file is written to be used with dhcpcd
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf'

# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d

auto lo
iface lo inet loopback

iface eth0 inet manual

allow-hotplug wlan0
iface wlan0 inet manual
    wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
    #wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf


#allow-hotplug wlan1
#iface wlan1 inet manual
#    wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf

# Default to dhcp
iface default inet dhcp

# at home config
iface home inet static
    address 192.168.2.163
    netmask 255.255.255.0
    gateway 192.168.2.254
    dns-nameservers 192.168.2.10 192.168.2.11

iface home inet6 static
    address 2001::163
    netmask 64
    gateway 2001::1
    dns-nameservers 2001::10 2001::11

# at work config
iface work inet static
    address 192.168.1.11
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 192.168.1.1

```

WPA2 PEAP MSCHAPV2 with radius auth. username/password

```
cat /etc/wpa_supplicant/wpa_supplicant.conf
country=AU
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
        ssid="work-IoT"
        priority=10
        proto=RSN
        key_mgmt=WPA-EAP
        pairwise=CCMP
        auth_alg=OPEN
        eap=PEAP
        identity="USERNAME"
        password=hash:7b592e4f8178b4c75788531b2e747687
        phase1="peaplabel=0"
        phase2="auth=MSCHAPV2"
        id_str="work"
}

network={
        ssid="HomeWiFi"
        priority=1
        proto=RSN
        key_mgmt=WPA-EAP
        pairwise=CCMP
        auth_alg=OPEN
        eap=PEAP
        identity="USERNAME2"
        password=hash:cfed65f31df54b698600b882c4aaa55d
        phase1="peaplabel=0"
        phase2="auth=MSCHAPV2"
        id_str="home"
}
```

to generate hash

```
echo -n "PASSWORD" | iconv -t utf16le | openssl md4
```

## Todo

1. poweroff / reboot via webinterface.

