#!/usr/bin/env bash
# Actual systemd on the native CI host, isolated veth, no physical deployment.
set -euo pipefail
PKG="$(realpath "$1")"
T="$(mktemp -d)"
original_forward="$(cat /proc/sys/net/ipv4/ip_forward)"
cleanup(){
 code=$?
 set +e
 if ((code));then sudo journalctl -u wbd-next.service -n 80 --no-pager >&2;fi
 if [[ -x /usr/local/bin/wbd-next ]];then sudo /usr/local/bin/wbd-next uninstall --yes || true;fi
 sudo ip link del wbd030srv 2>/dev/null || true
 rm -rf "$T"
}
trap cleanup EXIT
test "$(ps -p 1 -o comm=)" = systemd
test ! -e /etc/wbd-next/server.json
sudo ip link add wbd030srv type veth peer name wbd030peer
sudo ip addr add 198.18.30.1/24 dev wbd030srv
sudo ip addr add 198.18.30.2/24 dev wbd030peer
sudo ip link set wbd030srv up
sudo ip link set wbd030peer up
cat >"$T/config.json" <<'JSON'
{"listen":"198.18.30.1:443","server-name":"wbd.example.test","raw-interface":"wbd030srv","tun-name":"wbd030tun","public-address":"example.test","users":[{"username":"alice","password":"fixture-only-plan030"}]}
JSON
chmod 0600 "$T/config.json"
"$PKG/wbd-next" --help
sudo "$PKG/wbd-next" install --config "$T/config.json"
sudo systemctl is-active --quiet wbd-next.service
sudo systemctl is-enabled --quiet wbd-next.service
sudo wbd-next status --json >"$T/status.json"
sudo wbd-next clients --json >"$T/clients.json"
python3 - "$T" <<'PY'
import pathlib,json,sys
p=pathlib.Path(sys.argv[1]);s=json.loads((p/"status.json").read_text());c=json.loads((p/"clients.json").read_text())
assert s["native_ready"] and s["disk_revision"]==s["running_revision"] and s["online_devices"]==0,s
assert len(s["source_sha"])==40 and s["dormant_devices"] is None,s
assert c["state"]=="ready" and c["tun_os_mtu"]>0 and c["clients"]==[],c
PY
sudo wbd-next config check
sudo wbd-next disable
! sudo systemctl is-enabled --quiet wbd-next.service
sudo systemctl is-active --quiet wbd-next.service
sudo wbd-next enable
sudo systemctl is-enabled --quiet wbd-next.service
sudo wbd-next config export alice --output "$T/connection.json"
sudo python3 - "$T/connection.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["address"]=="example.test" and d["username"]=="alice" and len(d["route-key-hex"])==64
assert d["tls-verify-server"] is True and "BEGIN CERTIFICATE" in d["tls-ca-pem-content"]
PY
sudo sha256sum /var/lib/wbd-next/{route-key.hex,server.crt,server.key} >"$T/material.sha"
sudo wbd-next stop
sudo systemctl is-enabled --quiet wbd-next.service
! sudo ip link show wbd030tun
test "$(cat /proc/sys/net/ipv4/ip_forward)" = "$original_forward"
! sudo iptables-save | grep -E 'wbd-next-managed|wbd-v4-'
sudo wbd-next start
sudo wbd-next restart
sudo wbd-next status --json >"$T/after-restart.json"
python3 - "$T/config.json" "$T/changed.json" "$T/invalid.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["listen"]="198.18.30.1:444"
json.dump(d,open(sys.argv[2],"w"))
d["listen"]="198.18.30.1:99999"
json.dump(d,open(sys.argv[3],"w"))
PY
sudo wbd-next config --file "$T/changed.json"
sudo wbd-next status --json >"$T/changed-status.json"
python3 - "$T/changed-status.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]));assert s["disk_revision"]!=s["running_revision"]
PY
if sudo wbd-next config --file "$T/invalid.json";then echo invalid config accepted;exit 1;fi
sudo wbd-next config check
sudo wbd-next restart
sudo wbd-next clients --json >"$T/new-listen.json"
python3 - "$T/new-listen.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]));assert s["listen"]=="198.18.30.1:444",s
PY
sudo "$PKG/wbd-next" install --config "$T/config.json"
sudo sha256sum -c "$T/material.sha"
sudo wbd-next clients --json >"$T/reinstall-listen.json"
cmp "$T/new-listen.json" "$T/reinstall-listen.json"
sudo wbd-next uninstall --yes
for p in /opt/wbd-next /etc/wbd-next /var/lib/wbd-next /run/wbd-next /usr/local/bin/wbd-next /etc/systemd/system/wbd-next.service;do test ! -e "$p";done
test "$(cat /proc/sys/net/ipv4/ip_forward)" = "$original_forward"
! sudo iptables-save | grep -E 'wbd-next-managed|wbd-v4-'
sudo "$PKG/wbd-next" install --config "$T/config.json"
sudo wbd-next status --json >"$T/fresh-status.json"
sudo wbd-next uninstall --yes
echo "PLAN030_NATIVE_SYSTEMD_INSTALL_READY_CONFIG_STOP_REINSTALL_UNINSTALL_PASS"
