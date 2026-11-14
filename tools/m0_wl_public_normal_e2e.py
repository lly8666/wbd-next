#!/usr/bin/env python3
"""Run actual original-TLS Windows and Linux native public UDP/TCP, then Stop."""
import os,sys,subprocess,time,json,hashlib,pathlib,re,threading,faulthandler,atexit,secrets
from m0_wl_native_resource_sampler import sample_windows_original_process
from m0_wl_windows_cpu_audit import summarize_windows_cpu
from m0_wl_mode_runtime_report import source_locked_observability,summarize_auto_udp_progress,native_auto_true_applied_snapshots
from m0_wl_native_mtu_contract import configured_native_test_mtu,native_outer_choice,verified_native_windows_inner_mtu
from m0_wl_n0_drop_delta import latest_counter, measured_delta
from m0_wl_impairment_profile import get_profile
from m0_wl_lock_profile import parse_native_lock_profile
from m0_wl_plan027_linux_tun_fq import fq_delta
from m0_wl_plan027_linux_tun_link import link_delta,tun_queue_identity
root=pathlib.Path.cwd();out=root/"result"/"wl-public";out.mkdir(parents=True,exist_ok=True)
mode=os.environ.get("WBD_WL_PUBLIC_MODE","normal")
configured_mtu=configured_native_test_mtu()
native_outer=native_outer_choice(os.environ.get('WBD_WL_NATIVE_OUTER_MTU_REQUEST','legacy1400'))
plan028_owned_switch=os.environ.get('WBD_PLAN028_WSL_OWNED_SWITCH','0')=='1'
plan028_owned_mtu_only=os.environ.get('WBD_PLAN028_WSL_OWNED_MTU_ONLY','0')=='1'
# One new SOURCE-locked real signed Wintun NativeOwner scene. H1743
# pure Tunnel remains a separate immutable qualification record.
p029_direct=os.environ.get("WBD_PLAN029_V3_DIRECT_SCENE")=="1"
# H1840 tests the REAL user-selected cold split with all private CI trial
# switches off in the launched original Go process. One source, one signed
# Wintun and one Rust owner; no simulated GUI or routing Applied receipt.
p029_product=os.environ.get("WBD_PLAN029_PRODUCT_SPLIT_SCENE")=="1"
p029_tunnel_alias="203.0.113.77"
p029_converse_cn4="198.19.254.2"
p029_tcp53=os.environ.get("WBD_PLAN029_APP_TCP53_SCENE")=="1"
p029_padding=os.environ.get("WBD_PLAN029_STARTUP_PADDING_SCENE")=="1"
p029_outer1460=os.environ.get("WBD_PLAN029_REAL_DEFAULT_OUTER1460")=="1"
p029_cache=os.environ.get("WBD_PLAN029_DNS_CACHE_SCENE")=="1"
p029_pressure=os.environ.get("WBD_PLAN029_DIRECT_PRESSURE")=="1"
p029_multia=os.environ.get("WBD_PLAN029_D3_MULTIA_SCENE")=="1"
p029_p2=os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")=="1"
if p029_p2 and (not p029_direct or p029_multia or p029_cache or
                p029_pressure or p029_padding or p029_tcp53 or mode!="normal"):
 raise RuntimeError("H1815 P2 signed moderate physical/Direct/Tunnel single Normal scene is exclusive")
if p029_multia and (not p029_direct or p029_cache or p029_pressure or
                    p029_padding or p029_tcp53 or mode!="normal"):
 raise RuntimeError("H1807 genuine Normal signed CNAME+two-A scene must be exclusive")
if p029_outer1460 and not (p029_direct and not p029_pressure and
                           native_outer=="default1460" and mode=="normal"):
 raise RuntimeError("H1791 default1460 requires signed Normal Direct, no hard8 pressure")
if p029_cache and not p029_direct:
 raise RuntimeError("H1783 signed Direct cache witness requires CN Direct scene")
if p029_tcp53 and not p029_direct:
 raise RuntimeError("H1794 signed app TCP53 requires one original CN Direct owner")
if p029_padding and (mode!="normal" or p029_direct or
                     os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="1" or
                     os.environ.get("GITHUB_ACTIONS")!="true"):
 raise RuntimeError("H1799 single ordinary startup padding scene needs signed Normal V3 Tunnel-only")
if p029_pressure and not p029_direct:
 raise RuntimeError("hard8 pressure requires exactly one signed Normal Direct scene")
if p029_product and (not p029_direct or mode!="normal" or
    p029_multia or p029_cache or p029_pressure or p029_p2 or
    p029_padding or p029_tcp53 or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0"):
 raise RuntimeError("H1840 real product CN split requires single Normal owner, no private trial or mixed P2")
if p029_direct and not p029_product and (mode!="normal" or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="1" or
    os.environ.get("GITHUB_ACTIONS")!="true"):
 raise RuntimeError("PLAN029 legacy Direct CN trial requires exact source-locked Normal V3")
if plan028_owned_mtu_only and (not plan028_owned_switch or mode!='normal' or native_outer!='default1460'):
 raise RuntimeError('PLAN028 true physical MTU-only original Windows WSL2 test requires owned source IP, Normal Off and default1460')
if plan028_owned_switch and (mode not in ('normal','fixed','auto','game4','game4-fec') or native_outer!='default1460'):
 raise RuntimeError('PLAN028 owned source4 switch supports Normal off, fixed6, auto, Game4 off or Game4FEC6 with default1460 only')
if mode not in ("normal","fixed","auto","game2","game4","game2-fec","game4-fec","auto-revision","auto-adaptive"):
 raise RuntimeError("unknown exact native Windows public mode "+mode)
fixed6=mode=="fixed"
is_game=mode.startswith("game")
game_fixed=mode.endswith("-fec")
# One exact SOURCE-selected cold policy for both ORIGINAL endpoints.
outer_repair=os.environ.get("WBD_WL_OUTER_REPAIR","on")
if outer_repair not in ("on","off"):
 raise RuntimeError("unsupported original Windows outer-repair selection")
def game_cold_stage(stage):
 if not game_fixed:return
 # Append-only fixed stage name; no TLS/route keys, packets or identity.
 with (out/"gamefec-cold-stage.txt").open("a") as f:
  f.write(stage+"\n")
if game_fixed:
 (out/"gamefec-cold-stage.txt").unlink(missing_ok=True)
 game_cold_stage("COLD_E2E_STARTED")
 _e2e_stack=(out/"gamefec-e2e-stack.txt").open("w")
 faulthandler.dump_traceback_later(105,file=_e2e_stack,exit=False)
 atexit.register(lambda:(faulthandler.cancel_dump_traceback_later(),_e2e_stack.close()))
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
 "requested_native_outer_selector":native_outer,
  "requested_original_outer_repair":outer_repair,
 "runtime_os_mtu_guard":"ORIGINAL_NATIVE_M4_1HZ_FAIL_CLOSED"}
def run(a,timeout=30):
 # The outer suite already writes to a file, but this inner WSL command
 # must not leave an inherited capture_output PIPE writer inside WSL.
 # Reuse the existing bounded, file-backed OS-command runner. Its one
 # owning PID returns the real status even if Linux descendants remain.
 wrapped=[sys.executable,str(root/"tools"/"m0_wl_windows_bounded_cmd.py"),
          str(timeout),*a]
 p=subprocess.run(wrapped,capture_output=True,text=True,timeout=timeout+25)
 if p.returncode:raise RuntimeError(str(a[:4])+": "+(p.stderr or p.stdout)[-600:])
 return p.stdout.strip()
def wsl(*a,timeout=30):return run(["wsl.exe","-d","Ubuntu","-u","root","--",*a],timeout)
def unix(p):
 q=pathlib.Path(p).resolve()
 return "/mnt/"+q.drive[0].lower()+"/"+"/".join(q.relative_to(q.anchor).parts)

def h1775_owned_apply(host,peer):
 side=out/"plan029-h1775-owned-route-alias.json"
 if side.exists():raise RuntimeError("H1775 foreign owner file")
 target=p029_converse_cn4
 if target+"/32" in wsl("ip","-4","-o","addr","show","dev","eth0",timeout=8):
  raise RuntimeError("H1775 foreign Linux eth0 alias")
 ps=("$ErrorActionPreference='Stop';"+
  "if(@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -ErrorAction SilentlyContinue).Count -ne 0){throw 'foreign H1775 route'};"+
  "$a=@(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '__HOST__' -ErrorAction Stop);"+
  "if($a.Count -ne 1){throw 'nonunique physical source'};Write-Output $a[0].InterfaceIndex")
 ps=ps.replace("__TARGET__",target).replace("__HOST__",host)
 idx=run(["powershell.exe","-NoProfile","-NonInteractive","-Command",ps],timeout=15).strip()
 if not idx.isdigit() or int(idx)<=0:raise RuntimeError("H1775 physical ifindex invalid")
 owner={"source_sha":os.environ["GITHUB_SHA"],"target":target,
        "peer":peer,"host":host,"ifindex":int(idx),"state":"INTENT"}
 side.write_text(json.dumps(owner,sort_keys=True)+"\n")
 wsl("ip","-4","addr","add",target+"/32","dev","eth0",timeout=8)
 if target+"/32" not in wsl("ip","-4","-o","addr","show","dev","eth0",timeout=8):
  raise RuntimeError("H1775 Linux alias readback absent")
 ps=("$ErrorActionPreference='Stop';"+
  "New-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -InterfaceIndex __IDX__ -NextHop '__PEER__' -PolicyStore ActiveStore -ErrorAction Stop|Out-Null;"+
  "$r=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -ErrorAction Stop);"+
  "if($r.Count -ne 1 -or $r[0].InterfaceIndex -ne __IDX__ -or $r[0].NextHop -ne '__PEER__'){throw 'H1775 route readback mismatch'}")
 ps=ps.replace("__TARGET__",target).replace("__IDX__",idx).replace("__PEER__",peer)
 run(["powershell.exe","-NoProfile","-NonInteractive","-Command",ps],timeout=15)
 owner["state"]="OWNED";side.write_text(json.dumps(owner,sort_keys=True)+"\n")
 print("PLAN029_H1775_ONE_TEST_OWNED_PHYSICAL_ROUTE_AND_ALIAS_APPLIED",flush=True)

def h1775_owned_cleanup():
 side=out/"plan029-h1775-owned-route-alias.json"
 if not side.exists():return
 owner=json.loads(side.read_text())
 if (owner.get("source_sha")!=os.environ["GITHUB_SHA"] or
     owner.get("target")!=p029_converse_cn4 or
     owner.get("state") not in ("INTENT","OWNED") or
     type(owner.get("ifindex")) is not int or owner["ifindex"]<=0 or
     not owner.get("peer")):
  raise RuntimeError("H1775 foreign route/alias owner; do not mutate")
 target=owner["target"];idx=str(owner["ifindex"]);peer=owner["peer"]
 ps=("$ErrorActionPreference='Stop';"+
  "$r=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -ErrorAction SilentlyContinue);"+
  "if($r.Count -gt 1){throw 'H1775 ambiguous owned route'};"+
  "if($r.Count -eq 1){if($r[0].InterfaceIndex -ne __IDX__ -or $r[0].NextHop -ne '__PEER__'){throw 'H1775 foreign route'};"+
  "Remove-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -InterfaceIndex __IDX__ -NextHop '__PEER__' -Confirm:$false -ErrorAction Stop};"+
  "if(@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '__TARGET__/32' -ErrorAction SilentlyContinue).Count -ne 0){throw 'route not removed'}")
 ps=ps.replace("__TARGET__",target).replace("__IDX__",idx).replace("__PEER__",peer)
 run(["powershell.exe","-NoProfile","-NonInteractive","-Command",ps],timeout=15)
 if target+"/32" in wsl("ip","-4","-o","addr","show","dev","eth0",timeout=8):
  wsl("ip","-4","addr","del",target+"/32","dev","eth0",timeout=8)
 if target+"/32" in wsl("ip","-4","-o","addr","show","dev","eth0",timeout=8):
  raise RuntimeError("H1775 exact Linux alias not removed")
 side.unlink()
 print("PLAN029_H1775_ONE_ROUTE_AND_ALIAS_EXACT_CLEANUP_PASS",flush=True)

def game_due_first_fault():
 # Only the original Rust first-failure branch triggers an early verdict.
 # No synthetic delivery, packet parsing, extended watchdog or telemetry loop.
 if not is_game:return
 path=out/"client.log"
 if not path.exists():return
 lines=path.read_text(errors="replace").splitlines()
 fault=[line for line in lines if
  "M0_PLAN027_GAME_DUE_FAULT first_failure=1" in line or
  "M0_PLAN026_GAME_NATIVE_FIRST_ERROR" in line or
  "M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line or
  "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_disconnect result=FAIL" in line]
 if not fault:return
 print("WL_GAME_DUE_EXACT_PRODUCT_FIRST_FAILURE "+fault[0][-850:],flush=True)
 for line in lines:
  if ("M0_PLAN027_GAME_DUE_FAULT stage=send_records_entry" in line or
      "M0_PLAN027_GAME_DUE_FAULT stage=wire_frame_build_bytes" in line):
   print("WL_GAME_DUE_EXACT_PRODUCT_BRANCH "+line[-850:],flush=True)
 # Request normal owned Stop, then report Rust worker state separately
 # from upper native product WAL. Never forge successful Stop receipts.
 stop_windows(w)
 after=path.read_text(errors="replace").splitlines()
 for line in after:
  if ("M0_PLAN027_GAME_NATIVE_STOP_JOIN" in line or
      "M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line or
      "M0_PLAN027_NATIVE_STOP_RESULT" in line or
      "M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX" in line):
   print("WL_GAME_DUE_ORIGINAL_WORKER_WAL "+line[-850:],flush=True)
 native="JOINED" if any("M0_PLAN027_GAME_NATIVE_STOP_JOIN" in line for line in after) else (
   "NOT_DRAINED" if any("M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line for line in after) else "NOT_OBSERVED")
 wal="RESTORED" if any("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" in line for line in after) else "NOT_RESTORED"
 print("WL_GAME_DUE_DIAGNOSTIC_FINAL native_worker_stop="+native+
       " upper_wal_stop="+wal+" original_rc="+str(w.poll()),flush=True)
 raise RuntimeError("GAME_FEC_REAL_NATIVE_FIRST_FAULT native="+native+" wal="+wal)
def ready(path,marker,process,seconds):
 for _ in range(seconds*5):
  if game_fixed and (out/"gamefec-stop-request.flag").exists():
   raise RuntimeError("GAMEFEC_ORIGINAL_OWNER_STOP_REQUESTED_BEFORE_READY")
  game_due_first_fault()
  if path.exists() and marker in path.read_text(errors="replace"):return
  if process.poll() is not None:raise RuntimeError(marker+" process exited "+str(process.returncode)+": "+path.read_text(errors="replace")[-800:])
  time.sleep(.2)
 raise RuntimeError(marker+" not observed: "+path.read_text(errors="replace")[-800:])
def stop_linux():
 # A true Stop is witnessed by the server's drained marker and exit status.
 # The outer finally must not signal an already-exited PID again and emit
 # a misleading STOP_REQUEST_FAILED after an actual owned Stop PASS.
 if s is not None and s.poll() is not None:
  return
 # wsl.exe can hang independently of the original Rust server, and an
 # unbounded wsl.exe here previously swallowed the real preceding error.
 f=out/"linux-server.pid"
 if f.exists() and f.read_text().strip().isdigit():
  try:
   proc=subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--","kill","-TERM",f.read_text().strip()],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8,check=False)
   if proc.returncode:
    print("WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code="+str(proc.returncode),file=sys.stderr,flush=True)
  except subprocess.TimeoutExpired:
   print("WL_REAL_LINUX_OWNED_STOP_REQUEST_TIMEOUT seconds=8",file=sys.stderr,flush=True)
def stop_windows(p):
 if p and p.poll() is None:
  try:p.stdin.write("stop\n");p.stdin.flush();p.wait(timeout=15)
  except Exception:
   p.terminate()
   try:p.wait(timeout=4)
   except subprocess.TimeoutExpired:p.kill()
w=s=wa=la=wt=lt=tls_capture=p029_alias_proc=p029_guest_proc=p029_client_proc=p029_tun_dns_guest=p029_tun_dns_win=p029_dns_blackhole_guest=p029_dns_blackhole_win=p029_d2_tun_guest=p029_d2_tun_win=p029_d2_cn_guest=p029_d2_cn_win=p029_pressure_guest=p029_pressure_win=p029_tcp53_guest=p029_tcp53_win=None;logs=[]
route_local=route_guest=None
# The real Windows Npcap client and the Linux WSL2 server are one scenario,
# never an unattended seven-mode matrix or a scripted TLS clone.
tls_wire=os.environ.get("WBD_WL_TLS_WIRE_AUDIT","0")=="1"
if tls_wire and mode!="normal":
 raise RuntimeError("PLAN028 Windows TLS wire audit only supports one Normal mode")
def end_tls_capture():
 if tls_capture is None:return
 pid_file=out/"tls-capture.pid"
 if pid_file.exists() and pid_file.read_text().strip().isdigit():
  try:wsl("kill","-INT",pid_file.read_text().strip(),timeout=12)
  except Exception:pass
 try:tls_capture.wait(timeout=12)
 except subprocess.TimeoutExpired:
  tls_capture.terminate()
  try:tls_capture.wait(timeout=4)
  except subprocess.TimeoutExpired:tls_capture.kill()
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
 peer=m.group(1)
 if plan028_owned_switch:
  # The native Windows job prepared only test-owned WSL2 aliases and
  # verified the preferred original physical source before TLS begins.
  if '198.19.254.2/' not in ip:raise RuntimeError('original WSL guest owned server alias missing')
  alias=json.loads((out/"plan028-owned-alias.json").read_text())
  if alias["stage"]!="PREPARED" or alias["host_source_old"]!="198.19.254.1":
   raise RuntimeError("test-owned Windows WSL2 source not OS-prepared")
  peer="198.19.254.2"
  report["plan028_owned_underlay_before"]="198.19.254.1"
 server=unix(root/"linux-product");result=unix(out)
 game_cold_stage("COLD_WSL_IP_READY")
 # A fresh offline secret: no public constant, on-wire WB-R1, argv secret or
 # third-party KMS. WSL2 receives its own exact regular owner-only copy.
 route_local=out/"route-key-private.hex"
 fd=os.open(route_local,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,"w",encoding="ascii") as f:f.write(secrets.token_hex(32)+"\n")
 route_guest="/run/wbd-plan028-route-"+os.environ["GITHUB_RUN_ID"]+".hex"
 wsl("install","-m","600",unix(route_local),route_guest)
 report["route_key"]={"source":"offline_per_run_file","bytes":32,"online_exchange":False}
 tunnel="102030405060708090a0b0c0d0e0f001"
 user="wbd-ci-native";password="native-tls-ci-only"
 wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
     "-keyout",result+"/key.pem","-out",result+"/cert.pem","-subj","/CN=wbd-v4.example.test",
     "-addext","subjectAltName=DNS:wbd-v4.example.test")
 game_cold_stage("COLD_TLS_CERT_READY")
 if tls_wire:
  # Bounded real WSL2 eth0 capture starts BEFORE the original Npcap SYN.
  # Raw private PCAP is never part of the published Action artifact.
  wsl("sh","-c","command -v tcpdump >/dev/null || (apt-get update -qq && apt-get install -y -qq tcpdump)",timeout=120)
  capture_script=out/"start-tls-capture.sh"
  # Windows text-mode writes CRLF, which breaks WSL /bin/sh 'set -eu'.
  # Write the exact ELF/Go server script style: binary LF-only bytes.
  # $$ is expanded by the guest shell for its owned capture PID/Stop.
  capture_script.write_bytes(("#!/bin/sh\nset -eu\necho "+chr(36)*2+
    " > '"+result+"/tls-capture.pid'\nexec tcpdump -i eth0 -n -s 4096 -U -w '"+
    result+"/tls-firstflight.pcap' tcp port 443\n").encode("ascii"))
  caplog=(out/"tls-capture-stderr.log").open("w");logs.append(caplog)
  tls_capture=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(capture_script)],
    stdout=subprocess.DEVNULL,stderr=caplog)
  for tick in range(120):
   if tls_capture.poll() is not None:
    # First actual /bin/sh or tcpdump error, bounded and redacted from logs.
    caplog.flush()
    reason=(out/"tls-capture-stderr.log").read_text(errors="replace")[-1600:]
    raise RuntimeError("real WSL2 capture exited before Windows SYN"+
      " rc="+str(tls_capture.returncode)+" stderr="+repr(reason))
   caplog.flush()
   if "listening on eth0" in (out/"tls-capture-stderr.log").read_text(errors="replace"):break
   time.sleep(.1)
  else:raise RuntimeError("WSL2 tcpdump not listening before Windows SYN")
  report["tls_capture"]={"vantage":"WSL2_eth0_real_TCP","raw_pcap_artifact":False}
 linux=out/"start-linux.sh"
 # Original TLS-authenticated server selects the actual Windows11 carrier
 # persona before Rust M4 kernel RX; default W168 Linux legacy is unchanged.
 # Frozen-unadapted run 40357841232 rejected 546 original NPF frames.
 peer_persona=" --peer-persona windows11"
 report["expected_original_tcp_persona"]="windows11_original_go_server"
 # This ONE explicit original-Auto diagnostic scenario activates existing
 # Rust 500ms FEC/M4 snapshots, no per-record logging or release overhead.
 egress_diag=(" WBD_FEC_EGRESS_DIAG=1"
    if mode=="auto" and os.environ.get("WBD_WL_V2_SCENARIO","").endswith(
        "scenarios/plan027-h461-auto-egress-10m-25ms-loss0-60s.json") else "")
 linux.write_bytes(("#!/bin/sh\nset -eu\necho $$ > '"+result+"/linux-server.pid'\nexec env LD_LIBRARY_PATH='"+server+"' WBD_WL_RX_TUPLE_DIAG=1"+egress_diag+" '"+server+"/wbd-v4-server' --raw-interface eth0 --local-ip "+peer+" --local-port 443 --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24 --server-name wbd-v4.example.test --route-key-hex-file "+route_guest+" --username "+user+" --password "+password+" --tunnel-id "+tunnel+(" --manual-client-lease4 10.66.0.2/32" if plan028_owned_switch else "")+" --tls-cert '"+result+"/cert.pem' --tls-key '"+result+"/key.pem' --mode "+server_mode+" --outer-repair "+outer_repair+peer_persona+(" --outer-mtu "+str(configured_mtu) if native_outer in ("1280","1460","1500") else "")+"\n").encode("utf-8"))
 log=(out/"server.log").open("w");logs.append(log)
 s=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(linux)],stdout=log,stderr=subprocess.STDOUT)
 if p029_direct:
  # The existing Linux kernel TUN must have a test-owned PUBLIC /32 alias
  # for protected Tunnel business. Its ordinary 10.66.0.1 RFC1918 address
  # would be Direct by policy and could fake a successful split test.
  # The shell waits for the ORIGINAL server-created TUN and touches no
  # default route or foreign address. Its exact owner file is a CAS token.
  owned=out/"plan029-h1745-owned-tun-alias.txt"
  owned.unlink(missing_ok=True)
  helper=out/"plan029-h1745-create-tun-alias.sh"
  helper.write_bytes(("#!/bin/sh\nset -eu\n"+
    "for i in $(seq 1 240); do\n"+
    " if ip -4 -o addr show dev wbdwl4 >/dev/null 2>&1; then\n"+
    "  if ip -4 -o addr show dev wbdwl4 | grep -q '"+p029_tunnel_alias+"/32'; then exit 21; fi\n"+
    "  ip -4 addr add "+p029_tunnel_alias+"/32 dev wbdwl4\n"+
    "  echo '"+p029_tunnel_alias+"/32' > '"+result+"/plan029-h1745-owned-tun-alias.txt'\n"+
    "  echo PLAN029_H1745_ORIGINAL_LINUX_TUN_UNDERLAY_ALIAS_OWNED;exit 0\n"+
    " fi\n sleep .1\ndone\nexit 22\n").encode("ascii"))
  alias_log=(out/"plan029-h1745-tun-alias.log").open("w");logs.append(alias_log)
  p029_alias_proc=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
       "sh",unix(helper)],stdout=alias_log,stderr=subprocess.STDOUT)
  rules=out/"plan029-h1745-cn-domains.txt"
  rules.write_text("cn.example\n",encoding="ascii")
  os.environ["WBD_PLAN029_CN_RULES_FILE"]=str(rules)
  (out/"plan029-h1775-cn-one32.txt").write_text(p029_converse_cn4+"/32\n",encoding="ascii")
 # Linux server authenticated READY only AFTER the genuine Windows TLS client starts.
 # PLAN029 private signed V3 smoke first checks ONLY ordinary protected
 # Tunnel. The Linux 10.66/24 guest is intentionally in RFC1918, so
 # bypass-lan would Direct-route the test traffic and falsely fail the
 # authenticated tunnel contract. Mode=all means no Direct identities,
 # no FakeIP journal, no domain rule file, and no TCP Defender grant.
 p029_v3=os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1"
 if p029_v3 and mode!="normal":
  raise RuntimeError("PLAN029 one real signed V3 probe must run Normal only")
 if p029_v3 and os.environ.get("GITHUB_ACTIONS")!="true":
  raise RuntimeError("PLAN029 native V3 smoke requires real source-locked CI")
 args=[str(cli),"--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443","--source-port","41031","--server-name","wbd-v4.example.test","--route-key-hex-file",str(route_local),"--tls-ca-pem",str(out/"cert.pem"),"--username",user,"--password",password,"--tunnel-id",tunnel,"--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDWLMAIN","--state-path",str(out/"owned-wal.json"),"--mtu",str(configured_mtu),"--lanes",str(lanes),"--fec-mode",("fixed" if fixed6 else "off"),
  "--fec-parity",("4" if fixed6 else "0"),"--fec.mode",client_fec,
  "--fec.profile",("maximum" if fixed6 or game_fixed else "strong"),"--route-mode",("bypass-lan-cn" if p029_direct else "all" if p029_v3 else "bypass-lan"),"--outer-repair",outer_repair]
 if p029_padding:
  # Same default Normal original Windows Wintun pipeline; no new test
  # sender or artificial packet shape. Only the selected mode changes.
  args.extend(["--startup-padding","flows"])
 if p029_direct:
  # The exact Linux guest is the ONLY direct resolver for this controlled
  # scene; it also hosts an independent real physical business UDP socket.
  args.extend(["--dns.direct",peer,"--dns.tunnel","1.1.1.1",
               "--china-ip-file",str(out/"plan029-h1775-cn-one32.txt")])
 if p029_product:
  # Same Next-Connect CLI fields a portable user enters in real WinForms,
  # not WBD_PLAN029_CN_RULES_FILE or any GITHUB_ACTIONS test switch.
  args.extend(["--split-enable","--cn-rules-file",str(rules)])
 if p029_pressure:
  args.extend(["--direct-flow-hard","8"])
 if native_outer=="default1460":
  # Prove both real defaults by OMITTING their explicit user MTU flags.
  index=args.index("--mtu");del args[index:index+2]
 log=(out/"client.log").open("w");logs.append(log)
 # Original signed Windows Go passes one cold diagnostic bit to Rust only
 # for this P2 scene; ordinary users never incur socket-byte telemetry.
 client_env=os.environ.copy()
 if p029_p2:client_env["WBD_PLAN029_P2_RELAY_DIAG"]="1"
 if p029_product:
  client_env["GITHUB_ACTIONS"]="false"
  client_env["WBD_PLAN029_NATIVE_V3_TRIAL"]="0"
  client_env.pop("WBD_PLAN029_CN_RULES_FILE",None)
 w=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,
                    text=True,env=client_env)
 game_cold_stage("COLD_CLIENT_SPAWNED")
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
 app.write_text(r"""import socket,sys,time,json,pathlib,os
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
deadline=start+max(65. if os.environ.get("WBD_PLAN028_WSL_OWNED_SWITCH")=="1" else 35.,hold+9.)
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
 linux_app4=p029_tunnel_alias if p029_direct else "10.66.0.1"
 la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),linux_app4,"10.66.0.2",unix(done)],stdout=llog,stderr=subprocess.STDOUT)
 wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2",linux_app4,str(done)],stdout=wlog,stderr=subprocess.STDOUT)
 # This READY remains owned exclusively by the unmodified real product.
 game_cold_stage("COLD_READY_WAIT")
 ready(out/"client.log","WBD_WINDOWS_CLIENT_READY",w,30)
 if p029_product:
  cold_log=(out/"client.log").read_text(errors="replace")
  if ("WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE" not in cold_log or
      "source=explicit_config readiness=AWAIT_REAL_OS_RUST_RECEIPT" not in cold_log or
      "source=source_locked_CI_trial" in cold_log):
   raise RuntimeError("H1840 REAL product split did not select explicit --split-enable")
  # READY must follow real signed Wintun native OS WAL, not a GUI mock.
  if "WBD_WINDOWS_OS_APPLIED" not in cold_log:
   raise RuntimeError("H1840 product selection was READY without actual owned OS Apply")
  report["plan029_real_product_normal_cn"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "selection":"EXPLICIT_GUI_EQUIVALENT_CLI_WITH_GITHUB_ACTIONS_FALSE",
    "private_trial":"OFF","domain_rules":"ONE_COLD_OWNED_SNAPSHOT",
    "signed_windows_wintun_os_applied":"PASS_OBSERVED",
    "direct_tunnel_business":"PENDING","owned_stop":"PENDING"}
  print("PLAN029_H1840_REAL_PRODUCT_NONCI_EXPLICIT_CN_SPLIT_OWNED_OS_APPLIED_PRE_BUSINESS",flush=True)
 ready(out/"server.log",("V4_ORIGINAL_GO_GAME_NATIVE_READY" if is_game else
   "V4_PUBLIC_MULTI_SESSION_READY role=server" if plan028_owned_switch and not is_game else
   "V4_ORIGINAL_GO_SERVER_NATIVE_READY"),s,8)
 if tls_wire:
  end_tls_capture()
  from m0_plan028_tls_wire_audit import audit as audit_original_tcp
  raw=(out/"tls-firstflight.pcap").read_bytes()
  shape=audit_original_tcp(raw,server_ip=peer)
  shape.update({"platform":"Windows_Npcap_original_Go_client_to_Linux_WSL2_server",
     "source_sha":os.environ["GITHUB_SHA"],
     "linux_binary_sha":os.environ["LINUX_BINARY_SRC"],
     "first_payload_proof":"real_reassembled_TCP_not_segment_count",
     "raw_pcap_retained":False,"route_key_exchange":"OFFLINE_ONLY_32B"})
  (out/"tls-firstflight-audit.json").write_text(json.dumps(shape,indent=2)+"\n")
  (out/"tls-firstflight.pcap").unlink()
  report["tls_wire_first_flight"]=shape
  print("M0_PLAN028_REAL_WINDOWS_NPCAP_TO_WSL2_FIRST_TLS_CLIENTHELLO_NO_PRELUDE_PASS"+
       " session_id_bytes="+str(shape["session_id_length"])+
       " client_tls_record_bytes="+str(shape["client_hello_record_bytes"])+
       " server_tls_record_bytes="+str(shape["server_hello_record_bytes"]),flush=True)
 if plan028_owned_switch:
  # Actual native Windows source/IP mutation on the WSL virtual NIC.
  # The old normal authenticated Rust/Wintun owner still owns live
  # application traffic; the one existing supervisor must Stop exactly,
  # reauthenticate a fresh original Go TLS generation and apply OS MTU.
  assert (out/"plan028-owned-alias.json").is_file()
  started=time.monotonic()
  action="ShrinkMTU" if plan028_owned_mtu_only else "Switch"
  run(["pwsh","-NoProfile","-File",str(root/"tools"/"m0-plan028-win-wsl-product-owned-alias.ps1"),
       "-Action",action,"-Receipt",str(out/"plan028-owned-alias.json")],timeout=60)
  alias=json.loads((out/"plan028-owned-alias.json").read_text())
  if plan028_owned_mtu_only:
   if (alias["stage"]!="MTU_SHRUNK" or alias["host_source_old"]!="198.19.254.1" or
       alias["mtu_only_source4_after"]!="198.19.254.1" or
       int(alias["physical_ipv4_mtu_original"])!=1500 or
       int(alias["physical_ipv4_mtu_after"])!=1280):
    raise RuntimeError("same Windows physical NIC/IP 1500->1280 OS readback not verified")
  elif alias["stage"]!="SWITCHED" or alias["native_source4_after"]!="198.19.254.9":
   raise RuntimeError("new source IPv4 from real Windows OS readback was not selected")
  for _ in range(360):
   win=(out/"client.log").read_text(errors="replace")
   if ("WBD_WINDOWS_NATIVE_PATH_REAUTHORIZE generation=2" in win and
       (("WBD_WINDOWS_NATIVE_PATH_EFFECTIVE_CHANGED" in win and
          "physical_mtu=1280" in win and
          "WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=2" in win) if plan028_owned_mtu_only else
        "WBD_PLAN028_WINDOWS_VERIFIED_NATIVE_SOURCE4_REBOUND generation=2" in win) and
       win.count("WBD_WINDOWS_CLIENT_READY")>=2 and
       win.count("WBD_WINDOWS_OS_APPLIED")>=2 and
       (out/"server.log").read_text(errors="replace").count(
        "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4" if is_game else
        "V4_PUBLIC_MULTI_SESSION_READY role=server")>=2 and
       (("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes=4 wal_restored=1 rust_stopped=1" if is_game else
         "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1") in win)):
    break
   if w.poll() is not None:
    raise RuntimeError("original Windows native reauth product exited after real source change: "+win[-1500:])
   time.sleep(.15)
  else:raise RuntimeError("new authentic Windows TLS/Rust Npcap generation and old Stop not observed: "+win[-1500:])
  # For Game4, original server deliberately retains A RX for the
  # authenticated grace after B's full protected M4 commit. Its exact Stop
  # is validated after B's first real app business (below), not immediately
  # at the B-READY timestamp. Never shorten the product's retirement grace.
  # The two ORIGINAL live kernel UDP applications continue rather than
  # registering a fake packet. Demand NEW receive counters after B READY.
  def last_udp_count(role):
   path=out/(role+"-app.log")
   seen=[]
   if path.exists():
    for text in path.read_text(errors="replace").splitlines():
     try:
      entry=json.loads(text)
      if entry.get("phase")=="udp_1hz":seen.append(int(entry["received"]))
     except (ValueError,KeyError,TypeError):pass
   return seen[-1] if seen else 0
  before={x:last_udp_count(x) for x in ("windows","linux")}
  for _ in range(100):
   after={x:last_udp_count(x) for x in before}
   if all(after[x]>before[x] for x in before):break
   if w.poll() is not None:raise RuntimeError("new Windows path died before authenticated fresh inner UDP")
   time.sleep(.1)
  else:raise RuntimeError("actual Windows/Linux inner UDP did not continue beyond new authenticated generation: "+repr((before,after)))
  if is_game:
   # Exact existing server implementation: schedule 10–20s AFTER genuine
   # new Game M4 group COMMIT. Old group stays RX-capable during that grace.
   # The previous test demanded a nonexistent '...new-generation' reason
   # instantly after READY, so it always killed the server DURING grace.
   native_server=(out/"server.log").read_text(errors="replace")
   schedules=re.findall(
    r"V4_PUBLIC_GAME_OLD_SERVER_RETIRE_SCHEDULED role=server lanes=4 grace_ms=(\d+) old_m4_rx_preserved=1",
    native_server)
   if len(schedules)!=1 or not 10000<=int(schedules[0])<=20000:
    raise RuntimeError("exact protected Game4 server old RX grace schedule missing/invalid: "+repr(schedules))
   grace_ms=int(schedules[0])
   marker="V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-grace-expired"
   # This is the EXISTING retirement grace plus bounded observation slack,
   # not a new handshake SLA and not permission to lose B application.
   timeout_s=min(25.,grace_ms/1000.+5.)
   deadline=time.monotonic()+timeout_s
   watched_start=time.monotonic()
   while time.monotonic()<deadline:
    log=(out/"server.log").read_text(errors="replace")
    count=log.count(marker)
    if count>1:
     raise RuntimeError("duplicate exact Game4 old server retirement")
    if count==1:break
    if s.poll() is not None or w.poll() is not None:
     raise RuntimeError("original server/Windows product exited before old authenticated Game4 grace retirement")
    time.sleep(.2)
   else:
    raise RuntimeError("original Game4 old server RX still not retired after actual bounded grace")
   later={x:last_udp_count(x) for x in before}
   if time.monotonic()-watched_start>=1. and not all(later[x]>after[x] for x in before):
    raise RuntimeError("new authenticated Game4 business stalled during old server grace: "+repr((after,later)))
   report["plan028_game4_server_generation_grace"]={
     "actual_server_grace_ms":grace_ms,
     "old_rx_preserved_until_due":True,
     "server_exact_old_retire_reason":"same-protected-cohort-grace-expired",
     "new_both_direction_app_udp_after_B_ready":{x:after[x]-before[x] for x in before},
     "new_both_direction_app_udp_during_grace_wait":{x:later[x]-after[x] for x in before},
     "exact_old_server_retirement_verified":True,
     "source":"original_protected_GO_TLS_server_Rust_M4_plus_actual_native_UDP"}
  new_generation={
   "old_generation_exact_wal_stop":True,
   "new_generation_tls_native_ready":True,
   "new_inner_udp_receive_increments":{x:after[x]-before[x] for x in before},
   "OS_mutation_to_new_ready_observed_ms":round((time.monotonic()-started)*1000,2),
   "notification_to_TLS_start_ms":"NOT_MEASURED",
   "TLS_auth_to_first_single_packet_ms":"NOT_MEASURED"}
  if plan028_owned_mtu_only:
   # Real OS-owned WSL vEthernet interface, unchanged source and ifindex.
   # No synthetic callback, no modification to runner management uplink.
   new_generation.update({
    "scope":"TRUE_WINDOWS_WSL2_OWNED_SAME_IFINDEX_SAME_IP_PHYSICAL_MTU_ONLY_1500_TO_1280_ORIGINAL_TLS_NPCAP_WINTUN_RUST",
    "source4_before":"198.19.254.1","source4_after":"198.19.254.1",
    "physical_mtu_before":int(alias["physical_ipv4_mtu_original"]),
    "physical_mtu_after":int(alias["physical_ipv4_mtu_after"]),
    "mutated_test_owned_underlay_only":True})
   report["plan028_original_native_mtu_only_reauth"]=new_generation
   print("M0_PLAN028_WINDOWS_REAL_OWNED_WSL2_SAME_SOURCE_MTU_ONLY_REAUTH_ORIGINAL_TLS_NPCAP_RUST_UDP_PASS",flush=True)
  else:
   new_generation.update({
    "scope":("TRUE_WINDOWS_WSL2_OWNED_EGRESS_IP4_GAME4FEC6_NEW_GO_TLS_NPCAP_WINTUN_RUST" if is_game else
             "TRUE_WINDOWS_WSL2_OWNED_EGRESS_IP4_NEW_GO_TLS_NPCAP_WINTUN_RUST"),
    "source4_before":"198.19.254.1","source4_after":"198.19.254.9"})
   report["plan028_original_native_source4_reauth"]=new_generation
   print("M0_PLAN028_WINDOWS_REAL_OWNED_WSL2_SOURCE4_REAUTH_ORIGINAL_TLS_NPCAP_RUST_AND_NEW_UDP_PASS",flush=True)
 game_cold_stage("COLD_READY_COMPLETE")
 report["linux_ready"]="PASS_REAL_AFTER_ORIGINAL_TLS"
 winlog=(out/"client.log").read_text(errors="replace")
 if "WBD_WINDOWS_OS_APPLIED" not in winlog:raise RuntimeError("Windows public READY lacks native OS Applied")
 report["windows_ready"]="PASS_TRUE_TLS_RUST_WINTUN_NPCAP_OS_WAL"
 if native_outer!="legacy1400":
  # Independently validate the numeric receipt emitted by the REAL
  # same-generation Windows N4 owner before READY; no hand-fed inner MTU.
  if plan028_owned_switch:
   # The previous single-generation receipt helper is intentionally strict.
   # This specific authentic .1→.9 path has exactly TWO real generations.
   # Validate BOTH separately, not a synthesized collapsed last value.
   os_rows=re.findall(
    r"^WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=\d+ applied=\d+ outer_config=\d+$",
    winlog,re.MULTILINE)
   if len(os_rows)!=2:
    raise RuntimeError("PLAN028 original Windows generations require exactly two genuine OS MTU receipts")
   per_gen_inner=[verified_native_windows_inner_mtu(row,configured_mtu) for row in os_rows]
   windows_inner=per_gen_inner[-1]
   report["plan028_actual_windows_two_generation_os_inner_mtu"]=per_gen_inner
  else:
   windows_inner=verified_native_windows_inner_mtu(winlog,configured_mtu)
  if mode=="normal":
   from m0_wl_public_mss_contract import verified_current_v4_mss,verified_plan028_shared_manual_two_generation_v4_mss
   linux_log=(out/"server.log").read_text(errors="replace")
   if plan028_owned_mtu_only:
    # The same authenticated Linux shared-server TUN stays unchanged.
    # The Windows client alone must narrow its true NEW TCP SYN budget;
    # Linux SYNACK may legitimately advertise its own larger 1460 path.
    # Reuse the already source-tested strict two-original-TLS MSS verifier.
    # The real FakeTCP client may retransmit generation1 SYN unchanged
    # before SYNACK (H1345 observed two identical gen1 SYNs, one gen2).
    # This helper admits <=8 same-generation byte-identical SYN attempts,
    # rejects conflicting options, and requires both real Linux SYNACKs,
    # authentic M4 server session slots 1/2, and decoded peer SYNACKs.
    proof=verified_plan028_shared_manual_two_generation_v4_mss(
     winlog,linux_log,configured_mtu)
    observed=[
     (x["generation"],x["windows_physical_ip_mtu"],
      x["windows_local_syn_mss"],x["windows_inner_planned"],
      x["windows_actual_syn_tcp_option_bytes"],
      x["windows_received_peer_synack_mss"],
      x["linux_local_synack_mss"])
     for x in proof]
    expected=[(1,1500,1420,1389,"0204058c",1420,1420),
              (2,1280,1240,1209,"020404d8",1420,1420)]
    if observed!=expected:
     raise RuntimeError(
      "Windows native genuine two-generation same-IP OS NlMtu/SYN/SYNACK mismatch: "
      +repr(observed))
    source_ports=re.findall(
     r"WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=(\d+) configured_port=(\d+) source_port=(\d+) original_peer_port=(\d+) same_ip_reauth_safe_tuple=(true|false)",
     winlog)
    expected_ports=[("1","41031","41031","443","false"),
                    ("2","41031","41032","443","true")]
    if source_ports!=expected_ports:
     raise RuntimeError("genuine source-locked distinct Windows cold TLS tuples missing: "+repr(source_ports))
    if per_gen_inner!=[1389,1209]:
     raise RuntimeError("Windows real Wintun OS inner MTU did not narrow BEFORE B published: "+repr(per_gen_inner))
    report["plan028_verified_original_same_source_two_TLS_syn_synack"]=proof
    budget_and_wire={
     "scope":"WINDOWS_REAL_ORIGINAL_CLIENT_SYN_TWO_PHYSICAL_MTU_BUDGETS_ONLY",
     "windows_physical":[1500,1280],
     "windows_effective_outer":[1460,1280],
     "windows_actual_SYN_MSS":[1420,1240],
     "windows_real_inner_Wintun_OS":[1389,1209],
     "server_SYNACK_MSS":"INDEPENDENT_LINUX_PHYSICAL_PATH_NOT_ASSUMED_MATCHED"}
    report["plan028_actual_two_generation_syn_synack_mss"]=budget_and_wire
    print("M0_PLAN028_WINDOWS_REAL_SAME_IP_PHYSICAL_MTU_SHRUNK_ORIGINAL_SYN_AND_WINTUN_OS_PASS",flush=True)
   elif plan028_owned_switch:
    per_gen_wire=verified_plan028_shared_manual_two_generation_v4_mss(winlog,linux_log,configured_mtu)
    report["plan028_actual_two_generation_syn_synack_mss"]=per_gen_wire
    budget_and_wire=per_gen_wire[-1]
   else:
    budget_and_wire=verified_current_v4_mss(winlog,linux_log,configured_mtu)
   report["plan027a_real_syn_synack_mss"]=budget_and_wire
   if not plan028_owned_mtu_only:
    print("PLAN027A_BOTH_REAL_SYN_SYNACK_MSS_VERIFIED "+json.dumps(budget_and_wire,sort_keys=True),flush=True)

  if p029_outer1460:
   if configured_mtu!=1460 or native_outer!="default1460" or windows_inner!=1389:
    raise RuntimeError("H1791 original Windows real default1460 automatic inner mismatch")
   report["plan029_d5_real_default_outer1460"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "outer_arg_present":False,"outer_selector":"default1460",
    "configured_default_outer":configured_mtu,
    "real_windows_auto_inner":windows_inner,
    "real_linux_auto_inner":"NOT_RUN_UNTIL_TUN_READBACK",
    "stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
  report["plan027a_windows_os_inner_mtu_verified"]=windows_inner
  print("PLAN027A_WINDOWS_INNER_OS_READBACK",windows_inner,"outer",
        configured_mtu,"selector",native_outer,flush=True)
  # Real OS TUN readback AFTER authenticated TLS and original owner Apply.
  kernel=json.loads(wsl("ip","-j","link","show","dev","wbdwl4",timeout=12))
  if len(kernel)!=1 or type(kernel[0].get("mtu")) is not int:
   raise RuntimeError("PLAN027A Linux actual inner OS MTU readback missing")
  inner=kernel[0]["mtu"]
  if p029_outer1460:
   if inner!=1389:
    raise RuntimeError("H1791 original Linux actual TUN automatic inner not 1389")
   report["plan029_d5_real_default_outer1460"]["real_linux_auto_inner"]=inner
   print("PLAN029_H1791_REAL_DEFAULT_OUTER1460_TWO_OS_AUTO_INNER1389_PASS_PRE_STOP",flush=True)
  report["plan027a_linux_actual_inner_os_mtu"]=inner
  if not 576<=inner<=configured_mtu:
   raise RuntimeError("PLAN027A Linux OS inner MTU exceeds outer IP cap")
  print("PLAN027A_LINUX_INNER_OS_READBACK",inner,"outer",configured_mtu,"selector",native_outer,flush=True)
  # H981: green alone does not qualify Fixed: old H978 1333/1333 was
  # FEC1's 56B reserve, not V4 FEC2's 14B. Check wire, peer, record,
  # both live OS TUNs and authentic physical source before acceptance.
  if mode=="fixed" and plan028_owned_switch and native_outer=="default1460":
   # Exact two authenticated original Go TLS/FEC6 generations share ONE
   # server TUN. The retired singleton H981 MTU and peer-MSS log names
   # are not emitted by shared-multi; require genuine TWO-generation
   # client actual TCP SYN/peer SYNACK and server real SYNACK instead.
   linuxlog=(out/"server.log").read_text(errors="replace")
   # FEC2 installation is async after READY; require BOTH real Rust receipts.
   for _ in range(80):
    winlog=(out/"client.log").read_text(errors="replace")
    if winlog.count("WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=6 revision=1 applied=1")>=2:break
    if w.poll() is not None:break
    time.sleep(.1)
   expected=configured_mtu-40
   option="0204"+format(expected,"04x")
   clients=re.findall(r"WBD_WINDOWS_ACTUAL_SYN_MSS_V1[^\n]*generation=(\d+)[^\n]*local_advertised_mss=(\d+)[^\n]*tcp_option_bytes=([0-9a-fA-F]+)",winlog)
   servers=re.findall(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1[^\n]*side=server[^\n]*local_advertised_mss=(\d+)[^\n]*tcp_option_bytes=([0-9a-fA-F]+)",linuxlog)
   peer=re.findall(r"WBD_WINDOWS_PEER_SYNACK_MSS_V1[^\n]*peer_advertised_mss=(\d+)",winlog)
   records=re.findall(r"WBD_WINDOWS_ORIGINAL_GO_TLS_RECORD_CAP_AUTHENTICATED[^\n]*client_record_offer=(\d+)",winlog)
   cold=re.findall(r"WBD_WINDOWS_COLD_MSS_BUDGET_V1[^\n]*physical_outer_mtu=(\d+)[^\n]*effective_outer_mtu=(\d+)[^\n]*local_advertised_mss=(\d+)",winlog)
   server_preflight=re.findall(r"V4_PUBLIC_MTU_PREPARE[^\n]*role=server[^\n]*interface=(\d+)[^\n]*advertised_mss=(\d+)[^\n]*record_offer=(\d+)",linuxlog)
   source_profiles=linuxlog.count("V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=fixed profile=6")
   win_profiles=winlog.count("WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=6 revision=1 applied=1")
   valid=(len(clients)>=2 and set(x[0] for x in clients)=={"1","2"} and
          all(int(v)==expected and o.lower()==option for _,v,o in clients) and
          len(servers)==2 and all(int(v)==expected and o.lower()==option for v,o in servers) and
          len(peer)>=2 and all(int(v)==expected for v in peer) and
          len(records)==2 and all(int(v)==expected for v in records) and
          len(cold)==2 and all(int(p)>=configured_mtu and int(e)==configured_mtu and int(m)==expected for p,e,m in cold) and
          len(server_preflight)==1 and all(int(v)==expected for v in server_preflight[0][1:]) and
          source_profiles==2 and win_profiles==2 and
          windows_inner==configured_mtu-85 and inner==configured_mtu-85)
   report["plan028_fixed_shared_two_generation_authentic_mss"]={
      "verified":valid,"windows_actual_syn_generations":sorted(set(g for g,_,_ in clients)),
      "windows_actual_syn_count":len(clients),"linux_actual_synack_count":len(servers),
      "windows_peer_synack_count":len(peer),"windows_tls_record_offers":len(records),
      "original_linux_server_mtu_preflight_count":len(server_preflight),
      "protected_server_M4_FEC6":source_profiles,"original_windows_rust_FEC6_applied":win_profiles,
      "expected_mss":expected,"actual_windows_os_inner":windows_inner,"actual_linux_os_inner":inner}
   if not valid:raise RuntimeError("PLAN028_SHARED_FIXED6_AUTHENTIC_TWO_GENERATION_MSS_RECORD_M4_OS_MISSING")
   print("M0_PLAN028_SHARED_WINDOWS_FIXED6_TWO_REAL_TLS_SYN_SYNACK_MSS_RECORD_AND_M4_OS_PASS",flush=True)
  if mode=="fixed" and not plan028_owned_switch and native_outer in ("default1460","1500"):
   linuxlog=(out/"server.log").read_text(errors="replace")
   winlimit=re.findall(r"WBD_WINDOWS_COLD_MSS_BUDGET_V1[^\n]*physical_outer_mtu=(\d+)[^\n]*effective_outer_mtu=(\d+)",winlog)
   linlimit=re.findall(r"V4_PUBLIC_MTU_PREPARE[^\n]*role=server[^\n]*interface=(\d+)[^\n]*advertised_mss=(\d+)",linuxlog)
   winmss=re.findall(r"WBD_WINDOWS_ACTUAL_SYN_MSS_V1[^\n]*local_advertised_mss=(\d+)[^\n]*tcp_option_bytes=([0-9a-fA-F]+)",winlog)
   linmss=re.findall(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1[^\n]*side=server[^\n]*local_advertised_mss=(\d+)[^\n]*tcp_option_bytes=([0-9a-fA-F]+)",linuxlog)
   winpeer=re.findall(r"WBD_WINDOWS_PEER_SYNACK_MSS_V1[^\n]*peer_advertised_mss=(\d+)",winlog)
   linpeer=re.findall(r"V4_PUBLIC_ACTUAL_PEER_SYN_MSS_V1[^\n]*peer_advertised_mss=(\d+)",linuxlog)
   winoffer=re.findall(r"WBD_WINDOWS_ORIGINAL_GO_TLS_RECORD_CAP_AUTHENTICATED[^\n]*client_record_offer=(\d+)",winlog)
   linrecord=re.findall(r"V4_PUBLIC_MTU role=server[^\n]*record_wire=(\d+)[^\n]*tun_mtu=(\d+)",linuxlog)
   if not all((winlimit,linlimit,winmss,linmss,winpeer,linpeer,winoffer,linrecord)):
    raise RuntimeError("H981_FIXED_AUTHENTIC_MSS_RECORD_PHYSICAL_OS_RECEIPT_MISSING")
   wp,wo=map(int,winlimit[-1])
   lp,lm=map(int,linlimit[-1])
   syns=(int(winmss[-1][0]),int(linmss[-1][0]),int(winpeer[-1]),int(linpeer[-1]))
   options=(winmss[-1][1].lower(),linmss[-1][1].lower())
   expected=configured_mtu-40
   proof={"windows_physical":wp,"linux_physical":lp,
      "windows_inner_os":windows_inner,"linux_inner_os":inner,
      "local_and_peer_syn_mss":syns,"option_bytes":options,
      "windows_record_offer":int(winoffer[-1]),"linux_record_wire":int(linrecord[-1][0])}
   report["plan027a_fixed_true_wire_and_os_proof"]=proof
   if wp>=configured_mtu and lp>=configured_mtu:
    if (wo!=configured_mtu or lm!=expected or syns!=(expected,)*4 or
        options!=("0204"+format(expected,"04x"),)*2 or
        int(winoffer[-1])!=expected or
        int(linrecord[-1][0])!=expected or int(linrecord[-1][1])!=inner or
        windows_inner!=configured_mtu-85 or inner!=configured_mtu-85):
     raise RuntimeError("H981_FIXED_FEC1_56B_OR_MSS_RECORD_OS_REGRESSION "+repr(proof))
    print("H981_REAL_FIXED_BOTH_OS_V4_FEC2_14B_MSS_RECORD_PASS",configured_mtu,
          windows_inner,inner,flush=True)
   else:
    print("H981_REAL_FIXED_AUTHENTIC_PHYSICAL_NARROWING",proof,flush=True)

 if os.environ.get("WBD_WL_V2_SCENARIO"):
  from m0_wl_perf_v2_config import read_scenario
  scene_mtu=read_scenario(root/os.environ["WBD_WL_V2_SCENARIO"])["tun_mtu"]
  if configured_mtu!=scene_mtu:
   raise RuntimeError("original Windows native requested MTU does not match immutable scenario")
  if configured_mtu==1280:
   # Read the original Linux TUN AFTER protected TLS admission, not a
   # requested value in a JSON file. Both TUN owners must obey one budget.
   kernel=json.loads(wsl("ip","-j","link","show","dev","wbdwl4",timeout=12))
   if len(kernel)!=1 or type(kernel[0].get("mtu")) is not int:
    raise RuntimeError("Linux original TUN 1280 MTU real OS readback missing")
   linux_actual=kernel[0]["mtu"]
   report["original_native_mtu1280_kernel_readback"]={
    "requested_windows":configured_mtu,"linux_actual":linux_actual,
    "source":"REAL_LINUX_TUN_AFTER_AUTHENTICATED_ORIGINAL_GO_TLS"}
   if not 576<=linux_actual<=1280:
    raise RuntimeError("Linux original TUN negotiated larger than Windows 1280 budget "+str(linux_actual))
   print("H668_NATIVE_ORIGINAL_MTU1280_WINTUN_REQUEST_AND_REAL_LINUX_TUN_MAX_PASS linux_mtu="+str(linux_actual),flush=True)
 done.write_text("observed authentic client and Linux server READY\n")
 # The actual UDP app has a 30s real OS bind bound plus 35s payload
 # deadline. 18s parent wait previously killed it before it could report
 # which true kernel side was missing. Observe only liveness at low cost.
 until=time.monotonic()+70
 while wa.poll() is None or la.poll() is None:
  game_due_first_fault()
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

 if p029_direct:
  # D1/D2 real physical Direct first, once the SAME signed Windows
  # Wintun and two-OS Tunnel UDP are proved. The historical inbound
  # TCP comparator is still mandatory but must not mask CN failures.
  # The original Windows app and two independent guest kernel sockets
  # share the *same running* signed one-Wintun/one-Rust V3 generation.
  # No packet injection/second-ring/probe-only helper ABI. The CN hostname
  # is intentionally CNAME'd to a shared real public-IP peer so its
  # selective FakeIP must not expose that CDN IP on any underlay wire.
  if p029_alias_proc.wait(timeout=4)!=0 or not (out/"plan029-h1745-owned-tun-alias.txt").exists():
   raise RuntimeError("test-owned Linux TUN public alias not OS confirmed")
  guest_log=(out/"plan029-h1745-guest-physical.log").open("w");logs.append(guest_log)
  host_source=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host_source:raise RuntimeError("original Windows physical source readback absent")
  p029_guest_proc=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1745_guest_dns_direct.py"),
      peer,host_source,"2" if p029_multia else "1" if p029_cache else "0"],stdout=guest_log,stderr=subprocess.STDOUT)
  for tick in range(100):
   guest_log.flush()
   raw=(out/"plan029-h1745-guest-physical.log").read_text(errors="replace")
   if "PLAN029_H1745_LINUX_REAL_DNS53_AND_UDP46111_READY" in raw:break
   if p029_guest_proc.poll() is not None:
    raise RuntimeError("real Linux physical DNS53 business socket failed: "+raw[-600:])
   time.sleep(.1)
  else:raise RuntimeError("real Linux physical DNS53 not ready")
  cn_log=(out/"plan029-h1745-windows-fake-cn-direct.log").open("w");logs.append(cn_log)
  p029_client_proc=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1745_win_client_dns_direct.py"),
      "10.66.0.2",peer],stdout=cn_log,stderr=subprocess.STDOUT)
  try:cn_exit=p029_client_proc.wait(timeout=49)
  except subprocess.TimeoutExpired:
   raise RuntimeError("real Windows CN DNS/FakeIP direct UDP deadline")
  if cn_exit!=0:
   raise RuntimeError("original Windows CN FakeIP Direct app failed: "+
      (out/"plan029-h1745-windows-fake-cn-direct.log").read_text(errors="replace")[-900:])
  if p029_guest_proc.wait(timeout=4)!=0:
   raise RuntimeError("independent Linux DNS/UDP physical recipient failed: "+
      (out/"plan029-h1745-guest-physical.log").read_text(errors="replace")[-600:])
  win_lines=(out/"plan029-h1745-windows-fake-cn-direct.log").read_text().splitlines()
  guest_lines=(out/"plan029-h1745-guest-physical.log").read_text().splitlines()
  wproof=[x.split(" ",1)[1] for x in win_lines if
          x.startswith("PLAN029_H1745_REAL_WINDOWS_CN_DNS_FAKE_DIRECT_UDP ")]
  gproof=[x.split(" ",1)[1] for x in guest_lines if
          x.startswith("PLAN029_H1745_REAL_LINUX_GUEST_DIRECT ")]
  if len(wproof)!=1 or len(gproof)!=1:raise RuntimeError("missing real two-OS Direct evidence")
  wdata,gdata=json.loads(wproof[0]),json.loads(gproof[0])
  if not(gdata["dns"] and gdata["direct_business"] and
         gdata["dns_client_physical"]==host_source and
         gdata["business_client_physical"]==host_source and
         wdata["direct_resolver"]==peer):
   raise RuntimeError("real Direct DNS/UDP guest physical proof mismatch")
  if p029_multia:
   fakes=wdata.get("multi_a_fake_addresses",[])
   if (wdata.get("multi_a_mode") is not True or len(fakes)!=2 or
       fakes[0]!=wdata["fake4"] or len(set(fakes))!=2 or
       any(not ip.startswith("198.18.") for ip in fakes) or
       gdata.get("multi_a_mode") is not True or
       gdata.get("multi_a_answers")!=1 or gdata.get("target_dns_count")!=1):
    raise RuntimeError("H1807 signed CN CNAME two A/durable distinct FakeIP receipts absent")
   report["plan029_d3_multia_real"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "scope":"SIGNED_NORMAL_CN_CNAME_TWO_REAL_A_TO_TWO_DISTINCT_FAKEIP_PLUS_DIRECT_UDP",
    "windows":wdata,"linux":gdata,
    "hard_quota_overflow":"NOT_RUN_SEPARATE_PURE_TEST",
    "stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
   print("PLAN029_H1807_SIGNED_CN_CNAME_TWO_A_DISTINCT_FAKEIP_DIRECT_UDP_PRE_STOP",flush=True)
  if p029_cache:
   if not (wdata["cache_second_reply"] is True and
           wdata["cache_second_source_distinct"] is True and
           gdata["target_dns_count"]==1 and gdata["cache_mode"] is True):
    raise RuntimeError("H1783 two Windows DNS app sources did not share one physical DNS")
   report["plan029_d3_cn_native_dns_cache"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "scope":"REAL_TWO_WINDOWS_DNS_TICKETS_ONE_PHYSICAL_CN_DNS_FAKEIP",
    "windows":wdata,"linux":gdata,
    "stop":"NOT_RUN_UNTIL_REAL_OWNED_STOP",
    "full_DNS_pressure":"NOT_RUN"}
   print("PLAN029_H1783_REAL_CN_DNS_CACHE_TWO_APP_CLIENTS_ONE_UPSTREAM_PASS_PRE_STOP",flush=True)
  report["plan029_private_v3_cn_direct_udp"]={
   "scope":"SIGNED_ONE_WINTUN_RUST_V3_CN_DNS_JOURNALED_FAKE_AND_PHYSICAL_DIRECT_UDP",
   "source_sha":os.environ["GITHUB_SHA"],
   "windows_app":wdata,"linux_physical":gdata,
   "tunnel_udp":report["app_duplex"],"tunnel_tcp":"NOT_RUN_PRE_TCP_COMPARATOR",
   "stop":"NOT_RUN_UNTIL_OWNED_STOP","direct_tcp":"NOT_RUN",
   "tunnel_dns":"NOT_RUN","D1_D5_P1_P2":"NOT_FULLY_RUN"}
  print("PLAN029_H1749_SIGNED_CN_DNS_FAKE_DIRECT_UDP_STAGE_PASS_PRE_TCP_AND_STOP",flush=True)
  # H1760 actual Windows FakeIP TCP -> same owned Rust kernel listener ->
  # physical Windows TCP socket -> independent Linux physical listener.
  gname="plan029-h1760-guest-physical-tcp.log"
  wname="plan029-h1760-windows-fakeip-tcp.log"
  gfile=(out/gname).open("w");logs.append(gfile)
  tcp_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",
      unix(root/"tools"/"m0_plan029_h1760_guest_physical_direct_tcp.py"),
      peer,host_source],stdout=gfile,stderr=subprocess.STDOUT)
  try:
   for _ in range(75):
    gfile.flush()
    raw=(out/gname).read_text(errors="replace")
    if "PLAN029_H1760_PHYSICAL_KERNEL_TCP46112_READY" in raw:break
    if tcp_guest.poll() is not None:raise RuntimeError("Linux TCP bind failed: "+raw[-700:])
    time.sleep(.1)
   else:raise RuntimeError("Linux physical TCP ready deadline")
   wfile=(out/wname).open("w");logs.append(wfile)
   tcp_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1760_windows_fakeip_direct_tcp.py"),
      "10.66.0.2",wdata["fake4"]],stdout=wfile,stderr=subprocess.STDOUT)
   try:
    rc=tcp_win.wait(timeout=24)
   except subprocess.TimeoutExpired:
    raise RuntimeError("Windows genuine kernel TCP two-leg 24s deadline")
   finally:
    if tcp_win.poll() is None:
     tcp_win.terminate()
     try:tcp_win.wait(timeout=3)
     except subprocess.TimeoutExpired:tcp_win.kill()
   if rc:raise RuntimeError("Windows FakeIP Direct TCP failed: "+(out/wname).read_text(errors="replace")[-900:])
   if tcp_guest.wait(timeout=6):raise RuntimeError("Linux physical kernel TCP echo failed: "+(out/gname).read_text(errors="replace")[-900:])
  finally:
   if tcp_guest.poll() is None:
    tcp_guest.terminate()
    try:tcp_guest.wait(timeout=3)
    except subprocess.TimeoutExpired:tcp_guest.kill()
  a=[x.split(" ",1)[1] for x in (out/wname).read_text().splitlines()
    if x.startswith("PLAN029_H1760_WINDOWS_FAKEIP_DIRECT_TCP_ECHO ")]
  b=[x.split(" ",1)[1] for x in (out/gname).read_text().splitlines()
    if x.startswith("PLAN029_H1760_LINUX_PHYSICAL_TCP_ECHO ")]
  if len(a)!=1 or len(b)!=1:raise RuntimeError("unique real two-leg TCP app receipts missing")
  tcp_windows_receipt,li=json.loads(a[0]),json.loads(b[0])
  if not(tcp_windows_receipt.get("tcp_two_leg_echo") and tcp_windows_receipt.get("tcp_half_close") and
     tcp_windows_receipt.get("app_bytes_sent")==32768 and tcp_windows_receipt.get("app_bytes_echoed")==32768 and
     tcp_windows_receipt.get("presented_peer")==wdata["fake4"] and
     li.get("source_physical")==host_source and li.get("real_socket")==peer and
     li.get("received_bytes")==32768):
   raise RuntimeError("real Windows-to-Linux Direct kernel TCP socket receipts mismatch")
  report["plan029_private_v3_cn_direct_tcp"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "scope":"ONE_SIGNED_WINTUN_TWO_REAL_KERNEL_TCP_SOCKETS_CN_FAKEIP_PHYSICAL_32K_HALF_CLOSE",
    "windows":tcp_windows_receipt,"linux":li,"tunnel_tcp":"NOT_RUN_UNTIL_COMPARATOR","stop":"NOT_RUN"}
  report["plan029_private_v3_cn_direct_udp"]["direct_tcp"]="PASS_REAL_KERNEL_TWO_LEG_TCP_32K"
  print("PLAN029_H1760_SIGNED_CN_DIRECT_TCP_32K_TWO_LEG_HALF_CLOSE_PASS_PRE_TUNNEL_AND_STOP",flush=True)
  if p029_p2:
   from m0_plan029_h1815_p2_real_mixed import run_p2
   report["plan029_p2_mixed_real"]=run_p2(root,out,peer,host_source,linux_app4,
                                          wdata["fake4"],unix,ready)
   print("PLAN029_H1815_P2_PHYSICAL1M_DIRECT1M_AND_CONCURRENT_TUNNEL_SMALL_UDP_PRE_STOP",flush=True)
 # Functional-only *real TCP* over the same original authenticated public
 # Wintun/TUN: each OS binds one TCP listener and dials the other. Two
 # independently established IPv4 streams must echo exact application bytes.
 # This is NOT a throughput/RTT/packet-loss measurement or fake carrier ACK.
 if p029_direct:
  # This 029 business direction is actual Windows-app -> Linux TUN TCP.
  # PLAN028's previously failing Linux->Windows inbound comparator remains
  # untouched below in else, and is NOT promoted or relabeled as passed.
  app=root/"tools"/"m0_plan029_h1762_oneway_tunnel_tcp.py"
  ltlog=(out/"linux-tcp-app.log").open("w");logs.append(ltlog)
  wtlog=(out/"windows-tcp-app.log").open("w");logs.append(wtlog)
  lt=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(app),"server",linux_app4,"10.66.0.2"],
      stdout=ltlog,stderr=subprocess.STDOUT)
  ready(out/"linux-tcp-app.log","PLAN029_H1762_REAL_LINUX_TUN_TCP_READY",lt,20)
  wt=subprocess.Popen([sys.executable,str(app),"client","10.66.0.2",linux_app4],
      stdout=wtlog,stderr=subprocess.STDOUT)
  try:
   if wt.wait(timeout=36)!=0 or lt.wait(timeout=7)!=0:
    raise RuntimeError("real Windows->Linux nonCN Tunnel TCP failed win="+
     (out/"windows-tcp-app.log").read_text(errors="replace")[-550:]+
     " linux="+(out/"linux-tcp-app.log").read_text(errors="replace")[-550:])
  finally:
   for child in (wt,lt):
    if child.poll() is None:
     child.terminate()
     try:child.wait(timeout=3)
     except subprocess.TimeoutExpired:child.kill()
  tcp={}
  for role in ("windows","linux"):
   lines=(out/(role+"-tcp-app.log")).read_text().splitlines()
   observed=[x.split(" ",1)[1] for x in lines if x.startswith("PLAN029_H1762_ONEWAY_TUN_TCP ")]
   if len(observed)!=1:raise RuntimeError("unique real Tunnel TCP "+role+" receipt absent")
   tcp[role]=json.loads(observed[0])
  if not (tcp["windows"]["client_echo"] and
          tcp["windows"]["local"]=="10.66.0.2" and
          tcp["windows"]["remote"]==linux_app4 and
          tcp["linux"]["received_bytes"]>0 and
          tcp["linux"]["client_ip"]=="10.66.0.2"):
   raise RuntimeError("real Windows app Tunnel TCP guest receipt mismatched")
  report["actual_kernel_tcp"]=tcp
  report["tcp_duplex"]="PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP"
 else:
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
  # The test-owned Linux TUN secondary /32 is NOT automatically chosen
  # by socket.create_connection. Source-bind each CLIENT dial exactly to
  # the same address as its independently owned listening socket.
  # Otherwise Linux silently uses 10.66.0.1 while Windows Defender only
  # allows the exact 203.0.113.77 alias, causing a false native TCP fail.
  with socket.create_connection((remote,port),timeout=1.5,source_address=(local,0)) as conn:
   result["dial_source"]=conn.getsockname()[0]
   if result["dial_source"]!=local:raise RuntimeError("TCP kernel dial source differed from owned lease/alias")
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
  lt=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(tcpapp),linux_app4,"10.66.0.2"],
      stdout=ltlog,stderr=subprocess.STDOUT)
  wt=subprocess.Popen([sys.executable,str(tcpapp),"10.66.0.2",linux_app4],
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
 if p029_direct:
  proof=report.get("plan029_private_v3_cn_direct_udp")
  if not proof or proof.get("source_sha")!=os.environ["GITHUB_SHA"]:
   raise RuntimeError("PLAN029 signed CN Direct source/physical evidence missing")
  proof["tunnel_tcp"]=report["tcp_duplex"]
  proof["historical_028_linux_to_windows_tcp"]="NOT_RUN_028_SCOPED"
  print("PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP",flush=True)
  print("PLAN029_H1762_SIGNED_DIRECT_TCP_UDP_ONEWAY_TUN_TCP_UDP_PASS_PRE_STOP",flush=True)
  # Scoped D1 non-CN QNAME real UDP53. A TUN-only owned Linux /32 is
  # the unique dns.tunnel endpoint (not the physical CN Direct resolver).
  # Write INTENT before OS mutation so partial Apply is recoverable.
  dns_alias="1.1.1.1/32"
  dns_intent=out/"plan029-h1765-owned-tunnel-dns-alias.txt"
  dns_intent.unlink(missing_ok=True)
  if dns_alias in wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8):
   raise RuntimeError("foreign Linux TUN 1.1.1.1/32 DNS alias")
  dns_intent.write_text("INTENT "+dns_alias+" "+os.environ["GITHUB_SHA"]+"\n")
  wsl("ip","-4","addr","add",dns_alias,"dev","wbdwl4",timeout=8)
  if dns_alias not in wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8):
   raise RuntimeError("Linux Tunnel DNS owned /32 was not applied")
  dns_intent.write_text("OWNED "+dns_alias+" "+os.environ["GITHUB_SHA"]+"\n")
  dns_guest_log=(out/"plan029-h1765-linux-tun-dns.log").open("w");logs.append(dns_guest_log)
  p029_tun_dns_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1765_linux_tun_dns.py"),
      "1.1.1.1","10.66.0.2",linux_app4],
      stdout=dns_guest_log,stderr=subprocess.STDOUT)
  ready(out/"plan029-h1765-linux-tun-dns.log","PLAN029_H1765_LINUX_TUN_DNS53_READY",
      p029_tun_dns_guest,12)
  dns_win_log=(out/"plan029-h1765-windows-tun-dns.log").open("w");logs.append(dns_win_log)
  p029_tun_dns_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1765_windows_tunnel_dns.py"),
      "10.66.0.2","8.8.8.8",linux_app4],
      stdout=dns_win_log,stderr=subprocess.STDOUT)
  if p029_tun_dns_win.wait(timeout=24)!=0 or p029_tun_dns_guest.wait(timeout=8)!=0:
   raise RuntimeError("real nonCN Tunnel DNS endpoint failed windows="+
      (out/"plan029-h1765-windows-tun-dns.log").read_text(errors="replace")[-550:]+
      " linux="+(out/"plan029-h1765-linux-tun-dns.log").read_text(errors="replace")[-550:])
  dns_proofs={}
  for who,filename,marker in (
   ("windows","plan029-h1765-windows-tun-dns.log","PLAN029_H1765_REAL_WINDOWS_TUN_DNS "),
   ("linux","plan029-h1765-linux-tun-dns.log","PLAN029_H1765_REAL_LINUX_TUN_DNS ")):
   lines=[line.split(" ",1)[1] for line in (out/filename).read_text().splitlines()
          if line.startswith(marker)]
   if len(lines)!=1:raise RuntimeError("unique nonCN Tunnel DNS "+who+" receipt missing")
   dns_proofs[who]=json.loads(lines[0])
  if not (dns_proofs["linux"]["upstream_ip"]=="1.1.1.1" and
          dns_proofs["linux"]["client_ip"]=="10.66.0.2" and
          dns_proofs["windows"]["reply_source"]=="8.8.8.8" and
          dns_proofs["windows"]["real_answer"]==linux_app4 and
          dns_proofs["windows"]["fakeip"] is False):
   raise RuntimeError("real nonCN Tunnel DNS selected endpoint or original app answer differs")
  report["plan029_d1_noncn_udp_dns_real"]={
    "scope":"SIGNED_NONCN_QNAME_TUNNEL_UDP53_EXACT_ONE_UPSTREAM_AND_ORIGINAL_DNS_SOURCE",
    "source_sha":os.environ["GITHUB_SHA"],"windows":dns_proofs["windows"],
    "linux":dns_proofs["linux"],"app_tcp53":"NOT_RUN",
    "blackhole_no_fallback":"NOT_RUN"}
  print("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED",flush=True)
  # D2 scoped real counterexample: the nonCN DNS A was just read by the
  # original Windows app via its ONE authenticated Tunnel resolver; the
  # actual returned IP must be used by a NEW Windows kernel UDP business
  # socket and received by the original Linux TUN, never a FakeIP/Direct
  # resolution shortcut. This independently proves that DNS direction is
  # not silently re-used as a business flow routing classifier.
  d2_real=dns_proofs["windows"]["real_answer"]
  if d2_real!=linux_app4 or d2_real!=dns_proofs["linux"]["reply_a"]:
   raise RuntimeError("D2 real nonCN DNS A not bound to exact Linux TUN alias")
  d2_guest_log=(out/"plan029-h1770-linux-noncn-a-business.log").open("w");logs.append(d2_guest_log)
  p029_d2_tun_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",
      unix(root/"tools"/"m0_plan029_h1770_linux_resolved_noncn_tunnel_udp.py"),
      d2_real,"10.66.0.2"],stdout=d2_guest_log,stderr=subprocess.STDOUT)
  ready(out/"plan029-h1770-linux-noncn-a-business.log",
      "PLAN029_H1770_LINUX_ORIGINAL_TUN_A_BUSINESS_READY",p029_d2_tun_guest,12)
  d2_win_log=(out/"plan029-h1770-windows-noncn-a-business.log").open("w");logs.append(d2_win_log)
  p029_d2_tun_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1770_windows_resolved_noncn_tunnel_udp.py"),
      "10.66.0.2",d2_real],stdout=d2_win_log,stderr=subprocess.STDOUT)
  if p029_d2_tun_win.wait(timeout=17)!=0 or p029_d2_tun_guest.wait(timeout=6)!=0:
   raise RuntimeError("real nonCN DNS A Tunnel business failed win="+
      (out/"plan029-h1770-windows-noncn-a-business.log").read_text(errors="replace")[-500:]+
      " linux="+(out/"plan029-h1770-linux-noncn-a-business.log").read_text(errors="replace")[-500:])
  d2_receipts={}
  for who,filename,marker in (
   ("windows","plan029-h1770-windows-noncn-a-business.log","PLAN029_H1770_REAL_WINDOWS_NONCN_A_TUNNEL_BUSINESS "),
   ("linux","plan029-h1770-linux-noncn-a-business.log","PLAN029_H1770_REAL_LINUX_TUN_A_BUSINESS ")):
   rows=[line.split(" ",1)[1] for line in (out/filename).read_text().splitlines()
        if line.startswith(marker)]
   if len(rows)!=1:raise RuntimeError("D2 real nonCN DNS A business receipt missing "+who)
   d2_receipts[who]=json.loads(rows[0])
  if not (d2_receipts["windows"]["dns_real_a"]==d2_real and
          d2_receipts["windows"]["fakeip"] is False and
          d2_receipts["windows"]["reply_ip"]==d2_real and
          d2_receipts["linux"]["destination"]==d2_real and
          d2_receipts["linux"]["source_lease"]=="10.66.0.2" and
          d2_receipts["windows"]["received_bytes"]==
           d2_receipts["linux"]["echo_bytes"]):
   raise RuntimeError("D2 real nonCN resolved business did not follow Tunnel exact source")
  report["plan029_d2_noncn_resolved_a_tunnel_business"]={
       "source_sha":os.environ["GITHUB_SHA"],
       "scope":"SIGNED_NONCN_DNS_REAL_A_THEN_ORIGINAL_WINTUN_TO_LINUX_TUN_UDP",
       "windows":d2_receipts["windows"],"linux":d2_receipts["linux"],
       "cn_ip_a_converse":"NOT_RUN","overseas_cdn_reverse":"NOT_FULLY_RUN"}
  print("PLAN029_H1770_SIGNED_NONCN_DNS_REAL_A_FOLLOWED_BY_TRUE_TUNNEL_UDP_PASS_SCOPED",flush=True)
  # D2 nonCN DNS→CN IP converse. One explicit Wintun-bound socket is
  # used because the fixture's test-only physical route is more specific
  # than Wintun capture; never claim global on-link interception.
  h1775_owned_apply(host_source,peer)
  try:
   gn="plan029-h1775-linux-cn-converse.log"
   wn="plan029-h1775-windows-cn-converse.log"
   gf=(out/gn).open("w");logs.append(gf)
   p029_d2_cn_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
       "python3","-u",unix(root/"tools"/"m0_plan029_h1775_guest_cn_converse.py"),
       "1.1.1.1",p029_converse_cn4,"10.66.0.2",host_source],
       stdout=gf,stderr=subprocess.STDOUT)
   ready(out/gn,"PLAN029_H1775_LINUX_CN_DNS_AND_PHYSICAL_DIRECT_READY",p029_d2_cn_guest,12)
   wf=(out/wn).open("w");logs.append(wf)
   p029_d2_cn_win=subprocess.Popen([sys.executable,
       str(root/"tools"/"m0_plan029_h1775_windows_cn_converse.py"),
       "10.66.0.2",p029_converse_cn4],
       stdout=wf,stderr=subprocess.STDOUT)
   if p029_d2_cn_win.wait(timeout=39)!=0 or p029_d2_cn_guest.wait(timeout=8)!=0:
    raise RuntimeError("H1775 real Wintun→physical CN IP failed win="+
      (out/wn).read_text(errors="replace")[-700:]+
      " guest="+(out/gn).read_text(errors="replace")[-700:])
   proofs={}
   for key,file,marker in (
    ("windows",wn,"PLAN029_H1775_REAL_WINDOWS_D2_CNIP_DIRECT "),
    ("linux",gn,"PLAN029_H1775_REAL_LINUX_D2_CNIP_DIRECT ")):
    values=[ln.split(" ",1)[1] for ln in (out/file).read_text().splitlines()
            if ln.startswith(marker)]
    if len(values)!=1:raise RuntimeError("H1775 missing true two-OS CN-IP receipt "+key)
    proofs[key]=json.loads(values[0])
   if not(proofs["windows"]["dns_real_a"]==p029_converse_cn4 and
          proofs["windows"]["business_dst"]==p029_converse_cn4 and
          proofs["windows"]["fakeip"] is False and
          proofs["windows"]["echo_bytes"]==proofs["linux"]["echo_bytes"] and
          proofs["linux"]["dns_upstream"]=="1.1.1.1" and
          proofs["linux"]["dns_client_lease"]=="10.66.0.2" and
          proofs["linux"]["real_dns_a"]==p029_converse_cn4 and
          proofs["linux"]["physical_business_dst"]==p029_converse_cn4 and
          proofs["linux"]["physical_source"]==host_source):
    raise RuntimeError("H1775 actual DNS/Tunnel versus business/Direct disjoint proof missing")
   report["plan029_d2_noncn_cn_ip_direct_udp"]={
     "source_sha":os.environ["GITHUB_SHA"],
     "scope":"REAL_NONCN_TUNNEL_DNS_TO_CN_IP_RUST_PHYSICAL_DIRECT_UDP",
     "windows":proofs["windows"],"linux":proofs["linux"],
     "ordinary_on_link_os_capture":"NOT_PROVEN_EXPLICIT_WINTUN_BOUND_APP",
     "direct_tcp":"NOT_RUN","stop":"NOT_RUN_UNTIL_OWNED_CLEANUP"}
   report["plan029_d2_noncn_resolved_a_tunnel_business"]["cn_ip_a_converse"]=(
     "PASS_REAL_TUNNEL_DNS_CN_IP_PHYSICAL_DIRECT_UDP")
   print("PLAN029_H1775_REAL_NONCN_TUNNEL_DNS_CN_IP_PHYSICAL_DIRECT_UDP_PASS_PRE_CLEANUP",flush=True)
  finally:
   h1775_owned_cleanup()
  report["plan029_d2_noncn_cn_ip_direct_udp"]["stop"]="PASS_EXACT_ROUTE_ALIAS_CLEANUP"
  print("PLAN029_H1775_REAL_D2_CN_IP_CONVERSE_OWNED_CLEANUP_PASS",flush=True)
  # H1794: TWO actual Linux TCP/53 listeners, one physical eth0 (the
  # unique dns.direct), the other the previously owned WSL TUN /32
  # (the unique dns.tunnel). Both share the existing original signed
  # Windows Wintun owner and post-Apply authorized local TCP listener.
  if p029_tcp53:
   gn="plan029-h1794-linux-two-tcp53.log"
   wn="plan029-h1794-windows-app-tcp53.log"
   gf=(out/gn).open("w");logs.append(gf)
   p029_tcp53_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
     "python3","-u",unix(root/"tools"/"m0_plan029_h1794_linux_real_tcp53.py"),
     peer,"1.1.1.1",host_source,"10.66.0.2"],
     stdout=gf,stderr=subprocess.STDOUT)
   ready(out/gn,"PLAN029_H1794_REAL_TWO_LINUX_TCP53_ENDPOINTS_READY",p029_tcp53_guest,12)
   wf=(out/wn).open("w");logs.append(wf)
   p029_tcp53_win=subprocess.Popen([sys.executable,
     str(root/"tools"/"m0_plan029_h1794_windows_real_app_tcp53.py"),
     "10.66.0.2","8.8.8.8"],
     stdout=wf,stderr=subprocess.STDOUT)
   if p029_tcp53_win.wait(timeout=36)!=0 or p029_tcp53_guest.wait(timeout=8)!=0:
    raise RuntimeError("H1794 original Windows app TCP53 real two endpoint failed win="+
       (out/wn).read_text(errors="replace")[-950:]+" linux="+
       (out/gn).read_text(errors="replace")[-950:])
   witnesses={}
   for who,name,marker in (
     ("windows",wn,"PLAN029_H1794_WINDOWS_REAL_ORIGINAL_APP_TCP53 "),
     ("linux",gn,"PLAN029_H1794_LINUX_REAL_DIRECT_AND_TUNNEL_TCP53 ")):
    rows=[line.split(" ",1)[1] for line in (out/name).read_text().splitlines()
          if line.startswith(marker)]
    if len(rows)!=1:raise RuntimeError("H1794 missing unique real native TCP DNS receipt "+who)
    witnesses[who]=json.loads(rows[0])
   wrec,lrec=witnesses["windows"],witnesses["linux"]
   if not(wrec["two_original_kernel_tcp_app_connections"] is True and
       wrec["direct"]["was_fake"] is True and
       wrec["direct"]["dns_answer_a"].startswith("198.18.") and
       wrec["direct"]["real_upstream_a"]=="198.51.100.77" and
       wrec["tunnel"]["was_fake"] is False and
       wrec["tunnel"]["dns_answer_a"]=="203.0.113.77" and
       lrec["direct"]["real_socket_local"]==peer and
       lrec["direct"]["original_client_source"]==host_source and
       lrec["direct"]["real_a"]=="198.51.100.77" and
       lrec["tunnel"]["real_socket_local"]=="1.1.1.1" and
       lrec["tunnel"]["original_client_source"]=="10.66.0.2" and
       lrec["tunnel"]["real_a"]=="203.0.113.77" and
       lrec["no_other_dns_endpoint"] is True):
    raise RuntimeError("H1794 actual two DNS TCP egress/original source/FakeIP inconsistent")
   report["plan029_d1_original_app_tcp53"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "scope":"SIGNED_ORIGINAL_WINDOWS_KERNEL_APP_TCP53_CN_DIRECT_AND_NONCN_TUNNEL",
    "windows":wrec,"linux":lrec,
    "two_upstream_physical_sockets":"REAL_ETH0_TCP53_AND_ORIGINAL_TUN_TCP53",
    "stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
   report["plan029_d1_noncn_udp_dns_real"]["app_tcp53"]="PASS_REAL_DIRECT_AND_TUNNEL_TCP"
   print("PLAN029_H1794_REAL_ORIGINAL_APP_TCP53_BOTH_ENDPOINTS_PASS_PRE_STOP",flush=True)
  # One H1778 source-frozen hard8 real signed scene before DNS blackout.
  # Existing Windows Wintun owner and two independent Linux UDP sockets
  # witness full Direct, NEW Tunnel flow and 120s Direct expiry/recovery.
  if p029_pressure:
   gn="plan029-h1778-linux-flow-pressure.log"
   wn="plan029-h1778-windows-flow-pressure.log"
   gf=(out/gn).open("w");logs.append(gf)
   p029_pressure_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1778_guest_bounded_flow_pressure.py"),
      peer,p029_tunnel_alias,host_source,"10.66.0.2"],
      stdout=gf,stderr=subprocess.STDOUT)
   ready(out/gn,"PLAN029_H1778_LINUX_TWO_OS_SOCKETS_READY",p029_pressure_guest,15)
   wf=(out/wn).open("w");logs.append(wf)
   p029_pressure_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1778_windows_bounded_flow_pressure.py"),
      "10.66.0.2",wdata["fake4"],p029_tunnel_alias],
      stdout=wf,stderr=subprocess.STDOUT)
   try:wr=p029_pressure_win.wait(timeout=195)
   except subprocess.TimeoutExpired:
    raise RuntimeError("H1778 real hard8 original Windows app deadline")
   if wr or p029_pressure_guest.wait(timeout=10):
    raise RuntimeError("H1778 real Direct/Tunnel first fault win="+
      (out/wn).read_text(errors="replace")[-850:]+" linux="+
      (out/gn).read_text(errors="replace")[-850:])
   proof={}
   for who,name,marker in (
     ("windows",wn,"PLAN029_H1778_WINDOWS_DIRECT8_TUNNEL_PRESSURE "),
     ("linux",gn,"PLAN029_H1778_LINUX_BOUNDED_TWO_EGRESS ")):
    found=[line.split(" ",1)[1] for line in (out/name).read_text().splitlines()
           if line.startswith(marker)]
    if len(found)!=1:raise RuntimeError("H1778 missing unique true OS receipt "+who)
    proof[who]=json.loads(found[0])
   win,linux=proof["windows"],proof["linux"]
   if not(win["hard_configured"]==8 and win["new_direct_attempts"]==16 and
       1<=win["new_direct_real_echo"]<=8 and win["unanswered_new_direct"]>=8 and
       win["new_tunnel_while_full"] is True and
       win["old_direct_heartbeat"]>=8 and
       win["new_direct_after_expiry"] is True and win["old_direct_final"] is True and
       linux["direct_source_physical"]==host_source and
       linux["first_unique"]>=win["new_direct_real_echo"] and
       linux["tunnel_lease"]=="10.66.0.2" and
       linux["tunnel_dst"]==p029_tunnel_alias and
       linux["new_tunnel_echo"]>=1 and
       linux["old_direct_keep"]>=8 and
       linux["new_direct_after_idle"]>=1 and linux["old_direct_final"]>=1):
    raise RuntimeError("H1778 source-frozen real sockets did not prove Direct8/Tunnel isolation")
   report["plan029_d3_direct_hard_pressure"]={
     "source_sha":os.environ["GITHUB_SHA"],
     "scope":"SIGNED_ONE_WINTUN_DIRECT_HARD8_NEW_TUNNEL_AND_IDLE_RECOVERY",
     "windows":win,"linux":linux,
     "typed_native_capacity_drop_counter":"NOT_RUN",
     "dns_fakeip_tcp_buffer_pressure":"NOT_RUN",
     "stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
   print("PLAN029_H1778_SIGNED_DIRECT8_NEW_TUNNEL_OLD_DIRECT_RECOVERY_PASS_PRE_STOP",flush=True)
  # D1 single-upstream timeout proof. After genuine one-endpoint success,
  # leave the same run-owned TUN 1.1.1.1/32 in place and bind two independent
  # receivers: Tunnel DNS silently blackholes, physical Direct DNS is a
  # sentinel. The original Windows Wintun app MUST time out, with real
  # packets reaching only 1.1.1.1, not silently fail over to physical DNS.
  bh_guest_log=(out/"plan029-h1767-linux-dns-blackhole.log").open("w");logs.append(bh_guest_log)
  p029_dns_blackhole_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1767_linux_dns_blackhole.py"),
      "1.1.1.1",peer,"10.66.0.2"],
      stdout=bh_guest_log,stderr=subprocess.STDOUT)
  ready(out/"plan029-h1767-linux-dns-blackhole.log",
      "PLAN029_H1767_LINUX_TUN_DNS_BLACKHOLE_AND_PHYSICAL_SENTINEL_READY",
      p029_dns_blackhole_guest,12)
  bh_win_log=(out/"plan029-h1767-windows-dns-blackhole.log").open("w");logs.append(bh_win_log)
  p029_dns_blackhole_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1767_windows_dns_blackhole.py"),
      "10.66.0.2","8.8.8.8"],
      stdout=bh_win_log,stderr=subprocess.STDOUT)
  win_exit=p029_dns_blackhole_win.wait(timeout=10)
  guest_exit=p029_dns_blackhole_guest.wait(timeout=10)
  if win_exit or guest_exit:
   raise RuntimeError("D1 exact resolver blackout/fallback violated windows="+
      (out/"plan029-h1767-windows-dns-blackhole.log").read_text(errors="replace")[-700:]+
      " linux="+(out/"plan029-h1767-linux-dns-blackhole.log").read_text(errors="replace")[-700:])
  bh_proofs={}
  for who,filename,marker in (
   ("windows","plan029-h1767-windows-dns-blackhole.log","PLAN029_H1767_REAL_WINDOWS_DNS_BLACKHOLE "),
   ("linux","plan029-h1767-linux-dns-blackhole.log","PLAN029_H1767_REAL_LINUX_DNS_BLACKHOLE ")):
   lines=[line.split(" ",1)[1] for line in (out/filename).read_text().splitlines()
          if line.startswith(marker)]
   if len(lines)!=1:raise RuntimeError("blackhole real "+who+" unique receipt missing")
   bh_proofs[who]=json.loads(lines[0])
  if not (bh_proofs["windows"]["query_count"]==3 and
          bh_proofs["windows"]["unexpected_response"] is False and
          bh_proofs["linux"]["tunnel_query_count"]>=2 and
          bh_proofs["linux"]["physical_query_count"]==0 and
          bh_proofs["linux"]["replied"] is False and
          bh_proofs["linux"]["physical_ip"]==peer and
          bh_proofs["linux"]["client_source"]==["10.66.0.2"]):
   raise RuntimeError("D1 no-fallback exact real Windows/Linux DNS receipts diverge")
  report["plan029_d1_dns_blackhole_no_fallback"]={
      "source_sha":os.environ["GITHUB_SHA"],
      "scope":"SIGNED_WINDOWED_UDP53_NONCN_TUNNEL_DNS_BLACKHOLE_PHYSICAL_SENTINEL",
      "windows":bh_proofs["windows"],"linux":bh_proofs["linux"],
      "app_tcp53":"NOT_RUN","other_system_dns":"NOT_PROVEN"}
  report["plan029_d1_noncn_udp_dns_real"]["blackhole_no_fallback"]=(
      "PASS_REAL_TUNNEL_NO_REPLY_AND_ZERO_PHYSICAL_DIRECT_FALLBACK")
  print("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED",flush=True)
 # Exact native DF0/DF1 scenario only, after authenticated original-Go
 # TLS, actual Windows Wintun and WSL2 Linux TUN TCP+UDP smoke.
 if os.environ.get("WBD_WL_V2_SCENARIO")==(
     "scenarios/plan027a-h958-normal-1460-5m-df-60s.json"):
  df_file=root/"tools/m0_wl_native_df_kernel.py"
  df_flag=out/"df-real-kernel-ready.flag"
  df_flag.unlink(missing_ok=True)
  df_children=[]
  try:
   for name,cmd in (
    ("windows",[sys.executable,str(df_file),"10.66.0.2","10.66.0.1",str(df_flag)]),
    ("linux",["wsl.exe","-d","Ubuntu","-u","root","--","python3",
              unix(df_file),"10.66.0.1","10.66.0.2",unix(df_flag)])):
    log=(out/("df-"+name+".log")).open("w");logs.append(log)
    df_children.append((name,subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)))
   for name,p in df_children:
    ready(out/("df-"+name+".log"),'"phase": "bound"',p,25)
   df_flag.write_text("REAL_BOTH_OS_SOCKETS_BOUND\n")
   deadline=time.monotonic()+45
   while any(p.poll() is None for _,p in df_children):
    if s.poll() is not None or w.poll() is not None:
     raise RuntimeError("original Rust/Go native product exited during DF probe")
    if time.monotonic()>deadline:raise RuntimeError("real DF0/DF1 bounded OS deadline")
    time.sleep(.15)
   verified={}
   for name,p in df_children:
    content=(out/("df-"+name+".log")).read_text(errors="replace").strip().splitlines()
    if p.returncode or not content:
     raise RuntimeError("genuine "+name+" DF probe failed rc="+str(p.returncode)+
                        " tail="+repr(content[-3:]))
    item=json.loads(content[-1])
    if (item.get("result")!="REAL_DF0_REASSEMBLED_DF1_EMSGSIZE" or
        item.get("received_bytes")!=1728 or item.get("df1_errno") not in (90,10040)):
     raise RuntimeError("invalid true "+name+" OS DF receipt "+repr(item))
    verified[name]=item
   report["plan027a_real_native_df0_df1"]=verified
   print("PLAN027A_WINDOWS_LINUX_KERNEL_DF0_FRAGMENT_DF1_EMSGSIZE_PASS",flush=True)
  finally:
   for _,p in df_children:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=3)
     except subprocess.TimeoutExpired:p.kill()

 # One scoped B lifecycle scenario: both original 10.66.x app sockets have
 # closed after real UDP+TCP, so the owned tunnel has no user payload. Keep
 # the genuine Go TLS/Rust owners alive beyond the 90s authenticated-dead
 # threshold, then demand new reverse+first kernel UDP before V2 traffic.
 lifecycle_s=0
 source_scene=os.environ.get("WBD_WL_V2_SCENARIO","").strip()
 if source_scene:
  from m0_wl_perf_v2_config import read_scenario
  lifecycle_s=read_scenario(root/source_scene).get("lifecycle_idle_s",0)
 if lifecycle_s:
  print("WL_V2_B_IDLE_BEGIN seconds="+str(lifecycle_s),flush=True)
  started_idle=time.monotonic()
  while time.monotonic()-started_idle<lifecycle_s:
   if w.poll() is not None or s.poll() is not None:
    raise RuntimeError("genuine authenticated owner lost during no-payload idle")
   time.sleep(.5)
  awake=[]
  for name in ("windows","linux"):
   f=(out/("idle-wake-"+name+".log")).open("w")
   logs.append(f);awake.append(f)
  wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1",str(done),"3"],stdout=awake[0],stderr=subprocess.STDOUT)
  la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),"10.66.0.1","10.66.0.2",unix(done),"3"],stdout=awake[1],stderr=subprocess.STDOUT)
  deadline=time.monotonic()+65
  while wa.poll() is None or la.poll() is None:
   if w.poll() is not None or s.poll() is not None:raise RuntimeError("real owner exited during idle wake")
   if time.monotonic()>deadline:
    wa.terminate();la.terminate()
    raise RuntimeError("real idle wake kernel UDP deadline")
   time.sleep(.2)
  if wa.returncode or la.returncode:
   raise RuntimeError("real post-idle duplex failed win="+str(wa.returncode)+" linux="+str(la.returncode))
  for name in ("windows","linux"):
   rows=(out/("idle-wake-"+name+".log")).read_text().splitlines()
   wake=json.loads(rows[-1])
   if wake.get("received",0)<12 or wake.get("sent",0)<24 or not wake.get("public_ready_seen"):
    raise RuntimeError("real post-90s idle payload absent "+name+" "+repr(wake))
  report["lifecycle_idle_wake"]={"idle_seconds":round(time.monotonic()-started_idle,2),
   "both_owners_stayed_alive":True,"post_idle_genuine_udp":"PASS_BOTH_KERNEL_DIRECTIONS",
   "authenticated_health_count":"NOT_EXPLICITLY_MEASURED"}
  print("WL_V2_B_IDLE_90S_NO_PAYLOAD_THEN_REAL_BIDIRECTIONAL_WAKE_PASS",flush=True)
 # A source-controlled lifecycle phase with 100% *real tc loss* in
 # both original FakeTCP directions. A 106s outage must prove authentic new generation
 # instead of pretending the old 20s recovery implies dead90.
 blackhole_scene=os.environ.get("WBD_WL_V2_SCENARIO","").strip()
 blackout=read_scenario(root/blackhole_scene).get("lifecycle_blackhole_s",0) if blackhole_scene else 0
 if blackout:
  ctl=unix(root/"tools/m0_wl_netem.py")
  scenario_file=unix(root/blackhole_scene)
  def change_blackhole(action):
   return wsl("python3",ctl,action,unix(out),"v2",scenario_file,timeout=35)
  print("WL_B_KERNEL_BLACKHOLE_BEGIN seconds="+str(blackout),flush=True)
  change_blackhole("arm")
  try:
   change_blackhole("blackhole")
   time.sleep(blackout)
   if blackout==105:
    # The original Windows->Linux 443 IFB is actually dropping, rather
    # than merely receiving a requested 100% loss configuration.
    change_blackhole("snapshot")
    tc=json.loads((out/"wl-n0-netem-after.json").read_text())
    observed=[row.get("drops") for row in tc.get("ifb",[])
              if row.get("kind")=="netem"]
    if len(observed)!=1 or type(observed[0]) is not int or observed[0]<=0:
     raise RuntimeError("original Windows-origin 105s real IFB drops not observed")
    report["lifecycle_unilateral_ifb_drops"]=observed[0]
    print("WL_B_REAL_WINDOWS_ORIGIN_105S_IFB_DROPS="+str(observed[0]),flush=True)
   change_blackhole("recover")
  finally:
   change_blackhole("cleanup")
  if w.poll() is not None or s.poll() is not None:
   raise RuntimeError("original owner exited during real kernel outage")
  bw=(out/"blackhole-windows-udp.log").open("w");bl=(out/"blackhole-linux-udp.log").open("w")
  logs.extend([bw,bl])
  hold="120" if blackout==105 else "3"
  wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1",str(done),hold],stdout=bw,stderr=subprocess.STDOUT)
  la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),"10.66.0.1","10.66.0.2",unix(done),hold],stdout=bl,stderr=subprocess.STDOUT)
  until=time.monotonic()+(155 if blackout==105 else 65)
  while wa.poll() is None or la.poll() is None:
   if w.poll() is not None or s.poll() is not None:
    raise RuntimeError("original owner exited during post-blackhole wake")
   if time.monotonic()>until:
    wa.terminate();la.terminate()
    raise RuntimeError("bounded real post-blackhole UDP failed")
   time.sleep(.2)
  if wa.returncode or la.returncode:
   # Source-owned, allowlisted diagnostics survive an artifact API DNS error.
   # No TLS secrets, user identities, ciphertext, or packet bodies.
   fault={"source":os.environ["GITHUB_SHA"],"blackhole_s":blackout,
          "ifb_drops":report.get("lifecycle_unilateral_ifb_drops"),
          "wake_rc":{"windows":wa.returncode,"linux":la.returncode},
          "role_samples":{},"owner_markers":{}}
   for role in ("windows","linux"):
    path=out/("blackhole-"+role+"-udp.log")
    rows=[]
    if path.exists():
     for line in path.read_text(errors="replace").splitlines():
      if line.startswith("{"):
       try:
        item=json.loads(line)
        rows.append({k:item[k] for k in ("phase","sent","received","public_ready_seen","kernel_bind") if k in item})
       except (TypeError,ValueError):pass
    fault["role_samples"][role]={"count":len(rows),"first":rows[:1],"last":rows[-3:]}
   allow=("NATIVE_DEAD_RECONNECT_ARMED","ORIGINAL_GO_TLS_REAUTHORIZE",
          "WBD_WINDOWS_CLIENT_READY","NATIVE_STOP_DRAINED",
          "NATIVE_DISCONNECTED","NATIVE_HEALTH","HEALTH_DEAD",
          "RUST_NATIVE_HEALTH_TIMEOUT","NATIVE_FAILURE_SOURCE",
          "NATIVE_STOP_NOT_DRAINED","NATIVE_STOP_RESULT")
   for role,name in (("windows","client.log"),("linux","server.log")):
    path=out/name
    lines=[line[-320:] for line in path.read_text(errors="replace").splitlines()
           if any(marker in line for marker in allow)] if path.exists() else []
    fault["owner_markers"][role]={"count":len(lines),"tail":lines[-16:]}
   (out/"normal105-first-fault.json").write_text(json.dumps(fault,indent=2)+"\n")
   # A failed GitHub artifact upload previously erased the only uncut
   # owner markers. The existing one-shot failure path, not a packet loop,
   # prints at most six allowlisted terminal lines per OS to live stdout.
   # Each line is capped; no TLS credentials, payloads or wire bytes.
   for role in ("windows","linux"):
    tail=fault["owner_markers"][role]["tail"]
    for marker in tail[-6:]:
     clean=marker.replace("\r","\\r").replace("\n","\\n")
     print("PLAN027_ORIGINAL_105_OWNER_TAIL role="+role+
           " line="+clean[-320:],flush=True)
   print("PLAN027_ORIGINAL_105_FIRST_FAULT "+json.dumps(fault,separators=(",",":")),flush=True)
   report["lifecycle_blackhole_failure"]="POST105_WAKE_NOT_PROVEN"
   raise RuntimeError("real UDP blackout wake returned nonzero")
  for name in ("windows","linux"):
   wake=json.loads((out/("blackhole-"+name+"-udp.log")).read_text().splitlines()[-1])
   if not wake.get("public_ready_seen") or wake.get("sent",0)<24 or wake.get("received",0)<12:
    raise RuntimeError("real post-blackhole first UDP missing "+name+" "+repr(wake))
  report["lifecycle_blackhole_recovery"]={"blackhole_s":blackout,"kernel_loss_pct":100,
      "fresh_udp_both_directions":"PASS_REAL_KERNEL_UDP"}
  if blackout in (105,106):
   if blackout==105:
    report["lifecycle_blackhole_recovery"]["blackhole_direction"]="windows_to_linux"
    report["lifecycle_blackhole_recovery"]["actual_ifb_drops"]=report["lifecycle_unilateral_ifb_drops"]
    report["lifecycle_blackhole_recovery"]["restored_observation_seconds"]=120
    for name in ("windows","linux"):
     rows=[json.loads(line) for line in (out/("blackhole-"+name+"-udp.log")).read_text().splitlines() if line.startswith("{")]
     recovered=[i for i,row in enumerate(rows) if row.get("phase")=="udp_1hz" and row.get("received",0)>0]
     if not recovered:raise RuntimeError("genuine post-unilateral recovery first sample absent "+name)
     report["lifecycle_blackhole_recovery"][name+"_first_received_sample_index"]=recovered[0]
   server_log=(out/"server.log").read_text(errors="replace")
   if ("V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED role=server" not in server_log or
       "V4_PUBLIC_ORIGINAL_GO_TLS_REAUTHORIZE role=server" not in server_log):
    raise RuntimeError("106s blackout missing original new TLS generation "+server_log[-600:])
   win_log=(out/"client.log").read_text(errors="replace")
   if ("WBD_WINDOWS_NATIVE_DEAD_RECONNECT_ARMED generation=" not in win_log or
       "WBD_WINDOWS_ORIGINAL_GO_TLS_REAUTHORIZE generation=" not in win_log or
       win_log.count("WBD_WINDOWS_CLIENT_READY")<2):
    raise RuntimeError("106s blackout lacks Windows original new authenticated TLS generation "+win_log[-600:])
   report["lifecycle_blackhole_recovery"]["windows_reauth"]="PASS_NATIVE_DEAD90_ORIGINAL_TLS"
   report["lifecycle_blackhole_recovery"]["linux_reauth"]="PASS_NATIVE_DEAD90_ORIGINAL_TLS"
   if blackout==105:
    print("WL_B_REAL_WINDOWS_UNILATERAL_105S_AUTHENTICATED_DEAD_RECOVER_BOTH_OS_PASS",flush=True)
   else:
    print("WL_B_REAL_106S_AUTHENTICATED_DEAD_RECOVER_BOTH_OS_PASS",flush=True)
  else:
   print("WL_B_REAL_20S_BLACKHOLE_RESTORED_NEW_BILATERAL_UDP_PASS",flush=True)
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
  if stress or os.environ.get("WBD_WL_RUN_N0")=="1":
   raise RuntimeError("WL_V2_CANNOT_MIX_LEGACY_PERFORMANCE")
  v2_path=(root/v2_file).resolve()
  if not v2_path.is_relative_to((root/"scenarios").resolve()) or v2_path.suffix!=".json":
   raise RuntimeError("WL_V2_UNSAFE_SCENARIO_PATH")
  scenario=read_scenario(v2_path)
  if scenario.get("public_mode","normal")!=mode:
   raise RuntimeError("WL_V2_MODE_AND_SCENARIO_MISMATCH")
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
  def netem(action,stage_index=None):
   cmd=["wsl.exe","-d","Ubuntu","-u","root","--","python3",
        unix(root/"tools"/"m0_wl_netem.py"),action,unix(out),profile_name]
   if scenario:cmd.append(unix(v2_path))
   if stage_index is not None:cmd.append(str(stage_index))
   return run(cmd,timeout=35)
  # Actual Linux TUN FQ kernel qdisc, distinct from WSL eth0/IFB netem.
  def tun_fq_snapshot(phase):
   try:
    rows=json.loads(wsl("tc","-s","-j","qdisc","show","dev","wbdwl4",timeout=10))
    (out/("wl-v2-linux-tun-fq-"+phase+".json")).write_text(json.dumps(rows,indent=2)+"\n")
    return rows
   except (ValueError,RuntimeError) as error:
    report["linux_tun_fq_"+phase+"_error"]=type(error).__name__
    return None
  def tun_link_snapshot(phase):
   try:
    rows=json.loads(wsl("ip","-s","-j","link","show","dev","wbdwl4",timeout=10))
    (out/("wl-v2-linux-tun-link-"+phase+".json")).write_text(json.dumps(rows,indent=2)+"\n")
    return rows
   except (ValueError,RuntimeError) as error:
    report["linux_tun_link_"+phase+"_error"]=type(error).__name__
    return None
  tun_fq_before=tun_fq_snapshot("before") if scenario else None
  tun_link_before=tun_link_snapshot("before") if scenario else None
  tun_queue_lease=None
  owned=out/"wl-n0-netem-owned.json"
  try:
   report["WL_N0"]="ENVIRONMENT_OR_PRODUCT_NOT_YET_VERIFIED"
   if scenario and scenario.get("linux_tun_txqlen_packets") is not None:
    original=tun_queue_identity(tun_link_before)
    requested=scenario["linux_tun_txqlen_packets"]
    if original is None or original["txqlen"]!=500:
     raise RuntimeError("H491_ORIGINAL_TUN_QUEUELEN_BASELINE_NOT_500")
    wsl("ip","link","set","dev","wbdwl4","txqueuelen",str(requested),timeout=10)
    tun_queue_lease={"ifindex":original["ifindex"],"baseline":500,"requested":requested}
    applied=tun_queue_identity(tun_link_snapshot("configured"))
    if applied is None or applied["ifindex"]!=original["ifindex"] or applied["txqlen"]!=requested:
     raise RuntimeError("H491_TUN_QUEUELEN_DRIVER_READBACK_MISMATCH")
    report["linux_tun_queue_control"]={"status":"ORIGINAL_WSL_TUN_QUEUE_APPLIED",
      "original":500,"requested":requested,"ifindex":original["ifindex"],
      "source":"REAL_IP_LINK_NOT_WINDOWS_NPF_OR_TC_FQ",
      "scenario_sha256":scenario["scenario_sha256"]}
    print("H491_ORIGINAL_TUN_QUEUE_ACTUAL "+json.dumps(report["linux_tun_queue_control"]),flush=True)
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
    phase_events=[]
    phase_schedule=scenario.get("impairment_stages") if scenario else None
    kernel_bursts=scenario.get("kernel_loss_bursts") if scenario else None
    kernel_burst_index=0
    observed_kernel_bursts=[]
    phase_clock=time.monotonic()
    phase_next_index=1 if phase_schedule else 0
    if phase_schedule:
     phase_events.append({"index":0,"scheduled_s":0,"elapsed_s":0,
                          "source":"REAL_KERNEL_TC_ARM_BEFORE_APPLICATION_BARRIER",
                          "scenario_sha256":scenario["scenario_sha256"]})
    # Poll process liveness, never relay/transform tested traffic.
    until=time.monotonic()+int(seconds)+25
    while linuxrate.poll() is None or windowsrate.poll() is None:
     if w.poll() is not None or s.poll() is not None:
      # Do not replace the first native owner failure with a generic perf
      # timeout. This summary is allowlisted: never upload raw TLS/packet logs.
      markers=("WBD_WINDOWS_NATIVE_FAILURE_SOURCE",
               "WBD_WINDOWS_NATIVE_DISCONNECTED_V1",
               "WBD_WINDOWS_NATIVE_APPLIED_V1",
               "V4_PUBLIC_NATIVE_STOP_DRAINED")
      diagnostic={}
      for key,path in (("windows",out/"client.log"),("linux",out/"server.log")):
       rows=[]
       if path.is_file():
        with path.open("rb") as stream:
         stream.seek(0,2)
         stream.seek(max(0,stream.tell()-131072))
         for raw in stream.read().decode("utf-8","replace").splitlines():
          for marker in markers:
           if marker in raw:
            # A line digest can be matched to a private runner log if
            # necessary; only allowlisted code-stage tokens are public.
            allowed=("Npcap","Wintun","M1","M2","M3","M4","WAL",
                     "Stop","source","batch","peer","owner","route",
                     "expired","timeout","closed","ring","failure",
                     "capacity","kernel","NET","OS","backpressure")
            item={"marker":marker,
                  "sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                  "tokens":[t for t in allowed if t.lower() in raw.lower()]}
            rows.append(item)
        diagnostic[key]=rows[-6:]
       else:diagnostic[key]=[]
      report["native_early_exit"]={
       "windows_rc":w.poll(),"linux_rc":s.poll(),
       "observed_marker_signatures":diagnostic,
       "phase":"real_kernel_sustained_udp",
       "status":"FAIL_EXIT_DURING_REQUIRED_60S"}
      print("WL_V2_FIRST_NATIVE_EXIT "+json.dumps(report["native_early_exit"],sort_keys=True),flush=True)
      raise RuntimeError("real public product exited during WL-N0")
     if phase_schedule and phase_next_index<len(phase_schedule):
      target_phase=phase_schedule[phase_next_index]
      if time.monotonic()-phase_clock>=target_phase["start_s"]:
       print(netem("stage",phase_next_index),flush=True)
       phase_events.append({"index":phase_next_index,
                            "scheduled_s":target_phase["start_s"],
                            "elapsed_s":round(time.monotonic()-phase_clock,3),
                            "source":"REAL_ETH0_IFB_OWNED_TC_QDISC_CHANGE",
                            "scenario_sha256":scenario["scenario_sha256"],
                            "readback_file":f"wl-v2-kernel-stage-{phase_next_index:02}.json"})
       phase_next_index+=1
     if kernel_bursts and kernel_burst_index<len(kernel_bursts):
      pulse=kernel_bursts[kernel_burst_index]
      if time.monotonic()-phase_clock>=pulse["start_s"]:
       raw=netem("burst",kernel_burst_index)
       mark="WL_V2_BURST_PULSE_MEASURED "
       if mark not in raw:raise RuntimeError("true kernel burst missing tc readback")
       receipt=json.loads(raw.split(mark,1)[1].splitlines()[0])
       if (receipt.get("index")!=kernel_burst_index or
           receipt.get("requested_duration_ms")!=pulse["duration_ms"] or
           receipt.get("min_bilateral_100pct_active_ms",0)<pulse["duration_ms"]):
        raise RuntimeError("native tc burst measured duration shorter than declared")
       observed_kernel_bursts.append(receipt)
       kernel_burst_index+=1
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
   if scenario:
    tun_fq_after=tun_fq_snapshot("after")
    tun_link_after=tun_link_snapshot("after")
    report["linux_tun_link_kernel"]=link_delta(tun_link_before,tun_link_after)
    print("WL_V2_LINUX_TUN_IFACE_KERNEL "+json.dumps(report["linux_tun_link_kernel"],sort_keys=True),flush=True)
    report["linux_tun_fq_kernel"]=fq_delta(tun_fq_before,tun_fq_after)
    print("WL_V2_LINUX_TUN_FQ_KERNEL "+json.dumps(report["linux_tun_fq_kernel"],sort_keys=True),flush=True)
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
    if kernel_bursts:
     if len(observed_kernel_bursts)!=len(kernel_bursts):
      raise RuntimeError("WL_V2_REAL_KERNEL_BURST_SCOPE_NOT_COMPLETED")
     report["WL_V2"]["kernel_bursts_applied"]=observed_kernel_bursts
    if phase_schedule:
     if len(phase_events)!=len(phase_schedule):
      raise RuntimeError("WL_V2_AUTO_KERNEL_PHASE_NOT_APPLIED "+
                         str(len(phase_events))+"/"+str(len(phase_schedule)))
     report["WL_V2"]["kernel_phases_applied"]=phase_events
     report["WL_V2"]["a4_auto_mature_grade"]="NOT_PROVEN_UNTIL_NATIVE_QUALITY_AND_APPLIED_READBACK"
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
   try:
    if tun_queue_lease is not None:
     before=tun_queue_identity(tun_link_snapshot("pre-restore"))
     if before is None or before["ifindex"]!=tun_queue_lease["ifindex"] or before["txqlen"]!=tun_queue_lease["requested"]:
      raise RuntimeError("H491_TUN_QUEUELEN_FOREIGN_MUTATION_BLOCK_RESTORE")
     wsl("ip","link","set","dev","wbdwl4","txqueuelen",str(tun_queue_lease["baseline"]),timeout=10)
     restored=tun_queue_identity(tun_link_snapshot("restored"))
     if restored is None or restored["ifindex"]!=tun_queue_lease["ifindex"] or restored["txqlen"]!=tun_queue_lease["baseline"]:
      raise RuntimeError("H491_TUN_QUEUELEN_ORIGINAL_RESTORE_FAILED")
     report["linux_tun_queue_control"]["restored"]="PASS_ORIGINAL_500_READBACK"
     print("H491_ORIGINAL_TUN_QUEUE_RESTORED ifindex="+str(restored["ifindex"]),flush=True)
   finally:
    if owned.exists():
     print(netem("cleanup"),flush=True)
 game_due_first_fault()
 stop_windows(w)
 stop_marker="WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" if is_game else "WBD_WINDOWS_NATIVE_DISCONNECTED_V1"
 if w.returncode!=0 or stop_marker not in (out/"client.log").read_text():
  if is_game:
   # H679 lost the entire original client/server artifact when the artifact
   # service failed. Emit only a sanitized bounded diagnostic tail on this
   # actual product failure; not a new data-plane logger or source gate.
   for role in ("client","server"):
    content=(out/(role+".log")).read_text(errors="replace")[-4200:]
    content=re.sub(r"(?i)\b(password|secret|credential|token|key)([=:])\S+",r"\1\2[REDACTED]",content)
    print("WL_GAME_ORIGINAL_STOP_FAILURE_"+role.upper()+"_TAIL "+content,flush=True)
  raise RuntimeError("Windows native owned WAL Stop missing")
 stop_linux();s.wait(timeout=10)
 stop_marker=("V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close" if is_game and plan028_owned_switch else
  "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server" if is_game else
  "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" if plan028_owned_switch else
  "V4_PUBLIC_NATIVE_STOP_DRAINED role=server")
 if s.returncode or stop_marker not in (out/"server.log").read_text():raise RuntimeError("Linux original Rust Stop missing")
 report["stop"]="PASS_BOTH_OWNED"
 if p029_product:
  # Not a private trial: the same real original Go/Rust owner and OS WAL
  # must have independently shown Windows+Linux Stop and exact route/
  # Defender cleanup after true two-OS business, not just READY.
  win_native=(out/"client.log").read_text(errors="replace")
  required=("WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=bypass-lan-cn",
            "source=explicit_config readiness=AWAIT_REAL_OS_RUST_RECEIPT",
            "WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1",
            "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",
            "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")
  missing=[mark for mark in required if mark not in win_native]
  wal=out/"owned-wal.json.n4-owned-wal"
  routes=out/"owned-wal.json.n4-owned-wal.routes"
  tcp_sidecar=out/"owned-wal.json.plan029-defender-tcp"
  if missing or wal.exists() or routes.exists() or tcp_sidecar.exists():
   raise RuntimeError("H1840 signed real nonCI CN owner Stop/OS WAL missing "+
                      repr(missing)+" wal="+str(wal.exists())+
                      " routes="+str(routes.exists())+" defender="+str(tcp_sidecar.exists()))
  for key in ("plan029_private_v3_cn_direct_udp","plan029_private_v3_cn_direct_tcp"):
   if report.get(key,{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
    raise RuntimeError("H1840 nonCI product no actual same-SOURCE Direct DNS/TCP proof "+key)
  report["plan029_private_v3_cn_direct_tcp"]["stop"]="PASS_OWNED_DEFENDER_AND_WAL_ABSENT"
  report["plan029_private_v3_cn_direct_udp"]["stop"]="PASS_NO_WFP_V2_WAL_ABSENT"
  prod=report["plan029_real_product_normal_cn"]
  prod["direct_tunnel_business"]="PASS_SIGNED_PHYSICAL_DIRECT_DNS_TCP_UDP_AND_TUNNEL"
  prod["owned_stop"]="PASS_BOTH_OWNED"
  print("PLAN029_H1840_REAL_PRODUCT_NONCI_EXPLICIT_CN_SPLIT_SIGNED_BOTH_OS_AND_STOP_PASS_SCOPED",flush=True)
 if p029_padding:
  # Actual original Rust authenticated M1 encrypted LINK copied by NPF.
  # Staged/proposed bytes alone cannot count, and live Linux original
  # normal UDP/TCP must have been delivered before both owned Stops.
  win_text=(out/"client.log").read_text(errors="replace")
  rows=re.findall(
   r"WBD_PLAN029_M1_STARTUP_PADDING_NPF_RECEIPT mode=(\w+) copied_records=(\d+) copied_bytes=(\d+) source=original_Rust_M1_authenticated_NPF_accepted",
   win_text)
  if (len(rows)!=1 or rows[0][0]!="flows" or int(rows[0][1])<1 or
      int(rows[0][2])<1 or
      report.get("app_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
      report.get("tcp_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_TCP"):
   raise RuntimeError("H1799 signed original native M1 padding NPF accepted bytes and ordinary two-OS TCP/UDP missing")
  report["plan029_normal_startup_padding"]={
   "source_sha":os.environ["GITHUB_SHA"],
   "mode":"flows","driver_copied_records":int(rows[0][1]),
   "driver_copied_bytes":int(rows[0][2]),
   "record":"SAME_ORIGINAL_RUST_M1_AUTHENTICATED_NPF_PREFIX",
   "ordinary_windows_linux_udp":report["app_duplex"],
   "ordinary_windows_linux_tcp":report["tcp_duplex"],
   "stop":"PASS_BOTH_OWNED"}
  print("PLAN029_H1799_SIGNED_NORMAL_FLOWS_M1_NPF_PAD_AND_BOTH_OS_STOP_PASS_SCOPED",flush=True)
 if os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1":
  # These are actual current-source original TLS/Rust/OS receipts.
  # Do not promote a pure-Tunnel trial to DNS/Direct/D1-D5 evidence.
  win_native=(out/"client.log").read_text(errors="replace")
  required=(
   ("WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=bypass-lan-cn "
    if p029_direct else "WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=all "),
   "WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1",
   "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",
   "WBD_WINDOWS_NATIVE_DISCONNECTED_V1",
  )
  missing=[marker for marker in required if marker not in win_native]
  wal=out/"owned-wal.json.n4-owned-wal"
  routes=out/"owned-wal.json.n4-owned-wal.routes"
  tcp_sidecar=out/"owned-wal.json.plan029-defender-tcp"
  if missing or wal.exists() or routes.exists() or (p029_direct and tcp_sidecar.exists()):
   raise RuntimeError("PLAN029 private V3 signed Tunnel/Stop oracle FAILED "+
                      json.dumps({"missing":missing,"wal":wal.exists(),
                                  "route_sidecar":routes.exists(),"tcp_defender_sidecar":tcp_sidecar.exists()}))
  if p029_direct:
   if p029_tcp53:
    if report.get("plan029_d1_original_app_tcp53",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
     raise RuntimeError("H1794 original app TCP53 two-OS evidence missing at Stop")
    report["plan029_d1_original_app_tcp53"]["stop"]="PASS_BOTH_OWNED"
   if p029_outer1460:
    p=report.get("plan029_d5_real_default_outer1460",{})
    if p.get("source_sha")!=os.environ["GITHUB_SHA"] or p.get("real_linux_auto_inner")!=1389:
     raise RuntimeError("H1791 real default1460 Windows/Linux inner receipt missing at Stop")
    p["stop"]="PASS_BOTH_OWNED"
   if p029_cache:
    if report.get("plan029_d3_cn_native_dns_cache",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
     raise RuntimeError("H1783 cache proof lost before original owner Stop")
    report["plan029_d3_cn_native_dns_cache"]["stop"]="PASS_BOTH_OWNED"
   if p029_p2:
    p2=report.get("plan029_p2_mixed_real",{})
    if p2.get("source_sha")!=os.environ["GITHUB_SHA"] or p2.get("overlap") is not True:
     raise RuntimeError("H1815 true P2 mixed physical/tunnel receipt lost at Stop")
    p2["stop"]="PASS_BOTH_OWNED"
   if p029_multia:
    if report.get("plan029_d3_multia_real",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
     raise RuntimeError("H1807 D3 physical CNAME multi-A receipt missing at Stop")
    report["plan029_d3_multia_real"]["stop"]="PASS_BOTH_OWNED"
   if p029_pressure:
    if report.get("plan029_d3_direct_hard_pressure",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
     raise RuntimeError("H1778 physical capacity result lost at Stop")
    report["plan029_d3_direct_hard_pressure"]["stop"]="PASS_BOTH_OWNED"
   if report.get("plan029_private_v3_cn_direct_tcp",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
    raise RuntimeError("real Direct TCP source-bound physical app evidence missing")
   report["plan029_private_v3_cn_direct_tcp"]["stop"]="PASS_OWNED_DEFENDER_AND_WAL_ABSENT"
   if report.get("plan029_private_v3_cn_direct_udp",{}).get("source_sha")!=os.environ["GITHUB_SHA"]:
    raise RuntimeError("real PLAN029 Direct scenario lost SOURCE-locked Windows/Linux receipt")
   report["plan029_private_v3_cn_direct_udp"]["stop"]="PASS_NO_WFP_V2_WAL_ABSENT"
   print("PLAN029_H1745_REAL_ORIGINAL_GO_RUST_V3_CN_DNS_FAKE_DIRECT_UDP_AND_TUNNEL_OWNED_STOP_PASS",flush=True)
   print("PLAN029_H1762_SIGNED_DIRECT_32K_TCP_PLUS_ONEWAY_TUN_TCP_UDP_EXACT_OWNED_STOP_PASS_SCOPED",flush=True)
  else:
   report["plan029_private_v3_tunnel"]={
    "scope":"ORIGINAL_GO_CREDENTIAL_RUST_V3_ONE_WINTUN_SIGNED_TWO_OS_TUNNEL_ONLY",
    "source_sha":os.environ["GITHUB_SHA"],
    "normal_udp_tcp":report.get("app_duplex"),
    "app_tcp":report.get("tcp_duplex"),
    "os_and_crypto_stop":"PASS_NO_WFP_V2_WAL_ABSENT",
    "direct_dns":"NOT_RUN","tunnel_dns":"NOT_RUN",
    "direct_udp_tcp":"NOT_RUN","D1_D5_P1_P2":"NOT_RUN"
   }
   print("PLAN029_H1743_REAL_ORIGINAL_GO_RUST_V3_TUNNEL_ONLY_SIGNED_STOP_PASS",flush=True)
 if mode=="normal":
  # Same SOURCE actual effective on BOTH owners, not CLI intent.
  expected=1 if outer_repair=="on" else 0
  win_text=(out/"client.log").read_text(errors="replace")
  linux_text=(out/"server.log").read_text(errors="replace")
  if plan028_owned_switch:
   # Two *real* native Rust generations, each OS readback before Stop.
   # The shared Linux server now snapshots each original Rust session
   # before exact per-owner Stop; no CLI flag is accepted as readback.
   win_rows=re.findall(
    r"WBD_WINDOWS_OUTER_REPAIR_EFFECTIVE enabled=(\d+) shadow_limit=(\d+) source=original_rust_owner",
    win_text)
   linux_rows=re.findall(
    r"V4_PUBLIC_M2_OUTER role=server [^\n]*repair_enabled=(\d+) ",
    linux_text)
   win_ok=len(win_rows)==2 and all(int(enabled)==expected and int(limit)>=0 for enabled,limit in win_rows)
   linux_ok=len(linux_rows)==2 and all(int(enabled)==expected for enabled in linux_rows)
   report["original_outer_repair_effective"]={"windows":win_ok,"linux":linux_ok,
     "enabled":expected,"windows_generations":len(win_rows),
     "linux_authenticated_rust_sessions":len(linux_rows),
     "source":"REAL_PER_OWNER_RUST_COUNTERS_BEFORE_NATIVE_STOP"}
  else:
   win_ok=(f"WBD_WINDOWS_OUTER_REPAIR_EFFECTIVE enabled={expected} shadow_limit=" in win_text)
   linux_ok=(f"V4_PUBLIC_M2_OUTER role=server " in linux_text and
             f"repair_enabled={expected} " in linux_text)
   report["original_outer_repair_effective"]={"windows":win_ok,"linux":linux_ok,
     "enabled":expected}
  if not (win_ok and linux_ok):
   raise RuntimeError("real original two-OS outer repair effective mismatch")
 if is_game:
  # Two authenticated Go TLS lane groups; Rust effective rather than CLI.
  expected=1 if outer_repair=="on" else 0
  windows=(out/"client.log").read_text(errors="replace")
  linux=(out/"server.log").read_text(errors="replace")
  if plan028_owned_switch:
   # Exactly two original Rust Game M4 receipts, not CLI intent or one
   # legacy singleton sample; this signed scene has two authenticated
   # source4 generations and the first group's bounded exact Stop.
   wins=re.findall(r"^WBD_WINDOWS_GAME_OUTER_REPAIR_EFFECTIVE enabled=(\d+) source=rust_game_outer$",windows,re.MULTILINE)
   servers=re.findall(r"^.*V4_PUBLIC_GAME_OUTER role=server lanes=%d repair_enabled=(\d+) "%lanes,linux,re.MULTILINE)
   win_ok=len(wins)==2 and all(int(v)==expected for v in wins)
   linux_ok=len(servers)==2 and all(int(v)==expected for v in servers)
   report["original_outer_repair_effective"]={"windows":win_ok,"linux":linux_ok,
     "enabled":expected,"game_lanes":lanes,
     "windows_generations":len(wins),"linux_authenticated_rust_generations":len(servers)}
  else:
   win_ok=(f"WBD_WINDOWS_GAME_OUTER_REPAIR_EFFECTIVE enabled={expected} " in windows)
   linux_ok=(f"V4_PUBLIC_GAME_OUTER role=server lanes={lanes} repair_enabled={expected} " in linux)
   report["original_outer_repair_effective"]={"windows":win_ok,"linux":linux_ok,
     "enabled":expected,"game_lanes":lanes}
  if not (win_ok and linux_ok):
   raise RuntimeError("original Game two-OS Rust outer repair effective mismatch")
 if scenario:
  report["WL_V2"]["owned_stop"]="PASS_BOTH_OWNED"
  report["WL_V2"]["variant"]="rust-native"
 if fixed6:
  # PLAN027 legacy Fixed installation is a true native owner readback,
  # never an extra startup Quality window or retired M2 Receipt.
  linux_log=(out/"server.log").read_text(errors="replace")
  if plan028_owned_switch:
   # The shared server prints protected per-device actual M4 capability,
   # then its native effective owner counters at exact generational Stop.
   installed=(linux_log.count("V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=fixed profile=6")==2 and
              linux_log.count("V4_PUBLIC_MULTI_NATIVE_FEC_EFFECTIVE role=server mode=fixed profile=6 requested=1 applied=1 pending=false")==2)
   win_installed=(out/"client.log").read_text(errors="replace").count(
     "WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=6 revision=1 applied=1")==2
  else:
   installed="V4_PUBLIC_FEC2_READBACK role=server mode=fixed requested=1 applied=1 profile=6 pending=false" in linux_log
   win_installed="NOT_INSTRUMENTED_THIS_REAL_ABI"
  report["fixed_linux_native_installed"]=installed
  report["fixed_windows_native_installed"]=win_installed
  if plan028_owned_switch and not win_installed:raise RuntimeError("signed Windows actual Rust Fixed6 applied both generations missing")
  report["fixed_quality_maturity"]="NOT_MEASURED_SHORT_BURST"
  if not installed:raise RuntimeError("genuine Linux native FixedStream profile6 installed readback missing")
 if plan028_owned_switch and mode=="game4":
  server_text=(out/"server.log").read_text(errors="replace")
  receipts=server_text.count("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=off profile=0")
  report["plan028_game4_off_authenticated_rust_m4_receipts"]=receipts
  if receipts!=2:raise RuntimeError("PLAN028 two real Game4 OFF original protected Rust M4 receipts missing")
 if is_game and game_fixed:
  expected="V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=fixed profile=6"%lanes
  receipts=(out/"server.log").read_text(errors="replace").count(expected)
  if plan028_owned_switch:
   # Exactly two authentically adopted Game M4 cohorts, each native
   # FecCounters() verified before its protected FEC6 receipt.
   report["original_game_fec6_authenticated_group_receipts"]=receipts
   if receipts!=2:
    raise RuntimeError("original Game4 shared Rust FEC6 per-generation count mismatch")
  elif receipts<1:
   raise RuntimeError("actual Game FEC2 protected Linux profile readback missing")
  # H814: genuine 10%-loss native packet copies are required, not merely
  # a green test launcher. Cosmetic copies NEVER create FEC recovery credit.
  client_text=(out/"client.log").read_text(errors="replace")
  copied=re.search(r"WBD_GAME_FEC_NORMAL_OUTER_STOP copied_appearance=(\d+)",client_text)
  copied_count=int(copied.group(1)) if copied else None
  report["windows_game_outer_copied_appearance"]=copied_count if copied_count is not None else "NOT_MEASURED"
  if scenario and scenario.get("scenario_id")=="plan027-d-game2-fec6-normal-outer-1m-25ms-loss10-10s":
   if copied_count is None or copied_count<1:
    raise RuntimeError("H814_REAL_WINDOWS_GAMEFEC_NORMAL_OUTER_ZERO_NPF_COPIES")
   print("H814_REAL_WINDOWS_GAMEFEC_NORMAL_OUTER_NPF_COPIED="+str(copied_count),flush=True)
 report["mode_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_"+mode
 if mode=="normal":report["normal_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE"
 print("WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS "+mode)
except Exception as e:
 if is_game and (out/"client.log").exists():
  # On any fatal path, retain worker vs WAL states even if the normal
  # test-report artifact service is unreachable or the peer already exited.
  snap=(out/"client.log").read_text(errors="replace").splitlines()
  for line in snap:
   if ("M0_PLAN027_GAME_DUE_FAULT first_failure=1" in line or
       "M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line or
       "M0_PLAN027_GAME_NATIVE_STOP_JOIN" in line or
       "M0_PLAN027_NATIVE_STOP_RESULT" in line):
    print("WL_GAME_FATAL_EXACT_SOURCE "+line[-850:],flush=True)
  print("WL_GAME_FATAL_SEPARATE_STOP native="+
   ("JOINED" if any("M0_PLAN027_GAME_NATIVE_STOP_JOIN" in line for line in snap) else
    "NOT_DRAINED" if any("M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line for line in snap) else "NOT_OBSERVED")+
   " wal="+("RESTORED" if any("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" in line for line in snap) else "NOT_RESTORED"),flush=True)
 report["mode_public"]="FAIL_TRUE_PUBLIC_EXECUTION"
 if mode=="normal":report["normal_public"]="FAIL_TRUE_PUBLIC_EXECUTION"
 report["error"]=str(e)[-1100:]
 print("WBD_WL_TRUE_PUBLIC_MODE_FAIL "+mode+": "+str(e),file=sys.stderr)
 raise
finally:
 resource_stop.set()
 if resource_worker is not None:resource_worker.join(timeout=3)
 for p in (wa,la,wt,lt,p029_guest_proc,p029_client_proc,p029_alias_proc,p029_tun_dns_guest,p029_tun_dns_win,p029_dns_blackhole_guest,p029_dns_blackhole_win,p029_d2_tun_guest,p029_d2_tun_win,p029_d2_cn_guest,p029_d2_cn_win,p029_pressure_guest,p029_pressure_win,p029_tcp53_guest,p029_tcp53_win):
  if p is not None and p.poll() is None:p.terminate()
 if p029_direct and (out/"plan029-h1775-owned-route-alias.json").exists():
  try:h1775_owned_cleanup()
  except Exception as exc:
   report["plan029_h1775_owned_cleanup"]="FAIL_OWNED_ROUTE_ALIAS"
   print("PLAN029_H1775_OWNED_CLEANUP_FAILED "+str(exc)[-300:],flush=True)
 if p029_direct and (out/"plan029-h1765-owned-tunnel-dns-alias.txt").exists():
  # Current-generation INTENT is sufficient for safe partial Apply recovery:
  # the preexisting /32 check happened before durable intent was written.
  try:
   receipt=(out/"plan029-h1765-owned-tunnel-dns-alias.txt").read_text()
   if (receipt.startswith(("INTENT 1.1.1.1/32 ","OWNED 1.1.1.1/32 ")) and
       receipt.rstrip().endswith(os.environ["GITHUB_SHA"])):
    try:
     present=wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8)
    except RuntimeError:
     # After genuine Linux owned Stop the original TUN no longer exists.
     # Accept only a stopped original server; do NOT infer success while
     # the owner may still be live and our alias might remain installed.
     if s is None or s.poll() is None:raise
     present=""
    if "1.1.1.1/32" in present:
     wsl("ip","-4","addr","del","1.1.1.1/32","dev","wbdwl4",timeout=8)
    (out/"plan029-h1765-owned-tunnel-dns-alias.txt").unlink()
   else:
    raise RuntimeError("foreign Tunnel DNS alias receipt; preserve OS address")
  except Exception as exc:
   print("PLAN029_H1765_TUNNEL_DNS_ALIAS_CLEANUP_FAILED "+str(exc)[-250:],flush=True)
 if p029_direct and (out/"plan029-h1745-owned-tun-alias.txt").exists():
  # Exact ephemeral TUN alias only: cleanup is idempotent even after the
  # server has already removed its own interface on normal Stop.
  try:
   attached=wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8)
   if p029_tunnel_alias+"/32" in attached:
    wsl("ip","addr","del",p029_tunnel_alias+"/32","dev","wbdwl4",timeout=8)
  except Exception:pass
 stop_windows(w);stop_linux()
 if tls_capture is not None:
  try:end_tls_capture()
  except Exception:pass
 if route_guest:
  try:wsl("rm","-f",route_guest,timeout=10)
  except Exception:pass
 if route_local and route_local.exists():route_local.unlink()
 (out/"tls-firstflight.pcap").unlink(missing_ok=True)
 if s and s.poll() is None:
  try:s.wait(timeout=4)
  except subprocess.TimeoutExpired:s.terminate()
 for log in logs:log.close()
 if mode=="normal" and report.get("lifecycle_blackhole_failure"):
  client=(out/"client.log").read_text(errors="replace") if (out/"client.log").exists() else ""
  server=(out/"server.log").read_text(errors="replace") if (out/"server.log").exists() else ""
  audit={"source":os.environ.get("GITHUB_SHA",""),
    "windows_disconnected":"WBD_WINDOWS_NATIVE_DISCONNECTED_V1" in client,
    "linux_drained":"V4_PUBLIC_NATIVE_STOP_DRAINED role=server" in server,
    "windows_reauthorized":"WBD_WINDOWS_ORIGINAL_GO_TLS_REAUTHORIZE" in client,
    "linux_reauthorized":"V4_PUBLIC_ORIGINAL_GO_TLS_REAUTHORIZE" in server,
    "windows_dead_reconnect_armed":"WBD_WINDOWS_NATIVE_DEAD_RECONNECT_ARMED" in client,
    "linux_dead_reconnect_armed":"V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED" in server,
    "wal_exists":(out/"owned-wal.json.n4-owned-wal").exists(),
    "route_sidecar_exists":(out/"owned-wal.json.n4-owned-wal.routes").exists(),
    "both_owned_stop":"NOT_QUALIFIED_FAIL_PATH"}
  (out/"normal105-stop-audit.json").write_text(json.dumps(audit,indent=2)+"\n")
  print("PLAN027_ORIGINAL_105_STOP_AUDIT "+json.dumps(audit,separators=(",",":")),flush=True)
  report["lifecycle_blackhole_failed_stop_audit"]=audit
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
 if mode=="normal" and os.environ.get("WBD_WL_V2_CPU_AUDIT")=="1":
  try:
   cpu_audit=summarize_windows_cpu(out/"windows-original-go-rust-process-1hz.jsonl",client_log=out/"client.log")
  except Exception as cpu_err:
   cpu_audit={"status":"INCONCLUSIVE_CPU_AUDIT_PARSER",
              "exception_type":type(cpu_err).__name__}
  report["windows_cpu_audit"]=cpu_audit
  (out/"windows-cpu-audit.json").write_text(json.dumps(cpu_audit,indent=2)+"\n")
  print("WBD_WL_WINDOWS_CPU_AUDIT "+json.dumps({
   "status":cpu_audit["status"],"process_cpu_s":cpu_audit.get("process_cpu_s"),
   "top2_threads_cpu_share_lower_bound":cpu_audit.get("top2_threads_cpu_share_lower_bound")}),
   flush=True)
 try:
  report["runtime_observability"]=source_locked_observability(out)
 except Exception as sample_error:
  report["runtime_observability"]={
   "result":"NOT_MEASURED_DIAGNOSTIC_PARSER_ERROR",
   "type":type(sample_error).__name__}
 (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
