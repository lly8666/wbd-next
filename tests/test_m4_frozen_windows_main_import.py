"""Exact original M4 Git-object integration evidence; NOT Windows OS product validation."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_GO = "a7a82db31fe736ffedee330795a3234d358f1984"
M4_FROZEN = "e359fde5703cc7b92ac4cfcb09d79f388d55ce93"
PINNED_FILES = {
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

M0_AUTHORIZED_CURRENT = {
    "r0/go_overlay/internal/runtimeentry/r0_fec2_product_adapter.go": "948ff4c1456af24aa9ea845c1b6d866b9dd25bb8",
    "r0/go_overlay/internal/realityfront/fec_v2_policy.go": "76a707bf71abbcbed58c37c8cf7b2965e069da30",
    "r0/go_overlay/internal/realityfront/fec_v2_policy_test.go": "b9ef571fdbe523ca18ff807b7eb73d19c48f8967",
}

def object_sha(data):
    header = b"blob " + str(len(data)).encode("ascii") + bytes([0])
    return hashlib.sha1(header + data).hexdigest()

class M4FrozenOverlay(unittest.TestCase):
    def test_import_all_frozen_original_go_windows_source(self):
        self.assertEqual(len(PINNED_FILES), 34)
        for relative, expected in PINNED_FILES.items():
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file())
                # M4 frozen sha remains immutable in PINNED_FILES. M0 later
                # explicitly superseded the live path after PLAN020 ownership transfer.
                self.assertEqual(object_sha(path.read_bytes()),
                                 M0_AUTHORIZED_CURRENT.get(relative, expected))

    def test_original_go_manifest_and_guard_remain_exact(self):
        obj = json.loads((ROOT / "r0/go_overlay/assembly/manifest.json").read_text())
        self.assertEqual(obj["legacy_source"], ORIGINAL_GO)
        self.assertEqual(len(obj["operations"]), 37)
        creates = [x for x in obj["operations"] if x["kind"] == "create"]
        self.assertEqual(len(creates), 17)
        live = json.loads((ROOT / "r0/go_overlay/assembly/manifest-plan020-m0.json").read_text())
        self.assertEqual(live["legacy_source"], ORIGINAL_GO)
        live_creates = {x["overlay_path"]: x for x in live["operations"]
                        if x["kind"] == "create"}
        self.assertEqual(set(M0_AUTHORIZED_CURRENT) & set(PINNED_FILES),
                         {"r0/go_overlay/internal/runtimeentry/r0_fec2_product_adapter.go"})
        for row in creates:
            with self.subTest(path=row["overlay_path"]):
                path = row["overlay_path"]
                # The original M4 result_blob remains exact in the unchanged
                # manifest; PLAN020 assembly uses a separately pinned M0
                # overlay blob only for these three superseded live files.
                if path in M0_AUTHORIZED_CURRENT:
                    self.assertIn(path, live_creates)
                    self.assertEqual(live_creates[path]["result_blob"],
                                     M0_AUTHORIZED_CURRENT[path])
                expected = M0_AUTHORIZED_CURRENT.get(path, row["result_blob"])
                self.assertEqual(object_sha((ROOT / path).read_bytes()), expected)
        native = (ROOT / "r0/go_overlay/internal/windowsclient/native_product_entry_windows.go").read_text()
        self.assertIn("func N4NativeNetworkReady(", native)
        self.assertIn("production native WFP Apply and authenticated Stop have not been qualified", native)
        print("M0_PLAN014_34_HISTORIC_M4_SHA_PINS_AND_3_EXACT_M0_CURRENT_OVERRIDES_PASS_NETWORK_NOT_RUN")

if __name__ == "__main__":
    unittest.main()
