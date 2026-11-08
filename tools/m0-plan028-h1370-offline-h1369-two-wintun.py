#!/usr/bin/env python3
"""H1370 strictly OFFLINE audit of H1369 original real Windows two signed Wintun devices.
No native driver setup, no UDP injection and no rerun: original 4-file artifact only.
"""
import argparse,json,pathlib,re

SOURCE="5b63dffa62efcfa0642031cc80bd7c902bd46780"
NATIVE_RESULT="PASS_SCOPED_REAL_TWO_SIGNED_WINDOWS_WINTUN_NATIVE_KERNEL_UDP_ISOLATED_STOP_NO_AUTH"
def assess(root):
    receipt=json.loads((root/"two-wintun-native.json").read_text())
    source=json.loads((root/"source.json").read_text())
    assembly=json.loads((root/"assembly.json").read_text())
    log=(root/"two-wintun-native.log").read_text(errors="replace")
    assert receipt["source_sha"]==source["source_sha"]==SOURCE
    assert source["run_id"]==42450303401
    assert receipt["classification"]==NATIVE_RESULT
    assert receipt["real_signed_wintun_devices"]==2
    for field in (
      "distinct_original_GUID_LUID_IFINDEX_alias",
      "real_windows_udp_app_A_and_B",
      "B_native_kernel_app_after_A_stop",
      "B_windows_udp_socket_reverse_ring_after_A_stop",
      "exact_both_native_stops_and_stale_denial",
    ):
      assert receipt[field] is True,field
    assert receipt["native_copied_A_B"]==[1,2]
    assert receipt["native_B_received"]>=1
    for field in ("original_tls_rust_authentication","original_npcap_outer_wire",
      "single_shared_product_server443","two_original_product_accounts",
      "original_windows_global_routes_wfp"):
      assert receipt[field]=="NOT_RUN",field
    assert assembly["legacy_source"]=="a7a82db31fe736ffedee330795a3234d358f1984"
    assert assembly["overlay_source"]=="b53b5dac422a634cdd82178a29071f9f9f0ae5e7"
    assert "=== RUN   TestM0PLAN028TwoSignedWindowsWintunKernelSocketIsolation" in log
    assert re.search(r"--- PASS: TestM0PLAN028TwoSignedWindowsWintunKernelSocketIsolation \([0-9.]+s\)",log)
    assert re.search(r"(?m)^PASS\s*$",log)
    assert "M0_PLAN028_H1369_TWO_REAL_SIGNED_WINTUN_NATIVE_KERNEL_UDP_AND_STOP_ISOLATION_PASS" in log
    assert "result" not in receipt
    assert source["native_udp_log_exists"] is False
    assert source["native_udp_receipt_exists"] is False
    return {
      "schema_version":1,"original_ci_run":42450303401,
      "original_ci_conclusion":"failure",
      "original_artifact_id":13605785603,
      "source_sha":SOURCE,"original_go_donor_sha":assembly["legacy_source"],
      "frozen_m4_assembly_sha":assembly["overlay_source"],
      "network_rerun":False,
      "classification":NATIVE_RESULT,
      "native_original_go_test":"PASS_TEST_ORIGINAL_RAW",
      "two_original_real_signed_windows_wintun_devices":2,
      "real_windows_udp_app_A_B_and_B_after_A_stop":True,
      "real_windows_udp_reverse_B_after_A_stop":True,
      "both_original_native_ring_stop_and_stale_denial":True,
      "native_copied_A_B":[1,2],"real_B_ring_received":receipt["native_B_received"],
      "ci_reporter_external_fault":"After original real Windows test PASS, copied PLAN020 reporter wrongly reads nonexistent receipt['result'] while actual H1369 schema uses receipt['classification']; copied source.json obsolete native-udp filenames show false although original renamed JSON and log are present.",
      "original_ci_fail_preserved":True,
      "unqualified_original_product":["original_TLS_Rust_authentication","original_Npcap_outer_wire",
        "two_actual_product_accounts_one_server443","global_WFP_and_routes",
        "user_Connected_or_full_WinForms"],
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    args=p.parse_args()
    out=assess(pathlib.Path(args.art))
    path=pathlib.Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print("H1370_OFFLINE_ORIGINAL_H1369_TWO_REAL_WIN_NATIVE_WINTUN_AND_B_ISOLATED_STOP_PASS",flush=True)
if __name__=="__main__":main()
