"""Cheap deterministic contracts + real socket traffic selfcheck. Actions only."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import stat
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.network_harness.config import Unsupported, fec_residual, netem_args, validate
from tools.network_harness.report import active_gap, summarize
from tools.network_harness.traffic import Histogram, HEADER, UDP, Worker
from tools.network_harness.artifacts import verify, sha, attested_recovered_product_build

ROOT = Path(__file__).resolve().parents[2]


def request():
    return json.loads((ROOT / "tests/network/request.json").read_text())


class Contracts(unittest.TestCase):
    def test_strict_request_and_unsupported_knobs(self):
        r = request()
        validate(r)
        for key, value in [("repair_ratio", .1), ("cipher", "aes128"), ("game_fec", "strong")]:
            bad = copy.deepcopy(r)
            bad["product"][key] = value
            with self.assertRaises(Unsupported):
                validate(bad)
        r["traffic"]["c2s_mbps"] = float("nan")
        with self.assertRaises(ValueError):
            validate(r)

    def test_full_run_source_tun_zero_drop_gate_and_snapshot_delta(self):
        from tools.network_harness.runner import source_tun_tx_drops_by_role
        request_data=request()
        request_data["acceptance"]["require_zero_source_tun_drops_full_run"]=True
        self.assertTrue(validate(request_data)["acceptance"]
                        ["require_zero_source_tun_drops_full_run"])
        request_data["acceptance"]["require_zero_source_tun_drops_full_run"]="true"
        with self.assertRaises(ValueError):
            validate(request_data)
        def snapshot(client,server):
            return {"network":{
                "client":{"links":[{"ifname":"wbntun0",
                    "stats64":{"tx":{"dropped":client}}}]},
                "server":{"links":[{"ifname":"wbntun0",
                    "stats64":{"tx":{"dropped":server}}}]}
            }}
        self.assertEqual(source_tun_tx_drops_by_role(
            snapshot(0,0),snapshot(7471,0)),{"client":7471,"server":0})
        self.assertEqual(source_tun_tx_drops_by_role(
            snapshot(7471,0),snapshot(7471,0)),{"client":0,"server":0})
        self.assertEqual(source_tun_tx_drops_by_role(
            snapshot(0,0),{"network":{}}),
            {"client":"NOT_OBSERVED","server":"NOT_OBSERVED"})

    def test_testonly_tun_root_qdisc_fq_pacing_vs_fqcodel_strict(self):
        r=request()
        r["network"]["tun_qdisc_profiles"]={"A":"fq_codel","B":"fq"}
        self.assertEqual(validate(r)["network"]["tun_qdisc_profiles"],
                         {"A":"fq_codel","B":"fq"})
        r["network"]["tun_qdisc_profiles"]["B"]="pfifo_fast"
        with self.assertRaises(ValueError):
            validate(r)
        r["network"]["tun_qdisc_profiles"]={"C":"fq"}
        with self.assertRaises(ValueError):
            validate(r)

    def test_warmup_rate_is_isolated_and_does_not_mutate_steady_offer(self):
        r=request()
        r["network"]["warmup_rate_scale_profiles"]={"A":1,"B":0.30}
        self.assertEqual(validate(r)["network"]["warmup_rate_scale_profiles"],
                         {"A":1,"B":0.30})
        r["network"]["warmup_rate_scale_profiles"]["B"]=1.4
        with self.assertRaises(ValueError):
            validate(r)
        r["network"]["warmup_rate_scale_profiles"]={"C":0.30}
        with self.assertRaises(ValueError):
            validate(r)

    def test_native_tun_ring_profile_is_bound_and_per_leg(self):
        q=request()
        q["network"]["tun_txqlen_profiles"]={"A":500,"B":1024}
        self.assertEqual(validate(q)["network"]["tun_txqlen_profiles"],
                         {"A":500,"B":1024})
        q["network"]["tun_txqlen_profiles"]["B"]=2048
        self.assertEqual(validate(q)["network"]["tun_txqlen_profiles"]["B"],2048)
        q["network"]["tun_txqlen_profiles"]["B"]=8192
        with self.assertRaises(ValueError):
            validate(q)
        q["network"]["tun_txqlen_profiles"]={"C":500}
        with self.assertRaises(ValueError):
            validate(q)

    def test_true_idle_phase_has_no_synthetic_probe_sends(self):
        r=request()
        r["traffic"]["probe_hz"]=0
        r["traffic"]["udp_share"]=1
        r["phases"][0]["rate_scale"]=0
        q=validate(r)
        self.assertEqual(q["traffic"]["probe_hz"],0)
        self.assertEqual(q["phases"][0]["rate_scale"],0)
        r["traffic"]["probe_hz"]=-1
        with self.assertRaises(ValueError):
            validate(r)

    def test_opt_in_v3_owner_timeline_strict_and_privacy_whitelist(self):
        from tools.network_harness.runner import product_marker_line
        good = request()
        good["network"]["v3_timeline"] = True
        self.assertTrue(validate(good)["network"]["v3_timeline"])
        good["network"]["v3_timeline"] = "true"
        with self.assertRaises(ValueError):
            validate(good)
        self.assertTrue(product_marker_line(
            "2026/10/24 V4_PUBLIC_TIMELINE role=client unix_ns=42 rx_records=3 tx_records=9"))
        self.assertTrue(product_marker_line(
            "2026/10/24 V4_PUBLIC_WORKER_CPU role=server rx_thread_cpu_ns=123 tx_thread_cpu_ns=34"))
        self.assertFalse(product_marker_line("TOKEN secret=DO_NOT_UPLOAD"))
        self.assertFalse(product_marker_line("V4_PRIVATE_TLS_PASSWORD secret=DO_NOT_UPLOAD"))

    def test_capacity_action_digest_source_fields_and_no_raw_body(self):
        from tools.network_harness.runner import capacity_action_digest
        leg = {"label": "A", "result": "INCONCLUSIVE",
               "limits": ["c2s: INVALID_INJECTOR_RATE"],
               "observed": [{"direction": "c2s", "protocol": "udp",
                   "phase": "steady", "target_app_mbps": 3.0,
                   "injected_app_mbps": 2.5, "send_lag_ms": {"p99_ms": 4.0},
                   "first_arrival_ms": {"p99_ms": 600},
                   "payload_secret": "DO_NOT_EXPOSE"}],
               "host": {"cpu_psi_some_peak": 0.0, "processes":
                   {"client": {"rss_peak_bytes": 17000000}}},
               "telemetry": {"original_tx_chain": {"client":
                   {"arena_failed": 0, "pre_read_deferred": 8}}}}
        report = capacity_action_digest(leg)
        self.assertEqual(report["observed"][0]["injected_mbps"], 2.5)
        self.assertEqual(report["host"]["processes"]["client"]["peak_rss_bytes"], 17000000)
        self.assertEqual(report["original_tx_chain"]["client"]["pre_read_deferred"], 8)
        self.assertNotIn("DO_NOT_EXPOSE", json.dumps(report))

    def test_isolated_tcp_window_profiles_and_source_tun_loss(self):
        from tools.network_harness.runner import source_tun_tx_drops_by_role
        a = request()
        a["network"]["tcp_window_profiles"]={"A":"large"}
        self.assertEqual(validate(a)["network"]["tcp_window_profiles"],{"A":"large"})
        a["network"]["tcp_window_profiles"]={"A":"huge"}
        with self.assertRaises(ValueError):
            validate(a)
        a["network"]["tcp_window_profiles"]={"C":"large"}
        with self.assertRaises(ValueError):
            validate(a)
        def snap(x,y):
            return {"network":{"client":{"links":[{"ifname":"wbntun0",
                "stats64":{"tx":{"dropped":x}}}]},
                "server":{"links":[{"ifname":"wbntun0",
                "stats64":{"tx":{"dropped":y}}}]}}}
        self.assertEqual(source_tun_tx_drops_by_role(snap(30,90),snap(45,90)),
            {"client":15,"server":0})
        self.assertEqual(source_tun_tx_drops_by_role(snap(30,90),snap(29,95)),
            {"client":"NOT_OBSERVED","server":5})
        self.assertEqual(source_tun_tx_drops_by_role({"network":{}},snap(0,0)),
            {"client":"NOT_OBSERVED","server":"NOT_OBSERVED"})

    def test_tcp_reordering_profile_is_bounded_test_only(self):
        r=request()
        r["network"]["tcp_reordering_profiles"]={"A":"baseline","B":"outer_repair_tolerant"}
        r["bundles"]["B"]=dict(r["bundles"]["A"])
        r["order"]="AB"
        self.assertEqual(validate(r)["network"]["tcp_reordering_profiles"]["B"],
                         "outer_repair_tolerant")
        r["network"]["tcp_reordering_profiles"]["B"]="unbounded"
        with self.assertRaises(ValueError): validate(r)

    def test_same_vm_legacy_new_policy_checked_per_frozen_bundle(self):
        from tools.network_harness.runner import verify_outer_recovery_policy
        expected = "outer-single-repair-v2"
        native = {role: {"policy": expected, "repair_attempt_limit": 1,
                          "shadow_limit": 131072, "retain_cap_us": 1500000}
                  for role in ("client", "server")}
        self.assertTrue(verify_outer_recovery_policy(expected, native))
        self.assertFalse(verify_outer_recovery_policy(expected, {"client": native["client"]}))
        self.assertFalse(verify_outer_recovery_policy(expected, {
            **native, "server": {**native["server"], "repair_attempt_limit": 2}}))
        self.assertIsNone(verify_outer_recovery_policy("legacy-two-repair-v1", {}))
        ab = request()
        ab["policy"] = expected
        ab["bundles"]["A"]["recovery_policy"] = "legacy-two-repair-v1"
        ab["bundles"]["B"] = dict(ab["bundles"]["A"], recovery_policy=expected)
        ab["order"] = "AB"  # Independent of current committed A-only observation request.
        valid = validate(ab)
        self.assertEqual(valid["bundles"]["A"]["recovery_policy"], "legacy-two-repair-v1")
        self.assertEqual(valid["bundles"]["B"]["recovery_policy"], expected)
        ab["bundles"]["B"]["recovery_policy"] = "unproven"
        with self.assertRaises(ValueError):
            validate(ab)

    def test_presets_are_complete_and_valid(self):
        base = request()
        catalog = json.loads((ROOT / "tests/network/scenarios.json").read_text())
        for case in catalog.values():
            r = copy.deepcopy(base)
            for key, value in case.items():
                r[key] = value
            validate(r)

    def test_fec_model(self):
        for p in [0, .01, .05, .3, 1]:
            self.assertAlmostEqual(fec_residual(16, 0, p), p)
            self.assertAlmostEqual(fec_residual(1, 2, p), p**3)
        self.assertLess(fec_residual(16, 8, .2), fec_residual(16, 4, .2))

    def test_asymmetric_seeded_loss(self):
        r = validate(request())
        d = r["phases"][0]["c2s"]
        d.update(delay_ms=150, jitter_ms=10, loss_pct=5, reorder_pct=2)
        a = netem_args(d, 123, 32768)
        self.assertIn("150ms", a)
        self.assertIn("5%", a)
        self.assertEqual(a[-2:], ["seed", "123"])
        self.assertNotIn("seed", netem_args(d, None, 32768))

    def test_bundle_source_platform_and_binary_tamper(self):
        bundle = request()["bundles"]["A"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fixed-build").mkdir()
            (root / "fixed-kernel-result").mkdir()
            hashes = {}
            for name in ["wbd-v4-client", "wbd-v4-server", "libwbd_engine.so"]:
                p = root / "fixed-build" / name
                p.write_bytes(b"\x7fELF\x02\x01" + bytes(12) + b"\x3e\x00")
                hashes[name] = sha(p)
            manifest = {"source_sha": bundle["source"], "run_id": bundle["run_id"],
                        "attempt": bundle["attempt"], "binaries_sha256": hashes}
            (root / "fixed-kernel-result/manifest.json").write_text(json.dumps(manifest))
            verify(root, bundle)
            (root / "fixed-build/libwbd_engine.so").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                verify(root, bundle)
            wrong = dict(bundle, source="0" * 40)
            with self.assertRaises(ValueError):
                verify(root, wrong)

    def test_arm_native_manifest_sha256sums_and_source_provenance(self):
        b = request()["bundles"]["A"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ["wbd-v4-client", "wbd-v4-server", "libwbd_engine.so"]
            hashes = {}
            for name in names:
                p = root / name
                p.write_bytes(b"\x7fELF\x02\x01" + bytes(12) + b"\xb7\x00")
                hashes[name] = sha(p)
            (root / "SHA256SUMS").write_text("".join(
                hashes[n] + "  " + n + "\n" for n in names))
            manifest = {"source": b["source"], "architecture": "aarch64",
                        "go_source": "1"*40, "isa_source": "2"*40,
                        "backend_requested": "native_fec_acceleration (pinned ISA-L static)"}
            (root / "manifest.json").write_text(json.dumps(manifest))
            (root / "_verified-origin.json").write_text(json.dumps({
                "source": b["source"], "run_id": b["run_id"], "attempt": b["attempt"],
                "artifact_id": b["artifact_id"]}))
            with patch("tools.network_harness.artifacts.platform.machine", return_value="aarch64"):
                verify(root, b)
                (root / "fixed-build").mkdir()
                for name in names:
                    (root / "fixed-build" / name).write_bytes((root / name).read_bytes())
                verify(root, b)
                for name in names:
                    self.assertTrue((root / "fixed-build" / name).stat().st_mode & stat.S_IXUSR,
                                    "ARM64 normalized binary must remain executable after hash verification")
                (root / "fixed-build" / names[0]).write_bytes(b"tamper")
                with self.assertRaises(ValueError):
                    verify(root, b)
                (root / "fixed-build" / names[0]).write_bytes((root / names[0]).read_bytes())
                with self.assertRaises(ValueError):
                    verify(root, dict(b, source="0"*40))
            if sys.platform == "linux" and os.uname().machine != "aarch64":
                with self.assertRaises(ValueError):
                    verify(root, b)  # Native ARM64 cannot pass on x86_64 runner

    def test_failed_builder_must_prove_only_optional_unit_failed(self):
        run = {"path": ".github/workflows/arm64-public-go-build.yml",
               "head_branch": "experiment/network-matrix-tuning",
               "event": "push", "status": "completed", "conclusion": "failure"}
        required = [
            {"name": "Exact source native ARM64 original Go and Rust bundle", "conclusion": "success"},
            {"name": "Verify product parity maximum row 0..19 on native ARM64", "conclusion": "failure"},
            {"name": "Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
             "conclusion": "success"},
        ]
        jobs = {"total_count": 2, "jobs": [
            {"name": "native-go-rust-bundle", "conclusion": "failure",
             "steps": required + [{"name": "Run actions/checkout@x", "conclusion": "success"}]},
            {"name": "native-linux-netns", "conclusion": "skipped"}]}
        self.assertTrue(attested_recovered_product_build(run, jobs))
        broken = copy.deepcopy(jobs)
        broken["jobs"][0]["steps"][0]["conclusion"] = "failure"
        self.assertFalse(attested_recovered_product_build(run, broken))
        broken = copy.deepcopy(jobs)
        broken["jobs"][0]["steps"].append({"name": "another hidden failure", "conclusion": "failure"})
        self.assertFalse(attested_recovered_product_build(run, broken))
        self.assertFalse(attested_recovered_product_build({**run, "path": "unexpected.yml"}, jobs))
        self.assertFalse(attested_recovered_product_build({**run, "conclusion": "success"}, jobs))
        bad = request()
        # A legitimate single-source scenario need not contain bundle B.
        # Construct an independent B for this schema-negative test.
        bad["bundles"]["B"] = dict(bad["bundles"]["A"])
        bad["bundles"]["B"]["step_attested_failure"] = "true"
        with self.assertRaises(ValueError):
            validate(bad)

    def test_real_fec_tx_pre_stop_marker_conserves_counts(self):
        from tools.network_harness.runner import public_fec_tx_snapshot
        row=("V4_PUBLIC_FEC2_TX role=server accepted=6 notready=0 "
             "full=1 partial=1 k1=1 k2_4=0 k5_12=0 k13_16=1 "
             "rplanned=22 rsent=20 expired=0 pressure_jobs=0 "
             "pressure_sources=0 unknown_capacity=0")
        self.assertEqual(public_fec_tx_snapshot(row)["k13_16"],1)
        # The sanitized product marker whitelist must preserve the numeric
        # FEC sender snapshot rather than treating a real result as unknown.
        from tools.network_harness.runner import product_marker_line
        self.assertTrue(product_marker_line(row))
        self.assertTrue(product_marker_line("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client"))
        self.assertFalse(product_marker_line("password=secret role=client"))
        self.assertIsNone(public_fec_tx_snapshot(""))
        self.assertIsNone(public_fec_tx_snapshot(row.replace("rsent=20","rsent=23")))
        self.assertIsNone(public_fec_tx_snapshot(row.replace("k1=1","k1=0")))

    def test_original_fec_m1_postloan_stage_exact_causal_split(self):
        from tools.network_harness.runner import public_fec_m1_stage,product_marker_line
        row=("V4_PUBLIC_FEC2_M1_STAGE role=client attempted=120 "
             "queued=100 not_ready=4 error=16 oversize=12 mode_skipped=3")
        self.assertTrue(product_marker_line(row))
        self.assertEqual(public_fec_m1_stage(row)["oversize"],12)
        self.assertIsNone(public_fec_m1_stage(""))
        self.assertIsNone(public_fec_m1_stage(row.replace("oversize=12","no_size=12")))
        self.assertIsNone(public_fec_m1_stage(row.replace("attempted=120","attempted=300")))
        self.assertEqual(public_fec_m1_stage(row.replace("attempted=120","attempted=119"))["queued"],100)
        # No endpoint, packet size, ack number or original plaintext appears.
        self.assertNotIn("secret",str(public_fec_m1_stage(row)))

    def test_original_fec_m1_tun_ingress_real_numeric_contract(self):
        from tools.network_harness.runner import public_fec_m1_ingress,product_marker_line
        row=("V4_PUBLIC_FEC2_M1_INGRESS role=client read_ipv4=1200 "
             "small_loaned=1170 small_arena_fail=28 jumbo=2 rejected=5")
        self.assertTrue(product_marker_line(row))
        self.assertEqual(public_fec_m1_ingress(row)["small_arena_fail"],28)
        self.assertIsNone(public_fec_m1_ingress(""))
        self.assertIsNone(public_fec_m1_ingress(row.replace("read_ipv4=1200","read_ipv4=20")))
        self.assertIsNone(public_fec_m1_ingress(row.replace("small_loaned=1170","bad_loan=1170")))
        self.assertEqual(public_fec_m1_ingress(row.replace("read_ipv4=1200","read_ipv4=1199"))["read_ipv4"],1199)

    def test_original_m4_ipv4_packet_class_proof_not_business_goodput(self):
        from tools.network_harness.runner import public_fec_rx_ip_class,product_marker_line
        line=("V4_PUBLIC_FEC2_RX_IP_CLASS role=client sys_udp=12 rec_udp=8 "
              "sys_tcp=3 rec_tcp=7 other_ip=0 tcp_ack_only=6 "
              "tcp_data=4 tcp_other=0")
        self.assertTrue(product_marker_line(line))
        self.assertEqual(public_fec_rx_ip_class(line)["rec_tcp"],7)
        self.assertEqual(public_fec_rx_ip_class(line)["tcp_ack_only"],6)
        self.assertIsNone(public_fec_rx_ip_class(""))
        self.assertIsNone(public_fec_rx_ip_class(line.replace("rec_udp=8","missing=8")))
        self.assertIsNone(public_fec_rx_ip_class(line.replace("tcp_ack_only=6","tcp_ack_only=12")))
        self.assertNotIn("private",str(public_fec_rx_ip_class(line)))

    def test_original_fec_m3_m4_rx_numeric_receipt_contract(self):
        from tools.network_harness.runner import public_fec_rx_proof,product_marker_line
        row=("V4_PUBLIC_FEC2_RX_PROOF role=server source_seen=1809 "
             "source_accepted=1710 parity_seen=2800 parity_accepted=2710 "
             "systematic_candidate=1710 recovered_candidate=49 "
             "systematic_tun=1690 recovered_tun=47 tun_failed=22 "
             "decoder_rejected=111 admission_disabled=78")
        self.assertTrue(product_marker_line(row))
        self.assertEqual(public_fec_rx_proof(row)["recovered_tun"],47)
        self.assertIsNone(public_fec_rx_proof(""))
        self.assertIsNone(public_fec_rx_proof(row.replace("recovered_tun=47","renamed=47")))
        self.assertIsNone(public_fec_rx_proof(row.replace("recovered_tun=47","recovered_tun=50")))
        self.assertIsNone(public_fec_rx_proof(row.replace("source_seen=1809","source_seen=9")))
        self.assertIsNone(public_fec_rx_proof(row.replace("admission_disabled=78","admission_disabled=90000")))

    def test_tcp_kernel_cwnd_unacked_byte_progress_aggregates_without_endpoints(self):
        from tools.network_harness.runner import tcp_kernel_progress_counts
        input_text=(
            "ESTAB 0 0 secret-client:5901 secret-server:5902\n"
            "  cubic rto:804 cwnd:3 unacked:2 notsent:900 bytes_sent:1200 "
            "bytes_acked:200 bytes_received:5 retrans:1/4 snd_wnd:1000\n"
            "ESTAB 0 0 secret-client:5903 secret-server:5904\n"
            "  cubic rto:402 cwnd:7 unacked:1 notsent:300 bytes_sent:500 "
            "bytes_acked:400 retrans:0/2 snd_wnd:2000\n"
        )
        x=tcp_kernel_progress_counts(input_text)
        self.assertEqual(x["established"],2)
        self.assertEqual(x["bytes_sent"],{"sampled_sockets":2,"sum":1700,"max":1200})
        self.assertEqual(x["bytes_acked"]["sum"],600)
        self.assertEqual(x["notsent"]["sum"],1200)
        self.assertEqual(x["unacked"]["sum"],3)
        self.assertEqual(x["retrans"]["total_sum"],6)
        self.assertEqual(x["bytes_received"]["sampled_sockets"],1)
        self.assertNotIn("secret-",str(x))
        missing=tcp_kernel_progress_counts("ESTAB 0 0 private:1 private:2\n")
        self.assertEqual(missing["established"],1)
        self.assertEqual(missing["bytes_acked"],"NOT_OBSERVED")
        self.assertEqual(tcp_kernel_progress_counts(""),{"established":0,
            **{k:"NOT_OBSERVED" for k in ("bytes_sent","bytes_acked",
                "bytes_received","notsent","unacked","cwnd","snd_wnd","rto",
                "mss","advmss","pmtu","rcvmss","ssthresh","reordering",
                "rcv_space","dsack_dups","retrans","rtt_ms",
                "congestion_algorithm_counts")}})
        enriched=tcp_kernel_progress_counts(
            "ESTAB 0 0 sensitive:111 sensitive:222\n"
            "  cubic wscale:7,7 rtt:401.4/3.5 mss:1289 pmtu:1329 "
            "advmss:1289 cwnd:43 unacked:49 snd_wnd:539648 "
            "ssthresh:24 reordering:3 rto:1743\n")
        self.assertEqual(enriched["mss"]["sum"],1289)
        self.assertEqual(enriched["pmtu"]["max"],1329)
        self.assertEqual(enriched["rtt_ms"]["max"],401.4)
        self.assertEqual(enriched["congestion_algorithm_counts"],{"cubic":1})
        self.assertNotIn("sensitive",str(enriched))

    def test_original_m2_numeric_proof_and_tcp_state_only_no_addresses(self):
        from tools.network_harness.runner import (
            public_fec_m2_proof, product_marker_line, tcp_socket_state_counts)
        row=("V4_PUBLIC_FEC2_M2_PROOF role=client accepted=113 not_sent=2 "
             "uncertain=1 unknown_2s=17 unknown_8s=25 covered_2s=88 "
             "covered_8s=74 reverse_reports=31 first_censored=0 cover_censored=1")
        self.assertTrue(product_marker_line(row))
        self.assertEqual(public_fec_m2_proof(row)["unknown_2s"], 17)
        self.assertIsNone(public_fec_m2_proof(""))
        self.assertIsNone(public_fec_m2_proof(row.replace("reverse_reports=31","no_report=31")))
        self.assertIsNone(public_fec_m2_proof(row.replace("cover_censored=1","cover_censored=3")))
        counts=tcp_socket_state_counts("SYN-SENT 0 1 private:333 private:444\n"
                                       "ESTAB 0 0 private:333 private:444\n"
                                       "ESTAB 0 0 private:333 private:444\n")
        self.assertEqual(counts, {"SYN-SENT":1, "ESTAB":2})
        self.assertNotIn("private", str(counts))

    def test_real_fec_failure_reasons_negative_unknown(self):
        from tools.network_harness.runner import public_fec_failure_reasons,product_marker_line
        row=("V4_PUBLIC_FEC2_FAILURE role=client source_payload=0 source_arena=7 "
             "source_seal=1 parity_policy=0 parity_arena=15 parity_seal=0 "
             "parity_m4_noncopy=2 source_m4_noncopy=3")
        self.assertTrue(product_marker_line(row))
        self.assertEqual(public_fec_failure_reasons(row)["source_arena"],7)
        self.assertIsNone(public_fec_failure_reasons(""))
        self.assertIsNone(public_fec_failure_reasons(row.replace("source_arena=7","no_data=7")))

    def test_safe_startup_failure_diagnostic_redacts_private_input(self):
        from tools.network_harness.runner import startup_diagnostic
        raw = "password=secret_value route-key=do-not-persist\nerror: no such device"
        d = startup_diagnostic(raw)
        self.assertIn("KERNEL_NO_DEVICE", d["safe_failure_classes"])
        self.assertNotIn("secret_value", json.dumps(d))
        self.assertNotIn("do-not-persist", json.dumps(d))

    def test_histogram_empty_overflow_and_sparse_gap(self):
        h = Histogram()
        self.assertIsNone(h.result()["p99_ms"])
        h.add(1.01)
        self.assertEqual(h.result()["p99_ms"], 1.1)
        h.add(40000)
        self.assertIsNone(h.result()["p99_ms"])
        self.assertEqual(active_gap([1, 0, 0, 1], [1, 0, 0, 1]), 0)
        self.assertEqual(active_gap([1, 1, 1], [0, 0, 1]), 20)

    def test_payload_integrity_duplicate_and_phase_accounting(self):
        r = validate(request())
        with tempfile.TemporaryDirectory() as tmp:
            w = Worker(r, "client", "127.0.0.2", "127.0.0.3", 45901, tmp + "/a.json", 1000000000)
            packet = w.packet(UDP, 1, 0, 64, 1000000000)
            w.receive(packet, 1001000000, "udp")
            w.receive(packet, 1002000000, "udp")
            w.receive(packet[:-1] + bytes([packet[-1] ^ 1]), 1003000000, "udp")
            self.assertEqual(w.stats["udp"][1]["rx_packets"], 1)
            self.assertEqual(w.stats["udp"][1]["duplicates"], 1)
            self.assertEqual(sum(s["invalid"] for s in w.stats["udp"]), 1)

    @unittest.skipUnless(os.environ.get("GITHUB_ACTIONS") == "true", "all execution validation belongs in Actions")
    def test_independent_udp_tcp_duplex_and_real_missing_accounting(self):
        r = request()
        r.update(warmup_s=1, drain_s=1, phases=[{"name": "test", "seconds": 2}])
        # Synthetic socket selfcheck has no product or retransmission receipt.
        # Do not inherit pressure-request repair gates into this independent contract.
        r["acceptance"]["require_retransmission"] = False
        r["acceptance"].pop("max_p99_ms", None)
        r["acceptance"].pop("max_active_gap_ms", None)
        r["traffic"].update(c2s_mbps=1, s2c_mbps=1, udp_share=.5, sizes=[[64, 1], [800, 1]])
        r = validate(r)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "config.json").write_text(json.dumps(r))
            start = time.monotonic_ns() + 3_000_000_000
            procs = []
            try:
                for role, local, peer in [("server", "127.0.0.3", "127.0.0.2"), ("client", "127.0.0.2", "127.0.0.3")]:
                    procs.append(subprocess.Popen([sys.executable, str(ROOT / "tools/network_harness/traffic.py"),
                        "--role", role, "--local", local, "--peer", peer, "--config", str(tmp / "config.json"),
                        "--output", str(tmp / (role + ".json")), "--start-ns", str(start)]))
                for p in procs:
                    self.assertEqual(p.wait(timeout=15), 0)
            finally:
                for p in procs:
                    if p.poll() is None:
                        p.kill()
                        p.wait()
            c, s = [json.loads((tmp / (role + ".json")).read_text()) for role in ["client", "server"]]
            for sender, receiver in [(c, s), (s, c)]:
                for proto in ["udp", "tcp"]:
                    self.assertGreater(sender["stats"][proto][1]["tx_packets"], 100)
                    self.assertEqual(sender["stats"][proto][1]["tx_packets"], receiver["stats"][proto][1]["rx_packets"])
            tele = {"stop_drained_both": True, "effective_config_verified": True, "repair_packets": 0}
            report = summarize(r, c, s, tele, {})
            self.assertEqual(report["result"], "PASS_SCOPED_OBSERVATION", report["limits"])
            report = summarize(r, c, s, tele, {"cpu_psi_some_peak": 36, "cpu_psi_some_mean": 7})
            self.assertEqual(report["result"], "PASS_SCOPED_OBSERVATION")
            self.assertTrue(report["warnings"])
            report = summarize(r, c, s, tele, {"cpu_psi_some_peak": 36, "cpu_psi_some_mean": 30})
            self.assertEqual(report["performance_comparison"], "INCONCLUSIVE_HOST_CONTENTION")
            self.assertFalse(report["stop_heavier_resource_cases"])
            s["stats"]["udp"][1]["rx_packets"] -= 2
            r["acceptance"]["max_loss_pct"] = 0
            report = summarize(r, c, s, tele, {})
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["missing_after_drain"] == 2 for x in report["observed"]))


if __name__ == "__main__":
    unittest.main()
