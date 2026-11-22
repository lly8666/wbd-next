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
        self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"), 2)
        self.assertIn("runs-on: ubuntu-24.04\n    timeout-minutes: 5", wf)
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

    def test_direct_path_parser_keeps_derp_even_with_nonzero_exit(self):
        from types import SimpleNamespace
        with patch.object(h, "run", return_value=SimpleNamespace(
            stdout="pong from runner (100.101.0.2) via DERP(iad) in 40ms\n",
            returncode=1)):
            row=h.ping_class("100.101.0.2")
        self.assertEqual(row["status"], "DERP_OR_RELAY_LIMIT")
        self.assertEqual(row["run_returncode"], 1)

    def test_relay_os_role_requires_native_arm_linux(self):
        self.assertIn("aarch64", h.meta.__code__.co_consts.__str__())

    def test_reuse_proven_tailnet_tcp_and_udp_ports(self):
        self.assertEqual(h.PORT, 18727)
        self.assertEqual(h.tcp.PORT, 18727)
        self.assertEqual(h.CONTROL_PORT, 4789)

    def test_relay_config_preserves_tailnet_firewall(self):
        own = {**identity("relay"), "control_token": "ephemeral"}
        commands = []
        with patch.object(h, "run", side_effect=lambda *a, **k: commands.append(a)), \
             patch.object(h, "shaped", return_value={"stage_id": 0}), \
             patch.object(h, "ping_class", return_value={"status": "DIRECT_CANDIDATE"}):
            h.configure_relay(own, identity("server"), identity("client"))
        self.assertFalse(any("stateful-filtering" in str(a)
                             for command in commands for a in command))

    def test_live_forwarding_counter_readback_is_scoped(self):
        from types import SimpleNamespace
        own = {**identity("relay"), "control_token": "scoped"}
        def fake(*args, **kwargs):
            return SimpleNamespace(stdout=(
                " pkts bytes target prot opt in out source destination\n"
                " 5 300 DNAT tcp -- tailscale0 * 100.101.0.1 100.101.0.2 "
                "tcp dpt:18727 to:100.101.0.3:18727\n"
            ), returncode=0)
        with patch.object(h, "run", side_effect=fake), \
             patch.object(h, "tc_read", return_value=[{"kind": "netem", "packets": 7}]):
            result = h.observed_relay_counters(own)
        self.assertEqual(result["kernel_tc"][0]["packets"], 7)
        self.assertEqual(result["owned_tcp_forward_rule_counters"]
                         ["nat_PREROUTING"]["matched_rules"][0]["packets"], 5)

    def test_h2279_clean_path_uses_identical_windows_and_arm_real_tcp(self):
        relay={"tail_ip":"100.101.0.2","relay_ip":"100.101.0.2",
               "client_ip":"100.101.0.1"}
        server={"tail_ip":"100.101.0.3"}
        # Legacy H2279 stage routing must be tested under its own mode;
        # H2282 intentionally takes precedence only when WINDOW_AB is enabled.
        with patch.object(h, "WINDOW_AB", False), patch.object(h, "CAPACITY_H2284", False):
            with patch.dict(h.os.environ, {"WBD_H2279_CAPACITY_AB":"1"}):
                self.assertEqual(h.active_stages(),("direct",-1))
            with patch.dict(h.os.environ, {"WBD_H2279_CAPACITY_AB":"0"}):
                self.assertEqual(h.active_stages(),h.TIERS)
        self.assertEqual(h.client_tcp_target("direct",relay,server),
                         server["tail_ip"])
        self.assertEqual(h.client_tcp_target(-1,relay,server),
                         relay["tail_ip"])
        self.assertEqual(h.server_expected_tcp_peer("direct",relay),
                         relay["client_ip"])
        self.assertEqual(h.server_expected_tcp_peer(-1,relay),
                         relay["relay_ip"])
        wf=(ROOT/".github/workflows/qa-h2276-dual-win-relay-arm-tcp.yml").read_text()
        self.assertIn("WBD_H2279_CAPACITY_AB: \"1\"",wf)
        self.assertEqual(wf.count("[m0-029-h2279-clean-path]"),3)

    def test_h2280_nat_egress_reverse_must_match_relay_ip_not_arm(self):
        own = {**identity("relay"), "control_token": "verify-real-tc"}
        calls = []
        with patch.object(h, "run", side_effect=lambda *a, **k: calls.append(a)), \
             patch.object(h, "shaped", return_value={"stage_id": 0}), \
             patch.object(h, "ping_class", return_value={"status":"DIRECT_CANDIDATE"}):
            h.configure_relay(own, identity("server"), identity("client"))
        tc_filter = [x for x in calls if x[:4] ==
                     ("sudo","-n","tc","filter")]
        self.assertEqual(len(tc_filter),2)
        forward,reverse = tc_filter
        self.assertIn("1:3",forward)
        self.assertIn("1:4",reverse)
        self.assertIn("100.101.0.2/32",reverse)  # post-NAT relay src
        self.assertIn("100.101.0.1/32",reverse)  # return client dst
        self.assertNotIn("100.101.0.3/32",reverse)  # wrong old pre-NAT src
        qdiscs=[x for x in calls if x[:5] ==
                ("sudo","-n","tc","qdisc","replace")]
        self.assertEqual(len(qdiscs),1)  # shaped is mocked
        self.assertIn("bands",qdiscs[0])
        self.assertEqual(qdiscs[0][qdiscs[0].index("bands")+1],"4")

    def test_h2280_true_two_direction_kernel_packet_loss_or_fail_closed(self):
        def snap(forward,reverse,drop_f=0,drop_r=0):
            return [
                {"kind":"prio","handle":"1:","packets":forward+reverse},
                {"kind":"netem","handle":"30:","parent":"1:3",
                 "packets":forward,"drops":drop_f},
                {"kind":"netem","handle":"40:","parent":"1:4",
                 "packets":reverse,"drops":drop_r},
            ]
        old=snap(0,0)
        passed=h.netem_phase_receipt(old,snap(900,120,10,2),1)
        self.assertEqual(passed["status"],
            "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED")
        self.assertEqual(passed["per_direction"]["win_to_arm"]["intentional_netem_drops"],10)
        self.assertEqual(passed["per_direction"]["arm_to_win"]["egress_packets"],120)
        with self.assertRaisesRegex(RuntimeError,"ARM_TO_WIN_NO_REAL_TRAFFIC"):
            h.netem_phase_receipt(old,snap(900,0,10,0),1)
        with self.assertRaisesRegex(RuntimeError,"ARM_TO_WIN_LOSS_NO_ACTUAL_DROPS"):
            h.netem_phase_receipt(old,snap(900,120,10,0),1)
        with self.assertRaisesRegex(RuntimeError,"NETEM_TWO_DIRECTION_READBACK_ABSENT"):
            h.netem_phase_receipt(old,snap(900,120,10,2)[:2],1)
        with self.assertRaisesRegex(RuntimeError,"WIN_TO_ARM_NO_REAL_TRAFFIC"):
            h.netem_phase_receipt(old,snap(0,120),0)


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
             patch.object(h, "relay_resource_sample",
                          return_value={"at_monotonic":1.0,"host_allcore":[0,0],
                                        "cores":{"cpu0":[0,0]},
                                        "tailscaled_cpu_s_by_pid":{"123":0.0}}), \
             patch.object(h, "tc_read", return_value=[
                 {"kind": "netem", "parent": "1:3", "handle": "30:"},
                 {"kind": "netem", "parent": "1:4", "handle": "40:"}]):
            for tier in h.TIERS:
                result = h.shaped(tier)
                self.assertEqual(result["loss_pct"], max(tier, 0))
                self.assertEqual(result["one_way_delay_ms"], 0 if tier == -1 else 200)
                self.assertTrue(result["real_bidir_kernel_netem"])
            with self.assertRaises(RuntimeError):
                h.shaped(20)
        self.assertEqual(len(calls), 8)
        self.assertTrue(all("0ms" in c for c in calls[:2]))
        self.assertTrue(all("200ms" in c for c in calls[2:4]))
        self.assertTrue(all("1%" in c for c in calls[4:6]))
        self.assertTrue(all("5%" in c for c in calls[6:8]))
        self.assertEqual([c[c.index("parent")+1] for c in calls],
                         ["1:3","1:4"] * 4)

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
