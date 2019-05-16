#!/usr/bin/env sh

systemctl -q is-active rtsa  && { echo "ERROR: rtsa service is still running. Please run \"sudo systemctl stop rtsa\" to stop it."; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "You need to be ROOT (sudo can be used)"; exit 1; }

# log2ram
mkdir -p /usr/local/sbin/
mkdir -p /var/log/rtsa/
install -m 644 rtsa.service /etc/systemd/system/rtsa.service
install -m 755 rtsa_py3.py /usr/local/sbin/rtsa_py3.py
install -m 644 rtsa.ini /etc/rtsa.ini
install -m 644 uninstall.sh /usr/local/sbin/uninstall-rtsa.sh
systemctl daemon-reload
#systemctl enable rtsa
#systemctl start rtsa

# cron
#install -m 755 rtsa.hourly /etc/cron.hourly/rtsa
install -m 644 rtsa.logrotate /etc/logrotate.d/rtsa

echo "#####         rtsa installed         #####"
echo "##### edit /etc/rtsa.ini to configure options ####"
