"""H2276: topology isolation and real Linux tc targeting, never product PASS."""
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import m0_h2276_three_runner_tcp as h


def identity(role, group="a", tail=None):
    return {"group": group, "role": role, "source_sha": "a" * 40,
            "run_id": "123456789", "topology": "TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM",
            "tail_ip": tail or {"client": "100.101.0.1", "relay": "100.101.0.2",
                                 "server": "100.101.0.3"}[role]}


class ExactDualTriplet(unittest.TestCase):
    def test_two_groups_share_workload_not_nodes(self):
        self.assertEqual(h.TIERS, (-1, 0, 1, 5))
        wf = (ROOT / ".github/workflows/qa-h2276-dual-win-relay-arm-tcp.yml").read_text()
        self.assertEqual(wf.count("group: [a, b]"), 3)
        self.assertIn("runs-on: windows-2025", wf)
        self.assertIn("runs-on: ubuntu-24.04-arm", wf)
        self.assertIn("runs-on: ubuntu-24.04", wf)
        self.assertEqual(wf.count("uses: tailscale/github-action@v4"), 3)
        self.assertIn("h2276-" + chr(36) + "{{ matrix.group }}-client-result", wf)

    def test_real_configure_relay_ready_receipt_reuses_exact_peer_token(self):
        # Regression: H2276 run44924127257 both relay jobs configured the
        # real Linux kernel then raised duplicate control_token in dict(**own).
        # Mock only OS calls: run the entire real Python configure_relay path.
        own = {**identity("relay"), "control_token": "same-existing-token"}
        client = identity("client")
        server = identity("server")
        calls = []
        with patch.object(h, "run", side_effect=lambda *args, **kw: calls.append(args)), \
             patch.object(h, "shaped", return_value={"stage_id": 0}), \
             patch.object(h, "ping_class", return_value={"status": "DIRECT_CANDIDATE"}):
            result = h.configure_relay(own, server, client)
        self.assertEqual(result["control_token"], own["control_token"])
        self.assertEqual(result["source_sha"], own["source_sha"])
        self.assertEqual(result["group"], "a")
        self.assertEqual(result["server_ip"], server["tail_ip"])
        self.assertEqual(result["client_ip"], client["tail_ip"])
        self.assertEqual(result["tcp_port"], h.PORT)
        self.assertEqual(result["role"], "relay")
        self.assertTrue(any("iptables" in args for args in calls))
        self.assertTrue(any("qdisc" in args for args in calls))

    def test_real_relay_config_disables_only_ephemeral_stateful_forwarding(self):
        own = {**identity("relay"), "control_token": "ephemeral"}
        commands = []
        with patch.object(h, "run", side_effect=lambda *a, **k: commands.append(a)), \
             patch.object(h, "shaped", return_value={"stage_id": 0}), \
             patch.object(h, "ping_class", return_value={"status": "DIRECT_CANDIDATE"}):
            h.configure_relay(own, identity("server"), identity("client"))
        self.assertIn(("sudo", "-n", "tailscale", "set",
                       "--stateful-filtering=false"), commands)

    def test_live_forwarding_counter_readback_is_scoped(self):
        from types import SimpleNamespace
        own = {**identity("relay"), "control_token": "scoped"}
        def fake(*args, **kwargs):
            return SimpleNamespace(stdout=(
                " pkts bytes target prot opt in out source destination\n"
                " 5 300 DNAT tcp -- tailscale0 * 100.101.0.1 100.101.0.2 "
                "tcp dpt:45902 to:100.101.0.3:45902\n"
            ), returncode=0)
        with patch.object(h, "run", side_effect=fake), \
             patch.object(h, "tc_read", return_value=[{"kind": "netem", "packets": 7}]):
            result = h.observed_relay_counters(own)
        self.assertEqual(result["kernel_tc"][0]["packets"], 7)
        self.assertEqual(result["owned_tcp_forward_rule_counters"]
                         ["nat_PREROUTING"]["matched_rules"][0]["packets"], 5)

    def test_relay_source_and_group_pair_must_be_identical(self):
        a = identity("relay")
        self.assertEqual(h.verify(a, identity("client"), "client"), "100.101.0.1")
        for bad in (
            {**identity("client"), "group": "b"},
            {**identity("client"), "source_sha": "b" * 40},
            {**identity("client"), "run_id": "123456788"},
            {**identity("client"), "tail_ip": a["tail_ip"]},
            {**identity("client"), "tail_ip": "8.8.8.8"},
            {**identity("client"), "role": "server"},
        ):
            with self.assertRaises(RuntimeError):
                h.verify(a, bad, "client")

    def test_kernel_nat_only_selected_tcp_service_and_known_three_peers(self):
        rules = h.command_plan("100.101.0.3", "100.101.0.1", "100.101.0.2")
        self.assertEqual(len(rules), 4)
        joined = " ".join(" ".join(r) for r in rules)
        self.assertIn("PREROUTING", joined)
        self.assertIn("DNAT", joined)
        self.assertIn("SNAT", joined)
        self.assertIn("--dport " + str(h.PORT), joined)
        self.assertNotIn("5202", joined)
        self.assertNotIn("tailscale0 -j", joined)
        for a in ("10.248.82.2", "0.0.0.0", "100.101.0.2"):
            with self.assertRaises(RuntimeError):
                h.command_plan(a, "100.101.0.1", "100.101.0.2")

    def test_limited_netem_zero_control_and_loss_tiers(self):
        calls = []
        with patch.object(h, "run", side_effect=lambda *x, **kw: calls.append(x)), \
             patch.object(h, "tc_read", return_value=[{"kind": "netem"}]):
            for tier in h.TIERS:
                result = h.shaped(tier)
                self.assertEqual(result["loss_pct"], max(tier, 0))
                self.assertEqual(result["one_way_delay_ms"], 0 if tier == -1 else 200)
            with self.assertRaises(RuntimeError):
                h.shaped(20)
        self.assertEqual(len(calls), 4)
        self.assertIn("0ms", calls[0])
        self.assertIn("200ms", calls[1])
        self.assertIn("1%", calls[2])
        self.assertIn("5%", calls[3])

    def test_workflow_never_calls_product_claim_without_original_owner(self):
        wf=(ROOT / ".github/workflows/qa-h2276-dual-win-relay-arm-tcp.yml").read_text()
        self.assertIn("NOT measured here", wf)
        self.assertIn("H2276_REAL_WINDOWS_TO_ARM_TUNNEL_TCP_FAILURE", wf)
        src=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        self.assertIn("product_go_tls_rust=\"NOT_RUN_THIS_PREFLIGHT\"", src)
        self.assertIn("tcp.server(", src)
        self.assertIn("tcp.client(", src)
        self.assertIn("H2276_SERVER_ALL_TCP_STAGES_PASS", src)


if __name__ == "__main__":
    unittest.main()
