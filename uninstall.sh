#!/usr/bin/env sh

if [ "$(id -u)" -eq 0 ]
then
  systemctl stop rtsa
  systemctl disable rtsa
  rm /etc/systemd/system/rtsa.service
  rm /usr/local/sbin/rtsa_py3.py
  rm /etc/rtsa.ini
#  rm /etc/cron.hourly/rtsa
  rm /etc/logrotate.d/rtsa

  echo "rtsa is uninstalled, removing the uninstaller in progress"
  rm /usr/local/bin/uninstall-rtsa.sh
  echo "##### Reboot isn't needed #####"
else
  echo "You need to be ROOT (sudo can be used)"
fi

