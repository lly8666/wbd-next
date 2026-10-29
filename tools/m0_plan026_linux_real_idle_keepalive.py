#!/usr/bin/env python3
"""Source-locked harness ONLY: 100s authentic Linux Auto/Health idle -> kernel app.

The original Go/Rust transport binaries and the normal two-netns fixture are
unchanged; transform a temporary fixture before launching real TLS/NPF-like
raw/TUN and original application UDP. Never simulate peer Health or Stop.
"""
import pathlib
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: m0_plan026_linux_real_idle_keepalive.py original.sh output.sh")
src = pathlib.Path(sys.argv[1]).read_text()
dst = pathlib.Path(sys.argv[2])
def once(before: str, after: str):
    global src
    if src.count(before) != 1:
        raise SystemExit("expected exactly one original Linux fixture anchor: " + repr(before[:65]))
    src = src.replace(before, after, 1)

# Real Linux UDP application echo server must stay alive during a >90s
# absence of business. Its count includes the real post-idle datagram.
once('s.bind(("10.66.0.1",45901));s.settimeout(28)',
     's.bind(("10.66.0.1",45901));s.settimeout(160)')
once('env WBD_REAL_COUNT="$PACKETS" python3 -u -c \x27',
     'env WBD_REAL_COUNT="$((PACKETS+1))" python3 -u -c \x27')
anchor = """s.close()
' >"$ART/public-v4-normal-business.log" 2>&1;then"""
post_idle = """# One real original-Go-TLS/Rust owner must remain alive while there is
# NO application data for 100s (> the native authenticated dead=90s).
# Missing authenticated peer Health should fail-closed before the replay.
assert fec and not loss and os.environ.get("WBD_REAL_MODE")=="fec-auto"
time.sleep(100)
extra=b"WBD_REAL_V4_ORIGINAL_GO/HEALTH_IDLE_100S_RESUME/"+bytes([211])*64
assert s.sendto(extra,("10.66.0.1",45901))==len(extra)
want=b"V4_SERVER_APP_ECHO/"+extra
deadline=time.monotonic()+9
ok=False
s.settimeout(0.7)
while time.monotonic()<deadline:
    try:
        data,src=s.recvfrom(8192)
    except socket.timeout:
        continue
    if data==want and src[0]=="10.66.0.1":
        ok=True
        break
assert ok,"missing second real TUN application echo after 100 seconds business idle"
print("M0_PLAN026_LINUX_REAL_TLS_RUST_HEALTH_IDLE_100S_KERNEL_APP_RESUME_PASS initial_real_udp=64 resumed_real_udp=1 default_health_s=15 default_dead_s=90",flush=True)
"""
once(anchor, post_idle + anchor)
dst.write_text(src)
dst.chmod(0o755)
print("M0_PLAN026_LINUX_IDLE100_FIXTURE_SOURCE_LOCKED original_product_unchanged=1")
