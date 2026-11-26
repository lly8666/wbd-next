#!/bin/sh
set -eu
cd /opt/lab
uname -a
./kernel-probe
if [ "$BBR_LAB_CC" = kernel ]; then exit 0; fi
ip tuntap add dev bbrtest mode tun
ip addr add 10.249.90.1/24 dev bbrtest
ip link set bbrtest up
# CHR already showed forwarding=1; this is an ordinary routed TUN.
cat /proc/sys/net/ipv4/ip_forward
exec ./bin/wbd-bbr-lab
