#!/usr/bin/env python3
"""Run actual original-TLS Windows and Linux native public UDP/TCP, then Stop."""
import os,sys,subprocess,time,json,hashlib,pathlib,re,threading
from m0_wl_native_resource_sampler import sample_windows_original_process
from m0_wl_mode_runtime_report import source_locked_observability,summarize_auto_udp_progress,native_auto_true_applied_snapshots
from m0_wl_native_mtu_contract import configured_native_test_mtu
from m0_wl_n0_drop_delta import latest_counter, measured_delta
from m0_wl_impairment_profile import get_profile
from m0_wl_lock_profile import parse_native_lock_profile
root=pathlib.Path.cwd();out=root/"result"/"wl-public";out.mkdir(parents=True,exist_ok=True)
mode=os.environ.get("WBD_WL_PUBLIC_MODE","normal")
configured_mtu=configured_native_test_mtu()
if mode not in ("normal","fixed","auto","game2","game4","game2-fec","game4-fec","auto-revision","auto-adaptive"):
 raise RuntimeError("unknown exact native Windows public mode "+mode)
fixed6=mode=="fixed"
is_game=mode.startswith("game")
game_fixed=mode.endswith("-fec")
game_mode=mode[:5] if is_game else ""
lanes=int(game_mode[-1]) if is_game else 1
server_mode=("fec-fixed --fec-profile 6" if fixed6 else
             "fec-auto" if mode.startswith("auto") else
             game_mode+(" --game-fec fixed6" if game_fixed else " --game-fec off") if is_game
             else "normal")
client_fec="fixed" if fixed6 or game_fixed else "auto" if mode.startswith("auto") else "off"
report={"source":os.environ["GITHUB_SHA"],"linux_binary_source":os.environ["LINUX_BINARY_SRC"],"mode":mode,
 "mode_public":"NOT_RUN","normal_public":"NOT_RUN","windows_ready":"NOT_RUN",
 "linux_ready":"NOT_RUN","app_duplex":"NOT_RUN","tcp_duplex":"NOT_RUN",
 "stop":"NOT_RUN","WL_N0":"NOT_RUN","WL_P200":"NOT_RUN","WL_N1":"NOT_RUN","WL_N5":"NOT_RUN",
 "requested_original_win_mtu":configured_mtu,
 "runtime_os_mtu_guard":"ORIGINAL_NATIVE_M4_1HZ_FAIL_CLOSED"}
def run(a,timeout=30):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(a[:4])+": "+(p.stderr or p.stdout)[-600:])
 return p.stdout.strip()
def wsl(*a,timeout=30):return run(["wsl.exe","-d","Ubuntu","-u","root","--",*a],timeout)
def unix(p):
 q=pathlib.Path(p).resolve()
 return "/mnt/"+q.drive[0].lower()+"/"+"/".join(q.relative_to(q.anchor).parts)
def ready(path,marker,process,seconds):
 for _ in range(seconds*5):
  if path.exists() and marker in path.read_text(errors="replace"):return
  if process.poll() is not None:raise RuntimeError(marker+" process exited "+str(process.returncode)+": "+path.read_text(errors="replace")[-800:])
  time.sleep(.2)
 raise RuntimeError(marker+" not observed: "+path.read_text(errors="replace")[-800:])
def stop_linux():
 f=out/"linux-server.pid"
 if f.exists() and f.read_text().strip().isdigit():
  subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--","kill","-TERM",f.read_text().strip()],capture_output=True)
def stop_windows(p):
 if p and p.poll() is None:
  try:p.stdin.write("stop\n");p.stdin.flush();p.wait(timeout=15)
  except Exception:
   p.terminate()
   try:p.wait(timeout=4)
   except subprocess.TimeoutExpired:p.kill()
w=s=wa=la=wt=lt=None;logs=[]
resource_stop=threading.Event();resource_worker=None
try:
 cli=out/"wbd-client-embedded.exe";lib=out/"wbd_engine.dll"
 for f in (cli,lib,out/"wintun.dll",root/"linux-product"/"wbd-v4-server",root/"linux-product"/"libwbd_engine.so"):
  if not f.exists() or f.stat().st_size<10000:raise RuntimeError("missing actual public native binary "+str(f))
 report["windows_cli_sha256"]=hashlib.sha256(cli.read_bytes()).hexdigest()
 report["linux_server_sha256"]=hashlib.sha256((root/"linux-product"/"wbd-v4-server").read_bytes()).hexdigest()
 ip=wsl("ip","-4","-o","addr","show","dev","eth0")
 m=re.search(r"\binet (\d+(?:\.\d+){3})/",ip)
 if not m:raise RuntimeError("WSL2 actual eth0 IPv4 missing")
 peer=m.group(1);server=unix(root/"linux-product");result=unix(out)
 route="aabbccddeeff0011223344556677889900112233445566778899aabbccddeeff"
 tunnel="102030405060708090a0b0c0d0e0f001"
 user="wbd-ci-native";password="native-tls-ci-only"
 wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
     "-keyout",result+"/key.pem","-out",result+"/cert.pem","-subj","/CN=wbd-v4.example.test",
     "-addext","subjectAltName=DNS:wbd-v4.example.test")
 linux=out/"start-linux.sh"
 # Original TLS-authenticated server selects the actual Windows11 carrier
 # persona before Rust M4 kernel RX; default W168 Linux legacy is unchanged.
 # Frozen-unadapted run 40357841232 rejected 546 original NPF frames.
 peer_persona=" --peer-persona windows11"
 report["expected_original_tcp_persona"]="windows11_original_go_server"
 linux.write_bytes(("#!/bin/sh\nset -eu\necho $$ > '"+result+"/linux-server.pid'\nexec env LD_LIBRARY_PATH='"+server+"' WBD_WL_RX_TUPLE_DIAG=1 '"+server+"/wbd-v4-server' --raw-interface eth0 --local-ip "+peer+" --local-port 443 --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24 --server-name wbd-v4.example.test --route-key-hex "+route+" --username "+user+" --password "+password+" --tunnel-id "+tunnel+" --tls-cert '"+result+"/cert.pem' --tls-key '"+result+"/key.pem' --mode "+server_mode+peer_persona+"\n").encode("utf-8"))
 log=(out/"server.log").open("w");logs.append(log)
 s=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(linux)],stdout=log,stderr=subprocess.STDOUT)
 # Linux server authenticated READY only AFTER the genuine Windows TLS client starts.
 args=[str(cli),"--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443","--source-port","41031","--server-name","wbd-v4.example.test","--route-key-hex",route,"--username",user,"--password",password,"--tunnel-id",tunnel,"--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDWLMAIN","--state-path",str(out/"owned-wal.json"),"--mtu",str(configured_mtu),"--lanes",str(lanes),"--fec-mode",("fixed" if fixed6 else "off"),
  "--fec-parity",("4" if fixed6 else "0"),"--fec.mode",client_fec,
  "--fec.profile",("maximum" if fixed6 or game_fixed else "strong"),"--route-mode","bypass-lan"]
 log=(out/"client.log").open("w");logs.append(log)
 w=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
 resource_worker=threading.Thread(
  target=sample_windows_original_process,
  args=(w,out/"windows-original-go-rust-process-1hz.jsonl",resource_stop),
  daemon=True)
 resource_worker.start()
 # Launch true independent Windows/Wintun and Linux/TUN kernel applications
 # CONCURRENTLY with original authenticated client Apply. That product
 # requires first, reverse and a post-reverse packet BEFORE emitting READY.
 # No app packets, ACKs, READY or OS Applied are simulated by this harness.
 app=out/"app.py"
 app.write_text(r"""import socket,sys,time,json,pathlib
local,remote,ready_file=sys.argv[1:4]
hold=float(sys.argv[4]) if len(sys.argv)>4 else 2.
cadence=float(sys.argv[5]) if len(sys.argv)>5 else .09
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
bind_deadline=time.monotonic()+30
while True:
 try:
  sock.bind((local,45901))
  break
 except OSError as e:
  if time.monotonic()>=bind_deadline:
   raise RuntimeError('real TUN/Wintun IPv4 lease bind failed on '+local) from e
  time.sleep(.15)
print(json.dumps({'phase':'bound','local':local,'remote':remote,'source':'real_kernel_socket'}),flush=True)
sock.setblocking(False)
seen=set()
sent=0
start=time.monotonic()
deadline=start+max(35.,hold+9.)
next_send=start
last_diag=start
ready_since=None
while time.monotonic()<deadline:
 now=time.monotonic()
 # Absolute monotonic pacing: Windows hosted timer wakeups may coalesce
 # fifteen 1.5ms ticks into one ~16ms wake. Stage up to 16 *separate*
 # real kernel UDP sends rather than mistaking wake frequency for the
 # SOURCE send rate. Linux and Windows use the SAME simple fixture.
 if now>=next_send:
  due=min(16,1+int((now-next_send)/cadence))
  for _ in range(due):
   try:
    sock.sendto(('WBD-PUBLIC-NORMAL-%s-%06d'%(local,sent)).encode(),(remote,45901))
    sent+=1
   except OSError:
    # Before route activation only successful native socket writes count.
    pass
   next_send+=cadence
  if next_send<now-.02:next_send=now
 while True:
  try: payload,peer=sock.recvfrom(2048)
  except BlockingIOError:break
  if peer[0]==remote and payload.startswith(b'WBD-PUBLIC-NORMAL-'):
   seen.add(payload)
 if now-last_diag>=1.:
  print(json.dumps({'phase':'udp_1hz','local':local,'sent':sent,'received':len(seen),'public_ready_seen':ready_since is not None}),flush=True)
  last_diag=now
 if pathlib.Path(ready_file).is_file():
  if ready_since is None:ready_since=now
  # Keep both genuine generators active beyond authenticated Apply.
  if sent>=24 and len(seen)>=12 and now-ready_since>=hold:break
 time.sleep(min(.03,cadence))
print(json.dumps({'local':local,'remote':remote,'sent':sent,'received':len(seen),'kernel_bind':'PASS','public_ready_seen':ready_since is not None}),flush=True)
sys.exit(0 if ready_since is not None and sent>=24 and len(seen)>=12 else 8)
""")
 done=out/"public-ready.flag"
 if done.exists():done.unlink()
 llog=(out/"linux-app.log").open("w");logs.append(llog)
 wlog=(out/"windows-app.log").open("w");logs.append(wlog)
 la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),"10.66.0.1","10.66.0.2",unix(done)],stdout=llog,stderr=subprocess.STDOUT)
 wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1",str(done)],stdout=wlog,stderr=subprocess.STDOUT)
 # This READY remains owned exclusively by the unmodified real product.
 ready(out/"client.log","WBD_WINDOWS_CLIENT_READY",w,30)
 ready(out/"server.log","V4_ORIGINAL_GO_GAME_NATIVE_READY" if is_game else "V4_ORIGINAL_GO_SERVER_NATIVE_READY",s,8)
 report["linux_ready"]="PASS_REAL_AFTER_ORIGINAL_TLS"
 if "WBD_WINDOWS_OS_APPLIED" not in (out/"client.log").read_text():raise RuntimeError("Windows public READY lacks native OS Applied")
 report["windows_ready"]="PASS_TRUE_TLS_RUST_WINTUN_NPCAP_OS_WAL"
 done.write_text("observed authentic client and Linux server READY\n")
 # The actual UDP app has a 30s real OS bind bound plus 35s payload
 # deadline. 18s parent wait previously killed it before it could report
 # which true kernel side was missing. Observe only liveness at low cost.
 until=time.monotonic()+70
 while wa.poll() is None or la.poll() is None:
  if w.poll() is not None:
   raise RuntimeError("original Windows native product terminated before duplex: return="+str(w.returncode)+" client="+(out/"client.log").read_text(errors="replace")[-520:])
  if s.poll() is not None:
   raise RuntimeError("original Linux raw/TUN server terminated before duplex: return="+str(s.returncode)+" server="+(out/"server.log").read_text(errors="replace")[-520:])
  if time.monotonic()>=until:
   raise RuntimeError("bounded real UDP kernel duplex incomplete; windows="+(out/"windows-app.log").read_text(errors="replace")[-520:]+" linux="+(out/"linux-app.log").read_text(errors="replace")[-520:])
  time.sleep(.2)
 if wa.returncode or la.returncode:
  raise RuntimeError("actual UDP app duplex failed win="+str(wa.returncode)+" linux="+str(la.returncode)+" logs="+(out/"windows-app.log").read_text(errors="replace")[-350:]+(out/"linux-app.log").read_text(errors="replace")[-350:])
 real={}
 for role in ("windows","linux"):
  data=json.loads((out/(role+"-app.log")).read_text().strip().splitlines()[-1])
  if data["received"]<12 or data["sent"]<24 or not data["public_ready_seen"] or data["kernel_bind"]!="PASS":
   raise RuntimeError("true "+role+" kernel UDP receipt invalid: "+repr(data))
  real[role]=data
 report["actual_kernel_udp"]=real
 report["app_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_UDP"
 report["initial_smoke"]="PASS_REAL_TWO_OS_UDP_BEFORE_MEASUREMENT"

 # Functional-only *real TCP* over the same original authenticated public
 # Wintun/TUN: each OS binds one TCP listener and dials the other. Two
 # independently established IPv4 streams must echo exact application bytes.
 # This is NOT a throughput/RTT/packet-loss measurement or fake carrier ACK.
 tcpapp=out/"tcp-functional.py"
 tcpapp.write_text(r"""import json,socket,sys,threading,time
local,remote=sys.argv[1:3]
port=45902
marker=("WBD-TCP-NATIVE-"+local+"-to-"+remote).encode()
listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind((local,port));listener.listen(1);listener.settimeout(16)
result={"local":local,"remote":remote,"server_received":0,"client_echo":False}
issues=[]
def serve():
 try:
  conn,peer=listener.accept()
  with conn:
   conn.settimeout(8)
   if peer[0]!=remote:raise RuntimeError("unexpected TCP peer")
   expected=("WBD-TCP-NATIVE-"+remote+"-to-"+local).encode()
   data=b""
   while len(data)<len(expected):
    chunk=conn.recv(2048)
    if not chunk:break
    data+=chunk
   if data!=expected:raise RuntimeError("invalid or incomplete genuine TCP peer marker")
   conn.sendall(data)
   result["server_received"]=len(data)
 except Exception as e:issues.append(str(e))
thread=threading.Thread(target=serve,daemon=True);thread.start()
deadline=time.monotonic()+14
while time.monotonic()<deadline:
 try:
  with socket.create_connection((remote,port),timeout=1.5) as conn:
   conn.settimeout(5);conn.sendall(marker)
   echoed=b""
   while len(echoed)<len(marker):
    chunk=conn.recv(2048)
    if not chunk:break
    echoed+=chunk
   if echoed!=marker:raise RuntimeError("TCP echo bytes mismatch")
   result["client_echo"]=True
   break
 except (OSError,TimeoutError):
  time.sleep(.1)
thread.join(timeout=16);listener.close()
if thread.is_alive() or issues or not result["client_echo"] or result["server_received"]<=0:
 print(json.dumps({"FAIL_REAL_TCP":result,"issues":issues}),flush=True)
 sys.exit(9)
result["tcp"]="PASS_REAL_KERNEL_BIDIRECTIONAL_STREAM"
print(json.dumps(result),flush=True)
""")
 ltlog=(out/"linux-tcp-app.log").open("w");logs.append(ltlog)
 wtlog=(out/"windows-tcp-app.log").open("w");logs.append(wtlog)
 lt=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(tcpapp),"10.66.0.1","10.66.0.2"],
     stdout=ltlog,stderr=subprocess.STDOUT)
 wt=subprocess.Popen([sys.executable,str(tcpapp),"10.66.0.2","10.66.0.1"],
     stdout=wtlog,stderr=subprocess.STDOUT)
 until=time.monotonic()+40
 while lt.poll() is None or wt.poll() is None:
  if w.poll() is not None or s.poll() is not None:
   raise RuntimeError("actual original Windows/Linux owner exited during TCP")
  if time.monotonic()>until:
   raise RuntimeError("real TCP duplex deadline; windows="+(out/"windows-tcp-app.log").read_text(errors="replace")[-450:]+
      " linux="+(out/"linux-tcp-app.log").read_text(errors="replace")[-450:])
  time.sleep(.1)
 if wt.returncode or lt.returncode:
  raise RuntimeError("real public TCP apps failed; windows="+(out/"windows-tcp-app.log").read_text(errors="replace")[-400:]+
     " linux="+(out/"linux-tcp-app.log").read_text(errors="replace")[-400:])
 tcp={}
 for role in ("windows","linux"):
  line=(out/(role+"-tcp-app.log")).read_text().strip().splitlines()[-1]
  observed=json.loads(line)
  if observed["tcp"]!="PASS_REAL_KERNEL_BIDIRECTIONAL_STREAM" or not observed["client_echo"] or observed["server_received"]<=0:
   raise RuntimeError("invalid real TCP native "+role+" "+repr(observed))
  tcp[role]=observed
 report["actual_kernel_tcp"]=tcp
 report["tcp_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_TCP"
 if mode=="auto-revision":
  # Exact original Go TLS→Linux FecV2Step→Rust quiescent revision.
  # No alternate first-send ACK, kernel shortcut or fake Applied marker.
  w.stdin.write("fec.profile=light\n");w.stdin.flush()
  ready(out/"client.log","WBD_WINDOWS_AUTO_REVISION_REQUESTED_NOT_APPLIED revision=2 profile=0",w,15)
  report["auto_revision_requested"]="PASS_REAL_RUST_OPERATOR_REVISION2_PENDING"
  again=[]
  for name in ("windows","linux"):
   f=(out/("auto-revision-"+name+"-udp.log")).open("w");logs.append(f);again.append(f)
  wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1",str(done),"12"],
    stdout=again[0],stderr=subprocess.STDOUT)
  la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",
    unix(app),"10.66.0.1","10.66.0.2",unix(done),"12"],
    stdout=again[1],stderr=subprocess.STDOUT)
  until=time.monotonic()+75
  while wa.poll() is None or la.poll() is None:
   if w.poll() is not None or s.poll() is not None:
    raise RuntimeError("original Windows/Linux TLS owner exited during Auto revision")
   if time.monotonic()>until:raise RuntimeError("real Auto revision2 kernel UDP timed out")
   time.sleep(.2)
  if wa.returncode or la.returncode:raise RuntimeError("true two-OS revision2 UDP FAIL")
  for name in ("windows","linux"):
   data=json.loads((out/("auto-revision-"+name+"-udp.log")).read_text().splitlines()[-1])
   if data["kernel_bind"]!="PASS" or data["sent"]<24 or data["received"]<12:
    raise RuntimeError("Auto revision2 original kernel UDP "+name+": "+repr(data))
   report["auto_revision_"+name]=data
  snapshots=[]
  for line in (out/"client.log").read_text(errors="replace").splitlines():
   if "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY " in line:
    try:snapshots.append(json.loads(line.split("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY ",1)[1]))
    except json.JSONDecodeError:pass
  applied=any(row.get("auto_applied_revision",0)>=2 for row in snapshots)
  report["auto_revision_applied"]=applied
  if not applied:raise RuntimeError("original mature M2 revision2 not Applied "+repr(snapshots[-3:]))
  print("WBD_WL_REAL_AUTO_DYNAMIC_REVISION2_APPLIED_AFTER_TWO_OS_KERNEL_UDP",flush=True)
 if mode=="auto-adaptive":
  # Real original Go credential TLS / Rust M2 mature first-send
  # / ALREADY shared Linux FecV2Step Auto decisions. No operator write,
  # New 2026-10-28 acceptance: first true one-grade native Applied within
  # 120s of sustained healthy business is sufficient. Source traffic holds
  # 119s after real READY to distinguish slow honest downshift from FAIL;
  # correct M2 sample/coverage gates and fail-closed SEQ remain unchanged.
  # injected loss/ACK or synthetic kernel/OS state. Low Mbps, enough PPS
  # for the Linux 512-sample and 4096-source genuinely VALID evidence.
  outputs=[]
  for name in ("windows","linux"):
   f=(out/("auto-adaptive-"+name+"-udp.log")).open("w")
   logs.append(f);outputs.append(f)
  wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1",
    str(done),"119",".0015"],stdout=outputs[0],stderr=subprocess.STDOUT)
  la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3",unix(app),"10.66.0.1","10.66.0.2",unix(done),"119",".003"],
    stdout=outputs[1],stderr=subprocess.STDOUT)
  until=time.monotonic()+150
  while wa.poll() is None or la.poll() is None:
   if w.poll() is not None or s.poll() is not None:
    raise RuntimeError("native TLS/Rust Auto owner exited before mature natural 2s/8s policy")
   if time.monotonic()>=until:
    raise RuntimeError("bounded real kernel Auto 2s/8s traffic deadline")
   time.sleep(.25)
  if wa.returncode or la.returncode:
   raise RuntimeError("genuine Windows/Linux natural Auto kernel UDP failed: "+
       (out/"auto-adaptive-windows-udp.log").read_text(errors="replace")[-420:]+
       (out/"auto-adaptive-linux-udp.log").read_text(errors="replace")[-420:])
  for name in ("windows","linux"):
   data=json.loads((out/("auto-adaptive-"+name+"-udp.log")).read_text().splitlines()[-1])
   if not data["public_ready_seen"] or data["kernel_bind"]!="PASS" or data["received"]<512:
    raise RuntimeError("native "+name+" Auto first-source cohort insufficient: "+repr(data))
   report["auto_adaptive_"+name]=data
  snapshots=[]
  for line in (out/"client.log").read_text(errors="replace").splitlines():
   if "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY " in line:
    try:snapshots.append(json.loads(line.split("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY ",1)[1]))
    except json.JSONDecodeError:pass
  # Real original-Go packet-stats AutoPending uses Go JSON omitempty:
  # missing key means bool false, but ONLY matching positive native M2
  # applied==requested revisions count; a pending request never qualifies.
  good=native_auto_true_applied_snapshots(snapshots)
  report["auto_adaptive_applied"]=bool(good)
  report["auto_adaptive_observations_1hz"]=len(snapshots)
  report["auto_adaptive_last_revisions"]=[
     row.get("auto_requested_revision",0) for row in snapshots[-8:]]
  if not good:
   raise RuntimeError("native FecV2Step natural Auto downshift NOT_APPLIED: "+
      repr(snapshots[-5:]))
  report["auto_adaptive_first_genuine_applied_snapshot_index"]=good[0]["snapshot_index"]
  report["auto_adaptive_native_revision"]=good[-1]["auto_applied_revision"]
  report["auto_adaptive_native_profile"]=good[-1]["auto_requested_profile"]
  print("WBD_WL_REAL_AUTO_NATURAL_SHARED_POLICY_M2_2S8S_APPLIED_AFTER_KERNEL_UDP",flush=True)
 stress=os.environ.get("WBD_WL_RUN_P200")=="1"
 v2_file=os.environ.get("WBD_WL_V2_SCENARIO","").strip()
 scenario=None
 v2_path=None
 if v2_file:
  from m0_wl_perf_v2_config import read_scenario
  if mode!="normal" or stress or os.environ.get("WBD_WL_RUN_N0")=="1":
   raise RuntimeError("WL_V2_REQUIRES_SINGLE_NORMAL_NOT_LEGACY_PERF")
  v2_path=(root/v2_file).resolve()
  if not v2_path.is_relative_to((root/"scenarios").resolve()) or v2_path.suffix!=".json":
   raise RuntimeError("WL_V2_UNSAFE_SCENARIO_PATH")
  scenario=read_scenario(v2_path)
  if scenario["tun_mtu"]!=configured_mtu:raise RuntimeError("WL_V2_TUN_MTU_NOT_APPLIED")
  staged=out/"wl-v2-scenario.json"
  staged.write_bytes(v2_path.read_bytes())
  if read_scenario(staged)["scenario_sha256"]!=scenario["scenario_sha256"]:
   raise RuntimeError("WL_V2_SCENARIO_STAGING_CHANGED")
  v2_path=staged
 if os.environ.get("WBD_WL_RUN_N0")=="1" or stress or scenario:
  if stress and os.environ.get("WBD_WL_RUN_N0")=="1":
   raise RuntimeError("N0 and P200 must be separate measurements")
  profile_name="v2" if scenario else "p200-250m-30p" if stress else "n0"
  seconds=str(scenario["duration_s"]) if scenario else "60" if stress else os.environ.get("WBD_WL_N0_SECONDS","60")
  if not scenario and seconds not in ("60","240"):
   raise RuntimeError("WL-N0 duration selector must be 60 or 240 seconds")
  # One declared measurement scenario, not a mixed matrix. Genuine Linux
  # egress and eth0-ingress→IFB kernel tc, not an in-app drop/latency shim.
  # It is deliberately after functional warmup, before both owned Stop.
  def netem(action):
   cmd=["wsl.exe","-d","Ubuntu","-u","root","--","python3",
        unix(root/"tools"/"m0_wl_netem.py"),action,unix(out),profile_name]
   if scenario:cmd.append(unix(v2_path))
   return run(cmd,timeout=35)
  owned=out/"wl-n0-netem-owned.json"
  try:
   report["WL_N0"]="ENVIRONMENT_OR_PRODUCT_NOT_YET_VERIFIED"
   print(netem("arm"),flush=True)
   # Existing 1Hz owner telemetry only: distinguish pre-run cumulative NPF
   # drops from measurements and never fabricate zero if no sample exists.
   npf_before=latest_counter(out/"client.log")
   (out/"wl-n0-start.flag").unlink(missing_ok=True)
   rate=unix(root/"tools"/"m0_wl_public_rate_app.py")
   output=unix(out)
   lrate=(out/"wl-n0-linux-app.log").open("w");logs.append(lrate)
   wrate=(out/"wl-n0-windows-app.log").open("w");logs.append(wrate)
   linuxrate=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
       "python3","-u",rate,"10.66.0.1","10.66.0.2",
       "linux",unix(out/"wl-n0-start.flag"),output,seconds,profile_name]+
       ([unix(v2_path)] if scenario else []),stdout=lrate,stderr=subprocess.STDOUT)
   windowsrate=subprocess.Popen([sys.executable,"-u",str(root/"tools"/"m0_wl_public_rate_app.py"),
       "10.66.0.2","10.66.0.1","windows",str(out/"wl-n0-start.flag"),str(out),seconds,profile_name]+
       ([str(v2_path)] if scenario else []),
       stdout=wrate,stderr=subprocess.STDOUT)
   try:
    ready(out/"wl-n0-linux-app.log",'"phase": "bound"',linuxrate,25)
    ready(out/"wl-n0-windows-app.log",'"phase": "bound"',windowsrate,25)
    (out/"wl-n0-start.flag").write_text("REAL_TWO_OS_KERNEL_APPLICATIONS_BOUND\n")
    # Poll process liveness, never relay/transform tested traffic.
    until=time.monotonic()+int(seconds)+25
    while linuxrate.poll() is None or windowsrate.poll() is None:
     if w.poll() is not None or s.poll() is not None:
      raise RuntimeError("real public product exited during WL-N0")
     if time.monotonic()>until:
      raise RuntimeError("bounded WL-N0 "+seconds+"s native app duration exceeded")
     time.sleep(.2)
    if linuxrate.returncode or windowsrate.returncode:
     raise RuntimeError("real kernel generator error windows="+str(windowsrate.returncode)+
                        " linux="+str(linuxrate.returncode))
   finally:
    for p in (linuxrate,windowsrate):
     if p.poll() is None:p.terminate()
   print(netem("snapshot"),flush=True)
   npf_after=latest_counter(out/"client.log")
   npf_delta=measured_delta(npf_before,npf_after)
   report["wl_n0_npcap_drop"]={
    "before":npf_before,"after":npf_after,"delta":npf_delta,
    "scope":"WINDOWS_OWNER_1HZ_APPROX_BOUNDARY_NOT_PRECISE_KERNEL_COUNTER",
    "status":"OBSERVED" if npf_delta is not None else "UNKNOWN"}
   print("WL_N0_NPF_MEASUREMENT_DROP "+json.dumps(report["wl_n0_npcap_drop"]),flush=True)
   wl={}
   for role in ("windows","linux"):
    wl[role]=json.loads((out/("wl-n0-"+role+"-app.json")).read_text())
   report["wl_n0_measured"]=wl
   report["wl_n0_tc_after"]="wl-n0-netem-after.json"
   after=json.loads((out/"wl-n0-netem-after.json").read_text())
   def count_packets(qdiscs):
    def find_counts(obj):
     if isinstance(obj,dict):
      if "packets" in obj and isinstance(obj["packets"],int):
       return [obj["packets"]]
      return sum((find_counts(v) for v in obj.values()),[])
     if isinstance(obj,list):
      return sum((find_counts(v) for v in obj),[])
     return []
    return max(find_counts(qdiscs) or [0])
   if scenario:
    declared=json.loads((out/"wl-n0-netem-before.json").read_text())
    target={"windows":scenario["windows_to_linux"]["offered_mbps"],
            "linux":scenario["linux_to_windows"]["offered_mbps"]}
    offered={role:row["sent_payload_mbps"] for role,row in wl.items()}
    delivery={role:row["received_payload_mbps"] for role,row in wl.items()}
    loss_fraction={
      "windows":round(wl["windows"]["received_first_packets"]/max(1,wl["linux"]["sent_packets"]),6),
      "linux":round(wl["linux"]["received_first_packets"]/max(1,wl["windows"]["sent_packets"]),6)}
    valid=all(row.get("scenario_sha256")==scenario["scenario_sha256"] and
              row["measurement_duration_s"]==float(seconds) for row in wl.values())
    tc_seen=count_packets(after["eth0"])>0 and count_packets(after["ifb"])>0
    offered_ok=all(offered[k]>=.95*v for k,v in target.items())
    status=("INCONCLUSIVE_SCENARIO_OR_MEASUREMENT" if not valid
            else "INCONCLUSIVE_TC_CARRIER_NOT_OBSERVED" if not tc_seen
            else "CAPACITY_LIMITED_GENERATOR_OFFER" if not offered_ok
            else "MEASURED_BOTH_OS_KERNEL")
    report["WL_V2"]={
      "status":status,"scenario_id":scenario["scenario_id"],
      "scenario_sha256":scenario["scenario_sha256"],
      "declared":scenario,"offered_mbps":offered,"target_mbps":target,
      "first_delivered_mbps":delivery,"first_delivery_fraction":loss_fraction,
      "generator_cpu_s":{k:v["sender_cpu_seconds"] for k,v in wl.items()},
      "kernel_qdisc":"wl-n0-netem-after.json",
      "scope":"REAL_WINDOWS_WINTUN_NPF_GO_TLS_AND_LINUX_TUN_NOT_ONEWAY_P99"}
    print("WL_V2_TRUE_KERNEL_MEASUREMENT "+status,flush=True)
   elif stress:
    declared=json.loads((out/"wl-n0-netem-before.json").read_text())
    requested=declared.get("requested_kernel_profile")
    if declared.get("declared_profile")!=profile_name or requested!=get_profile(profile_name):
     report["WL_P200"]="FAIL_KERNEL_IMPAIRMENT_PROFILE_NOT_READ_BACK"
    elif any(row.get("measurement_duration_s")!=float(seconds) or
             row.get("kernel_impairment_profile")!=profile_name for row in wl.values()):
     report["WL_P200"]="FAIL_MISMATCHED_TWO_OS_GENERATOR_HORIZON"
    elif count_packets(after["eth0"])==0 or count_packets(after["ifb"])==0:
     report["WL_P200"]="INCONCLUSIVE_KERNEL_TC_DIRECTION_COUNTS_UNOBSERVED"
    elif not all(x["received_first_packets"]>0 for x in wl.values()):
     report["WL_P200"]="FAIL_NO_REAL_TWO_OS_APPLICATION_DELIVERY"
    elif min(x["sent_payload_mbps"] for x in wl.values())<225:
     report["WL_P200"]="CAPACITY_LIMITED_OFFERED_BELOW_90PCT_250MBPS"
    else:
     report["WL_P200"]="PASS_SCOPED_KERNEL_200MS_30PCT_250MBIT_60S_BOTH_DIRECTIONS"
    report["wl_p200_measured"]={
     "declared":requested,
     "offered_mbps":{side:row["sent_payload_mbps"] for side,row in wl.items()},
     "delivered_mbps":{side:row["received_payload_mbps"] for side,row in wl.items()},
     "unique_received_fraction":{
      "windows":round(wl["windows"]["received_first_packets"]/max(1,wl["linux"]["sent_packets"]),5),
      "linux":round(wl["linux"]["received_first_packets"]/max(1,wl["windows"]["sent_packets"]),5)},
     "kernel_qdisc":report["wl_n0_tc_after"],
     "interpretation":"250 Mbit/s is offered generator target and kernel link rate, not guaranteed end-to-end goodput",
    }
    print("WL_P200_TRUE_KERNEL_MEASUREMENT "+report["WL_P200"],flush=True)
   elif any(row.get("measurement_duration_s")!=float(seconds) for row in wl.values()):
    report["WL_N0"]="FAIL_MISMATCHED_OS_MEASUREMENT_DURATION"
   elif count_packets(after["eth0"])==0 or count_packets(after["ifb"])==0:
    report["WL_N0"]="INCONCLUSIVE_KERNEL_TC_DIRECTION_COUNTS_UNOBSERVED"
   elif min(x["sent_payload_mbps"] for x in wl.values())<9.7:
    report["WL_N0"]="HOST_OR_GENERATOR_OR_PRODUCT_CAPACITY_LIMITED"
   elif min(wl["windows"]["received_first_packets"]/max(wl["linux"]["sent_packets"],1),
            wl["linux"]["received_first_packets"]/max(wl["windows"]["sent_packets"],1))<.999:
    report["WL_N0"]="VALID_OBSERVATION_LOSSLESS_DELIVERY_BELOW_99_9_PCT"
   elif npf_delta is None:
    report["WL_N0"]="INCONCLUSIVE_NPCAP_MEASUREMENT_DELTA_UNKNOWN"
   elif npf_delta>0:
    report["WL_N0"]="LOCAL_NPCAP_DROPS_DURING_ZERO_INJECTED_LOSS"
   else:
    report["WL_N0"]="PASS_SCOPED_300MS_0PCT_10MBPS_"+seconds+"S_BOTH_DIRECTIONS"
   print("WL_N0_TRUE_KERNEL_MEASUREMENT "+report["WL_N0"],flush=True)
  finally:
   if owned.exists():
    print(netem("cleanup"),flush=True)
 stop_windows(w)
 stop_marker="WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" if is_game else "WBD_WINDOWS_NATIVE_DISCONNECTED_V1"
 if w.returncode!=0 or stop_marker not in (out/"client.log").read_text():raise RuntimeError("Windows native owned WAL Stop missing")
 stop_linux();s.wait(timeout=10)
 stop_marker="V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server" if is_game else "V4_PUBLIC_NATIVE_STOP_DRAINED role=server"
 if s.returncode or stop_marker not in (out/"server.log").read_text():raise RuntimeError("Linux original Rust Stop missing")
 report["stop"]="PASS_BOTH_OWNED"
 if scenario:
  report["WL_V2"]["owned_stop"]="PASS_BOTH_OWNED"
  report["WL_V2"]["variant"]="go-steady" if os.environ.get("WBD_WL_PERF_AB_GO_STEADY")=="1" else "rust-native"
 if fixed6:
  applied="WBD_WINDOWS_FEC2_M2_MATURE_SCOPED mode=fec-fixed" in (out/"client.log").read_text(errors="replace")
  report["fixed_m2_mature"]=applied
  if not applied:raise RuntimeError("original Rust Fixed FEC2 mature authenticated M2 Applied missing")
 if is_game and game_fixed:
  expected="V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=fixed profile=6"%lanes
  if expected not in (out/"server.log").read_text(errors="replace"):
   raise RuntimeError("actual Game FEC2 protected Linux profile readback missing")
 report["mode_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_"+mode
 if mode=="normal":report["normal_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE"
 print("WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS "+mode)
except Exception as e:
 report["mode_public"]="FAIL_TRUE_PUBLIC_EXECUTION"
 if mode=="normal":report["normal_public"]="FAIL_TRUE_PUBLIC_EXECUTION"
 report["error"]=str(e)[-1100:]
 print("WBD_WL_TRUE_PUBLIC_MODE_FAIL "+mode+": "+str(e),file=sys.stderr)
 raise
finally:
 resource_stop.set()
 if resource_worker is not None:resource_worker.join(timeout=3)
 for p in (wa,la,wt,lt):
  if p is not None and p.poll() is None:p.terminate()
 stop_windows(w);stop_linux()
 if s and s.poll() is None:
  try:s.wait(timeout=4)
  except subprocess.TimeoutExpired:s.terminate()
 for log in logs:log.close()
 if mode=="auto-adaptive":
  # On both PASS and FAIL, retain actual host socket progress per source.
  # These are application samples only, never synthetic M2 maturity.
  report["auto_adaptive_real_source_progress"]={
    name:summarize_auto_udp_progress(out/("auto-adaptive-"+name+"-udp.log"))
    for name in ("windows","linux")}
 # Preserve first error/Stop outcome, and attach only measured original
 # owner and whole Go+Rust EXE resource observations from THIS mode.
 # Absence remains typed NOT_MEASURED; no readiness/p99 fabricated.
 if mode=="normal":
  path=out/"client.log"
  report["rust_owner_lock_wait"]=parse_native_lock_profile(
   path.read_text(errors="replace") if path.exists() else "")
 try:
  report["runtime_observability"]=source_locked_observability(out)
 except Exception as sample_error:
  report["runtime_observability"]={
   "result":"NOT_MEASURED_DIAGNOSTIC_PARSER_ERROR",
   "type":type(sample_error).__name__}
 (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
