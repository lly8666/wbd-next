#!/usr/bin/env python3
"""Run original source-locked Go TLS/Rust native Auto 4096-source maturity.

Only mutate an ephemeral copy of current real original-Go Linux netns
fixture. Never alter protected original Go, source-authentic Rust or protocol.
"""
from pathlib import Path
import sys
if len(sys.argv)!=3:raise SystemExit("usage original.sh output.sh")
src=Path(sys.argv[1]).read_text()
def replace_one(old,new):
    global src
    if src.count(old)!=1:
        raise SystemExit("source-locked original Auto fixture changed: "+repr(old[:95]))
    src=src.replace(old,new,1)
replace_one("  PACKETS=64\n", "  PACKETS=4608\n")
replace_one('s.bind(("10.66.0.1",45901));s.settimeout(28)',
            's.bind(("10.66.0.1",45901));s.settimeout(160)')
start=src.index("if fec or loss:\n")
end=src.index("else:\n    for i in range(count):",start)
old=src[start:end]
# Concurrent real UDP receive is essential; serial burst 4608 echoes
# overfills the actual kernel app socket and creates a false loss verdict.
replacement=r'''if fec or loss:
    import threading
    assert fec and not loss and count==4608
    payloads={}
    unique=set()
    malformed=[]
    end_read=threading.Event()
    s.settimeout(.10)
    def receive():
        while not end_read.is_set() and len(unique)<count:
            try:
                data,source=s.recvfrom(8192)
            except socket.timeout:
                continue
            if not data.startswith(b"V4_SERVER_APP_ECHO/") or source[0]!="10.66.0.1":
                malformed.append(data[:24]);continue
            msg=data[len(b"V4_SERVER_APP_ECHO/"):]
            if msg not in payloads:
                malformed.append(msg[:24]);continue
            unique.add(payloads[msg])
    reader=threading.Thread(target=receive,daemon=True)
    reader.start()
    for i in range(count):
        msg=b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i%256])*64
        payloads[msg]=i
        assert s.sendto(msg,("10.66.0.1",45901))==len(msg)
        time.sleep(.009)
    wait_until=time.monotonic()+24
    while len(unique)<count and time.monotonic()<wait_until and not malformed:
        time.sleep(.05)
    end_read.set()
    reader.join(timeout=3)
    assert not malformed,("invalid real echo",malformed[:3])
    assert len(unique)==count,("missing genuine app first delivery",len(unique),count)
    print("M0_PUBLIC_ORIGINAL_GO_V4_FEC2_REAL_GROUP_APP_FIRST_DELIVERY_PASS mode="+
          os.environ.get("WBD_REAL_MODE","")+" delivered="+str(len(unique)),flush=True)
'''
src=src[:start]+replacement+src[end:]
# Native 2s quality maturity, Go 2s decision and 30s 4096-source slow down.
replace_one("  sleep 5\nfi\n# Confirm clean signal-to-actual-Rust-Stop",
            "  sleep 15\nfi\n# Confirm clean signal-to-actual-Rust-Stop")
check='''if ! grep -Eq "V4_PUBLIC_FEC2_READBACK role=$role mode=(fixed|auto) requested=1 applied=1 profile=[0-6] pending=false" "$TMP/$role.log";then'''
if src.count(check)!=1:
    raise SystemExit("source-locked native M2 readback guard changed")
src=src.replace(check,'''if ! grep -Eq "V4_PUBLIC_FEC2_READBACK role=$role mode=auto requested=[2-9] applied=[2-9] profile=[0-4] pending=false" "$TMP/$role.log";then''',1)
# Require exact same committed revision on both original Go endpoints:
# requested2 applied3 is false; the Python readback binds them by equality.
anchor='''elif [[ "$LOSS" == 1 ]];then
  # True 1pct UDP loss is counted by distinct first echo and missing,''';
natural=r'''  python3 - "$TMP" <<'GRADED'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1])
for role in ("client","server"):
    log=(p/(role+".log")).read_text()
    rows=re.findall(r"V4_PUBLIC_FEC2_READBACK role="+role+
        r" mode=auto requested=(\d+) applied=(\d+) profile=(\d+) pending=(true|false)",log)
    assert rows,(role,"no genuine final Rust Auto readback")
    requested,applied,profile,pending=rows[-1]
    assert requested==applied and int(applied)>=2 and int(profile)<=4 and pending=="false",(role,rows[-1])
    assert "V4_PUBLIC_NATIVE_STOP_DRAINED role="+role in log,(role,"no owned Stop")
print("M0_PLAN026_LINUX_ORIGINAL_GO_RUST_AUTO_NATURAL_4096_30S_APPLIED_AND_STOP_PASS source=real_kerneltun")
GRADED
'''
# Insert after original for-role FEC2 M2 readback guard, before branch LOSS.
# The guard ends with two "fi" lines; ensure exact scoped location.
scoped='''      exit 1
    fi
  done
elif [[ "$LOSS" == 1 ]];then'''
if src.count(scoped)!=1:
    raise SystemExit("original auto M2 branch layout changed")
src=src.replace(scoped,'''      exit 1
    fi
  done
'''+natural+'''elif [[ "$LOSS" == 1 ]];then''',1)
dst=Path(sys.argv[2])
dst.write_text(src);dst.chmod(0o755)
print("M0_PLAN026_LINUX_AUTO_4096_REAL_FEC_M2_NATURAL_SOURCE_LOCKED no_product_change=1")
