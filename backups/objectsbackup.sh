#!/bin/bash
# This script is used on prod-api
# It makes an incremental backup (by mirroring) the local objectstore to a external objectstore.
# Logfiles are produced and kept 30 days.
# Monitoring is done in Grafana, by means of updating the influxdb directly.
# CopyLeft Huub, March 2019
#set -xv

MC=/usr/local/bin/mc
LOCALSTORE=cac/fullnoise01
REMOTESTORE=cat-nz-por-1/cacophony-backup/fullnoise01
DAYS=30
LOGFILE=/var/log/mc-mirror.log-`date +%F`
ERRORLOG=/var/log/mc-mirror-error.log-`date +%F`
MAIL="coredev@cacophony.org.nz"
CURL=/usr/bin/curl
HOST=$(grep " hostname =" /etc/telegraf/telegraf.conf |cut -d"\"" -f2)
INFLUX='http://10.0.0.3:8086'
INFLUXDB=server_metrics
# failure: 0, success: 1
SUCCESS=0


# Backup to external place
echo "##############  Started mirror at `date`  ########" >> $LOGFILE
echo "##############  Started mirror at `date`  ########" >> $ERRORLOG

$MC mirror --quiet $LOCALSTORE $REMOTESTORE >> $LOGFILE 2>> $ERRORLOG

echo "##############  Ended mirror at `date`  ########" >> $LOGFILE

# Inform influxdb and grafana
DATA=`grep Total $LOGFILE  |tail -1| cut -d" " -f2`
# We count data in bytes, division by 1 do get an integer
grep KB, $LOGFILE && DATA=`echo " $DATA * 1000 /1 "|bc`
grep MB, $LOGFILE && DATA=`echo " $DATA * 1000000 /1 "|bc`
grep GB, $LOGFILE && DATA=`echo " $DATA * 1000000000 /1"|bc`
TOTFILES=`wc -l < $LOGFILE`
FAILFILES=`grep 'Failed to copy' $ERRORLOG|wc -l`
ERRORS=`wc -l < $ERRORLOG`
# Get rid of the header and 'failed to copy'
ERRORS=`echo "$ERRORS" - 1 - $FAILFILES|bc`
[[ $ERRORS -eq 0 ]] && SUCCESS=1

# Write to monitoring-database
$CURL -i -XPOST "$INFLUX/write?db=$INFLUXDB" --data-binary "backup,objectstore=$REMOTESTORE,host=$HOST success=$SUCCESS,data=$DATA,totfiles=$TOTFILES,failfiles=$FAILFILES"

# Mailing if there is an error
if [[ "$SUCCESS" == "0" ]] ; then
  echo "There is problem with the objectstore backup at $HOST, please investigate" | mailx -s "Backup objectstore failed at $HOST" -A $ERRORLOG $MAIL
fi

# Cleaning
find /var/log/ -mtime +$DAYS -name "mc-mirror*" -delete

