#!/usr/bin/env python3
"""Audit exactly 99% labelled TLS app and 1% full AES WBD native paired legs.

Four modes x four alternating passes (forward,backward,forward,backward)
run in one native VM. Packet type and mode both externally trusted fixtures,
not real live traffic classification.
"""
import argparse,json,pathlib,statistics
MODES=["full_aead_31b","hybrid_pn_xor","hybrid_fastgate_pn_xor","all_pn_xor_insecure_floor"]
EXPECTED=MODES+MODES[::-1]+MODES+MODES[::-1]
def analyze(path):
    lines=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    pre=[r for r in lines if "preflight" in r]
    assert len(pre)==1 and pre[0]["preflight"]=="PASS"
    assert pre[0]["scenarios"]==1 and pre[0]["modes"]==4
    prof=[r for r in lines if "profile" in r]
    assert len(prof)==1
    assert prof[0]["profile"]=="equal_99"
    assert prof[0]["eligible_records"]==99
    assert prof[0]["eligible_bytes"]==99*1345
    assert prof[0]["total_inner_bytes"]==100*1345
    rows=[r for r in lines if "mode" in r]
    assert len(rows)==16,len(rows)
    assert [r["mode"] for r in rows]==EXPECTED
    result={}
    for row in rows:
        assert row["scenario"]=="equal_99"
        n=row["packets"]
        assert n>0 and n%100==0
        assert row["eligible_per_100"]==99
        assert row["inner_bytes"]==n*1345
        assert 0<row["cpu_ns"]<=1.2*row["wall_ns"]
        q=n*99//100
        m=row["mode"]
        if m in ("hybrid_pn_xor","hybrid_fastgate_pn_xor"):
            assert row["xor_records"]==q and row["aes_records"]==n-q,(m,row)
            assert row["wire_bytes"]==row["inner_bytes"]+15*q+31*(n-q)
        elif m=="all_pn_xor_insecure_floor":
            assert row["xor_records"]==n and row["aes_records"]==0
            assert row["wire_bytes"]==row["inner_bytes"]+15*n
        elif m=="full_aead_31b":
            assert row["xor_records"]==0 and row["aes_records"]==n
            assert row["wire_bytes"]==row["inner_bytes"]+31*n
    for mode in MODES:
        samples=[r for r in rows if r["mode"]==mode]
        assert len(samples)==4
        values=[r["cpu_ns"]/r["inner_bytes"] for r in samples]
        result[mode]={
            "cpu_ns_per_inner_byte":statistics.mean(values),
            "replicate_ns_per_inner_byte":values,
            "stddev_ns_per_inner_byte":statistics.stdev(values),
            "cv_pct":statistics.stdev(values)/statistics.mean(values)*100,
            "cpu_ns_per_original_packet":statistics.mean(
                [r["cpu_ns"]/r["packets"] for r in samples]),
            "total_measured_packets":sum(r["packets"] for r in samples),
            "wire_bytes_per_100_inner_packets":statistics.mean(
                [r["wire_bytes"]/r["packets"]*100 for r in samples])
        }
    allxor=result["all_pn_xor_insecure_floor"]["cpu_ns_per_inner_byte"]
    full=result["full_aead_31b"]["cpu_ns_per_inner_byte"]
    ideal=result["hybrid_pn_xor"]["cpu_ns_per_inner_byte"]
    gate=result["hybrid_fastgate_pn_xor"]["cpu_ns_per_inner_byte"]
    return{
        "profile":"99% ideal-confirmed TLS13 application packets, 1% trusted protected-edge fallback AES",
        "scope":"ONLY original WBD Rust seal/open record CPU; trusted oracle input; no actual product TCP reassembly or classifier/admission cost",
        "replicates_per_mode":4,
        "each_leg_seconds":2,
        "exact_legs":16,
        "security":"all XOR is totally reversible and violates 1% handshake privacy requirement",
        "modes":result,
        "gate_hybrid_extra_cost_vs_ALL_XOR_pct":(gate/allxor-1)*100,
        "gate_hybrid_extra_cost_vs_ALL_XOR_cpu_ns_per_inner_byte":gate-allxor,
        "ideal_99pct_hybrid_extra_cost_vs_ALL_XOR_pct":(ideal/allxor-1)*100,
        "fast_gate_extra_cost_vs_ideal_99pct_hybrid_pct":(gate/ideal-1)*100,
        "full_AES_cpu_saving_of_99pct_hybrid_pct":(1-gate/full)*100,
        "all_XOR_cpu_saving_vs_full_AES_pct":(1-allxor/full)*100,
        "bytes_extra_per_100_packets_hybrid_over_all_XOR":16,
        "average_wire_bytes_extra_per_inner_packet_hybrid_over_all_XOR":0.16,
        "caveat":"The 1% fallback is equally sized TLS-edge fixture; other mixtures or smaller ACKs produce different ns-per-original-byte",
    }
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    summary=analyze(a.input)
    a.output.write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
