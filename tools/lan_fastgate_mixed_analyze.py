#!/usr/bin/env python3
"""Independent strict validator for bounded SAME-VM hybrid record CPU jobs."""
import argparse
import json
import pathlib
import statistics

PROFILES=["equal_0","equal_25","equal_50","equal_75","equal_90","equal_100",
          "web_bulk","mixed_session","non_tls_heavy"]
MODES=["full_aead_31b","selective_aad_33b","full_aad_layout_33b",
       "hybrid_pn_xor","hybrid_fastgate_pn_xor","hybrid_word_rolling_xor","all_pn_xor_insecure_floor"]
def analyze(path):
    objects=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    preflight=[r for r in objects if "preflight" in r]
    assert len(preflight)==1 and preflight[0]["preflight"]=="PASS"
    profiles=[r for r in objects if "profile" in r]
    assert [x["profile"] for x in profiles]==PROFILES
    assert [x["eligible_records"] for x in profiles[:6]]==[0,25,50,75,90,100]
    rows=[r for r in objects if "mode" in r]
    assert len(rows)==len(PROFILES)*len(MODES)*2
    summary={}
    for p,prof in zip(PROFILES,profiles):
        subset=[r for r in rows if r["scenario"]==p]
        assert [r["mode"] for r in subset]==MODES+MODES[::-1],(p,"wrong symmetric mode order")
        eligible=prof["eligible_records"]
        tbytes=prof["total_inner_bytes"]
        assert tbytes>0
        counts=[r["packets"] for r in subset]
        assert all(n%100==0 for n in counts)
        results={}
        for r in subset:
            assert r["eligible_per_100"]==eligible
            assert all(r[k]>0 for k in ["packets","cpu_ns","wall_ns","inner_bytes","wire_bytes"])
            assert r["inner_bytes"]==r["packets"]*tbytes//100
            assert r["cpu_ns"]<=r["wall_ns"]*1.2
            e=r["packets"]*eligible//100
            if r["mode"] in ("hybrid_pn_xor","hybrid_fastgate_pn_xor","hybrid_word_rolling_xor"):
                assert r["xor_records"]==e and r["aes_records"]==r["packets"]-e
                assert r["wire_bytes"]==r["inner_bytes"]+15*e+31*(r["packets"]-e)
            elif r["mode"]=="all_pn_xor_insecure_floor":
                assert r["xor_records"]==r["packets"] and r["aes_records"]==0
                assert r["wire_bytes"]==r["inner_bytes"]+15*r["packets"]
            elif r["mode"]=="full_aead_31b":
                assert r["aes_records"]==r["packets"] and r["xor_records"]==0
                assert r["wire_bytes"]==r["inner_bytes"]+31*r["packets"]
            elif r["mode"]=="selective_aad_33b":
                assert r["aad_partial_records"]==e and r["aes_records"]==r["packets"]-e
                assert r["wire_bytes"]==r["inner_bytes"]+33*r["packets"]
            elif r["mode"]=="full_aad_layout_33b":
                assert r["aad_partial_records"]==0 and r["aes_records"]==r["packets"]
                assert r["wire_bytes"]==r["inner_bytes"]+33*r["packets"]
        for m in MODES:
            pair=[r for r in subset if r["mode"]==m]
            assert len(pair)==2
            vals=[r["cpu_ns"]/r["inner_bytes"] for r in pair]
            vals_packet=[r["cpu_ns"]/r["packets"] for r in pair]
            mean=statistics.mean(vals)
            results[m]={
                "cpu_ns_per_inner_byte":mean,
                "cpu_ns_per_packet":statistics.mean(vals_packet),
                "two_legs_ns_per_inner_byte":vals,
                "paired_spread_pct":abs(vals[0]-vals[1])/mean*100,
                "packet_count_both_legs":sum(r["packets"] for r in pair),
                "wire_bytes_per_100_packets":sum(r["wire_bytes"]/r["packets"]*100 for r in pair)/2,
            }
        ref=results["full_aead_31b"]["cpu_ns_per_inner_byte"]
        for m in results:
            results[m]["saving_vs_full_aead_pct"]=(1-results[m]["cpu_ns_per_inner_byte"]/ref)*100
        oracle_cpu=results["hybrid_pn_xor"]["cpu_ns_per_inner_byte"]
        gate_cpu=results["hybrid_fastgate_pn_xor"]["cpu_ns_per_inner_byte"]
        results["hybrid_fastgate_pn_xor"]["incremental_gate_cpu_over_oracle_pct"]=(gate_cpu/oracle_cpu-1)*100
        summary[p]={
            "eligible_packets_per_100":eligible,
            "eligible_inner_byte_pct":prof["eligible_byte_pct"],
            "mean_inner_bytes_per_packet":tbytes/100,
            "results":results
        }
    return{
        "scope":"native same-VM mixed per-packet WBD record seal/open CPU, IDEAL ORACLE, NOT PRODUCT",
        "important":"TLS1.3 0x17 cannot distinguish encrypted handshake, app and alert; only external trusted labels here",
        "classification_cost":"BENCHMARK_ONLY_IP_TCP_SEQ_FAST_GATE_CHECK_INCLUDED; TRUSTED_ORACLE_PROVENANCE_EXCLUDED",
        "mode_discriminator_and_receive_capability_cost":"EXCLUDED",
        "tls13_app_content":"GENUINE local TLS1.3 ciphertext corpus",
        "other_packet_classes":"constructed IPv4 TLS edge/handshake, TCP, ACK, UDP",
        "security":"hybrid PN/XOR data NEVER AEAD authenticated, unlike ordinary fallback",
        "profiles":summary
    }
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    a=ap.parse_args()
    result=analyze(a.input)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
