#!/usr/bin/env python3
"""Attach a same-triplet bare OS capacity reference to the actual product receipt.
A low reference means the environment has not demonstrated the target capacity.
A high reference is not a claim that WBD achieved it, nor a fixed physical cap.
"""
import json
import pathlib
import sys

def comparison(bare,product):
    if any(bare.get(k)!=product.get(k) for k in ("source_sha","group","run_id")):
        raise ValueError("H2343 unrelated run/group/source")
    if bare["status"]!="PASS_H2285_NATIVE_WSL2_L3_FORWARD_TO_INDEPENDENT_ARM_TCP_SCOPED" or product["status"]!="PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP":
        raise ValueError("H2343 missing actual scoped receipts")
    if bare["delivered"]["sparse_echo_received"]!=160:
        raise ValueError("H2343 incomplete bare TCP")
    rate=bare["delivered"]["bulk_receiver_goodput_mbps"]
    if rate<=0:raise ValueError("H2343 nonpositive reference")
    stages=product["h2292_same_vm_original_product_abaprime"]["stages"]
    return dict(source_sha=product["source_sha"],group=product["group"],run_id=product["run_id"],
        scope="same three VMs, WSL2/ARM relay, bare before product, 4x25s 2MiB, no added loss",
        bare_mbps=rate,bare_p99_ms=bare["delivered"]["sparse_tcp_rtt_p99_ms"],
        reference_at_least_600=rate>=600,reference_at_least_800=rate>=800,
        product_legs=[dict(stage=s["stage"],mbps=s["tcp_mbps"],relative_to_bare_reference=round(s["tcp_mbps"]/rate,4)) for s in stages],
        note="Temporal drift and protocol/MSS differences remain; reference is not a product qualification.")

def main():
    bare_path,product_path=map(pathlib.Path,sys.argv[1:3])
    bare=json.loads(bare_path.read_text())
    product=json.loads(product_path.read_text())
    result=comparison(bare,product)
    product["h2343_same_vm_bare_capacity"]=result
    product_path.write_text(json.dumps(product,indent=2)+"\n")
    print("H2343_SAME_VM_BARE_REFERENCE "+json.dumps(result),flush=True)

if __name__=="__main__":main()
