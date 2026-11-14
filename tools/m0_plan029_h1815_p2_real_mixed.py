#!/usr/bin/env python3
"""PLAN029 H1815: two genuine OS kernel paths, moderate 1MiB TCP plus
concurrent small Tunnel UDP. A test fixture, not another product packet pump.
"""
import hashlib,json,math,os,pathlib,socket,subprocess,sys,time

PORT=46112
SMALL_PORT=46114
SIZE=1024*1024
COUNT=120  # old exact receipt minimum; sustained overlap uses a separate counter
MAX_SUSTAIN=3200
FINISH_PACKET=b"PLAN029-P2-TUNNEL-FINISH"
PREFIX=b"PLAN029-H1815-ORIGINAL-SIGNED-COMPARATIVE-TCP/"
PAYLOAD=(PREFIX*((SIZE+len(PREFIX)-1)//len(PREFIX)))[:SIZE]
SHA=hashlib.sha256(PAYLOAD).hexdigest()
LABEL=b"PLAN029-P2-REAL-SMALL-TUNNEL-UDP"
def udp_packet(i):
    return i.to_bytes(4,"big")+LABEL+bytes(96-4-len(LABEL))
def receipt(label,data):
    print(label+" "+json.dumps(data,sort_keys=True),flush=True)

def tcp_guest(physical,expected_host):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sock.bind((physical,PORT));sock.listen(2);sock.settimeout(40)
        print("PLAN029_H1815_P2_PHYSICAL_TCP_READY",flush=True)
        sources=[];sizes=[]
        for step in range(2):
            conn,peer=sock.accept()
            if peer[0]!=expected_host:
                raise RuntimeError("physical WinSock source changed under Direct")
            with conn:
                conn.settimeout(35)
                data=bytearray()
                while len(data)<SIZE:
                    chunk=conn.recv(min(16384,SIZE-len(data)))
                    if not chunk:break
                    data.extend(chunk)
                if len(data)!=SIZE or hashlib.sha256(data).hexdigest()!=SHA:
                    raise RuntimeError("P2 real Linux physical TCP 1MiB bytes mismatch")
                if conn.recv(1)!=b"":
                    raise RuntimeError("P2 kernel TCP missing half-close")
                conn.sendall(data);conn.shutdown(socket.SHUT_WR)
            sources.append(peer[0]);sizes.append(len(data))
        receipt("PLAN029_H1815_P2_PHYSICAL_TCP_GUEST",
          {"source_ips":sources,"received_bytes":sizes,"socket":physical,
           "kernel_socket":True})

def tcp_client(role,local,remote):
    if role=="direct" and (local!="10.66.0.2" or not remote.startswith("198.18.")):
        raise RuntimeError("P2 direct must use original Wintun /32 and announced local FakeIP")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(35);sock.bind((local,0))
        started=time.monotonic();sock.connect((remote,PORT))
        connected=time.monotonic()
        for n in range(0,SIZE,16384):
            sock.sendall(PAYLOAD[n:n+16384])
            time.sleep(.004) # SAME application pacing; NOT peak throughput
        uploaded=time.monotonic()
        sock.shutdown(socket.SHUT_WR)
        half_closed=time.monotonic()
        echoed=bytearray();first_reply=None
        while len(echoed)<SIZE:
            part=sock.recv(min(16384,SIZE-len(echoed)))
            if not part:break
            if first_reply is None:first_reply=time.monotonic()
            echoed.extend(part)
        ended=time.monotonic()
        if len(echoed)!=SIZE or hashlib.sha256(echoed).hexdigest()!=SHA:
            raise RuntimeError("P2 Windows actual one-MiB kernel TCP echo wrong")
        data={"role":role,"echo_bytes":len(echoed),"payload_sha256":SHA,
              "socket_source":sock.getsockname()[0],"presented_peer":remote,
              "start_monotonic_s":started,"end_monotonic_s":ended,
              "elapsed_ms":round((ended-started)*1000,3),"kernel_tcp":True,
              "half_close":True,
              "connect_ms":round((connected-started)*1000,3),
              "upload_ms":round((uploaded-connected)*1000,3),
              "half_close_ms":round((half_closed-uploaded)*1000,3),
              "first_reply_wait_ms":round(((first_reply or ended)-half_closed)*1000,3),
              "download_ms":round((ended-(first_reply or ended))*1000,3),
              "nominal_send_sleep_ms":256,
              "throughput_scope":"PACED_FUNCTIONAL_NOT_PEAK_GOODPUT"}
    receipt("PLAN029_H1815_P2_TCP_CLIENT",data)

def udp_guest(tun_ip,lease):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind((tun_ip,SMALL_PORT));sock.settimeout(47)
        print("PLAN029_H1815_P2_LINUX_TUN_SMALL_READY",flush=True)
        total=0
        while total<MAX_SUSTAIN:
            packet,peer=sock.recvfrom(512)
            if peer[0]!=lease:
                raise RuntimeError("P2 Linux TUN small UDP source mismatch")
            if packet==FINISH_PACKET:
                sock.sendto(FINISH_PACKET,peer)
                break
            if packet!=udp_packet(total):
                raise RuntimeError("P2 Linux TUN small UDP content mismatch")
            sock.sendto(packet,peer);total+=1
        else:raise RuntimeError("P2 Linux sustained packet cap reached")
        if total<COUNT:raise RuntimeError("P2 Linux 120 minimum not covered")
    receipt("PLAN029_H1815_P2_TUNNEL_SMALL_LINUX",
      {"received":COUNT,"sustained_total":total,"source_lease":lease,
       "tunnel_local":tun_ip,"kernel_tun_socket":True})

def udp_windows(lease,tun_ip):
    if lease!="10.66.0.2":raise RuntimeError("wrong original signed Wintun lease")
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind((lease,0));sock.settimeout(1.5)
        print("PLAN029_H1815_P2_WINDOWS_TUN_SMALL_READY",flush=True)
        started=time.monotonic();rtts=[];gaps=[];prev=None;total=0
        # Test-only host completion marker: UDP must span the entire real
        # Direct TCP lifetime, not end after the old first ~2 seconds.
        done=pathlib.Path(os.environ["WBD_PLAN029_P2_TCP_DONE_MARKER"])
        for seq in range(MAX_SUSTAIN):
            begin=time.monotonic()
            sock.sendto(udp_packet(seq),(tun_ip,SMALL_PORT))
            payload,fromaddr=sock.recvfrom(512)
            end=time.monotonic()
            if fromaddr!=(tun_ip,SMALL_PORT) or payload!=udp_packet(seq):
                raise RuntimeError("P2 small UDP echo escaped Tunnel or wrong sequence")
            rtts.append((end-begin)*1000)
            if prev is not None:gaps.append((end-prev)*1000)
            prev=end;total+=1
            if total>=COUNT and done.exists():break
            time.sleep(.014)
        else:raise RuntimeError("P2 UDP sustained cap before TCP completion")
        sock.sendto(FINISH_PACKET,(tun_ip,SMALL_PORT))
        payload,fromaddr=sock.recvfrom(512)
        if fromaddr!=(tun_ip,SMALL_PORT) or payload!=FINISH_PACKET:
            raise RuntimeError("P2 Tunnel final controlled echo missing")
        finished=time.monotonic()
    receipt("PLAN029_H1815_P2_TUNNEL_SMALL_WINDOWS",
      {"received":COUNT,"sustained_total":total,
       "start_monotonic_s":started,"end_monotonic_s":finished,
       "kernel_lease":lease,"tunnel_ip":tun_ip,
       "rtt_p99_ms":round(sorted(rtts)[math.ceil(.99*total)-1],3),
       "max_interreply_gap_ms":round(max(gaps),3),"kernel_udp":True})

def run_p2(root,out,physical,host_source,tunnel_ip,fake,unix,ready):
    if os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")!="1":
        raise RuntimeError("H1815 true original test scene gate missing")
    source=os.environ["GITHUB_SHA"]
    exe=root/"tools"/"m0_plan029_h1815_p2_real_mixed.py"
    children=[];streams=[]
    completed=out/"plan029-h1828-direct-fully-finished.marker"
    if completed.exists():completed.unlink()
    def spawn(name,role,first,second,linux=False):
        log=out/("plan029-h1815-"+name+".log")
        f=log.open("w");streams.append(f)
        args=(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",unix(exe)]
              if linux else [sys.executable,"-u",str(exe)])
        child_env=os.environ.copy()
        child_env["WBD_PLAN029_P2_TCP_DONE_MARKER"]=str(completed)
        p=subprocess.Popen([*args,role,first,second],stdout=f,
                           stderr=subprocess.STDOUT,env=child_env)
        children.append(p)
        return p,log
    def wait(p,log,limit):
        try:code=p.wait(timeout=limit)
        except subprocess.TimeoutExpired:raise RuntimeError("P2 bounded original kernel app timeout "+str(log))
        if code!=0:raise RuntimeError("P2 kernel app failed "+str(log)+" "+
                 log.read_text(errors="replace")[-600:])
    def proof(log,marker):
        lines=[line.split(" ",1)[1] for line in log.read_text().splitlines()
               if line.startswith(marker+" ")]
        if len(lines)!=1:raise RuntimeError("P2 exact receipt count missing "+str(log))
        return json.loads(lines[0])
    try:
        guest,gn=spawn("linux-physical-tcp","guest_tcp",physical,host_source,True)
        ready(gn,"PLAN029_H1815_P2_PHYSICAL_TCP_READY",guest,12)
        baseline,bn=spawn("baseline-windows","baseline",host_source,physical)
        wait(baseline,bn,35)
        lin,ln=spawn("linux-tunnel-small","guest_udp",tunnel_ip,"10.66.0.2",True)
        ready(ln,"PLAN029_H1815_P2_LINUX_TUN_SMALL_READY",lin,12)
        win,wn=spawn("windows-tunnel-small","windows_udp","10.66.0.2",tunnel_ip)
        ready(wn,"PLAN029_H1815_P2_WINDOWS_TUN_SMALL_READY",win,8)
        direct,dn=spawn("direct-windows","direct","10.66.0.2",fake)
        wait(direct,dn,38)
        completed.write_text("direct-finished\n",encoding="ascii")
        wait(win,wn,23);wait(lin,ln,7);wait(guest,gn,7)
        base=proof(bn,"PLAN029_H1815_P2_TCP_CLIENT")
        direct_value=proof(dn,"PLAN029_H1815_P2_TCP_CLIENT")
        linux=proof(gn,"PLAN029_H1815_P2_PHYSICAL_TCP_GUEST")
        small_win=proof(wn,"PLAN029_H1815_P2_TUNNEL_SMALL_WINDOWS")
        small_linux=proof(ln,"PLAN029_H1815_P2_TUNNEL_SMALL_LINUX")
        overlap=(max(direct_value["start_monotonic_s"],small_win["start_monotonic_s"])<
                 min(direct_value["end_monotonic_s"],small_win["end_monotonic_s"]))
        whole_direct=(small_win["start_monotonic_s"]<=
                      direct_value["start_monotonic_s"] and
                      small_win["end_monotonic_s"]>=direct_value["end_monotonic_s"])
        if (base["role"]!="baseline" or direct_value["role"]!="direct" or
            base["echo_bytes"]!=SIZE or direct_value["echo_bytes"]!=SIZE or
            base["payload_sha256"]!=direct_value["payload_sha256"] or
            base["socket_source"]!=host_source or
            direct_value["presented_peer"]!=fake or
            linux["source_ips"]!=[host_source,host_source] or
            linux["received_bytes"]!=[SIZE,SIZE] or
            small_win["received"]!=COUNT or small_linux["received"]!=COUNT or
            small_linux["source_lease"]!="10.66.0.2" or not overlap or
            not whole_direct or
            small_win["sustained_total"]!=small_linux["sustained_total"]):
            raise RuntimeError("P2 real baseline/Direct 1MiB + concurrent Tunnel UDP independent proof invalid")
        # Same-run, same-VM phase attribution, not an inferred algorithmic
        # bottleneck or a peak throughput number. Additive deltas expose the
        # first dominant wait without changing the paced 1-MiB workload.
        phases=("connect_ms","upload_ms","half_close_ms",
                "first_reply_wait_ms","download_ms")
        delta={phase:round(direct_value[phase]-base[phase],3)
               for phase in phases}
        dominant=max(phases,key=lambda phase:delta[phase])
        ratio=round(direct_value["elapsed_ms"]/max(.001,base["elapsed_ms"]),3)
        return {"source_sha":source,"binary_source_sha":os.environ.get("WBD_WL_BINARY_SOURCE",source),
                "p2_timeline":{"direct_over_physical_elapsed_ratio":ratio,
                    "direct_minus_physical_phase_ms":delta,
                    "dominant_added_wait_phase":dominant,
                    "same_vm_sequential_baseline":True,
                    "workload":"PACED_16K_BLOCKS_4MS_NOT_PEAK",
                    "no_single_kernel_cause_claim":True},
                "scope":"REAL_PHYSICAL_SOCKET_BASELINE_1M_VS_FAKEIP_RUST_DIRECT_1M_AND_120_CONCURRENT_TUNNEL_UDP",
                "physical_baseline":base,"direct_windows":direct_value,"physical_guest":linux,
                "tunnel_windows":small_win,"tunnel_linux":small_linux,
                "windows_direct_fakeip":fake,"overlap":overlap,
                "covered_whole_direct_tcp":whole_direct,
                "udp_sustained_total":small_win["sustained_total"],
                "cpu_attribution":"NOT_MEASURED_P2_TWO_DIFFERENT_KERNEL_SOCKET_PATHS",
                "stop":"NOT_RUN_UNTIL_OWNER_STOP"}
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill()
        for f in streams:f.close()

if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit("P2 role and two bounded addresses required")
    role,a,b=sys.argv[1:4]
    if role=="guest_tcp":tcp_guest(a,b)
    elif role=="guest_udp":udp_guest(a,b)
    elif role in ("baseline","direct"):tcp_client(role,a,b)
    elif role=="windows_udp":udp_windows(a,b)
    else:raise SystemExit("P2 unrecognized role")
