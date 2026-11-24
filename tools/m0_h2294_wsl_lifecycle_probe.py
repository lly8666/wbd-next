#!/usr/bin/env python3
"""H2294 test-fixture only: one real Windows2025 WSL guest PID/Stop smoke.

No WBD socket, fake traffic, FEC, driver, VPN, product state or global sysctl.
The separate 2x3Runner job remains the ONLY genuine throughput qualification.
"""
import os
import pathlib
import sys
import time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import m0_h2293_true_product_fec_loss as test

def main():
    test.require(os.name=="nt","WSL_KEEPER_SMOKE_WINDOWS_ONLY")
    for generation in range(2):
        child,marker,boot=test.start_owned_wsl_liveness("a")
        verified=False
        try:
            for k in range(3):
                seen=test.require_owned_wsl_liveness(
                    child,marker,boot,f"SMOKE_GEN{generation}_CHECK{k}")
                test.require(seen["guest_boot_id_unchanged"],
                    "WSL_KEEPER_SMOKE_BOOT_CHANGE")
                time.sleep(0.25)
            verified=True
        finally:
            test.stop_owned_wsl_liveness(child,marker)
        test.require(verified,"WSL_KEEPER_SMOKE_NOT_VERIFIED")
        print("H2294_EXACT_WINDOWS_WSL_PID_STOP_PASS "+
            str(generation),flush=True)
    print("H2294_WINDOWS_ONLY_WSL_TWO_GENERATION_KEEPER_TRUE_STOP_PASS",
          flush=True)

if __name__=="__main__":
    main()
