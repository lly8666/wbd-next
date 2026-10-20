"""Actions main-source attestation of the precise frozen M4 Windows integration.

These tests verify Git blob provenance, not native WFP execution or product ON.
The original source and Windows 2022 GUI smoke are independently qualified.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
M4_FROZEN_SOURCE = "e359fde5703cc7b92ac4cfcb09d79f388d55ce93"
ORIGINAL_GO_SOURCE = "a7a82db31fe736ffedee330795a3234d358f1984"
EXPECTED_M4_IMPORTED_BLOBS = {
    "r0/go_overlay/assembly/assemble.py": "4d4d64390c8025a56fc54c783c4bbf908b151b19",
    "r0/go_overlay/assembly/manifest.json": "ebe2beac0aa5317eddf3c2d7db5d833d48ea01eb",
    "r0/go_overlay/assembly/test_assemble.py": "bd6914be073a57394275122cf5d8bd02a88f12e9",
    "r0/go_overlay/cmd/wbd-client/control_windows_test.go": "4ac427a84135efcc6f92c8fd3561a812f2ec302b",
    "r0/go_overlay/cmd/wbd-client/n4_entry_windows_test.go": "1f6854e6d9e2ad27e34d4958cb04ee8c3cd8517d",
    "r0/go_overlay/cmd/wbd-client/n4_network_cancel_windows_test.go": "a930b8129ac620947571eb34b1239af329ea5543",
    "r0/go_overlay/cmd/wbd-client/native_owner_slot_windows_test.go": "e6d39932c112bf47db25ffb127d82f114fad1ad6",
    "r0/go_overlay/internal/configfile/fec2_product_test.go": "774976b765cfd16638f866ef8c07bbd33c13abe6",
    "r0/go_overlay/internal/runtimeentry/r0_admission_mode_test.go": "c40d8c2c62af709f2ab251713ea7538d60d12869",
    "r0/go_overlay/internal/runtimeentry/r0_admission_mode.go": "3528d71f988ec252503bbca25dccb2f35970ef12",
    "r0/go_overlay/internal/runtimeentry/r0_fec2_product_adapter.go": "2dbb06dcb5c33878c450a594e56345b281ad6186",
    "r0/go_overlay/internal/windowsclient/native_admin_preroute_real_crash_windows_test.go": "18876a185c2d1504379e81f9e5622dfbdf6f367a",
    "r0/go_overlay/internal/windowsclient/native_admin_unified_wal_windows_test.go": "4407375879b7e00edb4458dba033a552006cc99a",
    "r0/go_overlay/internal/windowsclient/native_orphan_ghost_dns_windows_test.go": "00dc19131a5dc4ddeff7610fbb5cbaf82ec844fd",
    "r0/go_overlay/internal/windowsclient/native_orphan_ghost_dns_windows.go": "985be09054322e183693644e225f492ed0019a81",
    "r0/go_overlay/internal/windowsclient/native_orphan_ghost_lease_audit_windows_test.go": "918bb01ad25c520e41271ac27882d99255fc3792",
    "r0/go_overlay/internal/windowsclient/native_orphan_ghost_lease_audit_windows.go": "ec228a8b103fe60c8338b2c05fb328df947c0282",
    "r0/go_overlay/internal/windowsclient/native_orphan_persisted_preroute_windows.go": "888d51375480b5f90134e5f910fa03292d5aaa4f",
    "r0/go_overlay/internal/windowsclient/native_orphan_pnp_probe_windows_test.go": "151bd2e59ecd4ce744d615e722ff40bce6d8184f",
    "r0/go_overlay/internal/windowsclient/native_orphan_pnp_probe_windows.go": "fe60f3297a1860e0ca915d827235b283dc3407c6",
    "r0/go_overlay/internal/windowsclient/native_product_entry_windows_test.go": "9866a5815f91d4678b5c30fab544aa7567e2e3ee",
    "r0/go_overlay/internal/windowsclient/native_product_entry_windows.go": "27e3d2721dd98a87806ed3eb12e7636584f043f7",
    "r0/go_overlay/internal/windowsclient/native_product_preflight_windows_test.go": "e13390c864e6631c619139a919d54632e9296147",
    "r0/go_overlay/internal/windowsclient/native_product_preflight_windows.go": "bfe2eb69305b1599b0798b92aa38a3ff282ea529",
    "r0/go_overlay/internal/windowsclient/native_product_status_windows_test.go": "c9157436a57ea16500484ca4a72a1214968cd57c",
    "r0/go_overlay/internal/windowsclient/native_product_status_windows.go": "83452baab8358f0f7e0be5527e54fc8e6360248f",
    "r0/go_overlay/internal/windowsclient/native_unified_assembly_windows_test.go": "f9f48f9412cf3699a3d4cd773943d7e96da1efe7",
    "r0/go_overlay/internal/windowsclient/native_unified_assembly_windows.go": "5ecc75d43e333d5826a3ecffa8d38e6146f1a3f2",
    "r0/go_overlay/internal/windowsclient/native_unified_network_transaction.go": "1e02718d9b9b7f80c8f1f54a8b8d3cbfe11ae28f",
    "r0/go_overlay/internal/windowsclient/native_wfp_exact_arm_windows_test.go": "0cca3e225ea95932eab09666cf5195107bd61351",
    "r0/go_overlay/internal/windowsclient/native_wfp_exact_arm_windows.go": "f46b85b56d5c5a318c400b7cbab30a6032de5f01",
    "r0/go_overlay/scripts/fec2_assembly_smoke.py": "3e8e10976e00667892fef91e4393824a57dd0d5c",
    "r0/go_overlay/scripts/fec2_native_bundle_probe.py": "44beacf5e1fb4f41f969f67d92eaa02ee269c9da",
    "r0/go_overlay/scripts/fec2_windows_gui_smoke.ps1": "c2617fedd954c75c7d4809fad42dba265611f599"
}

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw).hexdigest()

class OriginalGoWinFormsFrozenImport(unittest.TestCase):
    def test_frozen_m4_34_git_blobs_not_rewritten_by_main(self):
        self.assertEqual(len(EXPECTED_M4_IMPORTED_BLOBS), 34)
        for relative, expected in EXPECTED_M4_IMPORTED_BLOBS.items():
            with self.subTest(relative=relative):
                actual = ROOT / relative
                self.assertTrue(actual.is_file(), f"not imported: {relative}")
                self.assertEqual(git_blob_sha(actual.read_bytes()), expected,
                    "M4 source modified without new exact product provenance: " + relative)

    def test_37_manifest_operations_and_product_fail_closed_contract(self):
        m = json.loads((ROOT / "r0/go_overlay/assembly/manifest.json").read_text())
        self.assertEqual(m["legacy_source"], ORIGINAL_GO_SOURCE)
        ops = m["operations"]
        self.assertEqual(len(ops), 37)
        self.assertEqual(sum(x["kind"] == "create" for x in ops), 17)
        for op in ops:
            with self.subTest(path=op["path"]):
                self.assertIn(op["kind"], ("create", "replace"))
                self.assertEqual(len(op["result_blob"]), 40)
                if op["kind"] == "create":
                    created = ROOT / op["overlay_path"]
                    self.assertTrue(created.is_file(), f"missing original Go overlay {created}")
                    self.assertEqual(git_blob_sha(created.read_bytes()), op["result_blob"])
        native = (ROOT / "r0/go_overlay/internal/windowsclient/native_product_entry_windows.go").read_text()
        self.assertIn("production native WFP Apply and authenticated Stop have not been qualified", native)
        self.assertIn("func N4NativeNetworkReady(", native)
        self.assertIn("ErrN4NativeGuard", native)
        print("M0_FROZEN_M4_WINDOWS_OVERLAY_GIT_BLOBS_EXACT_MAIN_PASS_NATIVE_WFP_PRODUCT_NOT_RUN")

if __name__ == "__main__":
    unittest.main()
