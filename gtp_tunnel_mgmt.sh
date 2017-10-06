#!/bin/bash
## Author: Bjoern Riemer
#set -x


#args: add gtp1 v1 1361413701 33563160 192.168.3.120 192.168.4.94
#      1   2    3  4          5        6             7

# $ gtp-tunnel list
#version 1 tei 1360997700/33561368 ms_addr 192.168.3.121 sgsn_addr 192.168.4.94
#version 1 tei 1360997697/33560600 ms_addr 192.168.3.120 sgsn_addr 192.168.4.94
#1       2 3   4                   5       6             7         8

## exec cmd: gtp_tunnel_mgmt.sh add gtp1 v1 2746449698 33554968 192.168.3.33 192.168.41.71
##                              1   2    3  4          5        6            7
function usage_exit() {
	echo "usage: $0 add gtp1 v1 1361413701 33563160 192.168.3.120 192.168.4.94"
	echo "usage: $0 del gtp1 v1 1361413701"
	exit 0

}

GTPVER=$3
ULID=$4
DLID=$5
UE_IP=$6
ENB_IP=$7
GTP_IF=$2
ADDDEL=$1

case $ADDDEL in
  add)
	[ $# -ne 7 ] && usage_exit	
	OLD_ID=$(gtp-tunnel list |awk "/$UE_IP/"'{split($4,ids,"/"); print ids[1]}')
	[ -z $OLD_ID ] || echo gtp-tunnel del $GTP_IF $GTPVER $OLD_ID
	[ -z $OLD_ID ] || $ECHO gtp-tunnel del $GTP_IF $GTPVER $OLD_ID
	echo gtp-tunnel add $GTP_IF $GTPVER $ULID $DLID $UE_IP $ENB_IP
	gtp-tunnel add $GTP_IF $GTPVER $ULID $DLID $UE_IP $ENB_IP
	;;
  del)
	[ $# -ne 4 ] && usage_exit	
	echo gtp-tunnel del $GTP_IF $GTPVER $ULID
	gtp-tunnel del $GTP_IF $GTPVER $ULID
	;;
  list)
	echo gtp-tunnel list
	gtp-tunnel list
	;;
  *)
	usage_exit
	;;
esac



