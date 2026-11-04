#!/usr/bin/env python3
"""H1137 x86+ x86: append strict real shared-session Rust counters to frozen netns harness."""
from pathlib import Path
import sys
out=Path(sys.argv[1])
src=Path("tools/m0-v4-public-real-linux-netns.sh").read_text()
marker='if [[ "${WBD_V4_PUBLIC_WIRE_AUDIT:-0}" == 1 ]];then'
at=src.rfind(marker)
if at<0 or src.count(marker)!=2:raise RuntimeError("original mature shell audit anchors changed")
probe="""python3 - "$TMP/server.log" "$TMP/client.log" "$ART/plan028-h1137-native-rust-m2.json" <<'PY_H1137'
import json,pathlib,re,sys
server=pathlib.Path(sys.argv[1]).read_text()
client=pathlib.Path(sys.argv[2]).read_text()
rows=re.findall(r"V4_PUBLIC_M2_OUTER role=server [^\\n]*repair_enabled=(\\d+) first_wire_bytes=(\\d+) [^\\n]*shadow_limit=(\\d+) ",server)
ready=re.findall(r"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443 active_detached_flows=(\\d+) auto_lease=1 original_TLS=1 Rust_M4=1",server)
retired=re.findall(r"V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=([^ ]+) remaining=(\\d+)",server)
assert len(rows)==2 and all(int(enabled)==1 and int(first)>0 and int(shadow)>=0 for enabled,first,shadow in rows),(rows,"original Rust M2 per-session readback")
assert ready==["1","2"],ready
assert retired==[("same-lease-new-generation","1"),("server-close","0")],retired
assert client.count("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2")>=1
assert "V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1" in client
assert "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" in server
out={"source":"original_authenticated_Rust_M2_per_session","real_native_role":"x86_64_client_and_x86_64_server",
"session_ready_flows":[int(n) for n in ready],"outer_repair_enabled":[int(x[0]) for x in rows],
"first_wire_bytes":[int(x[1]) for x in rows],"rust_shadow_limit":[int(x[2]) for x in rows],
"exact_native_stop":[list(x) for x in retired],"CLI_intent_not_used_for_effective":True}
pathlib.Path(sys.argv[3]).write_text(json.dumps(out,indent=2)+"\\n")
print("M0_PLAN028_H1137_X86_TWO_GENUINE_RUST_M2_READBACK_REBIND_AND_STOP_PASS",flush=True)
PY_H1137
"""
out.write_text(src[:at]+probe+src[at:])
out.chmod(0o700)
print("M0_PLAN028_H1137_NATIVE_X86_FROZEN_PRODUCT_M2_PROBE_READY")
