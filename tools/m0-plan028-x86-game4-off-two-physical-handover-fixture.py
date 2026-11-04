#!/usr/bin/env python3
"""PLAN028 H1202 native x86_64 Game4 FEC Off A→B→A real physical TLS/Rust.
Reuse qualified x86 Game4 fixed6 two physical source swaps and shared443.
Only cold FEC mode and test expected OS budget/receipts change.
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);old=sys.argv
sys.argv=["tools/m0-plan028-x86-mixed-game4-two-switch-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=old
s=out.read_text()
def one(a,b):
    global s
    assert s.count(a)==1,"qualified original Game4 native source changed "+a[:110]
    s=s.replace(a,b,1)
one("start_client \"$NSB\" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec fixed6 --record-cipher aes-256-gcm'",
    "start_client \"$NSB\" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec off --record-cipher aes-256-gcm'")
oldfec="V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6"
assert s.count(oldfec)>=2
s=s.replace(oldfec,"V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0")
one('"game4-fixed6-AES256"','"game4-off-AES256"')
s=s.replace("GAME4_FIXED6","GAME4_OFF")
s=s.replace("GAME4_FEC6_B","GAME4_OFF_B")
one('[[ "$old_game" == 1358 && "$new_game" == 1178 &&\n   "$old_normal" == 1375 && "$new_normal" == 1375 ]]',
    '[[ "$old_game" -ge 1100 && "$new_game" -ge 1100 && "$new_game" -lt "$old_game" &&\n   "$old_normal" == 1375 && "$new_normal" == 1375 ]]')
one('[[ "$new_restore_game" == 1178 && "$new_restore_normal" == 1375 ]]',
    '[[ "$new_restore_game" -ge 1100 && "$new_restore_game" -le "$new_game" && "$new_restore_normal" == 1375 ]]')
one('"$changed_restore_ns" "$ready_restore_ns" "$IPB" "$ART/plan028-h1167-two-physical-switch.json" <<\'PY_H1167\'',
    '"$changed_restore_ns" "$ready_restore_ns" "$IPB" "$old_game" "$new_game" "$new_restore_game" "$ART/plan028-h1167-two-physical-switch.json" <<\'PY_H1167\'')
one('"os_mtu_first_generation":1358,"os_mtu_second_generation":1178,',
    '"os_mtu_first_generation":int(sys.argv[9]),"os_mtu_second_generation":int(sys.argv[10]),')
one('"os_mtu_third_generation_overlap_conservative":1178,',
    '"os_mtu_third_generation_overlap_conservative":int(sys.argv[11]),')
one('pathlib.Path(sys.argv[9]).write_text(json.dumps(out,indent=2)+"\\n")',
    'pathlib.Path(sys.argv[12]).write_text(json.dumps(out,indent=2)+"\\n")')
one('"game4_fixed6":True','"game4_fec_off":True')
one('assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=")>=2',
    'assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=")>=2\nassert server.count("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=off profile=0")==3\nassert game.count("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0")==3')
s=s.replace("plan028-h1162","plan028-h1202-first")
s=s.replace("plan028-h1167","plan028-h1202-second")
s=s.replace("h1202-first-arm64-mixed-game4-source4.log","h1202-first-x86-game4-off-source4.log")
s=s.replace("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS",
            "M0_PLAN028_H1202_X86_GAME4_OFF_FIRST_PHYSICAL_NORMAL_LIVE_PASS")
s=s.replace("M0_PLAN028_H1167_NATIVE_X86_MIXED_GAME4_TWO_PHYSICAL_REAUTH_NORMAL_LIVE64_NEW48_PASS",
            "M0_PLAN028_H1202_X86_GAME4_OFF_TWO_PHYSICAL_NORMAL_LIVE_PASS")
s=s.replace("M0_PLAN028_H1151_X86_ORIGINAL_TLS_ONE443_NORMAL_GAME2_GAME4_FEC6_48_REAL_UDP_EXACT_STOP_PASS",
            "M0_PLAN028_H1202_X86_ONE443_GAME4_OFF_REAL_UDP_STOP_PASS")
s=s.replace("NATIVE_ARM64_MIXED_NORMAL_GAME2_GAME4_PHYSICAL_REAUTH_SINGLE_SHARED_443",
            "NATIVE_X86_X86_GAME4_OFF_NORMAL_HEALTHY_AUTHENTIC_TWO_PHYSICAL")
s=s.replace("NATIVE_X86_X86_MIXED443_GAME4_TWO_SOURCE4_AND_MTU_HANDOVERS",
            "NATIVE_X86_X86_GAME4_OFF_TWO_AUTHENTIC_PHYSICAL_HANDOVERS")
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1202_X86_GAME4_OFF_TWO_ORIGINAL_TLS_FIXTURE_READY",flush=True)
