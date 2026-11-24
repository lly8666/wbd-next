"""H2285 two triplets: real Windows guest Linux kernel route gate, NOT WBD TLS."""
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2285_windows_wsl_route as h


class H2285NativeWindowsWSL2Routing(unittest.TestCase):
    def test_exact_nat_scoped_original_vethernet_to_direct_arm_kernel_relay(self):
        win="172.28.32.1"
        guest="172.28.32.2"
        relay="100.101.20.3"
        rules=h.nat_rules(win,guest,relay)
        self.assertEqual(len(rules),4)
        self.assertEqual([r[r.index("-I")+1] for r in rules],
                         ["PREROUTING","POSTROUTING","FORWARD","FORWARD"])
        self.assertIn(relay+":18727"," ".join(rules[0]))
        self.assertIn("-i eth0"," ".join(rules[0]))
        self.assertIn("-o eth0"," ".join(rules[1]))
        self.assertIn("MASQUERADE"," ".join(rules[1]))
        self.assertNotIn("--dport 443"," ".join(" ".join(r) for r in rules))
        for rule in rules:
            old=h.reversible_rule(rule)
            self.assertIn("-D",old)
            self.assertNotIn("-I",old)
            self.assertNotIn("-F",old)
            self.assertNotIn("-X",old)
            self.assertEqual(len(old),len(rule)-1)
        with self.assertRaises(RuntimeError):
            h.nat_rules(win,guest,"8.8.8.8")
        with self.assertRaises(RuntimeError):
            h.nat_rules("8.8.8.8",guest,relay)

    def test_true_nat_phase_counter_requirement_and_no_forged_tcp(self):
        rows={
          "nat_PREROUTING":[{"packets":2,"bytes":112}],
          "nat_POSTROUTING":[{"packets":2,"bytes":112}],
          "filter_FORWARD":[{"packets":22,"bytes":9042}]
        }
        self.assertEqual(h.nat_live_receipt(rows)["status"],
                         "REAL_WSL2_KERNEL_DNAT_SNAT_COUNTERS_POSITIVE")
        with self.assertRaises(RuntimeError):
            h.nat_live_receipt({"nat_PREROUTING":rows["nat_PREROUTING"],
                                "nat_POSTROUTING":[{"packets":0}]})
        with self.assertRaises(RuntimeError):
            h.nat_live_receipt({"nat_PREROUTING":[],
                                "nat_POSTROUTING":rows["nat_POSTROUTING"]})

    def test_own_original_arm_kernel_sysctl_restored_even_if_native_app_fails(self):
        own={"role":"server","group":"a","source_sha":"a"*40,
             "run_id":"444444","topology":"TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM",
             "tail_ip":"100.101.20.4"}
        relay={"role":"relay","group":"a","source_sha":"a"*40,
             "run_id":"444444","topology":"TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM",
             "tail_ip":"100.101.20.3","relay_ip":"100.101.20.3"}
        commands=[]
        def run(*args,**kw):
            commands.append(args)
            return SimpleNamespace(stdout="4194304\n")
        with patch.object(h.core,"run",side_effect=run), \
             patch.object(h.tcp,"server",side_effect=RuntimeError("synthetic server failure")):
            with self.assertRaisesRegex(RuntimeError,"synthetic server failure"):
                h.server(own,relay)
        restored=[args for args in commands if "net.core.rmem_max=4194304" in args or
                  "net.core.wmem_max=4194304" in args]
        self.assertEqual(len(restored),2)
        self.assertEqual(len([args for args in commands if
                              any("=16777216" in str(x) for x in args)]),2)

    def test_source_identical_two_independent_groups_reuse_original_core_artifacts(self):
        p=(ROOT/".github/workflows/qa-h2285-dual-wsl2-arm-route.yml").read_text()
        self.assertEqual(p.count("group: [a, b]"),3)
        self.assertEqual(p.count("runs-on: windows-2025"),1)
        self.assertEqual(p.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(p.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(p.count("[m0-029-h2285-wsl2-arm-route]"),3)
        self.assertIn("PASS_H2285_NATIVE_WSL2_L3_FORWARD_TO_INDEPENDENT_ARM_TCP_SCOPED",p)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",p)
        self.assertIn("No fake WBD driver/TLS/Go/Rust assertion",h.__doc__ or "")
        self.assertIn("NOT measured here",p)
        self.assertIn("H2285_REAL_ARM_TCP_SERVER_DONE",p)
        self.assertNotIn("PASS_FULL_PRODUCT",p)


if __name__=="__main__":
    unittest.main()
