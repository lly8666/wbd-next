#!/usr/bin/env python3
"""Real veth tuple blackhole; scheduled rotation OFF; original native Game."""
from pathlib import Path
import sys
if len(sys.argv)!=3 or sys.argv[2] not in ("game2","game4"):
    raise SystemExit("usage: fixture.py OUTPUT game2|game4")
out=Path(sys.argv[1]); mode=sys.argv[2]; n=int(mode[-1])
who="alice" if n==2 else "bob"
host="mha0" if n==2 else "mhb0"
s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
anchor="# Client A only stops; independent Game4 and Normal still deliver traffic."
assert s.count(anchor)==1
block=r'''
# The far veth, not the client or server AF_PACKET socket, drops the exact
# OLD lane in both directions. Never unblock that port to manufacture recovery.
WHO=@WHO@
HOST=@HOST@
N=@N@
ART=fixed-kernel-result
OLD="$(sed -n 's/.*V4_PUBLIC_GAME_GROUP_LANE_READY role=client .*lane=2 local_port=\([0-9]*\) .*/\1/p' "$TMP/$WHO.log" | head -1)"
test -n "$OLD"
sudo -n tc qdisc add dev "$HOST" clsact
sudo -n tc filter add dev "$HOST" ingress protocol ip pref 1 flower ip_proto tcp src_port "$OLD" dst_port 443 action drop
sudo -n tc filter add dev "$HOST" egress protocol ip pref 1 flower ip_proto tcp src_port 443 dst_port "$OLD" action drop
cat >"$TMP/lane-blackhole.py" <<'PY_STREAM'
import json,os,socket,sys,time
src,finish,out=sys.argv[1:]
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind((src,0));sock.settimeout(.20)
sent=got=0;received=[];start=time.monotonic()
while not os.path.exists(finish) and time.monotonic()-start<290:
    msg=("WBD_MIXED443/BLACKHOLE/"+str(sent)).encode()
    sent+=1;sock.sendto(msg,("10.66.0.1",45901))
    try:
        data,peer=sock.recvfrom(4096)
        if data==b"WBD_MIXED_ECHO/"+msg and peer[0]=="10.66.0.1":
            got+=1;received.append(time.monotonic())
    except socket.timeout:pass
    time.sleep(.10)
sock.close()
v={"sent":sent,"received":got,"max_gap_s":max((b-a for a,b in zip(received,received[1:])),default=None)}
open(out,"w").write(json.dumps(v)+"\n")
PY_STREAM
for item in "alice $NSA $IPA" "bob $NSB $IPB" "carol $NSC $IPC";do
 read -r peer ns addr <<<"$item"
 sudo -n ip netns exec "$ns" python3 "$TMP/lane-blackhole.py" "$addr" "$TMP/blackhole-finish" "$ART/blackhole-$peer.json" &
 case "$peer" in alice) PA=$!;;bob) PB=$!;;carol) PC=$!;;esac
done
recovered=0
for _ in $(seq 1 260);do
  if grep -q "V4_PUBLIC_GAME_SINGLE_LANE_READY role=client .*lane=2 .*old_client_port=$OLD " "$TMP/$WHO.log";then
    recovered=1;break
  fi
  sudo -n kill -0 "$(cat "$TMP/$WHO.pid")"
  sleep 1
done
sleep 5
touch "$TMP/blackhole-finish"
wait "$PA" "$PB" "$PC"
sudo -n tc -s -j filter show dev "$HOST" ingress >"$ART/blackhole-ingress.json"
sudo -n tc -s -j filter show dev "$HOST" egress >"$ART/blackhole-egress.json"
for peer in server alice bob carol;do cp "$TMP/$peer.log" "$ART/blackhole-runtime-$peer.log";done
python3 - "$WHO" "$N" "$OLD" "$recovered" <<'PY_CHECK'
import json,pathlib,re,sys
who,n,old,recovered=sys.argv[1:]
art=pathlib.Path("fixed-kernel-result")
client=(art/f"blackhole-runtime-{who}.log").read_text()
server=(art/"blackhole-runtime-server.log").read_text()
assert recovered=="1",client[-3000:]
assert "V4_PUBLIC_GAME_LANE_REBUILD_DUE role=client lane=2 authenticated_stale=1" in client
rows=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=1 lane=2 cycle=\d+ old_client_port=(\d+) new_client_port=(\d+)",client)
assert len(rows)==1 and rows[0][0]==old and rows[0][1]!=old,rows
assert re.search(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=2 rotation=\d+ client_port="+rows[0][1]+r" server_port=443",server)
assert client.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes="+n)==1
assert "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2" not in client
assert "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" not in client
assert client.count("V4_PUBLIC_GAME_SINGLE_LANE_READY role=client")==1
def packets(v):
    if isinstance(v,dict):
        return max([int(v.get("packets",0))]+[packets(x) for x in v.values()])
    if isinstance(v,list):return max([0]+[packets(x) for x in v])
    return 0
drop={d:packets(json.loads((art/f"blackhole-{d}.json").read_text())) for d in ("ingress","egress")}
assert all(x>0 for x in drop.values()),drop
streams={p:json.loads((art/f"blackhole-{p}.json").read_text()) for p in ("alice","bob","carol")}
assert all(x["sent"]>=1000 and x["received"]>=x["sent"]*.995 and x["max_gap_s"]<1 for x in streams.values()),streams
result={"result":"PASS","mode":"game"+n,"old_port":int(old),"new_port":int(rows[0][1]),"drop_packets":drop,"scheduled_rotation":False,"same_group":True,"streams":streams}
(art/"blackhole-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
print("GAME_REAL_SINGLE_LANE_BLACKHOLE_RECOVERY_PASS", "game"+n,flush=True)
PY_CHECK
'''
block=block.replace("@WHO@",who).replace("@HOST@",host).replace("@N@",str(n))
out.write_text(s.replace(anchor,block+"\n"+anchor));out.chmod(0o700)
