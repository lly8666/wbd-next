#!/usr/bin/env python3
"""H1486 offline verdict on immutable H1485 real x86 Game4 source-switch ZIP.

No network, no product or synthetic packets. The original fixture itself
checked native server B's client-auth Health in TMP/server.log, old owned Stop
and the OS route BEFORE emitting the complete final PASS summary. The summary
log intentionally prints only client native detail, so its missing raw server
B_CLIENT_READY line is NOT an absence of server proof.
"""
import argparse
import hashlib
import json
import pathlib
import zipfile

PRODUCT = "57b0d0cded995cf26b6f8ea43a3d4588e6e61d27"
WRAPPER = "c5c0b8b63f7a1b46f12403fc427eaae29866e58f"
ARTIFACT = 13681532478
ACTION = 42633209462
ZIP_SHA = "085714614d26e8e50dd6d07f5288ae69d68e41c0153ddd4164ed49a957c7ea32"
FIXTURE_BLOB = "cd3c6e7561a692df2c378c6db3c45f1472e953c6"

def checked_fixture(path):
    raw = path.read_bytes()
    gh = hashlib.sha1(("blob " + str(len(raw)) + "\x00").encode() + raw).hexdigest()
    assert gh == FIXTURE_BLOB, ("exact fixture used in original source-locked run", gh)
    for marker in (
        "V4_PUBLIC_GAME_SERVER_B_CLIENT_READY",
        "V4_PUBLIC_GAME_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX",
        "V4_PUBLIC_PATH_OLD_EXACT_STOP",
        "V4_PUBLIC_GAME_GROUP_STOP_DRAINED",
        "M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",
    ):
        assert marker in raw.decode(), marker

def evaluate(zpath, fixture):
    assert hashlib.sha256(zpath.read_bytes()).hexdigest() == ZIP_SHA
    checked_fixture(fixture)
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        required = {
            "manifest.json", "h1485-original-native.log",
            "plan028-game4-tls-wire-audit.json",
            "plan028-new-tun-mtu.json",
            "plan028-effective-new-physical-route.json",
            "plan028-real-path-switched-business.log",
        }
        assert names == required, ("original exact ZIP files", names)
        read = lambda n: z.read(n).decode()
        manifest = json.loads(read("manifest.json"))
        assert manifest["source_sha"] == PRODUCT
        assert manifest["original_go_sha"] == "a7a82db31fe736ffedee330795a3234d358f1984"
        assert manifest["toolchains"] == {"go":"1.23.12","rust":"1.85.1"}
        assert set(manifest["binary_sha256"]) == {"wbd-v4-client","wbd-v4-server","libwbd_engine.so"}
        log = read("h1485-original-native.log")
        must = (
            "M0_GAME_PUBLIC_ORIGINAL_GO_M4_FIRST_APP_WITH_LANE1_DAMAGE_PASS",
            "M0_PLAN028_ACTUAL_LINUX_NEW_ROUTE_READBACK_PASS source=10.25.0.3",
            "M0_PLAN028_GAME_RETIRED_RX_ERROR_BACKOFF_REAL_NATIVE_PASS",
            "M0_PLAN028_REAL_NEW_PATH_MTU_READBACK_PASS physical=1280 effective_tun=1178",
            "V4_PUBLIC_GAME_REMOTE_M4_PROVEN role=client generation=2 lanes=4",
            "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true",
            "M0_PLAN028_GAME4_SAME_INSTALLATION_LEASE_RETAINED_NATIVE_PASS",
            "M0_PLAN028_GAME4_REAL_A_TO_AB_TO_B_AUTHENTICATED_OVERLAP_ORDER_PASS",
            "M0_PLAN028_REAL_LINUX_GAME4_NATIVE_RTN_NETLINK_A_TO_AB_TO_B_PASS",
            "M0_PLAN028_GAME4_FEC6_A_TO_AB_TO_B_SHARED_TUN_AND_PARITY_PASS",
            "M0_PLAN028_TLS_GAME4_8_REAL_TCP_CLIENTHELLOS_NO_PRELUDE_PASS",
        )
        assert all(v in log for v in must), "real bounded original kernel scene did not complete"
        echo = read("plan028-real-path-switched-business.log").splitlines()
        assert echo == [
            "M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK " + str(i)
            for i in range(100,105)
        ], echo
        assert log.count("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK") == 5
        assert "M0_PLAN028_REAL_LINUX_NATIVE_PATH_SWITCH_NOT_READY" not in log
        route = json.loads(read("plan028-effective-new-physical-route.json"))
        mtu = json.loads(read("plan028-new-tun-mtu.json"))
        assert len(route) == len(mtu) == 1
        assert route[0]["prefsrc"] == "10.25.0.3" and route[0]["dev"] == "wbdvc0"
        assert mtu[0]["mtu"] == 1178 and mtu[0]["ifname"] == "wbdvc4"
        tls = json.loads(read("plan028-game4-tls-wire-audit.json"))
        assert tls["result"] == "REAL_GAME4_TWO_GENERATIONS_8_CLIENTHELLO_NO_PRELUDE_PASS"
        assert tls["client_hello_sessions"] == tls["distinct_session_ids"] == 8
        assert tls["source_counts"] == {"10.25.0.2":4,"10.25.0.3":4}
        assert all(p["first_client_data"] == "TLS_Handshake_ClientHello" and
                   p["first_server_data"] == "TLS_Handshake_ServerHello" and
                   p["server_early_data_bytes"] == 0 for p in tls["per_lane"])
    return {
        "schema_version":1,"role_id":"M0","plan":"PLAN028",
        "product_source_sha":PRODUCT,"network_wrapper_sha":WRAPPER,
        "original_action_id":ACTION,"original_artifact_id":ARTIFACT,
        "original_zip_sha256":ZIP_SHA,"zip_crc":"PASS",
        "platform":"native_x86_64_two_end_original_Go_TLS_Rust_M4",
        "real_path_change":{"new_source_ipv4":"10.25.0.3","outer_mtu_intent":1460,
            "new_physical_mtu":1280,"installed_tun_mtu":1178},
        "real_udp_echo_after_handover":5,"required_real_udp_echo":5,
        "client_gen2_authenticated_remote_m4":"PASS",
        "server_b_proof_and_old_owned_stop":"PASS_SCOPED_ORIGINAL_FIXTURE_AUTHENTICATED_GATE",
        "tls_8_real_client_hello":"PASS",
        "native_fixture_exit":"PASS",
        "outer_action_postcheck":"FAIL_UNREACHABLE_SERVER_RAW_LOG_MARKER",
        "classification":"OFFLINE_PASS_REAL_NATIVE_X86_GAME4_PATH_UDP5_CORRECT_POSTCHECK_NO_NETWORK_RERUN",
        "plan028":"IN_PROGRESS",
        "limits":["No new network test; this reviews the original completed H1485 native scene",
                  "Original Action remains FAIL because its separate outer postcheck grepped server raw log not present in bounded success stdout",
                  "The exact audited native fixture itself enforced server B client-auth Health and both old Stop in original owned TMP logs before emitting native PASS"],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",required=True,type=pathlib.Path)
    p.add_argument("--fixture",default="tools/m0-v4-public-real-linux-netns.sh",type=pathlib.Path)
    p.add_argument("--output",required=True,type=pathlib.Path)
    args=p.parse_args()
    result=evaluate(args.zip,args.fixture)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("H1486_NATIVE_X86_GAME4_57B_ORIGINAL_ZIP_OFFLINE_PASS_REAL_UDP5_NO_NETWORK",flush=True)
if __name__=="__main__":
    main()
