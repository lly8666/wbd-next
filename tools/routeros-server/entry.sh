#!/bin/sh
# CHR lab only. No protocol changes or packet-path wrapper.
set -eu
cd /opt/wbd
echo WBD_ROS_CONTAINER_PREFLIGHT
uname -a
ip -br addr
ip -4 route
# ROS may hide proc sysctls. Readback is diagnostic; actual kernel operations
# and end-to-end forwarded bytes determine qualification.
ls -ld /proc /proc/sys /proc/sys/net /proc/sys/net/ipv4 /dev/net/tun 2>&1 || :
if [ -r /proc/sys/net/ipv4/tcp_available_congestion_control ]; then
  cat /proc/sys/net/ipv4/tcp_available_congestion_control
else
  echo WBD_ROS_CC_PROC_UNAVAILABLE
fi
dev=$(ip -o -4 addr show | awk '$4=="10.248.82.2/24"{sub(/@.*/, "", $2); print $2}')
test -n "$dev"
echo "WBD_ROS_UNDERLAY=$dev"
./cap-probe
if [ -r /proc/sys/net/ipv4/ip_forward ]; then
  if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != 1 ]; then
    sysctl -w net.ipv4.ip_forward=1 || echo WBD_ROS_IP_FORWARD_WRITE_FAILED
  fi
  echo "WBD_ROS_IP_FORWARD=$(cat /proc/sys/net/ipv4/ip_forward)"
else
  echo WBD_ROS_IP_FORWARD_PROC_UNAVAILABLE
fi
if ! ip tuntap add dev wbprobe mode tun; then
  echo WBD_ROS_TUN_UNAVAILABLE
  exit 2
fi
ip link set wbprobe up
echo WBD_ROS_TUN_AVAILABLE
fq=600
if tc qdisc replace dev wbprobe root fq maxrate 600mbit flow_limit 256; then
  tc -d qdisc show dev wbprobe
  echo WBD_ROS_FQ_AVAILABLE
else
  fq=0
  echo WBD_ROS_FQ_UNAVAILABLE_EXPLICIT_0
fi
# Exercise the exact NAT extensions used by the original CLI; choose a working
# iptables userspace backend, without changing rule semantics.
natprobe() {
  "$1" -w 3 -t nat -A POSTROUTING -s 10.66.0.0/24 -o "$dev" -m comment --comment wbd-ros-probe -j MASQUERADE &&
  "$1" -w 3 -t nat -D POSTROUTING -s 10.66.0.0/24 -o "$dev" -m comment --comment wbd-ros-probe -j MASQUERADE
}
if natprobe iptables; then
  iptables --version
elif natprobe iptables-legacy; then
  update-alternatives --set iptables /usr/sbin/iptables-legacy
  iptables --version
else
  echo WBD_ROS_MASQUERADE_UNAVAILABLE
  exit 2
fi
echo WBD_ROS_MASQUERADE_AVAILABLE
# The tested nft path lacks TPROXY. One isolated legacy control tests whether
# the old xtables backend exposes it; the REDIRECT candidate uses nft NAT.
if [ "$WBD_INGRESS" = legacy-tproxy ]; then
  update-alternatives --set iptables /usr/sbin/iptables-legacy
  iptables --version
fi
if iptables -w 3 -t mangle -A PREROUTING -i wbprobe -p tcp -m addrtype ! --dst-type LOCAL -j TPROXY --on-port 46180 --on-ip 127.0.0.1 --tproxy-mark 0x5742b464/0xffffffff; then
  iptables -w 3 -t mangle -D PREROUTING -i wbprobe -p tcp -m addrtype ! --dst-type LOCAL -j TPROXY --on-port 46180 --on-ip 127.0.0.1 --tproxy-mark 0x5742b464/0xffffffff
  echo WBD_ROS_TPROXY_AVAILABLE
else
  echo WBD_ROS_TPROXY_UNAVAILABLE
fi
ip link del wbprobe
# Existing original native lab semantics: the host TCP stack must not reset the
# raw carrier's port. Only this container and only the WBD port.
if ! iptables -w 3 -A OUTPUT -o "$dev" -p tcp --sport 443 --tcp-flags RST RST -j DROP; then
  echo WBD_ROS_RST_RULE_UNAVAILABLE
  exit 2
fi
echo WBD_ROS_RST_RULE_APPLIED
set -- --raw-interface "$dev" --local-ip 10.248.82.2 --local-port 443 --tun-name wbds0 --tun-ipv4 10.66.0.1/24 --server-name wbd-h2228.example.test --route-key-hex-file fixture/route-key.hex --users-file fixture/users.json --lease-pool 10.66.0.128/25 --tls-cert fixture/cert.pem --tls-key fixture/key.pem --outer-mtu 1460 --mode shared --outer-repair on --tun-fq-maxrate-mbps "$fq"
if [ -n "$WBD_CC" ]; then
  set -- "$@" --tcp-proxy-cc "$WBD_CC" --tcp-proxy-port 46180
  if [ "$WBD_INGRESS" = redirect ]; then set -- "$@" --tcp-proxy-ingress redirect; fi
fi
if [ -z "$WBD_BBR_PROXY_CC" ]; then exec ./wbd-v4-server "$@"; fi
# Experimental separate TCP endpoint. Original WBD TUN remains singly owned.
./wbd-v4-server "$@" &
wbd_pid=$!
proxy_pid=
routed=0
cleanup_proxy() {
  trap - EXIT
  if [ "$routed" = 1 ]; then
    iptables -w 3 -t mangle -D PREROUTING -i wbds0 -p tcp -m addrtype ! --dst-type LOCAL -j MARK --set-mark 0x5742b001
    ip rule del pref 14680 iif wbds0 fwmark 0x5742b001 lookup 14680
    ip route del default dev bbrtun table 14680
  fi
  if [ -n "$proxy_pid" ]; then kill -TERM "$proxy_pid" 2>/dev/null || :; wait "$proxy_pid" || :; fi
  kill -TERM "$wbd_pid" 2>/dev/null || :
  wait "$wbd_pid"
}
trap cleanup_proxy EXIT
trap 'exit 0' TERM INT
for i in $(seq 1 100); do
  if ip link show wbds0 >/dev/null 2>&1; then break; fi
  kill -0 "$wbd_pid"
  sleep .1
done
ip tuntap add dev bbrtun mode tun
ip addr add 10.249.90.1/30 dev bbrtun
ip link set bbrtun mtu 1500 up
./proxy/wbd-bbr-proxy "$WBD_BBR_PROXY_CC" &
proxy_pid=$!
ip route add default dev bbrtun table 14680
ip rule add pref 14680 iif wbds0 fwmark 0x5742b001 lookup 14680
iptables -w 3 -t mangle -A PREROUTING -i wbds0 -p tcp -m addrtype ! --dst-type LOCAL -j MARK --set-mark 0x5742b001
routed=1
echo "WBD_BBR_PROXY_ROUTED cc=$WBD_BBR_PROXY_CC"
wait "$wbd_pid"
