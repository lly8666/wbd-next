"""One screened Windows host: two timer modes, one outstanding BBR retest."""
import json,os,pathlib,shutil,subprocess,sys
from m0_wl_windows_bounded_cmd import run_captured

ROOT=pathlib.Path.cwd();OUT=ROOT/"result/wl-public";E=ROOT/"result/winxdp-windows-timer"
E.mkdir(parents=True,exist_ok=True)
def read(p):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError,ValueError):return {}
def owned_stop():
    # On a failed measurement retain actual native and server Stop
    # evidence rather than pretending the functional test passed.
    c=(OUT/"client.log").read_text(errors="replace") if (OUT/"client.log").exists() else ""
    s=(OUT/"server.log").read_text(errors="replace") if (OUT/"server.log").exists() else ""
    return ("WBD_WINDOWS_NATIVE_DISCONNECTED_V1" in c or "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" in c) and (
        "V4_PUBLIC_NATIVE_STOP_DRAINED role=server" in s or "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server" in s or
        "V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close" in s or "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" in s) and not (OUT/"owned-wal.json.n4-owned-wal").exists()
def run(args,env,log,limit):
    with log.open("w") as f:
        p=subprocess.Popen([sys.executable,"-u",*args],env=env,stdout=f,stderr=subprocess.STDOUT)
        try:return p.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            run_captured(["taskkill.exe","/PID",str(p.pid),"/T","/F"],20)
            if p.poll() is None:p.kill()
            return 124
def main():
    # Keep the failed Game4 TCP scene separate from timer renewal, so
    # a cold timer does not pollute 30s weak-link throughput attribution.
    env=dict(os.environ,WBD_XDP_GAME_DOWNLOAD_MODES="game4-fec",WBD_XDP_GAME_DOWNLOAD_TRANSPORT="tcp",
             WBD_XDP_GAME_DOWNLOAD_BBR="1",WBD_XDP_GAME_DOWNLOAD_DIAG="1",WBD_XDP_WINDOWS_ROTATION="0")
    tcp_rc=run(["tools/m0_winxdp_game_download.py"],env,E/"game4-tcp-driver.log",260)
    print("WINXDP_GAME4_TCP_RETEST_RC "+str(tcp_rc),flush=True)
    if tcp_rc and not owned_stop():return 2
    codes=[]
    for mode in ("normal","game4-fec"):
        case=E/mode;case.mkdir()
        for pat in ("report.json","*-report.json","client.log","server.log","windows-app.log","linux-app.log","windows-tcp-app.log","linux-tcp-app.log","windows-timer-*","gamefec-*.flag","mode-batch.json","windows-original-go-rust-process-1hz.jsonl","wl-v2-scenario.json"):
            for p in OUT.glob(pat):
                if p.is_file() and not p.name.endswith("owned.json"):p.unlink()
        env=dict(os.environ,WBD_WL_PUBLIC_MODE=mode,WBD_WL_PUBLIC_MODES=mode,
                 WBD_XDP_WINDOWS_ROTATION="1",WBD_XDP_GAME_DOWNLOAD_BBR="0",WBD_XDP_GAME_DOWNLOAD_DIAG="0")
        for k in ("WBD_WL_V2_SCENARIO","WBD_WL_RUN_N0","WBD_WL_RUN_P200","WBD_XDP_GAME_DOWNLOAD_TRANSPORT"):env.pop(k,None)
        rc=run(["tools/m0_wl_public_modes_e2e.py"],env,case/"fixture.log",225)
        report=read(OUT/"report.json");report["fixture_rc"]=rc
        (case/"timer-measurement.json").write_text(json.dumps(report,indent=2))
        for pat in ("client.log","server.log","windows-app.log","linux-app.log","windows-timer-*","gamefec-*.txt","mode-batch.json","windows-original-go-rust-process-1hz.jsonl"):
            for p in OUT.glob(pat):
                if p.is_file():shutil.copyfile(p,case/p.name)
        codes.append(rc)
        print("WINXDP_WINDOWS_TIMER_MODE "+json.dumps({"mode":mode,"rc":rc,"stop":report.get("stop"),"error":report.get("error"),"rotation":report.get("windows_timed_rotation")}),flush=True)
        if rc and not owned_stop():break
    return 0 if tcp_rc==0 and codes==[0,0] else 2
if __name__=="__main__":raise SystemExit(main())
