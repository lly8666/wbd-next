#!/usr/bin/env python3
"""PLAN028 H1144: one original TLS 443 server with real per-device Normal
off/auto/fixed Rust owners. Only changes a frozen native test shell copy."""
from pathlib import Path
import sys
out=Path(sys.argv[1])
src=Path("tools/m0-plan028-two-client-real-linux-netns.sh").read_text()
def replace(a,b):
 global src
 if src.count(a)!=1:raise RuntimeError("frozen original 3-device native test changed "+a[:95])
 src=src.replace(a,b,1)

replace('  local pidfile="$1"\n  sudo -n ip netns exec "$ns" bash -c "',
'''  local pidfile="$1" fec_mode=normal outer_arg=''
  case "$port" in
    42031) fec_mode=fec-auto ;;
    44031) fec_mode=fec-fixed;outer_arg='--outer-mtu 1280' ;;
  esac
  sudo -n ip netns exec "$ns" bash -c "''')
replace("      --auto-ip --installation-id-file '$key' --mode normal\n",
        "      --auto-ip --installation-id-file '$key' --mode '$fec_mode' $outer_arg\n")
probe=r'''
# Snapshot genuine, independently applied client native TUN OS MTUs while
# all 3 authenticated originals and the shared server TUN are still live.
for row in "$NSA wbdva4 A" "$NSB wbdvb4 B" "$NSD wbdvd4 D" "$NSS wbdvs4 server";do
  read -r n t role <<<"$row"
  sudo -n ip -n "$n" -j link show dev "$t" >"$ART/plan028-h1144-$role-inner.json"
done
python3 - "$TMP/A.log" "$TMP/B.log" "$TMP/D.log" "$ART" <<'PY_PER_DEVICE'
import json,pathlib,re,sys
root=pathlib.Path(sys.argv[4])
rows=[]
for label,logfile in zip(("A","B","D"),sys.argv[1:4]):
    t=pathlib.Path(logfile).read_text()
    matches=re.findall(r"V4_PUBLIC_MTU_PREPARE role=client mtu_budget_version=3 outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)",t)
    assert len(matches)==1,(label,matches)
    outer,physical,mss,record,planned=map(int,matches[0])
    osrows=json.loads((root/f"plan028-h1144-{label}-inner.json").read_text())
    assert len(osrows)==1 and osrows[0]["mtu"]==planned,(label,osrows,planned)
    rows.append({"client":label,"outer_intent":outer,"actual_syn_mss":mss,
      "real_os_tun_inner":osrows[0]["mtu"],"record_offer":record,
      "real_original_tls_readback":True})
server=json.loads((root/"plan028-h1144-server-inner.json").read_text())
assert [r["outer_intent"] for r in rows]==[1460,1460,1280]
assert rows[0]["real_os_tun_inner"]==1389
assert 900<=rows[1]["real_os_tun_inner"]<1389
assert 900<=rows[2]["real_os_tun_inner"]<=1209
assert len(server)==1 and server[0]["mtu"]==1389
(root/"plan028-h1144-mixed-fec-os.json").write_text(json.dumps({
 "real_client_config":rows,"shared_server_tun_inner":1389,
 "source":"original_authenticated_TLS_and_OS_readback","per_client_fec_policy":True},indent=2)+"\n")
print("M0_PLAN028_H1144_THREE_ORIGINAL_OS_TUN_EFFECTIVE_MODES_BEFORE_BUSINESS_PASS",flush=True)
PY_PER_DEVICE
'''
replace('await_client "$TMP/D.log" 3\nIPD="$(get_auto_ip "$TMP/D.log")"',
        'await_client "$TMP/D.log" 3\n'+probe+'IPD="$(get_auto_ip "$TMP/D.log")"')
end=r'''
python3 - "$TMP/server.log" "$TMP/B.log" "$TMP/D.log" "$ART/plan028-h1144-mixed-fec-os.json" <<'PY_MODES'
import json,pathlib,re,sys
server=pathlib.Path(sys.argv[1]).read_text()
bob=pathlib.Path(sys.argv[2]).read_text()
alice_d=pathlib.Path(sys.argv[3]).read_text()
matches=re.findall(r"V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=(off|fixed|auto) profile=(\d+) cipher=(\d+) authenticated_TLS=1 original_Rust_M4=1",server)
assert [r[0] for r in matches]==["off","auto","fixed","off"],matches
assert all(int(row[2])==1 for row in matches)
assert "V4_PUBLIC_GO_RX_HANDOFF role=client mode=auto" in bob
assert "V4_PUBLIC_GO_RX_HANDOFF role=client mode=fixed" in alice_d
assert server.count("V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443")==4
assert server.count("V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation")==1
assert server.count("V4_PUBLIC_M2_OUTER role=server")==4
p=pathlib.Path(sys.argv[4])
result=json.loads(p.read_text())
result["original_server_protected_rust_modes"]=[row[0] for row in matches]
result["one_server_port_443"]=True
result["sequential_A_to_AB_to_B_and_siblings_70_udp"]=True
p.write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1144_ONE_443_PER_CLIENT_OFF_AUTO_FIXED_PROTECTED_RUST_70_UDP_STOP_PASS",flush=True)
PY_MODES
'''
replace("echo 'M0_PLAN028_REAL_GO_TLS_TWO_ACCOUNTS_ONE_PORT_MULTIDEVICE_NATIVE_STOP_PASS'",
        "echo 'M0_PLAN028_REAL_GO_TLS_TWO_ACCOUNTS_ONE_PORT_MULTIDEVICE_NATIVE_STOP_PASS'\n"+end)
out.write_text(src)
out.chmod(0o700)
print("M0_PLAN028_H1144_ORIGINAL_MULTI_CLIENT_MIXED_NORMAL_FEC_NATIVE_FIXTURE_READY")
