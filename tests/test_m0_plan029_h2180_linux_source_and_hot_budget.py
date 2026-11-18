"""Permanent cheap governance guards after H2177 genuine dual Linux ISA PASS.

Never dispatch network or infer a new qualification from these local file checks.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = "docs/evidence/M0/PLAN029-H2177-LINUX-X86-ARM64-TWO-ENDPOINT-FIVE-NATIVE-PASS-20261118.json"
SOURCE = "3cc095e38d98fd1a9b2a8f00835b113bc434c9e1"


def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class LinuxSignedSourceAndGovernanceBudget(unittest.TestCase):
    def test_h2177_archived_native_receipt_is_two_real_isa_times_five(self):
        e = data(EVIDENCE)
        self.assertEqual(SOURCE, e["source_sha"])
        self.assertEqual(SOURCE, e["same_exact_source_sha"])
        self.assertEqual(SOURCE, e["action"]["exact_source_sha"])
        self.assertEqual("success", e["action"]["conclusion"])
        self.assertEqual(10, e["action"]["successful_native_sessions"])
        self.assertEqual("PASS_SCOPED_TEN_ACTUAL_LINUX_NATIVE_TCP_UDP_TWO_ENDPOINTS",
                         e["qualification"])
        self.assertEqual(["aarch64", "x86_64"],
                         sorted(a["architecture"] for a in e["architectures"]))
        for arch in e["architectures"]:
            self.assertEqual(SOURCE, arch["build_source_sha"])
            self.assertTrue(arch["original_binary_set_verified"])
            self.assertTrue(arch["one_build_reused_for_five_independent_sessions"])
            self.assertEqual(
                {"normal", "fixed", "auto", "game2", "game4-fixed6"},
                {x["name"] for x in arch["case_results"]})
            for row in arch["case_results"]:
                self.assertEqual("PASS_SCOPED_NATIVE_LINUX_TWO_ENDPOINTS",
                                 row["result"])
                self.assertEqual("PASS", row["real_linux_kernel_udp_two_directions"])
                self.assertEqual("PASS", row["real_linux_kernel_tcp_two_directions"])
                self.assertEqual("PASS_BOTH", row["original_both_owned_stop"])

    def test_live_cursor_refs_must_identify_exact_same_signed_source(self):
        cursor = data(".governance/workstreams/M0/cursor.json")
        for path in cursor["evidence_refs"]:
            evidence = data(path)
            self.assertEqual(cursor["last_tested_source"], evidence["source_sha"])
        self.assertLessEqual(len(cursor["context_refs"]), data(".governance/policy.json")["max_cursor_refs"])

    def test_read_set_keeps_existing_32k_budget_without_bypass(self):
        project = data(".governance/project.json")
        policy = data(".governance/policy.json")
        registry = data(".governance/registry.json")
        self.assertEqual(32768, policy["max_hot_bytes"])
        for role in registry["roles"]:
            if role["state"] != "active":
                continue
            read = list(dict.fromkeys(project["hot_read_set"] +
                                      [role["prompt"], role["cursor"]]))
            self.assertLessEqual(len(read), policy["max_hot_files"])
            size = sum((ROOT / path).stat().st_size for path in read)
            self.assertLessEqual(size, policy["max_hot_bytes"], (role["id"], size))


if __name__ == "__main__":
    unittest.main()
