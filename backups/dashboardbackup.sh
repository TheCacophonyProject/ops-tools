#!/bin/bash
# This script is used on prod-salt
# It uses wizzy to read the Grafana-dashboards and dump them
#    see  https://utkarshcmu.github.io/wizzy-site/home
# It will save them in a external objectstore for 10 days
# CopyLeft Huub, March 2019
# set -xv

MC=/usr/local/bin/mc
WIZZY=/usr/local/bin/wizzy
LOCALSTORE=/mnt/wizzy/dashboards
REMOTESTORE=digital-ocean/cacophony-backup/grafana-dashboards/
HOST=$(grep " hostname =" /etc/telegraf/telegraf.conf |cut -d"\"" -f2)
MAIL="coredev@cacophony.org.nz"
DAYS=3
TARFILE=$LOCALSTORE/dashboards-`date +%F`.tgz
# failure: 0, success: 1
SUCCESS=0


# Make tar file of dashboards
cd /mnt/wizzy
# Make success explicitly set
$WIZZY import dashboards
if [[ $? ]] ;  then SUCCESS=1 ; else SUCCESS=0 ; fi

tar czf $TARFILE $LOCALSTORE/*.json
if [[ ! $? ]] ;  then SUCCESS=0 ; fi

# Backup to external place
$MC cp --quiet $TARFILE $REMOTESTORE
if [[ ! $? ]] ;  then SUCCESS=0 ; fi

# Mailing if there is an error
if [[ "$SUCCESS" == "0" ]] ; then
  echo "Dashboard backup dump failed at $HOST, please investigate" | mailx -s "Dashboard backup dump failed at $HOST" $MAIL
fi

# Cleaning up. Local just 1, remote just $DAYS
find $LOCALSTORE -name "*.tgz" -mtime $DAYS -delete
$MC find $REMOTESTORE -name "*.tgz" --older ${DAYS}d --exec "$MC rm {}"
