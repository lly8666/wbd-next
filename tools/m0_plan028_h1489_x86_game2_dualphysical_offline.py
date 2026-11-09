#!/usr/bin/env python3
"""H1489: two immutable genuine x86 Game2/Normal/Game4 dual-physical native ZIPs.

Both original Actions ended FAIL at their OUTER Python reporter after the
original native shell had already completed two physical replacements,
two owned A Stops, and all real UDP. This reviewer never creates packets
or modifies a source/denominator. It verifies both archives independently.
"""
import argparse
import hashlib
import json
import pathlib
import zipfile

EXPECTED_BINARY_SHA = {
    "wbd-v4-client": "a5360594851707d1e9783ca553a8e5e71bbfa4745c703bc8a2f1e7b781f42d7b",
    "wbd-v4-server": "652b7cd22bd232944c5a3cac2ca64c7680d6a7900965d956dffd5fc39e8083c8",
    "libwbd_engine.so": "909f0ace9a95ca2ef16132969edef8c6cf768143f4102bcd276a46c86147ebf6",
}
GAME2_SCOPE = "NATIVE_X86_X86_GAME2_FIXED6_TWO_SOURCE_IP_REAUTH_WITH_GAME4_AND_NORMAL_HEALTHY"
CASES = (
    ("frozen", "57b0d0cded995cf26b6f8ea43a3d4588e6e61d27",
     42638378892, 13684650590,
     "0f004276205331efd7165bcfb893bf649b20421370df99c340e29d44faddbd68", ""),
    ("same-binaries-rebuilt", "222a03eb53064771620e5821d82478969f8ee93b",
     42638378870, 13684297738,
     "c2837a8d3334f2596256ec3df67228d6ff7ec43672e5804eb6aa9d2d64dca7e6",
     "fixed-kernel-result/"),
)

def verify_fixture(path):
    raw = path.read_bytes()
    digest = hashlib.sha1(("blob " + str(len(raw)) + "\0").encode()+raw).hexdigest()
    assert digest == "7f78aaa5e132e8153029ab3809e038b68c95fa41", ("original fixture SHA", digest)
    text = raw.decode("utf-8")
    for marker in ('for i in $(seq 0 79);do',
                   'for i in range(640):',
                   'assert len(t1)==80 and',
                   'assert len(t2)==80 and'):
        assert marker in text, marker

def verify(path, case):
    label,source,action,artifact,sha,prefix = case
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha, ("immutable ZIP",label)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, ("zip CRC",label)
        names=set(z.namelist())
        manifest_path="manifest.json" if not prefix else "fixed-build/manifest.json"
        log_path=prefix+("h1488-real-x86-native.log" if not prefix else "plan028-h1151-mixed-normal-game-x86.log")
        required={manifest_path,log_path,
            prefix+"plan028-h1199-game2-two-physical.json",
            prefix+"plan028-h1151-mixed-one443.json"}
        assert required <= names, (label, required-names)
        read=lambda name: json.loads(z.read(name))
        manifest=read(manifest_path)
        assert manifest["source_sha"]==source
        assert manifest["original_go_sha"]=="a7a82db31fe736ffedee330795a3234d358f1984"
        assert (manifest.get("binary_sha256") or manifest.get("sha256"))==EXPECTED_BINARY_SHA
        if "architecture" in manifest:
            assert manifest["architecture"]=="native_x86_64"
        game=read(prefix+"plan028-h1199-game2-two-physical.json")
        mixed=read(prefix+"plan028-h1151-mixed-one443.json")
        log=z.read(log_path).decode(errors="replace")
        assert game["scope"]==GAME2_SCOPE
        assert game["physical_source4_sequence"]==["10.25.0.2","10.25.0.9","10.25.0.2"]
        assert game["physical_mtu_sequence"]==[1500,1280,1500]
        assert game["outer_user_mtu"]==1460
        assert game["game2_authenticated_generations"]==[1,2,3]
        assert game["game2_exact_old_stops"]==[1,2]
        assert game["game2_new_udp"]==[16,16]
        assert game["sibling_udp_each_switch"]==[[80,80],[80,80]]
        assert game["tunnel_ip_preserved"] and game["sibling_game4_stable"] and game["sibling_normal_stable"]
        assert [game[k] for k in ("game2_initial_inner_mtu","game2_new_inner_mtu","game2_restored_inner_mtu")]==[1358,1178,1178]
        assert [game[k] for k in ("other_game4_inner_mtu","other_normal_inner_mtu")]==[1358,1375]
        assert game["one_server_port"]==mixed["server_port"]==443
        assert mixed["native_peers"]==["game2-fixed6-ChaCha","game4-fixed6-AES256","normal-auto-AES128"]
        assert len(set(mixed["distinct_authenticated_client_ips"]))==3
        assert mixed["real_udp_echoes"]=={"game2":12,"game4":18,"normal":18}
        assert mixed["game2_stop_did_not_stop_game4_or_normal"] and mixed["shared_rust_tun_reader_final_stop"]
        for marker in (
            "M0_PLAN028_H1199_X86_GAME2_FIXED6_TWO_PHYSICAL_HEALTHY_SIBLINGS_PASS",
            "M0_PLAN028_H1151_X86_ORIGINAL_TLS_ONE443_NORMAL_GAME2_GAME4_FEC6_48_REAL_UDP_EXACT_STOP_PASS",
        ):
            assert marker in log, (label,marker)
        if not prefix:
            for stem,ip in (("new","10.25.0.9"),("restored","10.25.0.2")):
                rows=read("plan028-h1199-game2-route-"+stem+".json")
                assert len(rows)==1 and rows[0]["dev"]=="mxa0" and rows[0]["prefsrc"]==ip
    return {
        "kind":label, "product_source_sha":source, "original_action_id":action,
        "original_artifact_id":artifact, "original_zip_sha256":sha, "zip_crc":"PASS",
        "original_action_conclusion":"FAIL_RETAINED_OUTER_REPORT_ONLY",
        "native_scope":"PASS_SCOPED_TWO_PHYSICAL_GAME2_FIXED6_HEALTHY_GAME4_NORMAL",
        "actual_udp_gen2_gen3":[16,16],
        "actual_sibling_game4_normal_each_wave":[[80,80],[80,80]],
        "all_three_authenticated_generations":[1,2,3],
        "old_exact_stop_generations":[1,2],
        "command_to_old_stop_ms_NOT_handshake_SLA":game["command_to_ready_ms"],
        "post_stop_all_shared_tun_owners":"PASS",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--frozen",type=pathlib.Path,required=True)
    ap.add_argument("--rebuilt",type=pathlib.Path,required=True)
    ap.add_argument("--fixture",type=pathlib.Path,default=pathlib.Path(
        "tools/m0-plan028-x86-game2fixed6-two-physical-handover-fixture.py"))
    ap.add_argument("--out",type=pathlib.Path,required=True)
    args=ap.parse_args()
    verify_fixture(args.fixture)
    rows=[verify(args.frozen,CASES[0]),verify(args.rebuilt,CASES[1])]
    output={
        "schema_version":1,"role_id":"M0","plan":"PLAN028",
        "classification":"OFFLINE_PASS_TWO_ORIGINAL_NATIVE_X86_GAME2_TWO_PHYSICAL_NO_NEW_NETWORK",
        "arch":"genuine_native_x86_64_both_end_original_Go_TLS_Rust_M4",
        "original_fails_preserved":True,"same_binary_hash_across_original_source_manifests":True,
        "cases":rows,
        "limits":["Original Action conclusions remain FAIL due outer reporter mismatches",
                  "No new network or rebuild for this offline review",
                  "No claim about Windows, external physical WAN, CPU causality or L3 long soak",
                  "Command-to-old-Stop includes owned 10-20s grace; not a handshake SLA"],
        "plan028":"IN_PROGRESS"
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    print("H1489_SOURCE57B_GAME2_X86_TWO_ORIGINAL_SCENES_OFFLINE_PASS_NO_NEW_NETWORK",flush=True)

if __name__=="__main__":
    main()
