#!/usr/bin/env python3
"""1800s genuine signed Windows ONE client plus independent Linux TUN client.

This test-only observer does not own VPN, change wire, or synthesize receipts.
"""
import json, os, pathlib, re, subprocess, time
from m0_plan028_h1412_wsl_cross_os_client_preflight import NS
from m0_wl_windows_bounded_cmd import run_captured

def resources(out,win,wsl):
    cmd=("$p=Get-Process -Id "+str(win.pid)+" -ErrorAction Stop;"
         "@{rss_bytes=$p.WorkingSet64;cpu_seconds=$p.CPU}|ConvertTo-Json -Compress")
    x=run_captured(["powershell.exe","-NoProfile","-Command",cmd],14)
    if x.returncode:
        raise RuntimeError("Windows original VPN RSS OS sample failed: "+x.stderr[-400:])
    w=json.loads(x.stdout)
    if int(w["rss_bytes"])<=0:raise RuntimeError("Windows original VPN RSS not readable")
    ids=[]
    for role in ("linux","server"):
        p=out/("h1415-"+role+".pid")
        value=p.read_text().strip()
        if not value.isdigit():raise RuntimeError(role+" actual Linux owner PID missing")
        ids.append(value)
    y=wsl("ps","-o","pid=,rss=,pcpu=","-p",",".join(ids),timeout=15)
    rows=[line.split() for line in y.stdout.splitlines() if line.strip()]
    if len(rows)!=2 or any(len(v)<3 or int(v[1])<=0 for v in rows):
        raise RuntimeError("Linux original server/client RSS unavailable")
    return {"windows_rss_bytes":int(w["rss_bytes"]),
            "windows_cpu_s":float(w.get("cpu_seconds") or 0),
            "linux_rss_kib":{v[0]:int(v[1]) for v in rows}}

def refresh_runner_management():
    """Cold test-only CAS /32 refresh; no VPN packets, wire, or product owner."""
    script=pathlib.Path("tools/m0_wl_gamefec_management_route.ps1").resolve()
    cmd=["powershell.exe","-NoProfile","-NonInteractive","-File",str(script),
         "-Action","Refresh","-Receipt",
         "result/wl-public/crossos1800-management-route-lease.json"]
    p=run_captured(cmd,18)
    if p.returncode:
        raise RuntimeError("L3 managed Runner /32 refresh failed (test infrastructure): "+p.stderr[-420:])
    m=re.search(r"PLAN028_CROSSOS1800_MGMT_REFRESH observed=(\d+) added=(\d+) total=(\d+) repaired=(\d+)",p.stdout)
    if not m:
        raise RuntimeError("L3 managed Runner /32 refresh readback absent: "+p.stdout[-300:])
    return {"observed":int(m[1]),"added":int(m[2]),"total":int(m[3]),"repaired":int(m[4])}

def qualify(out,seconds,paths,stats,need,win_tcp,wsl,guestapp,owners):
    need(seconds==1800 and len(paths)==2 and len(owners)==4,
         "L3 requires 1800s exactly, two clients and one server/echo")
    initial={who:stats(p) for who,p in paths.items()}
    for who,entry in initial.items():
        need(entry["received"]>=8 and entry["reverse_received"]>=5,
             who+" L3 not yet authenticated app-ready")
    begin=time.monotonic();next_check=begin+5;next_tcp=begin+30
    next_resources=begin+90;next_mgmt=begin+8
    sample=[];rss=[];tcps=0;management=[];added_peers=0;repaired_routes=0
    print("H1448_L3_OS_COMMANDS_FILE_BACKED_BOUNDED_AND_PARENT_IDLE_WITNESS_ARMED",flush=True)
    print("H1430_REAL_1800S_CROSS_OS_NATIVE_APP_BEGIN",flush=True)
    while time.monotonic()-begin<seconds:
        now=time.monotonic();elapsed=now-begin
        for who,p in owners.items():
            need(p.poll() is None,"real "+who+" exited during 1800s")
        if now>=next_mgmt:
            managed=refresh_runner_management()
            management.append({"elapsed_s":round(elapsed,2),**managed})
            added_peers+=managed["added"]
            repaired_routes+=managed["repaired"]
            if managed["added"] or managed["repaired"] or len(management)%6==0:
                print("H1430_REAL_RUNNER_MANAGEMENT "+
                      json.dumps({"elapsed_s":round(elapsed,1),
                       "new_peer_routes":managed["added"],
                       "cumulative_new_routes":added_peers,
                       "repaired_owned_routes":managed["repaired"],
                       "cumulative_repairs":repaired_routes,
                       "current_runner_targets":managed["observed"],
                       "owned_routes":managed["total"]}),flush=True)
            next_mgmt=time.monotonic()+10
        if now>=next_check:
            cur={who:stats(p) for who,p in paths.items()}
            for who,v in cur.items():
                need(v["sent"]>initial[who]["sent"],who+" no real active UDP offered")
                for key in ("echo_age_ms","reverse_age_ms",
                            "max_echo_gap_ms","max_reverse_gap_ms"):
                    need(v[key] is not None and float(v[key])<1500,
                         who+" real app "+key+" >=1500ms at "+str(round(elapsed,1)))
            sample.append({"elapsed_s":round(elapsed,2),
                           "windows":cur["windows"],"linux":cur["linux"]})
            if len(sample)%12==0:
                print("H1430_REAL_NATIVE_L3_MINUTE "+
                      json.dumps({"elapsed_s":round(elapsed,1),
                       "windows_rx":cur["windows"]["received"],
                       "linux_rx":cur["linux"]["received"]}),flush=True)
            next_check+=5
        if now>=next_tcp:
            win_tcp("10.66.0.2")
            p=wsl("ip","netns","exec",NS,"python3","-u",guestapp,
                  "tcp","10.66.0.3",timeout=22)
            need("H1415_LINUX_NATIVE_KERNEL_TCP_ECHO_PASS" in p.stdout,
                 "Linux authenticated TCP failed during cross-OS L3")
            tcps+=1;next_tcp+=60
        if now>=next_resources:
            rss.append({"elapsed_s":round(elapsed,2),
                        **resources(out,owners["windows"],wsl)})
            next_resources+=120
        time.sleep(.25)
    elapsed=time.monotonic()-begin
    after={who:stats(p) for who,p in paths.items()}
    delta={}
    for who,v in after.items():
        b=initial[who]
        sent=v["sent"]-b["sent"]
        received=v["received"]-b["received"]
        reverse=v["reverse_received"]-b["reverse_received"]
        delta[who]={"sent":sent,"received":received,"reverse_received":reverse}
        need(sent>=12500 and received>=int(sent*.97) and reverse>=12500,
             who+" true 1800s UDP offered/echo/reverse below contract: "+str(delta[who]))
        for key in ("echo_age_ms","reverse_age_ms",
                    "max_echo_gap_ms","max_reverse_gap_ms"):
            need(v[key] is not None and float(v[key])<1500,
                 who+" terminal no-RX gap >=1500ms: "+key)
    need(len(management)>=60,"L3 runner management dynamic /32 refresh not actually exercised")
    need(elapsed>=1800 and tcps>=28 and len(rss)>=12,
         "true 1800s duration/dual TCP/resource samples missing")
    (out/"h1430-l3-samples.json").write_text(json.dumps({
        "source_sha":os.environ["GITHUB_SHA"],"duration_s":round(elapsed,2),
        "tcp_both_count":tcps,"before":initial,"after":after,
        "samples":sample,"resources":rss,"runner_management":management,
        "runner_new_peer_routes":added_peers,
        "runner_repaired_owned_routes":repaired_routes},indent=2)+"\n")
    return {"status":"PASS_SCOPED_REAL_1800S_BOTH_CLIENTS",
        "duration_s":round(elapsed,2),"tcp_both_count":tcps,
        "resource_samples":len(rss),"runner_refresh_samples":len(management),
        "runner_new_peer_routes":added_peers,
        "runner_repaired_owned_routes":repaired_routes,"actual_udp_delta":delta,
        "maximum_echo_gap_ms":{x:after[x]["max_echo_gap_ms"] for x in paths},
        "maximum_reverse_gap_ms":{x:after[x]["max_reverse_gap_ms"] for x in paths},
        "windows_peak_rss_bytes":max(x["windows_rss_bytes"] for x in rss)}
