#!/usr/bin/env python3
"""H1141: exact mature three-device original TLS/Rust business fixture,
with only Alice-D's user outer IPv4 intent changed to 1280B."""
from pathlib import Path
import sys
source=Path("tools/m0-plan028-two-client-real-linux-netns.sh").read_text()
def replace_once(a,b):
 global source
 if source.count(a)!=1:
  raise RuntimeError("frozen three-device source fixture changed: "+a[:115])
 source=source.replace(a,b,1)

replace_once('  local pidfile="$1"\n  sudo -n ip netns exec "$ns" bash -c "',
'''  local pidfile="$1" outer_arg=""
  if [[ "$port" == 44031 ]];then outer_arg="--outer-mtu 1280";fi
  sudo -n ip netns exec "$ns" bash -c "''')
replace_once("      --auto-ip --installation-id-file '$key' --mode normal\n", 
             "      --auto-ip --installation-id-file '$key' --mode normal $outer_arg\n")
probe=r'''
# REAL readback of every independent active original Rust TUN and
# the shared server TUN. Never write derived values as user configuration.
sudo -n ip -n "$NSA" -j link show dev wbdva4 >"$ART/plan028-h1141-a-inner.json"
sudo -n ip -n "$NSB" -j link show dev wbdvb4 >"$ART/plan028-h1141-b-inner.json"
sudo -n ip -n "$NSD" -j link show dev wbdvd4 >"$ART/plan028-h1141-d-inner.json"
sudo -n ip -n "$NSS" -j link show dev wbdvs4 >"$ART/plan028-h1141-server-inner.json"
python3 - "$TMP/A.log" "$TMP/B.log" "$TMP/D.log" "$ART/plan028-h1141-mixed-outer.json" "$ART" <<'PY_MIXED'
import json,pathlib,re,sys
logs=[pathlib.Path(p).read_text() for p in sys.argv[1:4]]
root=pathlib.Path(sys.argv[5])
def read(name):
 data=json.loads((root/("plan028-h1141-"+name+"-inner.json")).read_text())
 assert len(data)==1 and isinstance(data[0].get("mtu"),int),name
 return data[0]["mtu"]
outer=[]
for log in logs:
 matches=re.findall(r"V4_PUBLIC_MTU_PREPARE role=client mtu_budget_version=3 outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)",log)
 assert len(matches)==1,matches
 outer.append(list(map(int,matches[0])))
actual=[read("a"),read("b"),read("d")]
server=read("server")
assert [x[0] for x in outer]==[1460,1460,1280],outer
assert [x[2] for x in outer]==[1420,1420,1240],outer
assert actual==[1389,1389,1209],actual
assert [x[4] for x in outer]==actual,(outer,actual)
assert server==1389,server
receipt={"source":"original_Go_TLS_per_device_cold_MTU_and_real_Rust_OS_TUN",
  "user_outer_ipv4_intent":[1460,1460,1280],
  "client_real_syn_mss":[x[2] for x in outer],
  "client_inner_tun_os_mtu":actual,
  "server_shared_tun_os_mtu":server,
  "same_account_two_installations_different_outer":True,
  "server_port":443,"server_global_tun_not_lowered":True}
pathlib.Path(sys.argv[4]).write_text(json.dumps(receipt,indent=2)+"\n")
print("M0_PLAN028_H1141_MIXED_OUTER_USER_INTENT_THREE_ACTUAL_RUST_OS_TUN_PASS",flush=True)
PY_MIXED
'''
replace_once('await_client "$TMP/D.log" 3\nIPD="$(get_auto_ip "$TMP/D.log")"', 'await_client "$TMP/D.log" 3\n'+probe+'IPD="$(get_auto_ip "$TMP/D.log")"')
replace_once("echo 'M0_PLAN028_REAL_GO_TLS_TWO_ACCOUNTS_ONE_PORT_MULTIDEVICE_NATIVE_STOP_PASS'",
'''echo 'M0_PLAN028_REAL_GO_TLS_TWO_ACCOUNTS_ONE_PORT_MULTIDEVICE_NATIVE_STOP_PASS'
test -s "$ART/plan028-h1141-mixed-outer.json"
echo 'M0_PLAN028_H1141_X86_SAME_ACCOUNT_OTHER_DEVICE_CONTINUOUS_UDP_DIFFERENT_OUTER_INTENT_AND_STOP_PASS' ''')
out=Path(sys.argv[1]);out.write_text(source);out.chmod(0o700)
print("M0_PLAN028_H1141_SOURCE_FROZEN_MIXED_OUTER_FIXTURE_READY",flush=True)
