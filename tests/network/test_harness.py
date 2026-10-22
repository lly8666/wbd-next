"""Cheap deterministic contracts + real socket traffic selfcheck. Actions only."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.network_harness.config import Unsupported, fec_residual, netem_args, validate
from tools.network_harness.report import active_gap, summarize
from tools.network_harness.traffic import Histogram, HEADER, UDP, Worker
from tools.network_harness.artifacts import verify, sha

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
                (root / "fixed-build" / names[0]).write_bytes(b"tamper")
                with self.assertRaises(ValueError):
                    verify(root, b)
                (root / "fixed-build" / names[0]).write_bytes((root / names[0]).read_bytes())
                with self.assertRaises(ValueError):
                    verify(root, dict(b, source="0"*40))
            if sys.platform == "linux" and os.uname().machine != "aarch64":
                with self.assertRaises(ValueError):
                    verify(root, b)  # Native ARM64 cannot pass on x86_64 runner

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
