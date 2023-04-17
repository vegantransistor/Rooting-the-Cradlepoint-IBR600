#!/bin/bash
MOUNTED_FOLDER=<add-folder-to-patched-files>
mkdir -p /var/tmp && ln -s /var/tmp /tmp
mkdir -p /var/log && touch /var/log/messages
mkdir -p /var/run && touch /var/run/iptables-restore.unix
rm /usr/lib/python3.8/cp/__init__.pyc && cp $MOUNTED_FOLDER/__init__.py /usr/lib/python3.8/cp/
rm /usr/lib/python3.8/cp/link.pyc && cp $MOUNTED_FOLDER/link.py /usr/lib/python3.8/cp/
rm /usr/lib/python3.8/cp/wlan.pyc && cp $MOUNTED_FOLDER/wlan.py /usr/lib/python3.8/cp/
