#!/usr/bin/env python3
"""Analyze one source-pinned same-VM ten-leg LAN codec CPU job.
Never combine x86 and ARM64 numbers into a mixed-machine percentage.
"""
import argparse
import json
import pathlib
import statistics

ORDER=["aes128_gcm","chacha20_poly1305","fixed_xor","rolling_xor","clear",
       "clear","rolling_xor","fixed_xor","chacha20_poly1305","aes128_gcm"]
def analyze(path):
    lines=[json.loads(l) for l in pathlib.Path(path).read_text().splitlines() if l.strip()]
    measure=[l for l in lines if "kind" in l]
    transitions=[l for l in lines if "sequence_index" in l]
    assert [x["kind"] for x in measure] == ORDER, "unexpected predeclared balanced order"
    assert len(transitions)==10 and all(x["sequence_index"]==i and x["next_kind"]==ORDER[i] for i,x in enumerate(transitions))
    for x in measure:
        assert all(x[k]>0 for k in ["packets","bytes_inner","bytes_wire","cpu_ns","wall_ns"])
        assert x["bytes_inner"]==x["packets"]*1345
        overhead=31 if x["kind"] in ("aes128_gcm","chacha20_poly1305") else 15
        assert x["bytes_wire"]==x["packets"]*(1345+overhead)
        assert x["cpu_ns"]<=x["wall_ns"]*1.10, "CPU time implausibly exceeds wall for a single thread"
    groups={}
    for x in measure:
        name=x["kind"]
        groups.setdefault(name,[]).append(x)
    assert len(groups)==5 and all(len(v)==2 for v in groups.values())
    results={}
    for kind,v in groups.items():
        vals=[x["cpu_ns"]/x["bytes_inner"] for x in v]
        walls=[x["wall_ns"]/x["bytes_inner"] for x in v]
        mean=statistics.mean(vals)
        results[kind]={
            "cpu_ns_per_inner_byte":mean,
            "cpu_ns_per_packet":mean*1345,
            "cpu_seconds_per_GiB_of_inner_bytes":mean*(1024**3)/1e9,
            "wall_ns_per_inner_byte":statistics.mean(walls),
            "forward_reverse_cpu_ns_per_byte":vals,
            "forward_reverse_spread_pct":abs(vals[1]-vals[0])/mean*100,
            "packets_in_2_measured_legs":sum(x["packets"] for x in v),
            "wire_overhead_bytes_per_inner_packet":31 if kind in ("aes128_gcm","chacha20_poly1305") else 15,
            "wire_bytes_per_1345B_packet":1376 if kind in ("aes128_gcm","chacha20_poly1305") else 1360
        }
    reference=results["aes128_gcm"]["cpu_ns_per_inner_byte"]
    for val in results.values():
        val["cpu_saving_vs_AES128_GCM_pct"]=(1-val["cpu_ns_per_inner_byte"]/reference)*100
    return {
        "scope":"one-host native reusable-buffer record seal+open CPU, not WBD/TUN/Go/TCP",
        "cpu_semantics":"Linux /proc/thread-self/schedstat CPU nanos; one thread; no IO, real hardware selected by aws-lc-rs",
        "packet":"1345B IPv4/TCP synthetic fixed fixture, identical across all legs",
        "test_order":ORDER,
        "warmup_per_leg_ms":700,
        "nonce":"all record modes independent per-packet PN; old AEAD full seal+open; XOR clear-PN; rolling noncrypto",
        "allocation":"buffers reused per leg; hot-loop no explicit Vec allocation; Rust APIs differ internally",
        "measurement_note":"two legs per mode in symmetric same-VM order; means of two CPU per inner-byte rates; CPU values not cross-VM percentages",
        "results":results,
        "limitations":["NOT product Go/TUN end-to-end","NOT TLS authenticated handshake speed",
                       "NOT network transfer throughput or latency","NOT confidentiality of XOR",
                       "NOT real application mix or queue drops","NOT memory allocation instrumentation",
                       "NOT Windows/Android validation"]
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=pathlib.Path)
    p.add_argument("--output",required=True,type=pathlib.Path)
    a=p.parse_args()
    out=analyze(a.input)
    a.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
