#!/system/bin/sh
# CI-only, on disposable x86 guest. Reattach only owned relay filters.
set -eu
client="$1"
old_index="$2"
echo B113_CARRIER_REBIND_ARMED
i=0
while [ "$i" -lt 600 ];do
 i=$((i+1))
 index="$(cat /sys/class/net/wlan0/ifindex 2>/dev/null || true)"
 if [ -z "$index" ];then sleep .05;continue;fi
 if [ "$index" = "$old_index" ] && tc filter show dev wlan0 egress 2>/dev/null | grep -Fq 49152;then
  sleep .05;continue
 fi
 if ! tc qdisc show dev wlan0 | grep -Fq clsact;then
  if tc qdisc add dev wlan0 clsact;then echo B113_OWNED_NEW_CLSACT;else sleep .05;continue;fi
 fi
 tc filter del dev wbdrg0 ingress pref 49152 protocol ip 2>/dev/null || true
 if ! tc filter add dev wbdrg0 ingress protocol ip pref 49152 u32 match ip src 10.0.2.2/32 match ip dst "$client/32" match ip protocol 6 0xff match ip sport 443 0xffff action mirred ingress redirect dev wlan0;then
  sleep .05;continue
 fi
 if ! tc filter show dev wlan0 egress | grep -Fq 49152;then
  if ! tc filter add dev wlan0 egress protocol ip pref 49152 u32 match ip src "$client/32" match ip dst 10.0.2.2/32 match ip protocol 6 0xff match ip dport 443 0xffff action mirred egress redirect dev wbdrg0;then
   sleep .05;continue
  fi
 fi
 tc filter show dev wlan0 egress | grep -Fq 49152
 tc filter show dev wbdrg0 ingress | grep -Fq 49152
 echo "B113_CARRIER_REBOUND index=$index"
 exit 0
done
echo B113_CARRIER_REBIND_NOT_PROVEN
exit 1
