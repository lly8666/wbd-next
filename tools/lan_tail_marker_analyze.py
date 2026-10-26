#!/usr/bin/env python3
"""Strict analyzer; Go native full seal+open 5 replicas each, 100 original 1345B."""
import argparse,json,pathlib,re,statistics
NAMES=("Hybrid99NoTailXOR","Hybrid99Last8Bits","Hybrid99Last8Bytes",
       "Hybrid95Last8Bits","Hybrid80Last8Bits","AlwaysAESLast8Bits",
       "PreviousOptimizedFullXOR")
RE=re.compile(r'Benchmark([A-Za-z0-9]+)(?:-\d+)?\s+\d+\s+([\d.]+) ns/op(?:\s+[\d.]+ MB/s)?\s+(\d+) B/op\s+(\d+) allocs/op')
def run(src):
    if 'PASS' not in src or 'FAIL' in src: raise RuntimeError('Go bench not PASS')
    rows={name:[] for name in NAMES}
    for ln in src.splitlines():
        m=RE.search(ln)
        if m:
            n,ns,mem,alloc=m.groups()
            if n not in rows: raise RuntimeError('unknown '+n)
            rows[n].append(dict(ns_per_100=float(ns),B_per_100=int(mem),allocs_per_100=int(alloc)))
    for n,v in rows.items():
        if len(v)!=5:raise RuntimeError(f'{n} got {len(v)}, require exactly 5')
    out={}
    for n,v in rows.items():
        a=[z['ns_per_100'] for z in v]
        out[n]=dict(mean_ns_per_100=statistics.mean(a),mean_ns_per_packet=statistics.mean(a)/100,
                    sample_ns_per_100=a,stdev_ns=statistics.stdev(a),
                    allocated_bytes_per_100=statistics.mean(z['B_per_100'] for z in v),
                    allocations_per_100=statistics.mean(z['allocs_per_100'] for z in v))
    b=out['Hybrid99Last8Bits']['mean_ns_per_100']
    controls={}
    for key in NAMES:
        val=out[key]['mean_ns_per_100']
        controls[key]={"pct_change_vs_hybrid99_last8bits":(val/b-1)*100,
                       "relative_factor":val/b}
    return {
      "status":"PASS_5X_NATIVE_SEAL_OPEN_GO_MICROBENCH",
      "scope":"not WBD rust wire; independent implicit counter supplied to both ends; no network; no real TLS Finished classifier",
      "input_bytes":1345,"packet_count_per_iteration":100,
      "markers":"2 bytes; fast 0000-EFFF, AES F000-FFFF; high byte visible with last-one-byte XOR",
      "fast_wire_overhead_bytes":7,"aes_wire_overhead_bytes":23,
      "timings_ns":out,"comparisons":controls,
      "security_warning":"TLS outer 23 is TLS-like not standard TLS; fast exposes original TLS header at body offset zero; marker leaks mode; no AEAD for fast; implicit counter desync risk"}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    a=p.parse_args()
    result=run(a.input.read_text())
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"ns_per_100":{k:round(v['mean_ns_per_100'],3) for k,v in result['timings_ns'].items()},
      "pct_vs_hybrid99":{k:round(v['pct_change_vs_hybrid99_last8bits'],3) for k,v in result['comparisons'].items()}},indent=2))
