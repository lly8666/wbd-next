"""Actual Windows timed generation-renewal observation, not hot-lane parity."""
import json,pathlib,re,select,socket,subprocess,sys,time

def echo():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(("10.66.0.1",45903))
        print("WINDOWS_ROTATION_ECHO_READY",flush=True)
        sock.settimeout(.5)
        until=time.monotonic()+175
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
            # 100pps independent offered packets; no stop-and-wait at
            # a 400ms RTT, no app retry, and no catch-up send burst.
            start=time.monotonic();seq=0;receipts=[];errors=[];gen_receipts={}
            sent={};seen=set();ready=0;retired=0;mbb=False;last_log=0.;next_send=start;drain_until=None
            prefix=b"WBD_WINDOWS_TIMER_NATIVE/"
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.bind(("10.66.0.2",0));sock.setblocking(False)
                while True:
                    now=time.monotonic()
                    if win.poll() is not None or server.poll() is not None:raise RuntimeError("owner exited during timer rotation")
                    if now-last_log>=.05:
                        client=(out/"client.log").read_text(errors="replace")
                        ready=client.count("WBD_WINDOWS_CLIENT_READY")+client.count("WBD_WINDOWS_NORMAL_MBB_GENERATION_READY")
                        retired=client.count("WBD_WINDOWS_NORMAL_MBB_OLD_EXACT_STOP")
                        mbb="scope=normal_mbb" in client
                        last_log=now
                    if drain_until is None and (now-start>=110 or (ready>=3 and gen_receipts.get(3,0)>=20 and (not mbb or retired>=2))):
                        drain_until=now+1.5
                    if drain_until is not None and now>=drain_until:break
                    if drain_until is None and now>=next_send:
                        data=prefix+str(seq).encode()
                        try:
                            sock.sendto(data,("10.66.0.1",45903))
                            sent[seq]=(now,ready)
                        except OSError as err:
                            errors.append({"seq":seq,"phase":"send","error":repr(err)})
                        seq+=1
                        next_send=now+.01
                    timeout=.01 if drain_until is not None else max(0.,min(.01,next_send-time.monotonic()))
                    if not select.select([sock],[],[],timeout)[0]:continue
                    while True:
                        try:response,peer=sock.recvfrom(2048)
                        except BlockingIOError:break
                        except OSError as err:
                            errors.append({"phase":"receive","error":repr(err)})
                            break
                        if peer[0]!="10.66.0.1" or not response.startswith(prefix):continue
                        try:i=int(response[len(prefix):])
                        except ValueError:continue
                        if i not in sent or i in seen:continue
                        seen.add(i)
                        at=time.monotonic();sent_at,gen=sent[i]
                        receipts.append({"seq":i,"elapsed_ms":round((at-start)*1000,3),
                            "rtt_ms":round((at-sent_at)*1000,3),"ready_generation":gen})
                        gen_receipts[gen]=gen_receipts.get(gen,0)+1
            rtts=sorted(r["rtt_ms"] for r in receipts)
            result={"scope":"WINDOWS_NORMAL_MBB_SAME_WINTUN" if mbb else "WINDOWS_FULL_GENERATION_RENEWAL_NOT_HOT_LANE",
                "sent":seq,"socket_accepted":len(sent),"received":len(receipts),
                "missing":seq-len(receipts),"generation_receipts":gen_receipts,
                "socket_errors":errors,"same_socket":True,"send_interval_ms":10,
                "rtt_p50_ms":rtts[len(rtts)//2] if rtts else None,
                "rtt_p99_ms":rtts[min(len(rtts)-1,int(len(rtts)*.99))] if rtts else None,
                "max_successful_receive_gap_ms":max((b["elapsed_ms"]-a["elapsed_ms"] for a,b in zip(receipts,receipts[1:])),default=None),
                "receipts":receipts}
            (out/"windows-timer-business.json").write_text(json.dumps(result,indent=2))
            if not all(gen_receipts.get(i,0)>0 for i in (1,2,3)):
                raise RuntimeError("missing same-socket business in each of three generations: "+str(gen_receipts))
            # Save diagnostic evidence even on continuity failure. Final
            # post-Stop audit enforces zero missing and exact retirement.
            return {k:v for k,v in result.items() if k!="receipts"}
        finally:
            if p.poll() is None:p.terminate()
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:p.kill()

def audit_stop(out):
    client=(out/"client.log").read_text(errors="replace")
    server=(out/"server.log").read_text(errors="replace")
    if "scope=normal_mbb" in client:return audit_normal_mbb(out,client,server)
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
    assert all(lo==30000 and hi==35000 and lo<=delay<=hi for lo,hi,delay,_ in arms),arms
    assert all(0<=due-(arm[3]+arm[2])<=2000 for due,arm in zip(dues,arms)),(dues,arms)
    assert len({x[1] for x in ports[:3]})==3 and [x[0] for x in ports[:3]]==[1,2,3],ports
    steady=[x for x in rss if x[3] in (1,4) and x[2] in {p[1] for p in ports}]
    assert len(steady)>=3 and all(x[1]==1 for x in steady) and len({x[0] for x in steady})==1,rss
    assert ready==3 and stops>=ready and not result["physical_path_events"],result
    if any(x[3]==4 for x in steady):
        group_ports=[(int(lane),int(port)) for lane,port in re.findall(r"V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=4 lane=(\d+) client_port=(\d+) server_port=443 protected_TLS=1 original_Rust_M4=1 grouped_commit=1",server)]
        assert group_ports==[(lane,base+lane-1) for _,base in ports[:3] for lane in range(1,5)],group_ports
        assert server.count("V4_PUBLIC_GAME_SERVER_B_CLIENT_READY role=server lanes=4 source=authenticated_client_native_Health promoted=1")==2,result
        assert server.count("V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-grace-expired")>=1,result
        result["server_authenticated_groups"]=3
    else:
        from m0_wl_public_mss_contract import verified_plan028_shared_manual_two_generation_v4_mss
        result["server_authenticated_generations"]=verified_plan028_shared_manual_two_generation_v4_mss(client,server,1460,expected_sessions=(1,2,2))
    (out/"windows-timer-audit.json").write_text(json.dumps(result,indent=2))
    return result

def audit_normal_mbb(out,client,server):
    from m0_wl_public_mss_contract import verified_plan028_shared_manual_two_generation_v4_mss
    business=json.loads((out/"windows-timer-business.json").read_text())
    ready=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_NORMAL_MBB_GENERATION_READY generation=(\d+) local_port=(\d+) grace_ms=(\d+) unix_ms=(\d+) original_tls=1 authenticated_candidate_rx=1 same_wintun=1",client)]
    retired=[(int(g),anchor=="true",int(at)) for g,anchor,at in re.findall(r"WBD_WINDOWS_NORMAL_MBB_OLD_EXACT_STOP generation=(\d+) os_anchor_retained=(true|false) native_rx_joined=1 unix_ms=(\d+)",client)]
    arms=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_TIMER_ROTATION_ARMED min_ms=(\d+) max_ms=(\d+) actual_delay_ms=(\d+) scope=normal_mbb unix_ms=(\d+)",client)]
    dues=[int(x) for x in re.findall(r"WBD_WINDOWS_TIMER_ROTATION_DUE scope=normal_mbb unix_ms=(\d+)",client)]
    native=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_NORMAL_MBB_PROMOTED old_owner=(\d+) new_owner=(\d+) old_rx_alive=1 same_wintun=1 grace_ms=(\d+)",client)]
    native_retired=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_NORMAL_MBB_OLD_RX_RETIRED owner=(\d+) old_port=(\d+) native_rx_joined=1",client)]
    changes=[(int(p),int(a)) for p,a in re.findall(r"WBD_XDP_RX_PORT_CHANGE port=(\d+) add=(\d+) same_program_umem=1",client)]
    rss=[tuple(map(int,x)) for x in re.findall(r"WBD_XDP_RX_READY ifindex=(\d+) queues=(\d+) port=(\d+) ports=(\d+) slots_per_queue=",client)]
    ports=[tuple(map(int,x)) for x in re.findall(r"WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=(\d+) configured_port=\d+ source_port=(\d+)",client)]
    result={"scope":"WINDOWS_NORMAL_MBB_SAME_WINTUN","ready":1+len(ready),"promotions":ready,
      "retired":retired,"native_promotions":native,"native_retired":native_retired,"armed":arms,
      "due_unix_ms":dues,"cold_ports":ports,"port_changes":changes,"rss":rss,
      "os_applies":client.count("WBD_WINDOWS_NATIVE_APPLIED_V1"),
      "initial_ready":client.count("WBD_WINDOWS_CLIENT_READY"),"os_stops":client.count("WBD_WINDOWS_NATIVE_DISCONNECTED_V1"),
      "rx_stops":client.count("WBD_XDP_RX_STOP "),"tx_stops":client.count("WBD_XDP_TX_STOP "),
      "server_promotions":server.count("source=authenticated_client_native_Health old_route_promoted=1"),
      "physical_path_events":client.count("WBD_WINDOWS_NATIVE_PATH_REAUTHORIZE"),
      "missing":business["missing"],"socket_errors":len(business["socket_errors"]),
      "max_gap_ms":business["max_successful_receive_gap_ms"]}
    (out/"windows-timer-audit.json").write_text(json.dumps(result,indent=2))
    assert len(ready)==len(retired)==len(native)==len(native_retired)==2,result
    assert [x[0] for x in ready]==[2,3] and [x[0] for x in retired]==[1,2],result
    assert [x[1] for x in retired]==[True,False],result
    assert len(arms)>=3 and len(dues)==2 and all(lo==30000 and hi==35000 and lo<=d<=hi for lo,hi,d,_ in arms),result
    # Unix millisecond truncation and sub-ms timer rounding can differ by 1ms.
    assert all(-1<=due-(arm[3]+arm[2])<=2000 for due,arm in zip(dues,arms)),result
    assert len(ports)==3 and len({p for _,p in ports})==3,result
    assert changes==[(ports[1][1],1),(ports[0][1],0),(ports[2][1],1),(ports[1][1],0)],result
    assert native[0][1]==native[1][0] and all(native_retired[i]==(native[i][0],ports[i][1]) for i in range(2)),result
    for i,(g,port,grace,at) in enumerate(ready):
        assert 10000<=grace<=20000 and native[i][2]==grace and port==ports[i+1][1],result
        assert grace-500<=retired[i][2]-at<=grace+5000,result
    assert len(rss)==1 and rss[0][1]==1 and rss[0][2]==ports[0][1],result
    assert result["os_applies"]==result["initial_ready"]==result["os_stops"]==result["rx_stops"]==result["tx_stops"]==1,result
    assert result["server_promotions"]==2 and result["physical_path_events"]==0,result
    import os
    mode={"normal":"normal","fixed":"fec-fixed","auto":"fec-auto"}[os.environ["WBD_WL_PUBLIC_MODE"]]
    result["server_authenticated_generations"]=verified_plan028_shared_manual_two_generation_v4_mss(client,server,1460,expected_sessions=(1,2,2),expected_mode=mode)
    assert business["missing"]==0 and not business["socket_errors"] and business["socket_accepted"]==business["sent"],result
    assert 350<=business["rtt_p50_ms"]<=500 and result["max_gap_ms"]<=100,result
    result["continuity"]="PASS_ZERO_MISSING_SAME_SOCKET"
    (out/"windows-timer-audit.json").write_text(json.dumps(result,indent=2))
    return result

if __name__=="__main__":echo()
