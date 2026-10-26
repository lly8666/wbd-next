#!/usr/bin/env python3
"""Parse same-native-host Go microbenchmark replicates of VMess none vs WBD XOR."""
import argparse, pathlib, json, re, statistics
NAMES=("VMessZero","VMessNonePlainLength","VMessNoneSHAKE128","WBDClearPNXOR","WBDHiddenPNXOR")
PAT=re.compile(r'Benchmark([A-Za-z0-9]+)(?:-\d+)?\s+(\d+)\s+([\d.]+) ns/op(?:\s+[\d.]+ MB/s)?\s+(\d+) B/op\s+(\d+) allocs/op')
def analyze(s):
    assert "PASS" in s and "FAIL" not in s,"benchmark run not successful"
    modes={name:[] for name in NAMES}
    for line in s.splitlines():
        m=PAT.search(line)
        if not m: continue
        name,it,ns,mem,nalloc=m.groups()
        assert name in modes,name
        modes[name].append({"iterations":int(it),"ns_per_100_packets":float(ns),
                            "B_allocated_per_100":int(mem),"allocs_per_100":int(nalloc)})
    assert all(len(vals)==5 for vals in modes.values()),{k:len(v) for k,v in modes.items()}
    means={}
    for name,vs in modes.items():
        values=[s["ns_per_100_packets"] for s in vs]
        means[name]={"mean_ns_per_100":statistics.mean(values),
        "median_ns_per_100":statistics.median(values),
        "stdev_ns_per_100":statistics.stdev(values),
        "ns_per_original_1345B":statistics.mean(values)/100,
        "heap_B_per_100":statistics.mean(s["B_allocated_per_100"] for s in vs),
        "allocs_per_100":statistics.mean(s["allocs_per_100"] for s in vs),
        "ns_raw":values}
    base=means["VMessNoneSHAKE128"]["mean_ns_per_100"]
    comparisons={}
    for name in NAMES:
        x=means[name]["mean_ns_per_100"]
        comparisons[name]={"relative_to_vmess_none_sha128_pct":(x/base-1)*100,
            "ratio_vmess_none_SHAKE128_vs_mode":base/x,
            "mean_ns_per_100":x}
    return {
      "status":"SCOPED_NATIVE_5x_GO_SEAL_OPEN_BENCH",
      "scope":"steady-state only, Go native lab copy/mask, NOT V2Fly runtime or WBD Rust production, no network",
      "fixtures":{"payload_bytes":1345,"packets_per_cycle":100,"results_per_mode":5,
        "clock":"go test wall ns/op per 100 originals"},
      "upstream_source":"v2fly/v2ray-core master proxy/vmess/encoding/auth.go SHAKE128 size mask; outbound.go NONE chunk masking true, default no global padding, ZERO raw",
      "security":"VMess none/zero payload transmitted plainly; WBD XOR public reversible and tamperable; neither authenticated",
      "full_headers_excluded":"VMess authenticated request header, WBD initial outer borrowed TLS bootstrap",
      "actual_wire_extra_bytes_per_packet":{"VMessZero":0,"VMessNonePlainLength":2,"VMessNoneSHAKE128":2,"WBDClearPNXOR":15,"WBDHiddenPNXOR":14},
      "means":means,"comparisons":comparisons
    }
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=pathlib.Path)
    ap.add_argument("--output",required=True,type=pathlib.Path)
    a=ap.parse_args()
    result=analyze(a.input.read_text())
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"means":{k:round(v["mean_ns_per_100"],2) for k,v in result["means"].items()},
       "comparisons":result["comparisons"],"status":result["status"]},indent=2))
