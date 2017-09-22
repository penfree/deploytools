#!/bin/bash
# Set the openvpn client as router which forward packet from local LAN to VPN

if [[ `id -u` != 0 ]]; then
	echo Require root user >&2
	exit 1
fi

ADDR=$1

if [[ $ADDR == '' ]] ;then
	echo Require local network address, e.g. 192.168.1.0/24 >&2
	exit 1
fi

# Enable ip forward
echo 1 > /proc/sys/net/ipv4/ip_forward
# Add a routing rule which forward local LAN packet to VPN subnet and change the source ip to the client ip
# NOTE:
#	1. The ip/mask should be configured for each private network
#	2. The tap0 interface is the default openvpn client interface, it depends if multiple openvpn servers is connected 
/usr/sbin/iptables -t nat -A POSTROUTING -s $ADDR -o tap0 -j MASQUERADE
