"""PLAN027 R: two real Linux original-Go TLS/Rust Normal legs on ONE VM, OFF then ON.
The only changed input between legs is outer repair. No new product algorithm,
no synthetic first delivery, and no CPU speedup claim from this measurement.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.fec_w167_dual_arch_matrix import _config
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id, enabled):
    assert scene["schema_version"] == 1
    assert scene["scenario_id"] == "plan027-h539-normal-10m-250ms-loss0-60s"
    assert (scene["duration_s"], scene["warmup_s"], scene["drain_s"],
            scene["tun_mtu"]) == (60, 5, 10, 1400)
    mix = [(64, 10), (128, 15), (512, 25), (1200, 50)]
    for side in ("windows_to_linux", "linux_to_windows"):
        direction = scene[side]
        assert (direction["offered_mbps"], direction["delay_ms"],
                direction["loss_pct"], direction["tc_rate_mbps"]) == (10, 250, 0, None)
        assert [(r["udp_payload_bytes"], r["packets_weight"])
                for r in direction["packet_mix"]] == mix
    config = _config("normal_off", "normal", "off", 1, 0, source,
                     run_id, "amd64", traffic_mbps=10)
    config["id"] = "M0_PLAN027_R_NORMAL_10M_250MS_ZERO_" + ("ON" if enabled else "OFF")
    config["seed"] = scene["seed"]
    config["product"]["repair_enabled"] = enabled
    config["traffic"].update(c2s_mbps=10, s2c_mbps=10, udp_share=1.0,
                             sizes=[list(x) for x in mix], deadline_ms=6000)
    config["warmup_s"] = 5
    config["drain_s"] = 10
    config["phases"] = [{"name": "iid", "seconds": 60,
                         "c2s": {"delay_ms": 250, "loss_pct": 0, "rate_mbps": 0},
                         "s2c": {"delay_ms": 250, "loss_pct": 0, "rate_mbps": 0}}]
    # ON may legitimately send zero repairs on a 0%-loss link.
    config["acceptance"]["require_retransmission"] = False
    config["acceptance"]["max_repair_fresh_pct"] = 10
    config["bundles"]["A"].update(repair_enabled=enabled,
                                  require_go_rx_handoff=True)
    config = validate(config)
    # The real locally built product is verified from manifest/hash, not a
    # fictitious Actions artifact locator entered into a runtime config.
    config["bundles"]["A"] = {"source": source,
                               "recovery_policy": "outer-opportunistic-v3",
                               "repair_enabled": enabled,
                               "require_go_rx_handoff": True}
    return config


def leg_summary(leg, enabled):
    telemetry = leg.get("telemetry", {})
    accounts = leg.get("v3_repair_accounting", {})
    result = {"product_result": leg.get("result"),
              "failures": leg.get("failures", []),
              "limits": leg.get("limits", []),
              "repair_enabled_requested": enabled,
              "repair_enabled_native_verified": telemetry.get("outer_repair_native_verified"),
              "native_policy_verified": telemetry.get("recovery_policy_verified"),
              "owned_stop": telemetry.get("stop_drained_both"),
              "owned_namespaces_absent": leg.get("cleanup", {}).get("owned_namespaces_absent"),
              "first_business": {}, "outer_ip_wire": {},
              "cpu_s": {}, "rss_peak_bytes": {}}
    valid = (leg.get("result") == "PASS_SCOPED_OBSERVATION"
             and telemetry.get("outer_repair_native_verified") is True
             and telemetry.get("recovery_policy_verified") is True
             and telemetry.get("stop_drained_both") is True
             and leg.get("cleanup", {}).get("owned_namespaces_absent") is True)
    for direction in ("c2s", "s2c"):
        rows = [r for r in leg.get("observed", [])
                if r.get("phase") == "iid" and r.get("direction") == direction]
        offered = sum(float(r.get("injected_app_mbps") or 0) for r in rows)
        arrived = sum(float(r.get("cohort_delivered_app_mbps") or 0) for r in rows)
        result["first_business"][direction] = {
            "offered_mbps": offered, "unique_delivered_mbps": arrived,
            "delivered_fraction": arrived / offered if offered else None,
            "traffic": "real_udp_only_64_128_512_1200"}
        if offered < 9.5 or arrived < offered * .999:
            valid = False
        account = accounts.get(direction, {})
        f, r = account.get("first_wire_bytes"), account.get("conservative_charged_wire_bytes")
        result["outer_ip_wire"][direction] = {
            "F_full_warmup_plus_steady": f, "R_charged_full_warmup_plus_steady": r,
            "R_over_F": r / f if type(r) is int and type(f) is int and f > 0 else None,
            "C": "NOT_MEASURED_IP_WIRE", "scope": "Linux original raw M4 IP wire, not L2"}
        if (not isinstance(f, int) or f <= 0 or not isinstance(r, int)
                or r < 0 or (not enabled and r != 0) or r > .1 * f):
            valid = False
    for role in ("client", "server"):
        result["cpu_s"][role] = leg.get("measurement_cost", {}).get(role, {}).get("cpu_s")
        result["rss_peak_bytes"][role] = leg.get("host", {}).get("processes", {}).get(role, {}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role], (int, float)):
            valid = False
    result["verdict"] = "PASS_SCOPED_MEASUREMENT" if valid else "FAIL_OR_INCONCLUSIVE"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    assert platform.machine() == "x86_64"
    source = os.environ["GITHUB_SHA"]
    assert len(source) == 40
    assert Path(args.scenario).name == "plan027-h539-normal-10m-250ms-loss0-60s.json"
    scene = json.loads(Path(args.scenario).read_text())
    bundle = Path(args.bundle).resolve()
    base = Path(args.out).resolve()
    base.mkdir(parents=True, exist_ok=True)
    binaries = ("wbd-v4-client", "wbd-v4-server", "libwbd_engine.so")
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["source"] == source and manifest["architecture"] == "x86_64"
    expected = {}
    for line in (bundle / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        expected[name.lstrip("*")] = digest
    for name in binaries:
        assert (bundle / name).is_file()
        assert hashlib.sha256((bundle / name).read_bytes()).hexdigest() == expected[name]
    home = base / "bundle-A" / "fixed-build"
    home.mkdir(parents=True, exist_ok=True)
    for name in binaries:
        (home / name).symlink_to(bundle / name)
    results = {"source": source, "scenario": scene["scenario_id"],
               "scenario_switch": "Normal original Linux outer repair OFF then ON, same VM",
               "platform": "Linux amd64 original Go TLS client+server Rust raw/TUN in owned netns",
               "binary_sha256": {name: expected[name] for name in binaries},
               "avg_udp_payload_bytes": 753.6,
               "theory": {"offered_mbps_each_direction": 10,
                          "approx_pps_each_direction": 1659,
                          "business_bdp_bytes_at_rtt_500ms_each_direction": 625000,
                          "inflight_business_packets_approx": 830,
                          "R_F_steady_limit": .10},
               "legs": {}, "cost_delta": {}, "verdict": "NOT_RUN"}
    try:
        for label, enabled in (("OFF", False), ("ON", True)):
            cfg = configuration(scene, source, int(os.environ["GITHUB_RUN_ID"]), enabled)
            leg = LinuxExperiment(cfg, base / "bundle-A", base / ("leg-" + label.lower()), "A").run()
            results["legs"][label] = leg_summary(leg, enabled)
            # Both product Stop and namespace cleanup must complete before
            # next leg. A failed first leg must NOT contaminate an ON comparison.
            if results["legs"][label]["verdict"] != "PASS_SCOPED_MEASUREMENT":
                break
        if len(results["legs"]) == 2:
            off, on = results["legs"]["OFF"], results["legs"]["ON"]
            results["cost_delta"] = {
                role: {"on_minus_off_cpu_s": on["cpu_s"][role] - off["cpu_s"][role],
                       "share_of_on_cpu": (on["cpu_s"][role] - off["cpu_s"][role]) /
                       on["cpu_s"][role] if on["cpu_s"][role] else None,
                       "on_minus_off_peak_rss_bytes":
                       (on["rss_peak_bytes"][role] - off["rss_peak_bytes"][role]
                        if isinstance(on["rss_peak_bytes"][role], int)
                        and isinstance(off["rss_peak_bytes"][role], int) else None)}
                for role in ("client", "server")}
            results["verdict"] = "PASS_SCOPED_PAIRED_COST_OBSERVATION_NOT_OPTIMIZATION" 
            results["limitations"] = ["Order OFF->ON only; reverse once only if decision noise requires",
                                      "CPU includes Go+Rust together, no language attribution",
                                      "Only Linux two-OS UDP Normal zero loss; no Windows/Game/ON combination PASS",
                                      "F and R include warmup plus measurement, CPU covers only measurement",
                                      "Control wire C and per-flow TCP p99 are NOT_MEASURED"]
        else:
            results["verdict"] = "FAIL_OR_INCONCLUSIVE_FIRST_LEG"
    finally:
        (base / "result.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
        print("PLAN027_R_NORMAL_PAIRED_VERDICT", results["verdict"], flush=True)
    if results["verdict"] != "PASS_SCOPED_PAIRED_COST_OBSERVATION_NOT_OPTIMIZATION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
