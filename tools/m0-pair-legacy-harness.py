#!/usr/bin/env python3
"""Pinned legacy SOURCE; modify ONLY workload harness for a predeclared paired
diagnostic, not the product or cryptography. Explicit SHA receipts and anchors."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(sys.argv[1]).resolve()
EXPECTED="a7a82db31fe736ffedee330795a3234d358f1984"
assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==EXPECTED
def rep(text,a,b,n=1):
    actual=text.count(a)
    if actual!=n:raise RuntimeError(f"expected {n} anchors, got {actual}: {a[:100]}")
    return text.replace(a,b)
p=ROOT/"scripts/strict_weaknet_sample.sh"
stage=ROOT/"tools/strict_weaknet_stage.py"
t=p.read_text()
t=rep(t,"delay 300ms","delay 0ms",2)
t=rep(t,"--duration 120 --drain 10","--duration 70 --drain 3",2)
t=rep(t,'"one_way_delay_ms": 300, "duration_s": 120, "stages_s": [30, 60, 30]',
      '"one_way_delay_ms": 0, "duration_s": 70, "stages_s": [10, 60, 0]')
# Unlike previous diagnostic sources, disable legacy per-second product JSONL
# telemetry to match the new default diagnostics-off path. Only harness argv.
t=rep(t,'--diagnostic-jsonl "$ART/server-diag.jsonl" --diagnostic-interval 1s','')
t=rep(t,'--diagnostic-jsonl "$ART/client-diag.jsonl" --diagnostic-interval 1s','')
# No tcpdump/capture overhead or large pcap bytes in either measurement leg.
lines=t.splitlines(keepends=True)
capture=[x for x in lines if 'tcpdump -n -U' in x]
assert len(capture)==4
lines=[x for x in lines if 'tcpdump -n -U' not in x and 'CAP_PIDS+=("$!")' not in x]
t="".join(lines)
p.write_text(t)
u=stage.read_text()
u=rep(u,'"300ms"','"0ms"')
u=rep(u,'("stress", 30, args.stress_loss)','("stress", 10, args.stress_loss)')
u=rep(u,'("post", 90, args.post_loss)','("post", 70, args.post_loss)')
u=rep(u,'args.start_ns + 120 * 1_000_000_000','args.start_ns + 70 * 1_000_000_000')
stage.write_text(u)
out=Path(sys.argv[2])
out.parent.mkdir(parents=True,exist_ok=True)
m={"source_sha":EXPECTED,"mutates_product_source":False,
"old_product_binaries":"UNMODIFIED_PINNED",
"harness_patch_only":True,
"old_full_product_topology":"five_netns_veth_TPROXY_real_raw_TUN",
"old_harness_relative_paths":[str(p.relative_to(ROOT)),str(stage.relative_to(ROOT))],
"old_harness_sha256":{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (p,stage)},
"modifications":["normal_single_lane_FEC_off_runner_config","tc_netem_zero_delay_zero_loss","70s_10s_warmup_60s_measure_3s_drain","three_equal_count_UDP_PAYLOAD_64_256_1200","no_tcpdump_or_diagnostic_logging"],
"limitations":["Old full-product veth/TPROXY/TUN topology differs from new dev-only loopback raw/TUN","Old genuine external TLS client/server vs new protected fixture Go TLS","Same VM sequential costs may be compared descriptively, not causal Rust-vs-Go efficiency"] }
out.write_text(json.dumps(m,indent=2)+"\n")
print(json.dumps(m))
