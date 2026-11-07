#!/usr/bin/env python3
"""Offline qualification of TWO real x86 native Game4 Actions, exact ONE SOURCE.

Both original CI conclusions stay FAIL. This only combines actual original
Go TLS/Rust M4 AEAD server-Commit proof from Action42345392910 with the
complete Game4 Stop/8 real ClientHello/UDP of Action42345932962.
"""
import argparse,hashlib,json,pathlib,re,struct
SOURCE="9cc5b0efc36a390d44154bcf7ae378eb1d30e7f3"
DONOR="a7a82db31fe736ffedee330795a3234d358f1984"
def read(root,name):
    for p in (root/"fixed-kernel-result"/name,root/name):
        if p.is_file():return p.read_bytes()
    raise AssertionError("source artifact missing "+name)
def js(root,name):return json.loads(read(root,name))
def qualify(first,done):
    a,b=js(first,"manifest.json"),js(done,"manifest.json")
    assert a["source_sha"]==b["source_sha"]==SOURCE
    assert a["original_go_sha"]==b["original_go_sha"]==DONOR
    assert a["toolchains"]==b["toolchains"]=={"go":"1.23.12","rust":"1.85.1"}
    assert a["binary_sha256"]==b["binary_sha256"]
    for name in ("wbd-v4-server","wbd-v4-client","libwbd_engine.so"):
        data=(first/"fixed-build"/name).read_bytes()
        assert data[:4]==b"\x7fELF" and struct.unpack_from("<H",data,18)[0]==62
        assert hashlib.sha256(data).hexdigest()==a["binary_sha256"][name]
    original=read(first,"game4-a-to-ab-to-b-native.log").decode()
    assert re.search(r"V4_PUBLIC_GAME_TUN_PROMOTED_AFTER_AUTH_RX generation=\d+ native_delivered=0 authenticated_health=1 old_route_revoked=1",original)
    assert ("V4_PUBLIC_GAME_REMOTE_M4_PROVEN role=client generation=2 "
            "lanes=4 native_authenticated_control_or_ipv4=1 tun_route_promoted=1") in original
    assert "M0_PLAN028_GAME4_REAL_A_TO_AB_TO_B_AUTHENTICATED_OVERLAP_ORDER_PASS" in original
    err_before=[int(x) for x in re.findall(
        r"M0_PLAN028_GAME_RETIRED_RX_ERROR_BACKOFF_REAL_NATIVE_PASS \[(\d+)\]",original)]
    assert err_before and max(err_before)<100000
    log=read(done,"game4-frozen-real.log").decode()
    assert "M0_PLAN028_AUTO_NATIVE_FAIL" not in log
    flags=("M0_PLAN028_GAME_RETIRED_RX_ERROR_BACKOFF_REAL_NATIVE_PASS",
        "M0_PLAN028_GAME4_REAL_A_TO_AB_TO_B_AUTHENTICATED_OVERLAP_ORDER_PASS",
        "M0_PLAN028_GAME4_FEC6_A_TO_AB_TO_B_SHARED_TUN_AND_PARITY_PASS",
        "M0_PLAN028_GAME4_SAME_INSTALLATION_LEASE_RETAINED_NATIVE_PASS",
        "M0_PLAN028_REAL_LINUX_GAME4_NATIVE_RTN_NETLINK_A_TO_AB_TO_B_PASS",
        "M0_PLAN028_REAL_NEW_PATH_MTU_READBACK_PASS",
        "M0_PUBLIC_ORIGINAL_GO_V4_GAME_REAL_TLS_M4_DAMAGED_LANE_NO_HOL_STOP_PASS",
        "M0_PLAN028_TLS_GAME4_8_REAL_TCP_CLIENTHELLOS_NO_PRELUDE_PASS")
    assert all(x in log for x in flags),[x for x in flags if x not in log]
    err_after=[int(x) for x in re.findall(
        r"M0_PLAN028_GAME_RETIRED_RX_ERROR_BACKOFF_REAL_NATIVE_PASS \[(\d+)\]",log)]
    assert err_after and max(err_after)<100000
    app=read(done,"plan028-real-path-switched-business.log").decode()
    echoes=list(map(int,re.findall(r"M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK (\d+)",app)))
    assert echoes==[100,101,102,103,104]
    mtu,route=js(done,"plan028-new-tun-mtu.json"),js(done,"plan028-effective-new-physical-route.json")
    assert len(mtu)==len(route)==1
    assert mtu[0]["ifname"]=="wbdvc4" and mtu[0]["mtu"]==1178
    assert route[0]["prefsrc"]=="10.25.0.3" and route[0]["dev"]=="wbdvc0"
    tls=js(done,"plan028-game4-tls-wire-audit.json")
    assert tls["result"]=="REAL_GAME4_TWO_GENERATIONS_8_CLIENTHELLO_NO_PRELUDE_PASS"
    assert tls["client_hello_sessions"]==tls["distinct_session_ids"]==8
    assert tls["client_generation_count"]==2 and tls["lanes_per_generation"]==4
    assert tls["source_counts"]=={"10.25.0.2":4,"10.25.0.3":4}
    assert len(tls["per_lane"])==8
    for l in tls["per_lane"]:
        assert (l["first_client_data"]=="TLS_Handshake_ClientHello" and
            l["first_server_data"]=="TLS_Handshake_ServerHello" and
            l["session_id_bytes"]==32 and l["server_early_data_bytes"]==0
            and l["tcp_syn_and_synack"])
    return {"qualification":"SCOPED_PASS_FROM_TWO_REAL_NATIVE_X86_ACTIONS_EXACT_SAME_BINARIES",
        "source_sha":SOURCE,"pinned_original_go_donor":DONOR,
        "original_product_binary_sha256":a["binary_sha256"],
        "actual_actions":[42345392910,42345932962],
        "actions_ci_conclusion":["FAIL_fixture_old_server_reason","FAIL_workflow_grep_product_log_not_printed"],
        "authenticated_cold_M4":{"genuine_new_generation":2,
            "canonical_server_kind0_AEAD_PN_verified":True,
            "client_reverse_user_ipv4_delivered":0,"old_route_preserved_until_verified":True},
        "real_network":{"source_changed":"10.25.0.2→10.25.0.3","outer_user_mtu":1460,
            "real_new_physical_mtu":1280,"OS_inner_TUN_mtu":1178,
            "new_application_udp_echoes":echoes,
            "old_owned_rx_driver_errors_first":err_before,
            "old_owned_rx_driver_errors_final":err_after,
            "old_group_and_final_product_Stop":"ACTUAL_PASS",
            "Game4_FEC6_first_delivery":"ACTUAL_PASS",
            "original_TLS_ClientHello_count":8,"TLS_private_prelude":"NONE"},
        "scope_limits":["Original GitHub Actions remain red due post-run fixture/reporting defects",
            "This is one Linux x86_64/x86_64 physical netns Game4 mode, not all seven Windows modes",
            "ARM64 Erin 30pct weak-net business gaps remain OPEN",
            "Remote ICMP3/4 and Android NOT_RUN, PLAN028 final long NOT_RUN"]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",required=True)
    p.add_argument("--final",required=True)
    p.add_argument("--out",required=True)
    v=p.parse_args()
    report=qualify(pathlib.Path(v.first),pathlib.Path(v.final))
    pathlib.Path(v.out).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("M0_PLAN028_H1307_NATIVE_X86_GAME4_SAME_SOURCE_COLD_M4_TLS8_STOP_UDP5_SCOPED_PASS",
          report["source_sha"],"old_raw_error",report["real_network"]["old_owned_rx_driver_errors_final"])
if __name__=="__main__":main()
