#!/usr/bin/env python3
"""Source-controlled TEST-ONLY Linux original GameFEC scenario overlay.

Patch the previously source-verified actual Linux kernel product E2E script
inside this one CI run, never a product binary, TLS handoff or cipher.
Fail closed on any fixture drift. The two live original Go binaries and
Rust .so are frozen and hash-checked independently by Actions.
"""
import pathlib
import sys

assert len(sys.argv) == 3
origin = pathlib.Path(sys.argv[1])
dest = pathlib.Path(sys.argv[2])
assert origin.is_file() and dest != origin and not dest.exists()
s = origin.read_text()
def sub(before, after, count=1):
    global s
    observed = s.count(before)
    assert observed == count, (before[:70], observed, count)
    s = s.replace(before, after)

sub("  normal|fec-fixed|fec-auto|game2|game4) ;;",
    "  normal|fec-fixed|fec-auto|game2|game4|game2-fec) ;;")
sub("FEC=0 GAME=0", "FEC=0 GAME=0 GAME_FEC=0")
sub("  game2) GAME=2 ;;", "  game2) GAME=2 ;;\n  game2-fec) GAME=2 GAME_FEC=1 ;;")
sub('if [[ "$LOSS" != 0 && "$LOSS" != 1 ]];then',
    'if [[ "$LOSS" != 0 && "$LOSS" != 1 && ! ( "$GAME_FEC" == 1 && "$LOSS" == 15 ) ]];then')
sub('if [[ "$LOSS" == 1 ]];then PACKETS=512;fi',
    'if [[ "$LOSS" == 1 ]];then PACKETS=512;fi\n'
    'if [[ "$GAME_FEC" == 1 ]];then PACKETS=64;fi\n'
    'CLI_MODE="$MODE"; GAME_FEC_WIRE=off\n'
    'if [[ "$GAME_FEC" == 1 ]];then CLI_MODE=game2; GAME_FEC_WIRE=fixed6;fi')
sub('--mode "$MODE" --fec-profile 1" >',
    '--mode "$CLI_MODE" --fec-profile 1 --game-fec "$GAME_FEC_WIRE"" >',2)
sub('if [[ "$LOSS" == 1 ]];then\n'
    '  sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss 1%\n'
    '  sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss 1%\nfi',
    'if [[ "$LOSS" == 1 || "$LOSS" == 15 ]];then\n'
    '  sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss "$LOSS"%\n'
    '  sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss "$LOSS"%\nfi')
sub('if [[ "$GAME" != 0 ]];then\n'
    '  # After true Go TLS and Rust M4 device readiness',
    'if [[ "$GAME" != 0 && "$GAME_FEC" == 0 ]];then\n'
    '  # After true Go TLS and Rust M4 device readiness')
sub('loss=os.environ.get("WBD_REAL_LOSS")=="1"',
    'loss=os.environ.get("WBD_REAL_LOSS")!="0"')
sub('if [[ "$PACKETS" == 5 || "$FEC" == 1 ]];then',
    'if [[ "$PACKETS" == 5 || "$FEC" == 1 || "$GAME_FEC" == 1 ]];then')
sub('if [[ "$GAME" != 0 ]];then\n'
    '  echo "M0_GAME_PUBLIC_ORIGINAL_GO_M4_FIRST_APP_WITH_LANE1_DAMAGE_PASS',
    'if [[ "$GAME" != 0 && "$GAME_FEC" == 0 ]];then\n'
    '  echo "M0_GAME_PUBLIC_ORIGINAL_GO_M4_FIRST_APP_WITH_LANE1_DAMAGE_PASS')
sub('  test "$(grep -c '
    "'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK'"
    ' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"\n'
    '  for role in client server;do',
    '''  if [[ "$GAME_FEC" == 1 ]];then
    grep -Eq '^M0_V4_PUBLIC_REAL_NETEM_APP_ACCOUNTING offered=64 first_unique_delivered=[1-9][0-9]* missing=[0-9]+$' "$ART/public-v4-normal-business.log"
    for role in client server;do
      grep -q "V4_PUBLIC_GAME_FEC_APPLIED role=$role lanes=2 mode=fixed profile=6" "$TMP/$role.log"
      grep -q "V4_PUBLIC_GAME_FEC_COUNTERS role=$role lanes=2" "$TMP/$role.log"
    done
    python3 - "$TMP" <<'PYFEC'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1])
for role in ("client","server"):
    content=(p/(role+".log")).read_text()
    rows=re.findall(r"V4_PUBLIC_GAME_FEC_COUNTERS role="+role+
                    r" lanes=2 source_offered=(\\d+) parity_offered=(\\d+) parity_copied=(\\d+)",content)
    assert rows,("no genuine FEC counter",role)
    first,offered,copied=map(int,rows[-1])
    assert first>0 and offered>0 and copied>0,(role,rows[-1])
    print(f"H650_TRUE_GAME_FEC_NATIVE_PARITY role={role} source={first} parity_offered={offered} copied={copied}",flush=True)
PYFEC
  else
    test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"
  fi
  for role in client server;do''')
sub('elif [[ "$GAME" != 0 ]];then\n'
    '  echo "M0_PUBLIC_ORIGINAL_GO_V4_GAME_REAL_TLS_M4_DAMAGED_LANE_NO_HOL_STOP_PASS',
    '''elif [[ "$GAME_FEC" == 1 ]];then
  sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 >"$ART/h650-real-client-tc.txt"
  sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 >"$ART/h650-real-server-tc.txt"
  python3 - "$ART" <<'PYNETEM'
import pathlib,re,sys
root=pathlib.Path(sys.argv[1])
for role in ("client","server"):
    text=(root/("h650-real-"+role+"-tc.txt")).read_text()
    assert "netem" in text
    drops=re.findall(r"dropped (\\d+)",text)
    assert drops and any(int(x)>0 for x in drops),(role,text[-400:])
    print("H650_REAL_KERNEL_15PCT_DROPS role="+role+" drop="+str(sum(map(int,drops))),flush=True)
PYNETEM
  echo "M0_PLAN027_LINUX_ORIGINAL_GAME2_FIXED6_15PCT_REAL_TLS_FEC_KERNEL_UDP_STOP_PASS windows_NOT_RUN=1 real_parity=1 true_kernel=1 source64=1"
elif [[ "$GAME" != 0 ]];then
  echo "M0_PUBLIC_ORIGINAL_GO_V4_GAME_REAL_TLS_M4_DAMAGED_LANE_NO_HOL_STOP_PASS''')
dest.write_text(s)
dest.chmod(0o755)
print("H650_SOURCE_CONTROLLED_ORIGINAL_LINUX_PRODUCT_NATIVE_FEC_SCENE_STAGED_NOT_PASS")
