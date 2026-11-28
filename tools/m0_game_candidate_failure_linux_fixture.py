#!/usr/bin/env python3
"""Fault one scheduled SYN on each live client, then allow the next timer."""
from pathlib import Path
import sys
out=Path(sys.argv[1]); scene=sys.argv[2]
assert scene in ("normal","fixed","auto")
s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
def sub(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a))
    s=s.replace(a,b)
extra=" --rotation-interval 30s --rotation-jitter 0s"
sub("alice alice-mixed-protected game2 '--record-cipher chacha20-poly1305'","alice alice-mixed-protected game2 '--record-cipher chacha20-poly1305"+(" --game-fec fixed6" if scene=="fixed" else "")+extra+"'")
sub("bob bob-mixed-protected game4 '--game-fec fixed6 --record-cipher aes-256-gcm'","bob bob-mixed-protected game4 '--record-cipher aes-256-gcm"+(" --game-fec fixed6" if scene!="fixed" else "")+extra+"'")
sub("carol carol-mixed-protected fec-auto '--record-cipher aes-128-gcm'","carol carol-mixed-protected "+{"normal":"normal","fixed":"fec-fixed","auto":"fec-auto"}[scene]+" '--record-cipher aes-128-gcm"+extra+"'")
# Reuse the exact real server, client, TUN, lease and warmup; replace
# post-warmup baseline assertions with this fault-specific oracle.
anchor='if [[ "'+'
s=s[:s.index(anchor)]
s=s.replace("for i in range(10000):","for i in range(20000):")
block=r'''
ART=fixed-kernel-result
mkdir -p "$ART"
for host in mha0 mhb0 mhc0;do
  sudo -n tc qdisc add dev "$host" clsact
  # Host-side veth ingress is upstream of server AF_PACKET. Only new
  # SYNs are dropped; established business/ACK/Health remain untouched.
  sudo -n tc filter add dev "$host" ingress protocol ip pref 1 flower ip_proto tcp dst_port 443 tcp_flags 0x02/0x12 action drop
done
cat >"$TMP/candidate-stream.py" <<'PY_STREAM'
import json,os,socket,sys,time
src,finish,out=sys.argv[1:]
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((src,0));s.settimeout(.2)
sent=got=0;receipts=[];start=time.monotonic()
while not os.path.exists(finish) and time.monotonic()-start<175:
    msg=("WBD_MIXED443/CANDIDATE/"+str(sent)).encode()
    sent+=1;s.sendto(msg,("10.66.0.1",45901))
    try:
        b,p=s.recvfrom(4096)
        if b==b"WBD_MIXED_ECHO/"+msg and p[0]=="10.66.0.1":
            got+=1;receipts.append(time.monotonic()-start)
    except socket.timeout:pass
    time.sleep(.10)
open(out,"w").write(json.dumps({"sent":sent,"received":got,"max_gap_s":max((b-a for a,b in zip(receipts,receipts[1:])),default=None),"receipts":receipts}))
PY_STREAM
for item in "alice $NSA $IPA" "bob $NSB $IPB" "carol $NSC $IPC";do
 read -r who ns addr <<<"$item"
 sudo -n ip netns exec "$ns" python3 "$TMP/candidate-stream.py" "$addr" "$TMP/candidate-finish" "$ART/candidate-$who.json" &
 case "$who" in alice) PA=$!;;bob) PB=$!;;carol) PC=$!;;esac
done
failed=0
for _ in $(seq 1 100);do
 if grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2 .*old_untouched=true' "$TMP/carol.log";then failed=1;break;fi
 for who in alice bob carol;do sudo -n kill -0 "$(cat "$TMP/$who.pid")";done
 sleep 1
done
test "$failed" = 1
for who in alice bob;do ! grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/$who.log";done
! grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2' "$TMP/carol.log"
for host in mha0 mhb0 mhc0;do
 sudo -n tc -s -j filter show dev "$host" ingress >"$ART/candidate-drop-$host.json"
 sudo -n tc filter del dev "$host" ingress protocol ip pref 1
done
recovered=0
for _ in $(seq 1 60);do
 if grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3' "$TMP/carol.log";then recovered=1;break;fi
 for who in alice bob carol;do sudo -n kill -0 "$(cat "$TMP/$who.pid")";done
 sleep 1
done
sleep 3
touch "$TMP/candidate-finish"
wait "$PA" "$PB" "$PC"
for who in server alice bob carol;do cp "$TMP/$who.log" "$ART/candidate-runtime-$who.log";done
python3 - "$recovered" <<'PY_CHECK'
import json,pathlib,re,sys
art=pathlib.Path("fixed-kernel-result")
assert sys.argv[1]=="1"
def packets(v):
    if isinstance(v,dict):return max([int(v.get("packets",0))]+[packets(x) for x in v.values()])
    if isinstance(v,list):return max([0]+[packets(x) for x in v])
    return 0
drop={h:packets(json.loads((art/f"candidate-drop-{h}.json").read_text())) for h in ("mha0","mhb0","mhc0")}
assert all(v>0 for v in drop.values()),drop
server=(art/"candidate-runtime-server.log").read_text()
rows={}
for who in ("alice","bob","carol"):
    client=(art/f"candidate-runtime-{who}.log").read_text()
    if who!="carol":
        fail="V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client"
        due="V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client"
        ready="V4_PUBLIC_GAME_SINGLE_LANE_READY role=client"
        assert client.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client")==1
        assert "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" not in client
        p=re.search(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=1 lane=1 cycle=\d+ old_client_port=(\d+) new_client_port=(\d+)",client)
        assert p and re.search(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=1 .*client_port="+p[2]+r" server_port=443",server)
    else:
        fail="V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2"
        due="V4_PUBLIC_TIMER_ROTATION_DUE role=client"
        ready="V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3"
        assert "V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=1" not in client
    assert client.count(fail)==1 and client.count(ready)==1
    offsets=[m.start() for m in re.finditer(due,client)]
    assert len(offsets)==2 and offsets[0]<client.index(fail)<offsets[1]<client.index(ready)
    v=json.loads((art/f"candidate-{who}.json").read_text())
    assert v["sent"]>400 and v["sent"]==v["received"] and v["max_gap_s"]<1,(who,v)
    v.pop("receipts");rows[who]=v
result={"result":"PASS_REAL_FAILED_SYN_KEEP_OLD_NEXT_TIMER","drop_packets":drop,"streams":rows}
(art/"candidate-evidence.json").write_text(json.dumps(result,indent=2))
print("LINUX_CANDIDATE_FAILURE_PASS "+json.dumps(result),flush=True)
PY_CHECK
for who in alice bob carol;do sudo -n kill -TERM "$(cat "$TMP/$who.pid")";done
for _ in $(seq 1 40);do
 if grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/carol.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/alice.log"
grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/bob.log"
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/carol.log"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for _ in $(seq 1 40);do
 if grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log"
'''
out.write_text(s+block);out.chmod(0o700)
+'{WBD_PLAN030_MANAGED:-0}" == 1 ]];then\n  sudo -n env LD_LIBRARY_PATH='
assert s.count(anchor)==1
s=s[:s.index(anchor)]
s=s.replace("for i in range(10000):","for i in range(20000):")
block=r'''
ART=fixed-kernel-result
mkdir -p "$ART"
for host in mha0 mhb0 mhc0;do
  sudo -n tc qdisc add dev "$host" clsact
  # Host-side veth ingress is upstream of server AF_PACKET. Only new
  # SYNs are dropped; established business/ACK/Health remain untouched.
  sudo -n tc filter add dev "$host" ingress protocol ip pref 1 flower ip_proto tcp dst_port 443 tcp_flags 0x02/0x12 action drop
done
cat >"$TMP/candidate-stream.py" <<'PY_STREAM'
import json,os,socket,sys,time
src,finish,out=sys.argv[1:]
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((src,0));s.settimeout(.2)
sent=got=0;receipts=[];start=time.monotonic()
while not os.path.exists(finish) and time.monotonic()-start<175:
    msg=("WBD_MIXED443/CANDIDATE/"+str(sent)).encode()
    sent+=1;s.sendto(msg,("10.66.0.1",45901))
    try:
        b,p=s.recvfrom(4096)
        if b==b"WBD_MIXED_ECHO/"+msg and p[0]=="10.66.0.1":
            got+=1;receipts.append(time.monotonic()-start)
    except socket.timeout:pass
    time.sleep(.10)
open(out,"w").write(json.dumps({"sent":sent,"received":got,"max_gap_s":max((b-a for a,b in zip(receipts,receipts[1:])),default=None),"receipts":receipts}))
PY_STREAM
for item in "alice $NSA $IPA" "bob $NSB $IPB" "carol $NSC $IPC";do
 read -r who ns addr <<<"$item"
 sudo -n ip netns exec "$ns" python3 "$TMP/candidate-stream.py" "$addr" "$TMP/candidate-finish" "$ART/candidate-$who.json" &
 case "$who" in alice) PA=$!;;bob) PB=$!;;carol) PC=$!;;esac
done
failed=0
for _ in $(seq 1 100);do
 if grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2 .*old_untouched=true' "$TMP/carol.log";then failed=1;break;fi
 for who in alice bob carol;do sudo -n kill -0 "$(cat "$TMP/$who.pid")";done
 sleep 1
done
test "$failed" = 1
for who in alice bob;do ! grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/$who.log";done
! grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2' "$TMP/carol.log"
for host in mha0 mhb0 mhc0;do
 sudo -n tc -s -j filter show dev "$host" ingress >"$ART/candidate-drop-$host.json"
 sudo -n tc filter del dev "$host" ingress protocol ip pref 1
done
recovered=0
for _ in $(seq 1 60);do
 if grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3' "$TMP/carol.log";then recovered=1;break;fi
 for who in alice bob carol;do sudo -n kill -0 "$(cat "$TMP/$who.pid")";done
 sleep 1
done
sleep 3
touch "$TMP/candidate-finish"
wait "$PA" "$PB" "$PC"
for who in server alice bob carol;do cp "$TMP/$who.log" "$ART/candidate-runtime-$who.log";done
python3 - "$recovered" <<'PY_CHECK'
import json,pathlib,re,sys
art=pathlib.Path("fixed-kernel-result")
assert sys.argv[1]=="1"
def packets(v):
    if isinstance(v,dict):return max([int(v.get("packets",0))]+[packets(x) for x in v.values()])
    if isinstance(v,list):return max([0]+[packets(x) for x in v])
    return 0
drop={h:packets(json.loads((art/f"candidate-drop-{h}.json").read_text())) for h in ("mha0","mhb0","mhc0")}
assert all(v>0 for v in drop.values()),drop
server=(art/"candidate-runtime-server.log").read_text()
rows={}
for who in ("alice","bob","carol"):
    client=(art/f"candidate-runtime-{who}.log").read_text()
    if who!="carol":
        fail="V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client"
        due="V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client"
        ready="V4_PUBLIC_GAME_SINGLE_LANE_READY role=client"
        assert client.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client")==1
        assert "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" not in client
        p=re.search(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=1 lane=1 cycle=\d+ old_client_port=(\d+) new_client_port=(\d+)",client)
        assert p and re.search(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=1 .*client_port="+p[2]+r" server_port=443",server)
    else:
        fail="V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2"
        due="V4_PUBLIC_TIMER_ROTATION_DUE role=client"
        ready="V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3"
        assert "V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=1" not in client
    assert client.count(fail)==1 and client.count(ready)==1
    offsets=[m.start() for m in re.finditer(due,client)]
    assert len(offsets)==2 and offsets[0]<client.index(fail)<offsets[1]<client.index(ready)
    v=json.loads((art/f"candidate-{who}.json").read_text())
    assert v["sent"]>400 and v["sent"]==v["received"] and v["max_gap_s"]<1,(who,v)
    v.pop("receipts");rows[who]=v
result={"result":"PASS_REAL_FAILED_SYN_KEEP_OLD_NEXT_TIMER","drop_packets":drop,"streams":rows}
(art/"candidate-evidence.json").write_text(json.dumps(result,indent=2))
print("LINUX_CANDIDATE_FAILURE_PASS "+json.dumps(result),flush=True)
PY_CHECK
for who in alice bob carol;do sudo -n kill -TERM "$(cat "$TMP/$who.pid")";done
for _ in $(seq 1 40);do
 if grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/carol.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/alice.log"
grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client' "$TMP/bob.log"
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/carol.log"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for _ in $(seq 1 40);do
 if grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log"
'''
out.write_text(s+block);out.chmod(0o700)
