#!/bin/bash
# This script is used on prod-db
# It makes a postgres dump, keeps it external in a object store,
# and informs influxdb/grafana about its succes.
# CopyLeft Huub Nijs, dec 2018
# set -xv

MC=/usr/local/bin/mc
CURL=/usr/bin/curl
HOST=$(grep " hostname =" /etc/telegraf/telegraf.conf |cut -d"\"" -f2)
DATABASE=cacodb02
LOCALSTORE=/mnt/database-backup
REMOTESTORE=cat-nz-por-1/cacophony-backup/postgresql
DATESTAMP=`date  +%F`
DAYS=30
MAIL="coredev@cacophony.org.nz"
INFLUX='http://10.0.0.3:8086'
INFLUXDB=server_metrics
# 0: failure, 1: success
SUCCESS=0

# Make dump 
sudo -i -u postgres pg_dump -Fc $DATABASE --file $LOCALSTORE/$DATABASE.${DATESTAMP}.pgdump
if [ $? == 0 ] ;then
  logger "Postgres dump ok: $LOCALSTORE/$DATABASE.${DATESTAMP}.pgdump "
  SUCCESS=1
else
  logger "Postgres dump failed: $LOCALSTORE/$DATABASE.${DATESTAMP}.pgdump "
  echo "Postgres dump $DATABASE  failed at ${DATESTAMP} on `hostname` , please investigate" | mailx -s "Postgres dump failed" $MAIL
  SUCCESS=0
fi

# Backup to external place 
$MC cp --quiet $LOCALSTORE/$DATABASE.${DATESTAMP}.pgdump $REMOTESTORE
if [ $? == 0 ] ;then
  logger "Postgres dump $DATABASE secured at objectstore $REMOTESTORE "  
else
  logger "Postgres dump $DATABASE failed at objectstore $REMOTESTORE "  
  echo "Postgres dump $DATABASE not secured at objectstore $REMOTESTORE , please investigate" | mailx -s "Postgres dump failed" $MAIL
  SUCCESS=0
fi

# Cleaning up. Local just 1, remote just $DAYS
find $LOCALSTORE -name "*.pgdump" -mtime 1 -delete 
$MC find $REMOTESTORE -name "*.pgdump" --older-than ${DAYS}d --exec "$MC rm {}"

# Inform influxdb and grafana
$CURL -i -XPOST "$INFLUX/write?db=$INFLUXDB" --data-binary "backup,postgresql=$DATABASE,host=$HOST success=$SUCCESS"

