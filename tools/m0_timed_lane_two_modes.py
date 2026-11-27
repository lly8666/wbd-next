"""Two actual existing Linux timer mechanisms, no Windows fake timer."""
import pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);scene=sys.argv[2]
if scene=="normal-off":
    subprocess.run([sys.executable,"tools/m0-plan028-x86-same-path-timed-rotation-fixture.py",str(out),"normal-auto"],check=True)
    s=out.read_text()
    s=s.replace("TIMER_SCENE=\"normal-auto\"","TIMER_SCENE=\"normal-off\"")
    s=s.replace("carol carol-mixed-protected fec-auto '--rotation-interval","carol carol-mixed-protected normal '--rotation-interval")
    s=s.replace('assert "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto" in server','assert "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" in server')
    s=s.replace('assert "V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=auto" in server','assert "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" in server')
elif scene=="game4-fixed6":
    subprocess.run([sys.executable,"tools/m0-h1231-arm64-game4-real-single-lane-fixture.py",str(out),scene],check=True)
    s=out.read_text()
    # One full four-lane cycle, not a broad matrix or eight-turn repeat.
    s=s.replace("-ge 8","-ge 4").replace("len(cr)>=8 and len(sr)>=8","len(cr)>=4 and len(sr)>=4").replace("cr[:8];sr=sr[:8]","cr[:4];sr=sr[:4]").replace("[1,2,3,4,1,2,3,4]","[1,2,3,4]").replace("list(range(1,9))","list(range(1,5))").replace("[1,1,1,1,2,2,2,2]","[1,1,1,1]").replace(")==8",")==4").replace("client)[:8]","client)[:4]").replace("len(due)==8","len(due)==4").replace('v["sent"]>=800','v["sent"]>=300').replace("seq 1 1120","seq 1 560").replace("230_000_000_000","150_000_000_000").replace("ARM64+ARM64 native","x86_64+x86_64 native").replace("H1231_NATIVE_ARM64_GAME4_EIGHT_TRUE_SINGLE_LANE_HOT_SWAPS_PASS","M0_NATIVE_X86_GAME4_FOUR_TRUE_SINGLE_LANE_HOT_SWAPS_PASS")
else:raise SystemExit("unknown scene")
# These are Linux functional checks, not Windows carrier benchmarks.
for marker in ("PY_ORACLE","PY_STREAM"):
    body=s.split("<<'"+marker+"'\n",1)[1].split("\n"+marker,1)[0]
    compile(body,str(out)+":"+marker,"exec")
out.write_text(s);out.chmod(0o700)
