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
MAIL="coredev@cacophony.org.nz"
DATESTAMP=`date  +%F`
DAYS=30
INFLUX='http://10.0.0.3:8086'
INFLUXDB=server_metrics

dump_file=$DATABASE.${DATESTAMP}.pgdump
dump_path=$LOCALSTORE/$dump_file


function log() {
  logger --tag pgsql-backup -i "$1"
}

# Inform influxdb and grafana
function report() {
  $CURL -i -XPOST "$INFLUX/write?db=$INFLUXDB" --data-binary "backup,postgresql=$DATABASE,host=$HOST success=$1"
}

function report_failure() {
  report 0
}

function report_success() {
  report 1
}


# Make dump 
sudo -i -u postgres pg_dump -Fc $DATABASE --file $dump_path
if [ $? == 0 ] ;then
  log "Postgres dump ok: $dump_path"
  SUCCESS=1
else
  log "Postgres dump failed: $dump_path"
  echo "Postgres dump $DATABASE  failed at ${DATESTAMP} on `hostname` , please investigate" | mailx -s "Postgres dump failed" $MAIL
  report_failure
  exit 1
fi

# Backup to external place 
output="$($MC cp --quiet $dump_path $REMOTESTORE 2>&1)"
exitcode=$?

# Horrible hack to work around bug in mc or Catalyst Cloud
if [[ $exitcode -eq 1 ]] && [[ $output == *"Object does not exist"* ]]; then
  log "recovering from spurious object store error"
  exitcode=0
fi

if [ $exitcode == 0 ] ;then
  log "Postgres dump $DATABASE secured at objectstore $REMOTESTORE "
else
  log "Postgres dump $DATABASE failed at objectstore $REMOTESTORE "
  log "mc output: $output"

  echo "Postgres dump $DATABASE not secured at objectstore $REMOTESTORE , please investigate" | mailx -s "Postgres dump failed" $MAIL
  report_failure
  exit 1
fi

# Verify download is correct
local_sum="$(md5sum $dump_path | cut -f1 -d' ')"
echo $local_sum
remote_sum="$($MC --quiet cat $REMOTESTORE/$dump_file | md5sum | cut -f1 -d' ')"
echo $remote_sum

if [[ $local_sum != $remote_sum ]]; then
  log "Remote dump backup does not match local dump file"
  echo "Postgres dump $DATABASE not secured at objectstore ${REMOTESTORE}: verification failed. Please investigate" | mailx -s "Postgres dump failed" $MAIL
  report_failure
  exit 1
fi

# Cleaning up. Local just 1, remote just $DAYS
find $LOCALSTORE -name "*.pgdump" -mtime 1 -delete 
$MC find $REMOTESTORE -name "*.pgdump" --older-than ${DAYS}d --exec "$MC rm {}"

report_success
