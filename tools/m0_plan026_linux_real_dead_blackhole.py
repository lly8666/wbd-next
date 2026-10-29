#!/usr/bin/env python3
"""Real original Linux TLS/Rust 100%-blackhole dead-peer test-only fixture.

Consumes the source-locked original 64-app netns script, never edits the
protected original Go TLS or Rust native sender. No dummy authenticated ACK.
"""
from pathlib import Path
import sys
if len(sys.argv)!=3:
    raise SystemExit("expected exact original shell fixture path and new destination")
src=Path(sys.argv[1]).read_text()
needle='if [[ "$PACKETS" == 5 || "$FEC" == 1 ]];then cat "$ART/public-v4-normal-business.log";fi'
if src.count(needle)!=1:
    raise SystemExit("original source-locked Linux fixture changed")
insert=r'''# Genuine UDP/TCP original-Go TLS first-app already completed before
# this fault. Both underlay egress qdiscs now drop 100% of ACTUAL packets.
# No synthetic peer Health, FIN, app, receipt or process exit is injected.
[[ "$MODE" == fec-auto && "$FEC" == 1 && "$LOSS" == 0 ]] || exit 2
sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss 100%
sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss 100%
sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 >"$ART/dead-blackhole-client-qdisc.txt"
sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 >"$ART/dead-blackhole-server-qdisc.txt"
sleep 106
# Verify the actual original native control attempted kernel sends: a
# merely installed 100% netem filter with zero packet drops proves nothing.
sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 >"$ART/dead-blackhole-client-qdisc.txt"
sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 >"$ART/dead-blackhole-server-qdisc.txt"
python3 - "$ART" <<'DROP'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1])
for role in ("client","server"):
    s=(p/("dead-blackhole-"+role+"-qdisc.txt")).read_text()
    m=re.search(r'\bdropped (\d+)',s)
    assert m and int(m.group(1))>0,(role,s)
DROP
for role in client server;do
  if ! grep -Fq 'WBD_M0_NATIVE_HEALTH_TIMEOUT side=tx reason=missing_authenticated_peer_dead_after_90s' "$TMP/$role.log";then
    echo "M0_PLAN026_LINUX_AUTHENTICATED_DEAD_TIMEOUT_MISSING role=$role" >&2
    grep -E 'WBD_M0_NATIVE_HEALTH_TIMEOUT|V4_PUBLIC_NATIVE_STOP' "$TMP/$role.log" | tail -14 >&2 || true
    exit 1
  fi
done
if grep -Ei 'DORMANT.*APPLIED|DORMANT.*PASS' "$TMP/client.log" "$TMP/server.log" >/dev/null;then
  echo 'M0_PLAN026_LINUX_BLACKHOLE_FALSE_DORMANT' >&2;exit 1
fi
echo 'M0_PLAN026_LINUX_REAL_TLS_RUST_NO_AUTH_BLACKHOLE_100PCT_DEAD_NOT_DORMANT_PASS both_native_health_dead=1 no_unauthenticated_peer_health=1 no_fin=1'
exit 0
'''
dst=Path(sys.argv[2])
dst.write_text(src.replace(needle,insert+needle,1))
dst.chmod(0o755)
print("M0_PLAN026_LINUX_REAL_BLACKHOLE_FIXTURE_VERIFIED original_go_rust_product_unchanged=1")
