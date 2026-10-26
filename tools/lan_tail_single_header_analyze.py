#!/usr/bin/env python3
"""Nine native Go A/B scenarios, each exactly five reps; full encode and decode."""
import argparse,json,pathlib,re,statistics
NAMES=("SingleHeader99Tail8Word","SingleHeader99Tail8ByteLoop",
       "SingleHeader99NoTail","SingleHeader99Tail1",
       "SingleHeader95Tail8Word","SingleHeader80Tail8Word",
       "SingleHeaderAllAESTail8Word","OldDoubleHeader99Tail8Word",
       "OldFullXOR")
RE=re.compile(r'Benchmark([A-Za-z0-9]+)(?:-\d+)?\s+\d+\s+([\d.]+) ns/op(?:\s+[\d.]+ MB/s)?\s+(\d+) B/op\s+(\d+) allocs/op')
def measure(raw):
    assert "PASS" in raw and "FAIL" not in raw
    hits={n:[] for n in NAMES}
    for line in raw.splitlines():
        x=RE.search(line)
        if x:
            n,ns,b,a=x.groups()
            if n not in hits:raise RuntimeError("unexpected bench "+n)
            hits[n].append(dict(ns=float(ns),B=int(b),allocs=int(a)))
    assert all(len(v)==5 for v in hits.values()), {k:len(v) for k,v in hits.items()}
    stats={}
    for name,values in hits.items():
        times=[x["ns"] for x in values]
        stats[name]={
          "mean_ns_per_100":statistics.mean(times),
          "mean_ns_per_packet":statistics.mean(times)/100,
          "median_ns_per_100":statistics.median(times),
          "stddev_ns_per_100":statistics.stdev(times),
          "raw_ns_per_100":times,
          "mean_B_per_100":statistics.mean(x["B"] for x in values),
          "mean_heap_allocs_per_100":statistics.mean(x["allocs"] for x in values)}
    baseline=stats["SingleHeader99Tail8Word"]["mean_ns_per_100"]
    controls={n:{"ns_per_100":d["mean_ns_per_100"],
                 "pct_vs_single99tail8word":(d["mean_ns_per_100"]/baseline-1)*100}
              for n,d in stats.items()}
    return{
      "status":"PASS_ORIGINAL_GO_NATIVE_9_MODES_5X",
      "scope":"Minimum single TLS header in fast mode, synthetic test oracle for genuine inner TLS, no WBD Rust integration",
      "full_encode_decode":"100x 1345B original TLS records per bench iteration",
      "wire_bytes_fast_single":1347,
      "wire_bytes_fast_double":1352,
      "wire_bytes_aes":1368,
      "extra_wire_fast_single":2,
      "extra_wire_aes":23,
      "fast_requires_restore_orig_tls_header_before_delivery":True,
      "fast_is_genuine_tls13_on_wire":False,
      "fast_mac_in_custom_wrapper":False,
      "rolling_last_bytes":8,
      "results":stats,"comparisons":controls}
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=pathlib.Path,required=True)
    a.add_argument("--output",type=pathlib.Path,required=True)
    args=a.parse_args()
    result=measure(args.input.read_text())
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"means_ns_per_100":{k:round(v["mean_ns_per_100"],3) for k,v in result["results"].items()},
                      "vs_single_header_99tail8word_pct":{k:round(v["pct_vs_single99tail8word"],3) for k,v in result["comparisons"].items()}},indent=2))
