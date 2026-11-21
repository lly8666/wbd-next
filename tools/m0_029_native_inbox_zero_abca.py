#!/usr/bin/env python3
"""PLAN029 distinct 0% high-supply A64/B256/A64 negative product screen.

Reuse EXACT pinned GE fixture code and genuine original-Go/Rust owner.
Only replace the physical router netem configuration with 0%/0ms.
Separate Action/scenario/runner: never compare its CPU directly with GE1%.
No test-provided crypto, bypass or faked direct/WBD traffic.
"""
import json
import os
import pathlib
import runpy
import subprocess

SOURCE_SCRIPT="tools/m0_029_native_inbox_abca.py"
FROZEN_BLOB_SHA="b1094391ec9729931979c5158357ef2cbf72b84e"

def verify_frozen_fixture():
    found=subprocess.check_output(["git","hash-object",SOURCE_SCRIPT],text=True).strip()
    if found!=FROZEN_BLOB_SHA:
        raise RuntimeError("M029_ZERO_UNVERIFIED_BASE_FIXTURE_SOURCE_CHANGE")
    return found

def main():
    verify_frozen_fixture()
    context=runpy.run_path(SOURCE_SCRIPT,run_name="m029_zero_loss_fixture_import")
    run=context["main"]
    globals_=run.__globals__
    owned=globals_["Owned"]
    original_save=globals_["save"]
    globals_["OUT"]=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"m029-inbox-zero-abca"
    globals_["TMP"]=pathlib.Path(os.environ["RUNNER_TEMP"])/(
        "m029-inbox-zero-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"])

    def zero_impair(self):
        # Preserve the same three real namespaces, kernel qdisc type, and
        # kernel skb accounting. This profile injects NO artificial drop
        # or delay; any loss must be identified elsewhere in the path.
        for dev in ("rcli0","rsrv0"):
            globals_["ns"](self.router,"tc","qdisc","replace","dev",dev,"root",
                           "netem","delay","0ms","loss","0%","limit","65536")
        return {dev:json.loads(globals_["ns"](self.router,"tc","-s","-j",
                           "qdisc","show","dev",dev).stdout)
                for dev in ("rcli0","rsrv0")}

    def exact_zero_save(name,data):
        data["scenario"]="ZERO_LOSS_0MS_NATIVE_ARM64_HIGH_SUPPLY_4_TCP_PLUS_SMALL"
        data["netem_ge_stationary_parameters"]={
            "profile":"ZERO_ARTIFICIAL_LOSS","target_loss_pct":0.0,
            "oneway_extra_delay_ms":0,
            "independent_from_GE1_A_B_A":True}
        data["base_fixture_git_blob_sha"]=FROZEN_BLOB_SHA
        original_save(name,data)

    owned.impair=zero_impair
    globals_["save"]=exact_zero_save
    if globals_["PHASES"]!=(
            ("original_before",64),("inbox256_candidate",256),
            ("original_after",64)):
        raise RuntimeError("M029_ZERO_CANDIDATE_ORDER_CHANGED")
    try:
        run()
    finally:
        print("M029_ZERO_LOSS_PROFILE_REAL_RUN_NOT_GE1 "
              "base_fixture_blob="+FROZEN_BLOB_SHA,flush=True)

if __name__=="__main__":main()
