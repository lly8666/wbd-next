#!/usr/bin/env python3
"""Fail-closed independent audit of 6 real Go native benchmark repetitions."""
import argparse,json,pathlib,re,statistics
MODES=[
 "PlainModeMixed99","HiddenPNModeMixed99",
 "PlainModeAllAES","HiddenPNModeAllAES",
 "PlainModeAllXOR","HiddenPNModeAllXOR",
 "ReadPlainModeOnly","ReadHiddenModeOnly"
]
RE=re.compile(r'^Benchmark(\w+)(?:-\d+)?\s+(\d+)\s+([\d.]+) ns/op(?:\s+[\d.]+ MB/s)?\s+(\d+) B/op\s+(\d+) allocs/op\s*
def read(p):
    text=p.read_text()
    assert 'PASS' in text and 'FAIL' not in text
    pairs={x:[] for x in MODES}
    for line in text.splitlines():
        m=RE.match(line.strip())
        if m:
            name,n,ns,alloc,objs=m.groups()
            assert name in pairs,name
            pairs[name].append(dict(iterations=int(n),ns_per_100packets_or_parse=float(ns),
             heap_B_per_cycle=int(alloc),heap_allocs_per_cycle=int(objs)))
    assert all(len(samples)==6 for samples in pairs.values()),[(x,len(y)) for x,y in pairs.items()]
    out={}
    for key,samples in pairs.items():
        v=[x["ns_per_100packets_or_parse"] for x in samples]
        mean=statistics.mean(v)
        out[key]={
            "samples_ns_per_cycle":v,"mean_ns_per_cycle":mean,
            "median_ns_per_cycle":statistics.median(v),
            "min_ns":min(v),"max_ns":max(v),
            "coefficient_variation_pct":statistics.stdev(v)/mean*100,
            "heap_B_per_cycle":statistics.mean(x["heap_B_per_cycle"] for x in samples),
            "allocs_per_cycle":statistics.mean(x["heap_allocs_per_cycle"] for x in samples),
            "total_iters":sum(x["iterations"] for x in samples)}
    compare={}
    for p in ("Mixed99","AllAES","AllXOR"):
        base=out["PlainMode"+p]["mean_ns_per_cycle"]
        hidden=out["HiddenPNMode"+p]["mean_ns_per_cycle"]
        compare[p]={
           "plain_ns_per_100_original_packets":base,
           "hidden_ns_per_100_original_packets":hidden,
           "additional_ns_per_packet":(hidden-base)/100,
           "additional_pct":(hidden/base-1)*100,
           "additional_heap_B_per_100":out["HiddenPNMode"+p]["heap_B_per_cycle"]-out["PlainMode"+p]["heap_B_per_cycle"],
           "additional_alloc_calls_per_100":out["HiddenPNMode"+p]["allocs_per_cycle"]-out["PlainMode"+p]["allocs_per_cycle"]}
    base=out["ReadPlainModeOnly"]["mean_ns_per_cycle"]
    hidden=out["ReadHiddenModeOnly"]["mean_ns_per_cycle"]
    return{
        "scope":"Go lab implementation end-to-end seal+open benchmark; no WBD Rust owner/TUN throughput or full-process CPU",
        "classification":"offline oracle exactly 99% fast, 1% real AES128GCM in Mixed99; not live TLS classifier",
        "sample_count_per_mode":6,"modes":out,"comparisons":compare,
        "parse_only_extra_ns_per_record":hidden-base,
        "parse_only_cryptographic_hp":"one AES128 block encryption keyed per lane, using first 16B ciphertext as sample",
        "original_wire":"5 TLS-like header + 1 clear mode + 8 clear PN + body",
        "hidden_wire":"5 TLS-like header + 8 hidden PNmode + body, 1 fewer byte per record",
        "xormode_security":"not authenticated, not confidential, not replay protected; hidden mode can be bit-flipped",
        "key_model":"independent fixed test keys, not production KDF or negotiation",
        "benchmark_risk":"wall-time Go benchmark, runner noise, constant-size 1345B test fixture, each loop 100 packets"}
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True,type=pathlib.Path)
    a.add_argument("--output",required=True,type=pathlib.Path)
    args=a.parse_args()
    out=read(args.input)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:out[k] for k in ("comparisons","parse_only_extra_ns_per_record",
    "sample_count_per_mode","xormode_security")},ensure_ascii=False,indent=2))
)
def read(p):
    text=p.read_text()
    assert 'PASS' in text and 'FAIL' not in text
    pairs={x:[] for x in MODES}
    for line in text.splitlines():
        m=RE.match(line.strip())
        if m:
            name,n,ns,alloc,objs=m.groups()
            assert name in pairs,name
            pairs[name].append(dict(iterations=int(n),ns_per_100packets_or_parse=float(ns),
             heap_B_per_cycle=int(alloc),heap_allocs_per_cycle=int(objs)))
    assert all(len(samples)==6 for samples in pairs.values()),[(x,len(y)) for x,y in pairs.items()]
    out={}
    for key,samples in pairs.items():
        v=[x["ns_per_100packets_or_parse"] for x in samples]
        mean=statistics.mean(v)
        out[key]={
            "samples_ns_per_cycle":v,"mean_ns_per_cycle":mean,
            "median_ns_per_cycle":statistics.median(v),
            "min_ns":min(v),"max_ns":max(v),
            "coefficient_variation_pct":statistics.stdev(v)/mean*100,
            "heap_B_per_cycle":statistics.mean(x["heap_B_per_cycle"] for x in samples),
            "allocs_per_cycle":statistics.mean(x["heap_allocs_per_cycle"] for x in samples),
            "total_iters":sum(x["iterations"] for x in samples)}
    compare={}
    for p in ("Mixed99","AllAES","AllXOR"):
        base=out["PlainMode"+p]["mean_ns_per_cycle"]
        hidden=out["HiddenPNMode"+p]["mean_ns_per_cycle"]
        compare[p]={
           "plain_ns_per_100_original_packets":base,
           "hidden_ns_per_100_original_packets":hidden,
           "additional_ns_per_packet":(hidden-base)/100,
           "additional_pct":(hidden/base-1)*100,
           "additional_heap_B_per_100":out["HiddenPNMode"+p]["heap_B_per_cycle"]-out["PlainMode"+p]["heap_B_per_cycle"],
           "additional_alloc_calls_per_100":out["HiddenPNMode"+p]["allocs_per_cycle"]-out["PlainMode"+p]["allocs_per_cycle"]}
    base=out["ReadPlainModeOnly"]["mean_ns_per_cycle"]
    hidden=out["ReadHiddenModeOnly"]["mean_ns_per_cycle"]
    return{
        "scope":"Go lab implementation end-to-end seal+open benchmark; no WBD Rust owner/TUN throughput or full-process CPU",
        "classification":"offline oracle exactly 99% fast, 1% real AES128GCM in Mixed99; not live TLS classifier",
        "sample_count_per_mode":6,"modes":out,"comparisons":compare,
        "parse_only_extra_ns_per_record":hidden-base,
        "parse_only_cryptographic_hp":"one AES128 block encryption keyed per lane, using first 16B ciphertext as sample",
        "original_wire":"5 TLS-like header + 1 clear mode + 8 clear PN + body",
        "hidden_wire":"5 TLS-like header + 8 hidden PNmode + body, 1 fewer byte per record",
        "xormode_security":"not authenticated, not confidential, not replay protected; hidden mode can be bit-flipped",
        "key_model":"independent fixed test keys, not production KDF or negotiation",
        "benchmark_risk":"wall-time Go benchmark, runner noise, constant-size 1345B test fixture, each loop 100 packets"}
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True,type=pathlib.Path)
    a.add_argument("--output",required=True,type=pathlib.Path)
    args=a.parse_args()
    out=read(args.input)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:out[k] for k in ("comparisons","parse_only_extra_ns_per_record",
    "sample_count_per_mode","xormode_security")},ensure_ascii=False,indent=2))
