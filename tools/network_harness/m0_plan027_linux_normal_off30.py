"""PLAN027 N: single independent real loss30 Normal outer-repair OFF control.
Reuse EXACT frozen product built for R OFF/ON; this action changes only
fixture/scenario. No restored repair and no synthetic loss/recovery claims.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.m0_plan027_linux_repair_pair import configuration
from tools.network_harness.runner import LinuxExperiment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--product-source", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    a = parser.parse_args()
    assert platform.machine() == "x86_64"
    assert len(os.environ["GITHUB_SHA"]) == 40 and len(a.product_source) == 40
    assert Path(a.scenario).name == "wl-outer-repair-10m-250ms-loss30-60s.json"
    scene = json.loads(Path(a.scenario).read_text())
    assert scene["schema_version"] == 1
    assert (scene["duration_s"], scene["warmup_s"], scene["drain_s"], scene["tun_mtu"]) == (60, 5, 10, 1400)
    for side in ("windows_to_linux", "linux_to_windows"):
        d = scene[side]
        assert (d["offered_mbps"], d["delay_ms"], d["loss_pct"]) == (10, 250, 30)
        assert [(x["udp_payload_bytes"], x["packets_weight"]) for x in d["packet_mix"]] == [
            (64, 10), (128, 15), (512, 25), (1200, 50)]
    bundle = Path(a.bundle).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["source"] == a.product_source and manifest["architecture"] == "x86_64"
    binaries = ("wbd-v4-client", "wbd-v4-server", "libwbd_engine.so")
    expected = {}
    for line in (bundle / "SHA256SUMS").read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        expected[name.lstrip("*")] = sha
    for name in binaries:
        assert hashlib.sha256((bundle / name).read_bytes()).hexdigest() == expected[name]
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    home = out / "bundle-A" / "fixed-build"
    home.mkdir(parents=True, exist_ok=True)
    for name in binaries:
        (home / name).symlink_to(bundle / name)
    # Reuse EXACT already-tested config/readback interface. The two scene
    # differences are real 30%-loss tc in each direction and a new case ID.
    zero = json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
    cfg = configuration(zero, a.product_source, int(os.environ["GITHUB_RUN_ID"]), False)
    cfg["id"] = "M0_PLAN027_N_NORMAL_10M_250MS_LOSS30_OFF"
    cfg["seed"] = scene["seed"]
    for direction in ("c2s", "s2c"):
        cfg["phases"][0][direction]["loss_pct"] = 30
    assert cfg["product"]["repair_enabled"] is False
    assert cfg["bundles"]["A"]["repair_enabled"] is False
    case = out / "leg-off-loss30"
    leg = LinuxExperiment(cfg, out / "bundle-A", case, "A").run()
    t = leg.get("telemetry", {})
    result = {"product_source": a.product_source,
              "fixture_source": os.environ["GITHUB_SHA"],
              "same_binary_as_R_pair": True,
              "scenario": scene["scenario_id"],
              "binary_sha256": {name: expected[name] for name in binaries},
              "scope": "Linux original Go TLS client+server Rust raw/TUN, actual iid tc loss30, 60s UDP-only",
              "native_result": leg.get("result"), "failures": leg.get("failures", []),
              "limits": leg.get("limits", []),
              "repair_off_native_readback": t.get("outer_repair_native_verified"),
              "policy_readback": t.get("recovery_policy_verified"),
              "owned_stop": t.get("stop_drained_both"),
              "owned_netns_cleanup": leg.get("cleanup", {}).get("owned_namespaces_absent"),
              "first_business": {}, "repair_F_R_IP_wire": {},
              "cpu_s": {}, "peak_rss_bytes": {}, "netem_drops": {},
              "verdict": "NOT_RUN"}
    valid = (leg.get("result") == "PASS_SCOPED_OBSERVATION"
             and t.get("outer_repair_native_verified") is True
             and t.get("recovery_policy_verified") is True
             and t.get("stop_drained_both") is True
             and leg.get("cleanup", {}).get("owned_namespaces_absent") is True)
    accounts = leg.get("v3_repair_accounting", {})
    for direction, role in (("c2s", "client"), ("s2c", "server")):
        rows = [row for row in leg.get("observed", [])
                if row.get("direction") == direction and row.get("phase") == "iid"]
        offered = sum(float(row.get("injected_app_mbps") or 0) for row in rows)
        arrived = sum(float(row.get("cohort_delivered_app_mbps") or 0) for row in rows)
        result["first_business"][direction] = {
            "offered_mbps": offered, "unique_delivered_mbps": arrived,
            "delivered_fraction": arrived / offered if offered else None}
        if offered < 9.5 or arrived <= 0:
            valid = False
        acc = accounts.get(direction, {})
        f, repair = acc.get("first_wire_bytes"), acc.get("conservative_charged_wire_bytes")
        result["repair_F_R_IP_wire"][direction] = {"F": f, "R": repair,
                "C": "NOT_MEASURED", "scope": "exact native M4 IP wire incl warmup"}
        if not isinstance(f, int) or f <= 0 or repair != 0:
            valid = False
        result["cpu_s"][role] = leg.get("measurement_cost", {}).get(role, {}).get("cpu_s")
        result["peak_rss_bytes"][role] = leg.get("host", {}).get("processes", {}).get(role, {}).get("rss_peak_bytes")
    snap = json.loads((case / "network-snapshots.json").read_text())
    before = next((v for v in snap if v["name"] == "before-iid"), None)
    after = next((v for v in snap if v["name"] == "measurement-end"), None)
    for role in ("client", "server"):
        def dropped(s):
            if s is None: return None
            q = [v for v in s["network"][role]["qdisc"] if v.get("kind") == "netem"]
            return q[0].get("drops") if len(q) == 1 else None
        b, e = dropped(before), dropped(after)
        count = e - b if isinstance(e, int) and isinstance(b, int) else None
        result["netem_drops"][role] = count
        if not isinstance(count, int) or count <= 0:
            valid = False
    result["verdict"] = ("PASS_SCOPED_REAL_LOSS30_REPAIR_OFF_CONTROL_NOT_RECOVERY"
                          if valid else "FAIL_OR_INCONCLUSIVE")
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PLAN027_N_NORMAL_OFF30_VERDICT", result["verdict"], flush=True)
    if not valid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
