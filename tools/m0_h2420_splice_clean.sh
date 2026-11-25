#!/usr/bin/env bash
# H2420: no added WAN delay/loss, one order per independent three-runner Action.
set -euo pipefail
role=$1; NS=$2; TMP=$3; OUT=$4
ROOT="$GITHUB_WORKSPACE/linux-plan029-public-bundle"
TOOL="$GITHUB_WORKSPACE/tools/m0_h2228_three_runner_relay.py"
ORIGIN=h2417origin
ns(){ sudo -n ip netns exec "$NS" "$@"; }
origin(){ sudo -n ip netns exec "$ORIGIN" "$@"; }
if [[ "$role" == server ]];then
  sudo -n ip netns add "$ORIGIN"
  sudo -n ip link add h2417exit type veth peer name h2417app
  sudo -n ip link set h2417exit netns "$NS"
  sudo -n ip link set h2417app netns "$ORIGIN"
  ns ip addr add 198.18.77.1/24 dev h2417exit
  ns ip link set h2417exit up
  origin ip addr add 198.18.77.2/24 dev h2417app
  origin ip link set h2417app up
  origin ip link set lo up
  origin ip route add 10.66.0.0/24 via 198.18.77.1
  ns sysctl -qw net.ipv4.ip_forward=1
  origin sysctl -qw net.ipv4.tcp_congestion_control=bbr
  origin sysctl -qw 'net.ipv4.tcp_wmem=4096 65536 67108864'
  origin sysctl -qw 'net.ipv4.tcp_rmem=4096 87380 67108864'
  origin sysctl -qw net.core.rmem_max=67108864
  origin sysctl -qw net.core.wmem_max=67108864
  origin tc qdisc replace dev h2417app root fq maxrate 600mbit
  origin tc -s qdisc show dev h2417app >"$OUT/origin-fq.txt"
  getconf CLK_TCK >"$OUT/splice-clock-tick.txt"
  origin sysctl -n net.ipv4.tcp_congestion_control >"$OUT/origin-cc.txt"
  ns iptables -w -t mangle -I PREROUTING 1 -i wbds0 -p tcp -d 198.18.77.2 --dport 5300:5307 -j RETURN
  ns iptables -w -t nat -I POSTROUTING 1 -o h2417exit -s 10.66.0.0/24 -j MASQUERADE
  ns iptables -w -t mangle -S >"$OUT/splice-mangle.txt"
  ns ip rule show >"$OUT/splice-rules.txt"
  for port in 5300 5301 5400 5401;do
    sudo -n ip netns exec "$ORIGIN" bash -c 'echo "$$" > "$1";exec iperf3 -s -1 -B 198.18.77.2 -p "$2"' bash "$TMP/origin-$port.pid" "$port" >"$OUT/origin-$port.log" 2>&1 &
  done
  for i in $(seq 1 40);do
    if [[ $(origin ss -ltn |grep -Ec ':53[0-9][0-9] |:54[0-9][0-9] ' || true) == 4 ]];then break;fi
    sleep .2
  done
  origin ss -ltn >"$OUT/origin-listeners.txt"
  test "$(grep -Ec ':53[0-9][0-9] |:54[0-9][0-9] ' "$OUT/origin-listeners.txt")" = 4
  (
    while sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null;do
      date +%s.%N
      sudo -n cat "/proc/$(cat "$TMP/server.pid")/stat" || true
      echo HOST_CPU; cat /proc/stat | head -n 6; cat /proc/pressure/cpu || true
      echo SERVER_SOCKETS
      ns ss -tinm || true
      echo ORIGIN_SOCKETS
      origin ss -tinm || true
      sleep 1
    done
  ) >"$OUT/splice-socket-samples.txt" 2>&1 &
  echo $! >"$TMP/splice-sampler.pid"
  exit 0
fi
if [[ "$role" == cleanup ]];then
  test ! -s "$TMP/splice-sampler.pid" || kill "$(cat "$TMP/splice-sampler.pid")" 2>/dev/null || true
  for port in 5300 5301 5400 5401;do
    test ! -s "$TMP/origin-$port.pid" || sudo -n kill -TERM "$(cat "$TMP/origin-$port.pid")" 2>/dev/null || true
  done
  if test -s "$TMP/server.pid";then
    sudo -n kill -TERM "$(cat "$TMP/server.pid")" 2>/dev/null || true
    for i in $(seq 1 100);do sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null || break;sleep .1;done
  fi
  sudo -n ip netns del "$ORIGIN" || true
  exit 0
fi
test "$role" == client
# Capacity check before long loss measurements. The previous run was DERP-limited to 21 Mbps.
python3 - "$OUT" <<'PY'
import json,os,pathlib,sys
p=pathlib.Path(sys.argv[1]); clear={}
for direction in ("upload","download"):
 f=next(iter(p.glob(f"case-*-clear-zero-direct-12s-8p-{direction}.json")),None)
 clear[direction]=json.loads(f.read_text()).get("mbps") if f else None
q=json.loads((p/"clear-after-relay.json").read_text())
paths={k:q.get("tail_to_"+k,{}).get("tail_path") for k in ("client","server")}
qualified=isinstance(clear["download"],(float,int)) and clear["download"]>=800 and isinstance(clear["upload"],(float,int)) and clear["upload"]>=100 and set(paths.values())=={"DIRECT_CANDIDATE"}
d={"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"direct_capacity_mbps":clear,"tail_paths":paths,"qualified_for_diagnostic":qualified,"absolute_800mbps_capacity":all(isinstance(v,(float,int)) and v>=800 for v in clear.values()) and qualified}
(p/"splice-preflight.json").write_text(json.dumps(d,indent=2)+"\n")
if not qualified:
 d.update(status="INFRA_CAPACITY_UNQUALIFIED",rows=[],real_three_runner_l3_relay=True,all_three_distinct_native_machines=True,actual_kernel_forwarding=True,streams=1)
 (p/"summary.json").write_text(json.dumps(d,indent=2)+"\n")
PY
if test -f "$OUT/summary.json";then echo H2418_INFRA_CAPACITY_UNQUALIFIED;exit 0;fi
sudo -n ip netns exec "$NS" bash -c 'echo "$$" > "$1";shift;exec "$@"' bash "$TMP/client.pid" \
  env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-client" \
  --raw-interface wan0 --local-ip 10.248.81.2 --local-port 44100 --peer-ip 10.248.82.2 --peer-port 443 \
  --tun-name wbdc0 --server-name wbd-h2228.example.test --route-key-hex-file "$TMP/route-key.hex" \
  --username bench0 --password H2228-ONLY-PASS --auto-ip --installation-id-file "$TMP/install-splice" \
  --mode normal --outer-repair on --outer-mtu 1160 >"$OUT/splice-client.log" 2>&1 &
for i in $(seq 1 200);do
  if grep -Fq 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/splice-client.log";then break;fi
  sleep .25
done
grep -Fq 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/splice-client.log"
ns ip route replace 198.18.77.2/32 dev wbdc0
ns ip route get 198.18.77.2 >"$OUT/splice-target-route.txt"
grep -q 'dev wbdc0' "$OUT/splice-target-route.txt"
case "$WBD_H2420_ORDER" in ABBA|BAAB);;*)exit 2;;esac
a=5300;b=5400
for i in 0 1 2 3;do
  leg="${WBD_H2420_ORDER:i:1}"
  label="splice-clean-$i-$leg"
  case "$leg" in A)port=$a;a=$((a+1));;B)port=$b;b=$((b+1));;esac
  python3 "$TOOL" remote h2228-peer/relay.json impair "$OUT/$label-shaping.json" --loss 0 --delay 0 --model iid
  sleep 1
  WBD_H2417_TARGET_PORT="$port" python3 "$TOOL" iperf wbd 30 1 download "$OUT/$label.json" --pidfile "$TMP/client.pid" || true
  python3 "$TOOL" remote h2228-peer/relay.json snapshot "$OUT/$label-relay.json"
done
python3 "$TOOL" remote h2228-peer/relay.json impair "$OUT/splice-final-clear.json" --loss 0 --delay 0 --model iid
sudo -n kill -TERM "$(cat "$TMP/client.pid")" 2>/dev/null || true
for i in $(seq 1 100);do sudo -n kill -0 "$(cat "$TMP/client.pid")" 2>/dev/null || break;sleep .1;done
python3 "$TOOL" iperf direct 12 8 upload "$OUT/post-direct-upload.json" || true
python3 "$TOOL" iperf direct 12 8 download "$OUT/post-direct-download.json" || true
python3 "$TOOL" remote h2228-peer/relay.json snapshot "$OUT/post-direct-relay.json"
python3 - "$OUT" <<'PY'
import json,os,pathlib,sys,statistics
out=pathlib.Path(sys.argv[1])
rows=[]
order=os.environ["WBD_H2420_ORDER"]
for i,leg in enumerate(order):
 p=out/f'splice-clean-{i}-{leg}.json'
 row=json.loads(p.read_text()) if p.exists() else {'status':'MISSING','mbps':None}
 rows.append({'index':i,'leg':leg,**row})
pre=json.loads((out/'splice-preflight.json').read_text())
post={direction:json.loads((out/f'post-direct-{direction}.json').read_text()).get('mbps') for direction in ('upload','download')}
complete=all(r.get('status')=='PASS_REAL_KERNEL_IPERF3_TCP' for r in rows)
post_ok=isinstance(post['download'],(float,int)) and post['download']>=800 and isinstance(post['upload'],(float,int)) and post['upload']>=100
d={'source_sha':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],
 'real_three_runner_l3_relay':True,'all_three_distinct_native_machines':True,
 'actual_kernel_forwarding':True,'status':'MEASURED_ALL' if complete and post_ok else 'MEASURED_WITH_INCOMPLETE_OR_POST_CAPACITY',
 'mode':'normal/off','outer_repair':'on','outer_mtu':1160,'loss_model':'iid','loss_pct':0,
 'added_rtt_ms':0,'jitter_ms':0,'seconds':30,'omit_seconds':8,'streams':1,
 'order':order,'direct_capacity_mbps':pre['direct_capacity_mbps'],'post_direct_capacity_mbps':post,'preflight':pre,'rows':rows,
 'scope':'Linux x86 client/server, ARM relay; independent origin namespace, existing fq600, no Windows or physical WAN qualification'}
if complete:
 a=[x['mbps'] for x in rows if x['leg']=='A'];b=[x['mbps'] for x in rows if x['leg']=='B']
 d.update(a_mean_mbps=statistics.mean(a),b_mean_mbps=statistics.mean(b),b_over_a_pct=100*(statistics.mean(b)/statistics.mean(a)-1),a_spread_pct=100*abs(a[1]-a[0])/statistics.mean(a),b_spread_pct=100*abs(b[1]-b[0])/statistics.mean(b))
(out/'summary.json').write_text(json.dumps(d,indent=2)+'\n')
PY
