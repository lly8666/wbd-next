#!/usr/bin/env python3
"""PLAN028 real native ARM64 original Go TLS/Rust M4 pure one-way L1 oracle."""
import argparse,json,pathlib,re
PROFILE={"alice":"uplink","bob":"downlink","carol":"uplink",
         "dave":"downlink","erin":"uplink"}
MODE={"alice":"normal","bob":"fec-auto","carol":"game2",
      "dave":"game4","erin":"fec-fixed"}
def read(root,name):
    return json.loads((root/name).read_text())
def check(root,source):
    root=pathlib.Path(root)
    p=read(root,"h1250-matrix-plan.json")
    r=read(root,"h1286-rapid-report.json")
    assert p["source_sha"]==r["source_sha"]==source
    assert p["application_scene"]=="strict_oneway"
    assert p["application_directionality"]==r["application_directionality"]==PROFILE
    assert len(r["clients"])==5 and r["server_single_port"]==443
    assert r["alert_count"]==0,r["alerts"]
    assert r["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"
    assert r["application_TCP_policy"]=="ZERO_FLOWS_ALL_FIVE"
    assert r["application_probe_policy"]=="ZERO_PROBE_HZ_ALL_FIVE"
    assert [(z["phase"],z["seconds"]) for z in r["actual_phase_windows"]]==[
        ("warmup",10),("first_wave",30),("sustained",60),
        ("overload",30),("recovery",50)]
    per=r["server_per_authenticated_lease_tun"]
    assert len(per)==5 and all(x["pending_overflow"]==0 for x in per.values())
    for phase in ("installed","after"):
        j=read(root,"h1312-static-neighbour-"+phase+".json")
        assert j["kind"]=="TEST_ONLY_PHYSICAL_VETH_L2_CONTROL"
        assert len(j["entries"])==j["native_owner_count"]==10
        assert j["data_netem_unchanged"]
        assert all(x["neighbor_state"]=="PERMANENT" and x["lladdr_present"]
                   for x in j["entries"])
    samples=read(root,"h1301-netem-clock.json")["samples"]
    assert len(samples)>100
    uplink=[z["client_uplink_netem"] for z in samples]
    downlink=[z["host_downlink_netem"] for z in samples]
    assert all(z["kind"]=="netem" for z in uplink+downlink)
    sent=uplink[-1]["packets"]-uplink[0]["packets"]
    lost=uplink[-1]["drops"]-uplink[0]["drops"]
    assert sent>2000 and lost>1000
    loss=100*lost/(sent+lost)
    assert 28<=loss<=32,loss
    cases={}
    for who,active in PROFILE.items():
        client=r["clients"][who]
        assert client["mode"]==MODE[who]
        assert client["rotation"]["result"]=="PASS_SCOPED"
        counters={}
        for direct in ("uplink","downlink"):
            item=client["directions"][direct]
            t=item["true_tcp"]
            assert t["framed_app_sent"]==t["framed_app_received"]==0
            assert t["sender_pending_at_deadline"]==0
            n=sum(z["actual_udp_sent"] for z in item["phases"])
            m=sum(z["unique_udp_delivered"] for z in item["phases"])
            if direct==active:
                assert item["expected_application"]=="REAL_UDP"
                assert n>1000 and m>1000
                assert all(z["actual_udp_sent"]>0 and z["unique_udp_delivered"]>0
                           for z in item["phases"])
                assert item["largest_10ms_bucket_no_receive_while_sender_active_ms"]<750
            else:
                assert item["expected_application"]=="NONE"
                assert n==m==0
                assert all(z["actual_udp_sent"]==z["unique_udp_delivered"]==0
                           for z in item["phases"])
            counters[direct]={"sent":n,"delivered":m}
        cases[who]={"mode":MODE[who],"active_app_direction":active,
                    "actual_app":counters}
    s=(root/"h1250-product-dave.log").read_text(errors="replace")
    m=re.findall(r"M0_GAME_M4_FEC_BACKEND_READBACK selected=(\S+) native_linked=(\d+) tx_native_quanta=(\d+) tx_scalar_quanta=(\d+)",s)
    assert m and m[-1][0]=="prefer-native" and int(m[-1][1])==1 and int(m[-1][2])>0
    return {"kind":"SCOPED_L1_TRUE_NATIVE_ARM64_PURE_ONEWAY_WITH_AUTH_ROTATIONS",
       "source_sha":source,"original_tls_server_port":443,
       "all_five_auth_rotations":r["rotation_verdict"],
       "genuine_app_alerts":0,"per_lease_tun_overflow":0,
       "native_isal_quanta":int(m[-1][2]),"legal_scalar_short_blocks":int(m[-1][3]),
       "Erin_true_oneway_upstream_netem_loss_pct":round(loss,3),
       "Erin_downstream_data_loss_pct":"NOT_MEASURED_NO_USER_APP",
       "test_only_ten_static_veth_mac":"PERMANENT_NEIGH",
       "application_data_profile":cases,
       "limits":["Original encrypted native Health/control can flow in idle user direction",
                 "No synthetic application probe, TCP SYN or reverse user DATA",
                 "Static veth ARP is test harness L2-only, not product behaviour",
                 "No Windows, Android or remote WAN qualification"]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args();j=check(x.art,x.source)
    pathlib.Path(x.out).write_text(json.dumps(j,indent=2,sort_keys=True)+"\n")
    print("M0_H1316_NATIVE_ARM64_FIVE_CLIENT_ONEWAY_REAL_APP_ROTATION_SCOPED_PASS",
          json.dumps({"loss":j["Erin_true_oneway_upstream_netem_loss_pct"],
             "native_quanta":j["native_isal_quanta"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
