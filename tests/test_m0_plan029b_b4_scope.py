"""029B B4: cheap hard gates before ONE original signed WinForms native Action."""
import ast
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class B4TrueGUIOriginalScope(unittest.TestCase):
    def test_no_legacy_two_generation_or_mock_product_pass(self):
        gui = (ROOT / "tools/m0_plan029b_b4_real_gui.cs").read_text()
        bridge = (ROOT / "tools/m0_plan029_gui_real_bridge.py").read_text()
        e2e = (ROOT / "tools/m0_wl_public_normal_e2e.py").read_text()
        for required in (
            "form.SetEditor(\"cn-domain-direct\",false)",
            'form.SetEditor("route-mode",ordinal==2?"bypass-lan-cn":"all")',
            "form.SaveEditor();",
            'Click(f,"连接 / 切换")',
            'Click(form,"断开连接")',
            'client.ValidateAsync',
            'WBD_WINDOWS_OS_APPLIED',
            'WBD_WINDOWS_CLIENT_READY',
            'PLAN029B_B4_REAL_GUI_OWNED_STOP_WAL_CLEAN',
            "QueryA(ordinal)",
            "Business(firstFake,ordinal,true)",
            "WaitGuestReady()",
            "Flush",
        ):
            if required == "Flush":
                self.assertIn('flush.StartInfo.Arguments="/flushdns"', gui)
            else:
                self.assertIn(required, gui)
        self.assertIn("m0_plan029b_b4_real_gui.cs", bridge)
        self.assertIn("plan029b-b4-three-real-receipt.json", bridge)
        self.assertIn("PLAN029B_B4_THREE_REAL_GUI_GENERATIONS_AND_STOPS_COMPLETE", e2e)
        self.assertIn("server_text.count(\"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443\")!=3", e2e)
        self.assertIn('exact("WBD_WINDOWS_CLIENT_READY")!=3', e2e)
        self.assertIn('exact("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS")!=3', e2e)
        self.assertIn('h1775_owned_cleanup(target=p029_tunnel_alias,tag="h2010")', e2e)
        ast.parse(e2e)
        ast.parse(bridge)

    def test_genuine_linux_dns_physical_vs_tunnel_and_retired_fake_wire(self):
        guest = (ROOT / "tools/m0_plan029b_b4_guest.py").read_text()
        ast.parse(guest)
        for gate in (
            'raw_socket("eth0")', 'raw_socket("wbdwl4")',
            'b"P29B4-G1"', 'b"P29B4-G2"', 'b"P29B4-G3"',
            'b"P29B4-STALE-G2"', 'b"P29B4-STALE-G3"',
            'b"\\xc6\\x12"', 'if peer[0] != expected',
            '"physical" if phase == "advanced" else "tun"',
            '"raw_old_fake_ipv4_egress": raw_fake',
            'len(observed) == 6',
        ):
            self.assertIn(gate, guest)
        # The real H2123 native guest failed before logging which query
        # caused an original WinForms DNS SERVFAIL. The first packet must
        # include only bounded header/hashed question provenance, and fail
        # closed; no blanket retry, foreign lane or silent fake DNS PASS.
        self.assertIn("PLAN029B_B4_FIRST_UNEXPECTED_DNS", guest)
        self.assertIn('hashlib.sha256(wire[12:]).hexdigest()[:24]', guest)
        self.assertIn('"qname_matches_cn_ticket": wire[12:] == question', guest)
        self.assertIn('peer[0] == lease and unrelated < 12', guest)
        # H2124 signed guest: app ID 2961 was correctly translated by
        # the original Rust owner to upstream ID 0001. Only the correct
        # original DNS socket, source, qname/qtype and generation sequence
        # qualify, and the guest echoes the upstream ticket unchanged.
        self.assertIn("PLAN029B_B4_ORIGINAL_DNS_UPSTREAM_TRANSACTION", guest)
        self.assertIn('"upstream_id": data[:2].hex()', guest)
        self.assertIn('"app_id_expected": app_ids[phase].hex()', guest)
        self.assertIn('if "ordinary_data" in observed:', guest)
        self.assertIn('if "ordinary_data" not in observed:', guest)
        self.assertIn('phase + "_dns" not in observed', guest)
        self.assertIn('first_dns_fault("wrong_original_kernel_dns_lane_or_source"', guest)
        self.assertIn('first_dns_fault("wrong_dns_flags_qname_or_qtype"', guest)
        self.assertIn('reply = data[:2] + b"\\x81\\x80', guest)
        self.assertNotIn('if ticket not in dns_ids:', guest)
        self.assertIn('raise RuntimeError("B4 original DNS first unexpected packet:', guest)
        self.assertIn("PLAN029B_B4_REAL_LINUX_EGRESS", guest)
        # H2123 actual signed first failure: physical CN A had no
        # positive answer and generic normal app used RFC1918 Direct;
        # this exact source must re-use the protected Tunnel public /32.
        e2e = (ROOT / "tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn('linux_app4=p029_tunnel_alias if p029_direct or p029_p1_policy or p029_game4_cn or p029b_b2 or p029b_b4', e2e)
        self.assertIn('if p029_p1_policy or p029_game4_cn or p029b_b4:', e2e)
        self.assertIn('PLAN029B_B4_FIRST_DNS_REPLY_FAILURE', (ROOT / "tools/m0_plan029b_b4_real_gui.cs").read_text())

    def test_exact_source_one_action_and_no_prior_matrices(self):
        workflow = (ROOT / ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        scope = (ROOT / "tools/m0_native_ci_scope.py").read_text()
        marker = "[plan029b-b4-gui-three-real]"
        self.assertIn(marker, workflow)
        self.assertIn(marker, scope)
        self.assertIn("WBD_PLAN029B_B4_GUI_THREE_GEN_SCENE:", workflow)
        self.assertIn("PLAN029B_B4_EXACT_ORIGINAL_GUEST_PHYSICAL_UDP53_OWNED_APPLIED", workflow)
        self.assertIn("hyperv-bootstrap-udp53-owned.json", workflow)
        self.assertIn("Recover H2050 exact owned WSL physical bootstrap UDP53 and TCP53", workflow)
        self.assertIn('"plan029b-b4-guest.log",', (ROOT / "tools/m0_wl_mode_evidence.py").read_text())
        self.assertIn("tests.test_m0_plan029b_b4_scope -v", workflow)
        self.assertIn("tools/m0_plan029b_b4_guest.py", workflow)
        self.assertIn("tools/m0_plan029b_b4_real_gui.cs", workflow)
        self.assertNotIn("[plan028-win-dual-original] [plan029b-b4-gui-three-real]", workflow)

    def test_three_actual_tls_children_and_protected_peer_synack(self):
        from tools.m0_wl_public_mss_contract import (
            verified_plan029b_b4_three_gui_child_mss as verify,
        )
        linux = [
            "V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=1 outer_config=1460 interface=1500 advertised_mss=1420 record_offer=1420 tun_planned=1389"
        ]
        win = []
        for number, port in enumerate((41031, 41032, 41033), 1):
            win += [
                "WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=1 mode=normal configured_outer_mtu=1460 physical_outer_mtu=1500 effective_outer_mtu=1460 local_advertised_mss=1420 inner_mtu_planned=1389 limiting_reason=configured_outer_ipv4 source=RUST_V1_REAL_OS",
                f"WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=1 configured_port=41031 source_port={port} original_peer_port=443 same_ip_reauth_safe_tuple={'false' if number == 1 else 'true'}",
                "WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=1 local_advertised_mss=1420 tcp_option_bytes=0204058c",
                "WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=1 peer_advertised_mss=1420 local_advertised_mss=1420",
            ]
            linux += [
                "V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=1420 tcp_option_bytes=0204058c",
                f"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443 active_detached_flows={number} auto_lease=0 original_TLS=1 Rust_M4=1",
            ]
        rows = verify("\n".join(win), "\n".join(linux), 1460)
        self.assertEqual(len(rows["generations"]), 3)
        self.assertEqual([row["windows_source_port"] for row in rows["generations"]],
                         [41031, 41032, 41033])
        with self.assertRaises(ValueError):
            verify("\n".join(win[:-4]), "\n".join(linux), 1460)
        with self.assertRaises(ValueError):
            verify("\n".join(win), "\n".join(linux[:-2]), 1460)
        duplicate = copy.copy(win)
        duplicate[5] = duplicate[1]
        with self.assertRaises(ValueError):
            verify("\n".join(duplicate), "\n".join(linux), 1460)
        bad_peer = copy.copy(win)
        bad_peer[11] = bad_peer[11].replace("1420", "1200", 1)
        with self.assertRaises(ValueError):
            verify("\n".join(bad_peer), "\n".join(linux), 1460)


if __name__ == "__main__":
    unittest.main()
