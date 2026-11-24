"""Android branch shared Linux original protocol reference, one mode per VM.
Does not claim Android UID/TUN/DNS or ARM phone performance qualification.
"""
import argparse,hashlib,json,os,platform
from pathlib import Path
from tools.network_harness.fec_w167_dual_arch_matrix import MODES,_config,analyze
from tools.network_harness.runner import LinuxExperiment

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bundle",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    bundle=a.bundle.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    src=os.environ["GITHUB_SHA"];arch=os.environ["TEST_ARCH"];label=os.environ["TEST_MODE"]
    machine={"amd64":"x86_64","arm64":"aarch64"}[arch]
    assert platform.machine()==machine
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==src
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    expected=m["linux_elf_sha256"] if arch=="amd64" else m["linux_native_sha256"]
    hashes={n:hashlib.sha256((bundle/n).read_bytes()).hexdigest() for n in names}
    assert hashes==expected
    for name in names:
        data=(bundle/name).read_bytes()
        assert data[:5]==b"\x7fELF\x02" and int.from_bytes(data[18:20],"little")=={"amd64":62,"arm64":183}[arch]
    for name in names[:2]:(bundle/name).chmod(0o755)
    local=out/"bundle-A"/"fixed-build";local.mkdir(parents=True)
    for name in names:(local/name).symlink_to(bundle/name)
    _,mode,gfec,profile=next(row for row in MODES if row[0]==label)
    cfg=_config(label,mode,gfec,profile,1,src,int(os.environ["GITHUB_RUN_ID"]),arch,traffic_mbps=10)
    # Reuse existing proven 20s 10Mbps per direction, 1% IID, 75ms
    # normal weak-network scenario, not an extreme stress sweep.
    case=out/cfg["id"]
    report={"source":src,"arch":arch,"mode":label,"binary_hashes":hashes,"scope":"original Linux native shared protocol; not Android runtime","status":"NOT_RUN"}
    try:
        leg=LinuxExperiment(cfg,out/"bundle-A",case,"A").run()
        report.update(analyze(case,leg))
        report["status"]=leg.get("result","NOT_PROVEN")
    except Exception as e:
        report["status"]="FAIL";report["error"]=str(e)[:400]
        raise
    finally:
        (out/"result.json").write_text(json.dumps(report,indent=2)+"\n")
        print("ANDROID_SHARED_LINUX_MODE_RESULT",label,arch,report["status"],flush=True)
    if str(report["status"]).upper() not in ("PASS","PASS_SCOPED_OBSERVATION","SUCCESS"):
        raise SystemExit(1)
if __name__=="__main__":main()
