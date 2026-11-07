#!/usr/bin/env python3
"""H1319 one SOURCE ARM64 real 180s five-client preterminal one-way audit.

Reconcile H1318 actual failed CI's directional FEC oracle with its original
real product/network artifact and original ELF SHA256. Never dispatch network
or edit an old Action conclusion.
"""
import argparse
import hashlib
import json
import pathlib
import re
import runpy
import struct

SOURCE = "4c12b5209a08a7eda4066256163f7a9f1c0cea93"
DONOR = "a7a82db31fe736ffedee330795a3234d358f1984"


def qualify(original, build):
    artifact = pathlib.Path(original) / "fixed-kernel-result"
    bpath = pathlib.Path(build)
    m = json.loads((artifact.parent / "fixed-build" / "manifest.json").read_text())
    other = json.loads((bpath / "manifest.json").read_text())
    assert m == other and m["source_sha"] == SOURCE
    assert m["original_go_sha"] == DONOR and m["architecture"] == "native_aarch64"
    assert m["go"] == "1.23.12" and m["rust"] == "1.85.1"
    for name, digest in m["sha256"].items():
        buf = (bpath / name).read_bytes()
        assert buf[:4] == b"\x7fELF" and struct.unpack_from("<H", buf, 18)[0] == 183
        assert hashlib.sha256(buf).hexdigest() == digest, name

    # This entry point is the SAME original H1316 real app, rotations,
    # per-lease queue, 30% real netem, zero reverse UDP/TCP/probe and
    # 750ms gap acceptance; its backend sender was fixed for DOWNLINK.
    one_way = runpy.run_path(
        str(pathlib.Path(__file__).with_name(
            "m0-plan028-h1316-oneway-native-report.py")))["check"]
    app = one_way(artifact, SOURCE)
    assert app["native_isal_quanta"] > 1000
    assert app["dave_client_native_ISAL_decoded"] > 0
    assert app["dave_client_no_reverse_FEC_tx_quanta"] is True

    blackhole = json.loads((artifact / "h1318-erin-native-health-blackhole.json").read_text())
    plan = json.loads((artifact / "h1250-matrix-plan.json").read_text())
    assert blackhole["type"] == "ORIGINAL_SERVER_TO_CLIENT_PHYSICAL_VETH_EGRESS"
    assert blackhole["client"] == "erin" and blackhole["application_direction"] == "uplink"
    assert blackhole["loss_during_preterminal_percent"] == 100
    assert blackhole["loss_after_restore_percent"] == 30
    assert blackhole["client_uplink_damage_unchanged"] is True
    assert blackhole["no_user_reverse_app_or_probe"] is True
    assert blackhole["restored_ns"] - blackhole["start_ns"] >= 55_000_000_000
    assert blackhole["restored_ns"] >= plan["start_monotonic_ns"] + 8_000_000_000
    assert blackhole["restored_ns"] < plan["start_monotonic_ns"] + 18_000_000_000

    log = (artifact / "h1250-product-erin.log").read_text(errors="replace")
    assert ("V4_PUBLIC_PATH_PREDEAD_AUTH_REFRESH role=client old_generation=1 "
            "authenticated_health_stale=1 old_route_preserved=1 terminal_native_dead=0") in log
    assert "V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED role=client" not in log
    for who in ("alice", "erin"):
        client = (artifact / ("h1250-product-" + who + ".log")).read_text(
            errors="replace")
        assert re.search(
            r"V4_PUBLIC_NORMAL_TUN_PROMOTED_AFTER_AUTH_RX generation=\d+ "
            r"native_rx=0 authenticated_health=1 old_route_revoked=1", client)
        assert re.search(
            r"V4_PUBLIC_NORMAL_REMOTE_M4_PROVEN role=client generation=\d+ "
            r"client_port=\d+ native_authenticated_control_or_ipv4=1 "
            r"tun_route_promoted=1", client)

    rapid = json.loads((artifact / "h1286-rapid-report.json").read_text())
    assert rapid["alert_count"] == 0 and not rapid["alerts"]
    assert rapid["rotation_verdict"] == "PASS_ALL_FIVE_SCOPED"
    assert all(c["rotation"]["result"] == "PASS_SCOPED"
               for c in rapid["clients"].values())
    gaps = {
        who: rapid["clients"][who]["directions"][direction][
            "largest_10ms_bucket_no_receive_while_sender_active_ms"]
        for who, direction in {
            "alice": "uplink", "bob": "downlink", "carol": "uplink",
            "dave": "downlink", "erin": "uplink"}.items()
    }
    assert max(gaps.values()) < 750
    return {
        "qualification": "H1319_ONE_SOURCE_ARM64_GENUINE_PREDEAD_ONEWAY_SCOPED_PASS",
        "original_source_sha": SOURCE,
        "original_network_action": 42366910850,
        "original_network_action_CI_conclusion": "FAIL_BACKEND_ORACLE_WRONG_DIRECTION",
        "source_build_artifact": 13572515555,
        "original_network_artifact": 13572551435,
        "original_Go_donor": DONOR,
        "actual_product_binary_sha256": m["sha256"],
        "blackhole_physical_downlink_seconds": round(
            (blackhole["restored_ns"] - blackhole["start_ns"]) / 1e9, 3),
        "native_preterminal_go_refresh_A_still_live": True,
        "authenticated_B_health_promoted_without_reverse_user_ipv4": True,
        "terminal_dead90_reconnection_not_triggered": True,
        "strict_unique_app_alerts": rapid["alert_count"],
        "rotation": rapid["rotation_verdict"],
        "max_active_no_receive_gap_ms_by_client": gaps,
        "server_native_ISAL_Game4_tx_quanta": app["native_isal_quanta"],
        "server_legal_short_scalar_blocks": app["legal_scalar_short_blocks"],
        "Dave_native_ISAL_Game4_rx_decodes": app["dave_client_native_ISAL_decoded"],
        "Dave_reverse_app_quanta": 0,
        "actual_app": app["application_data_profile"],
        "scope_limits": [
            "The original Action remains a CI FAIL, not rewritten",
            "The source-scoped 180s no-gap result does not prove stochastic"
            " H1317/historical pressure failure universally fixed",
            "No Windows Npcap/Wintun full seven-mode physical, Android or"
            " remote ICMP3/4 qualification; PLAN028 L3 not run"]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = qualify(args.network, args.build)
    pathlib.Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("M0_PLAN028_H1319_ARM64_REAL_100PCT_HEALTH_BLACKHOLE_PREDEAD_B_ONEWAY_SCOPED_PASS",
          result["original_source_sha"],
          result["max_active_no_receive_gap_ms_by_client"],
          "server-native", result["server_native_ISAL_Game4_tx_quanta"])


if __name__ == "__main__":
    main()
