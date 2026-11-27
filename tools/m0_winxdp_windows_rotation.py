"""Actual Windows timed generation-renewal observation, not hot-lane parity."""
import json,pathlib,re,socket,subprocess,sys,time

def echo():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(("10.66.0.1",45903))
        print("WINDOWS_ROTATION_ECHO_READY",flush=True)
        sock.settimeout(.5)
        until=time.monotonic()+120
        while time.monotonic()<until:
            try:data,peer=sock.recvfrom(2048)
            except socket.timeout:continue
            sock.sendto(data,peer)

def measure_rotation(root,out,unix,win,server):
    script=root/"tools/m0_winxdp_windows_rotation.py"
    logs=out/"windows-timer-echo.log"
    with logs.open("w") as f:
        p=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",unix(script),"echo"],stdout=f,stderr=subprocess.STDOUT)
        try:
            until=time.monotonic()+10
            while "WINDOWS_ROTATION_ECHO_READY" not in logs.read_text(errors="replace"):
                if p.poll() is not None or time.monotonic()>=until:raise RuntimeError("rotation UDP echo not ready")
                time.sleep(.1)
            start=time.monotonic();seq=0;receipts=[];errors=[];gen_receipts={}
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.bind(("10.66.0.2",0));sock.settimeout(.15)
                while time.monotonic()-start<85:
                    if win.poll() is not None or server.poll() is not None:raise RuntimeError("owner exited during timer rotation")
                    log=(out/"client.log").read_text(errors="replace")
                    ready=log.count("WBD_WINDOWS_CLIENT_READY")
                    if ready>=3 and gen_receipts.get(3,0)>=20:break
                    data=("WBD_WINDOWS_TIMER_NATIVE/"+str(seq)).encode();seq+=1
                    at=time.monotonic()
                    try:
                        sock.sendto(data,("10.66.0.1",45903))
                        while time.monotonic()-at<.15:
                            response,peer=sock.recvfrom(2048)
                            if response==data and peer[0]=="10.66.0.1":
                                elapsed=round((time.monotonic()-start)*1000,3)
                                receipts.append({"seq":seq-1,"elapsed_ms":elapsed,"ready_generation":ready})
                                gen_receipts[ready]=gen_receipts.get(ready,0)+1
                                break
                    except OSError as err:
                        if not isinstance(err,socket.timeout):errors.append({"seq":seq-1,"error":repr(err)})
                    time.sleep(.05)
            result={"scope":"WINDOWS_FULL_GENERATION_RENEWAL_NOT_HOT_LANE",
                "sent":seq,"received":len(receipts),"generation_receipts":gen_receipts,
                "socket_errors":errors,"same_socket":True,
                "max_successful_receive_gap_ms":max((b["elapsed_ms"]-a["elapsed_ms"] for a,b in zip(receipts,receipts[1:])),default=None),
                "receipts":receipts}
            (out/"windows-timer-business.json").write_text(json.dumps(result,indent=2))
            if not all(gen_receipts.get(i,0)>0 for i in (1,2,3)):
                raise RuntimeError("missing same-socket business in each of three generations: "+str(gen_receipts))
            return {k:v for k,v in result.items() if k!="receipts"}
        finally:
            if p.poll() is None:p.terminate()
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:p.kill()

def audit_stop(out):
    client=(out/"client.log").read_text(errors="replace")
    server=(out/"server.log").read_text(errors="replace")
    arms=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_TIMER_ROTATION_ARMED min_ms=(\d+) max_ms=(\d+) actual_delay_ms=(\d+) scope=full_generation unix_ms=(\d+)",client)]
    dues=[int(x) for x in re.findall(r"WBD_WINDOWS_TIMER_ROTATION_DUE scope=full_generation unix_ms=(\d+)",client)]
    generations=[int(x) for x in re.findall(r"WBD_WINDOWS_TIMER_ROTATION_REAUTHORIZE generation=(\d+) previous_native_joined=1",client)]
    ports=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=(\d+) configured_port=\d+ source_port=(\d+)",client)]
    rss=[tuple(map(int,x)) for x in re.findall(r"WBD_XDP_RX_READY ifindex=(\d+) queues=(\d+) port=(\d+) ports=(\d+) slots_per_queue=",client)]
    stops=client.count("WBD_XDP_RX_STOP ")
    ready=client.count("WBD_WINDOWS_CLIENT_READY")
    result={"armed":arms,"due_unix_ms":dues,"reauthorized":generations,"cold_ports":ports,"rss":rss,"rx_stops":stops,
            "ready":ready,"server_authenticated_ready":server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server")+server.count("V4_PUBLIC_MULTI_SESSION_READY role=server"),
            "physical_path_events":client.count("WBD_WINDOWS_NATIVE_PATH_REAUTHORIZE"),
            "game4_single_lane_hot_swap":False}
    (out/"windows-timer-audit.json").write_text(json.dumps(result,indent=2))
    assert len(arms)>=3 and len(dues)>=2 and generations[:2]==[2,3],result
    assert all(lo==12000 and hi==18000 and lo<=delay<=hi for lo,hi,delay,_ in arms),arms
    assert all(0<=due-(arm[3]+arm[2])<=2000 for due,arm in zip(dues,arms)),(dues,arms)
    assert len({x[1] for x in ports[:3]})==3 and [x[0] for x in ports[:3]]==[1,2,3],ports
    steady=[x for x in rss if x[3] in (1,4) and x[2] in {p[1] for p in ports}]
    assert len(steady)>=3 and all(x[1]==1 for x in steady) and len({x[0] for x in steady})==1,rss
    assert ready>=3 and stops>=ready and not result["physical_path_events"],result
    return result

if __name__=="__main__":echo()
