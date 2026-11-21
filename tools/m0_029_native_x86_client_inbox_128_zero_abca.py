#!/usr/bin/env python3
"""M0 PLAN029: x86_64 client-only M1 inbox64/128/64 real zero-loss ABA.

This is a separate direction-localized falsification, NOT cross-run A/B.
Reuses a frozen original Go/Rust 3-netns source fixture, actual kernel TCP4,
160 real UDP+TCP echoes, authentic per-phase client/server Rust Stop.

The previous server-only 256 candidate reduced server pending full but did not
improve receiver goodput; this test varies ONLY authenticated client Rust M1
inbox capacity, and requires exact cold per-generation readback at BOTH ends.
"""
import copy
import json
import os
import pathlib
import re
import runpy
import subprocess

BASE_SCRIPT="tools/m0_029_native_inbox_abca_x86.py"
BASE_GIT_BLOB="c77885ecfec42dba06bee76d015875f62ec89fc9"

def validate_base():
    blob=subprocess.check_output(["git","hash-object",BASE_SCRIPT],text=True).strip()
    if blob!=BASE_GIT_BLOB:
        raise RuntimeError("M029_CLIENT_128_UNVERIFIED_GENUINE_BASE_SOURCE")
    return blob

def main():
    validate_base()
    ns=runpy.run_path(BASE_SCRIPT,run_name="m029_client_inbox_frozen_fixture")
    original_main=ns["main"]
    g=original_main.__globals__
    Owned=g["Owned"]
    original_start=Owned.start_product
    original_spawn=Owned.spawn
    original_impair=Owned.impair
    original_save=g["save"]
    verified=[]

    def client_inbox_spawn(self,role,place,argv):
        if role=="client":
            # A native Go/Rust process, not a test-side packet shim:
            # exactly one cold test flag in the original Rust owner process.
            argv=list(argv)
            if argv[:2]!=["env","LD_LIBRARY_PATH="+str(g["BUNDLE"])]:
                raise RuntimeError("M029_CLIENT_128_NATIVE_PRODUCT_ARGS_CHANGED")
            if any("WBD_M0_029_INBOX_SLOTS_TEST=" in item for item in argv):
                raise RuntimeError("M029_CLIENT_128_DUPLICATE_COLD_INBOX_FLAG")
            argv.insert(2,"WBD_M0_029_INBOX_SLOTS_TEST="+str(self.client_trial_slots))
        return original_spawn(self,role,place,argv)

    def verified_client_start(self):
        # The frozen fixture's stage labels are 64/256/64. Only the actual
        # developer-only client Rust cold slot value is mapped 256->128.
        # Per-physical-generation readback below must prove the conversion.
        stage_slots=self.slots
        selected=128 if stage_slots==256 else 64
        self.client_trial_slots=selected
        # Force the original server setup + genuine native cold readback to
        # remain 64 in ALL legs. The original validation is NOT bypassed.
        self.slots=64
        try:
            lease=original_start(self)
        finally:
            self.slots=stage_slots
        log=self.logs["client"]
        if not g["ready"](log,"M0_PLAN029_NATIVE_INBOX_BOUND role=client",20):
            raise RuntimeError("M029_CLIENT_128_COLD_INBOX_RECEIPT_MISSING")
        text=log.read_text(errors="replace")
        rx=re.findall(
            r"M0_PLAN029_NATIVE_INBOX_BOUND role=client generation=(\d+) slots=(\d+) probe_only=1",text)
        if len(rx)!=1 or int(rx[0][0])<=0 or int(rx[0][1])!=selected:
            raise RuntimeError("M029_CLIENT_128_COLD_INBOX_NOT_ACTUALLY_APPLIED")
        server=self.logs["server"].read_text(errors="replace")
        srv=re.findall(
            r"M0_PLAN029_NATIVE_INBOX_BOUND role=server generation=(\d+) slots=(\d+) probe_only=1",server)
        if len(srv)!=1 or int(srv[0][0])<=0 or int(srv[0][1])!=64:
            raise RuntimeError("M029_CLIENT_128_SERVER_CONTROL_CAPACITY_CHANGED")
        verified.append({"phase":len(verified),"frozen_stage_slots":stage_slots,
                         "client_generation":int(rx[0][0]),
                         "client_inbox_slots":selected,
                         "server_generation":int(srv[0][0]),
                         "server_inbox_slots":64,
                         "native_cold_readback_verified":True})
        return lease

    def zero_impair(self):
        for dev in ("rcli0","rsrv0"):
            g["ns"](self.router,"tc","qdisc","replace","dev",dev,"root",
                    "netem","delay","0ms","loss","0%","limit","65536")
        return {dev:json.loads(g["ns"](self.router,"tc","-s","-j","qdisc",
                       "show","dev",dev).stdout) for dev in ("rcli0","rsrv0")}

    def client_zero_save(name,data):
        # The real fixture's internal A/B/A server_slots list is only a
        # stage identifier; public receipt names the actual changed END.
        # Deepcopy avoids altering original_main's internal final A/B/A
        # identity validation and never fabricates a successful Stop.
        result=copy.deepcopy(data)
        result["scenario"]="ZERO_LOSS_0MS_NATIVE_X86_64_CLIENT_ONLY_INBOX_128_ABA"
        # Exact real Rust cold readbacks and phase receipts, not a stale
        # inherited 256 label, are authoritative for the actual 128 trial.
        result["only_changed_setting"]="authenticated client Rust M1 inbox 64→128→64; server fixed64"
        result["netem_ge_stationary_parameters"]={
            "profile":"ZERO_ARTIFICIAL_LOSS","target_loss_pct":0.0,
            "oneway_extra_delay_ms":0}
        result["base_fixture_git_blob_sha"]=BASE_GIT_BLOB
        for i,row in enumerate(result.get("phases",[])):
            if i>=len(verified):
                raise RuntimeError("M029_CLIENT_128_NATIVE_RECEIPT_UNAVAILABLE")
            old_slots=row.pop("server_inbox_slots")
            if old_slots!=verified[i]["frozen_stage_slots"]:
                raise RuntimeError("M029_CLIENT_128_FROZEN_STAGE_MISMATCH")
            if i==1:row["name"]="inbox128_candidate"
            row.update(verified[i])
        original_save(name,result)

    if g["PHASES"]!=(
        ("original_before",64),("inbox256_candidate",256),("original_after",64)
    ):
        raise RuntimeError("M029_CLIENT_128_FROZEN_ABA_ORDER_CHANGED")
    Owned.spawn=client_inbox_spawn
    Owned.start_product=verified_client_start
    Owned.impair=zero_impair
    g["save"]=client_zero_save
    g["OUT"]=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"m029-x86-client-inbox-128-zero-abca"
    g["TMP"]=pathlib.Path(os.environ["RUNNER_TEMP"])/(
        "m029-x86-client-inbox-128-zero-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"])
    original_main()
    if len(verified)!=3 or [x["client_inbox_slots"] for x in verified]!=[64,128,64]:
        raise RuntimeError("M029_CLIENT_128_THREE_REAL_READBACKS_MISSING")
    print("M029_X86_CLIENT_ONLY_ZERO_REAL_GORUST_64_128_64_COMPLETED "
          "server_cold_control64=1 native_readbacks=3 product_gain=UNDECIDED",
          flush=True)

if __name__=="__main__":main()
