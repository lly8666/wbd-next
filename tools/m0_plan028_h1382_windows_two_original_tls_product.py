#!/usr/bin/env python3
"""H1382: two simultaneous, independently credential-authenticated ORIGINAL
Windows Go TLS443/Rust M4 signed Wintun clients on one genuine Ubuntu WSL2
server, each owning a different server-provisioned /32 and OS WAL.
A Stop must leave B real Win32 UDP and TCP alive. No synthetic data/READY.
"""
import hashlib,json,os,pathlib,re,secrets,signal,socket,subprocess,sys,time
root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
out.mkdir(parents=True,exist_ok=True)
source=os.environ["GITHUB_SHA"]
h1587=os.environ.get("WBD_PLAN028_WIN_MANUAL_AES128_CHA")=="1"
result={"schema_version":1,"source_sha":source,"scene":"H1382_WINDOWS_TWO_REAL_ORIGINAL_TLS_RUST_PRODUCTS",
        "status":"NOT_RUN","windows_two_clients":"NOT_RUN","server_multi_account":"NOT_RUN",
        "app_udp":"NOT_RUN","tcp_echo":"NOT_RUN","A_Stop_B_survival":"NOT_RUN",
        "both_owned_stop":"NOT_RUN","original_synchronous_windows_tunnel":"NOT_RUN"}
def unix(p):
 p=pathlib.Path(p).resolve()
 return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def wsl(*args,timeout=35):
 p=subprocess.run([sys.executable,str(root/"tools"/"m0_wl_windows_bounded_cmd.py"),
                   str(timeout),"wsl.exe","-d","Ubuntu","-u","root","--",*args],
                  capture_output=True,text=True,timeout=timeout+25)
 if p.returncode:
  raise RuntimeError("real WSL2 command "+str(args[:3])+" failed "+(p.stderr or p.stdout)[-450:])
 return p.stdout.strip()
def need(cond,desc):
 if not cond:raise RuntimeError(desc)
def marker(path,text,proc,deadline=75):
 start=time.monotonic()
 while time.monotonic()-start<deadline:
  current=path.read_text(errors="replace") if path.exists() else ""
  if text in current:return
  if proc is not None and proc.poll() is not None:
   raise RuntimeError(text+" original process exited="+str(proc.returncode)+" log="+current[-1100:])
  time.sleep(.2)
 raise RuntimeError(text+" original native unready "+(path.read_text(errors="replace") if path.exists() else "")[-950:])
def count(path):
 if not path.exists():return 0
 values=[]
 for line in path.read_text(errors="replace").splitlines():
  try:
   d=json.loads(line)
   if d.get("phase")=="udp":values.append(int(d["received"]))
  except (ValueError,TypeError,KeyError):pass
 return values[-1] if values else 0
def stop_win(proc):
 if proc and proc.poll() is None:
  try:
   if proc.stdin:proc.stdin.write("stop\n");proc.stdin.flush()
   proc.wait(timeout=22)
  except Exception:
   proc.terminate()
   try:proc.wait(timeout=6)
   except subprocess.TimeoutExpired:proc.kill()
def tcp_echo(lease,peer,label):
 s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(10)
 try:
  s.bind((lease,0));s.connect((peer,45902))
  payload=("WBD_H1382_REAL_TCP_"+label).encode()
  s.sendall(payload)
  received=b""
  while len(received)<len(payload):
   pkt=s.recv(4096)
   if not pkt:break
   received+=pkt
  need(received==payload,"real Win32 TCP echo mismatch "+label)
 finally:s.close()
def inspect_real_win_adapter(alias):
 command=["powershell.exe","-NoProfile","-Command",
          "(Get-NetAdapter -IncludeHidden -Name '"+alias+"' -ErrorAction Stop | "
          "Select-Object Name,InterfaceIndex,InterfaceGuid,Status) | ConvertTo-Json -Compress"]
 p=subprocess.run(command,capture_output=True,text=True,timeout=20)
 need(p.returncode==0,"real signed Windows original adapter absent "+alias+" "+p.stderr[-250:])
 d=json.loads(p.stdout.strip())
 need(d["Name"]==alias and int(d["InterfaceIndex"])>0,"real adapter OS readback "+alias)
 return d
windows={};senders={};logs=[];server=None;echo=None;guest_files=[]
local_secret_files=[]
def write_private_owned(path,data):
 path.write_text(data,encoding="utf-8")
 local_secret_files.append(path)
 return path
try:
 cli=out/"wbd-client-embedded.exe"
 dll=out/"wbd_engine.dll"
 lib=out/"wintun.dll"
 linux=root/"linux-product"/"wbd-v4-server"
 native=root/"linux-product"/"libwbd_engine.so"
 for path in (cli,dll,lib,linux,native):
  need(path.is_file() and path.stat().st_size>10000,"original binary absent "+str(path))
 result["windows_client_sha256"]=hashlib.sha256(cli.read_bytes()).hexdigest()
 result["linux_server_sha256"]=hashlib.sha256(linux.read_bytes()).hexdigest()
 result["windows_rust_sha256"]=hashlib.sha256(dll.read_bytes()).hexdigest()
 result["linux_rust_sha256"]=hashlib.sha256(native.read_bytes()).hexdigest()
 need(os.environ.get("LINUX_BINARY_SRC")==source,"source lock Linux original product differs")
 ip=wsl("ip","-4","-o","addr","show","dev","eth0")
 match=re.search(r"\binet (\d+(?:\.\d+){3})/",ip)
 need(match is not None,"real Linux WSL2 eth0 IPv4 missing")
 peer=match.group(1)
 serverdir=unix(root/"linux-product");resultdir=unix(out)
 route_local=write_private_owned(out/"h1382-route-key.hex",secrets.token_hex(32)+"\n")
 user_local=write_private_owned(out/"h1382-users.json",
    json.dumps({"alice":"native-ci-alice-manual","bob":"native-ci-bob-manual"})+"\n")
 mapping_local=write_private_owned(out/"h1382-manual.json",
    json.dumps({"alice":"10.66.0.2/32","bob":"10.66.0.3/32"})+"\n")
 for sourcefile,guest in ((route_local,"route"),(user_local,"users"),(mapping_local,"leases")):
  path="/run/wbd-plan028-h1382-"+os.environ["GITHUB_RUN_ID"]+"-"+guest
  wsl("install","-m","600",unix(sourcefile),path)
  guest_files.append(path)
 wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
     "-keyout",resultdir+"/h1382-server-key.pem",
     "-out",resultdir+"/h1382-cert.pem",
     "-subj","/CN=wbd-v4.example.test","-addext","subjectAltName=DNS:wbd-v4.example.test")
 server_script=out/"h1382-start-server.sh"
 server_script.write_bytes(("#!/bin/sh\nset -eu\n"
  "echo $$ > '"+resultdir+"/h1382-server.pid'\n"
  "exec env LD_LIBRARY_PATH='"+serverdir+"' '"+serverdir+"/wbd-v4-server'"
  " --raw-interface eth0 --local-ip "+peer+" --local-port 443"
  " --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24"
  " --server-name wbd-v4.example.test --route-key-hex-file '"+guest_files[0]+"'"
  " --users-file '"+guest_files[1]+"' --manual-client-leases-file '"+guest_files[2]+"'"
  " --tls-cert '"+resultdir+"/h1382-cert.pem'"
  " --tls-key '"+resultdir+"/h1382-server-key.pem'"
  " --mode normal --peer-persona windows11 --outer-repair on\n").encode("utf-8"))
 f=(out/"h1382-server.log").open("w");logs.append(f)
 server=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(server_script)],stdout=f,stderr=subprocess.STDOUT)
 marker(out/"h1382-server.log","V4_PUBLIC_MULTI_SERVER_READY role=server port=443",server,45)
 result["server_multi_account"]="SERVER_READY_ORIGINAL_GO_RUST_SHARED_TUN"
 echoapp=out/"h1382-true-echo-linux.py"
 echoapp.write_text("""import socket,select,sys,time,pathlib,json
u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);u.bind(("10.66.0.1",45901))
t=socket.socket(socket.AF_INET,socket.SOCK_STREAM);t.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
t.bind(("10.66.0.1",45902));t.listen(8)
owner=pathlib.Path(sys.argv[1])
targets={"A":"10.66.0.2","B":"10.66.0.3"}
reverse_sent={"A":0,"B":0}
next_send=time.monotonic()
while True:
 now=time.monotonic()
 if now>=next_send:
  for label,lease in targets.items():
   if not (owner/("h1382-client-"+label+"-started.flag")).is_file():continue
   payload=("WBD_H1382_REAL_UDP_REVERSE_%s_%d"%(label,reverse_sent[label])).encode()
   try:
    u.sendto(payload,(lease,45901))
    reverse_sent[label]+=1
    if reverse_sent[label] in (1,16,64):
     print(json.dumps({"event":"real_kernel_reverse_udp_sent","label":label,"count":reverse_sent[label]}),flush=True)
   except OSError:
    pass
  next_send=now+.09
 readable,_,_=select.select([u,t],[],[],.08)
 for s in readable:
  if s is u:
   data,addr=u.recvfrom(4096)
   if data.startswith(b"WBD_H1382_REAL_UDP_"):u.sendto(data,addr)
  else:
   c,addr=t.accept();c.settimeout(5)
   try:
    data=c.recv(4096)
    if data.startswith(b"WBD_H1382_REAL_TCP_"):c.sendall(data)
   finally:c.close()
""",encoding="utf-8")
 f=(out/"h1382-echo-linux.log").open("w");logs.append(f)
 echo=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",unix(echoapp),resultdir],stdout=f,stderr=subprocess.STDOUT)
 sender=out/"h1382-true-udp-windows.py"
 sender.write_text("""import json,socket,sys,time,pathlib
local,remote,label,stop=sys.argv[1:5];sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.settimeout(.25)
deadline=time.monotonic()+60
while True:
 try:sock.bind((local,45901));break
 except OSError:
  if time.monotonic()>deadline:raise
  time.sleep(.15)
sent=0;received=0;start=time.monotonic();last=start;last_route_error=start-2.
while not pathlib.Path(stop).exists() and time.monotonic()-start<150:
 msg=("WBD_H1382_REAL_UDP_%s_%d"%(label,sent)).encode()
 try:
  sock.sendto(msg,(remote,45901));sent+=1
 except OSError as e:
  # Keep a genuine app socket alive while original authenticated Windows
  # product installs the OS /32 and route; never invent a sent packet.
  if time.monotonic()-last_route_error>1.:
   print(json.dumps({"phase":"kernel_route_not_ready","label":label,"winerror":getattr(e,"winerror",None)}),flush=True)
   last_route_error=time.monotonic()
 try:
  data,src=sock.recvfrom(4096)
  if data==msg and src[0]==remote:received+=1
 except socket.timeout:pass
 if time.monotonic()-last>=.5:
  print(json.dumps({"phase":"udp","label":label,"sent":sent,"received":received,"kernel_socket":True}),flush=True)
  last=time.monotonic()
 time.sleep(.08)
print(json.dumps({"phase":"final","label":label,"sent":sent,"received":received,"kernel_socket":True}),flush=True)
sock.close()
""",encoding="utf-8")
 config={
 "A":{"user":"alice","password":"native-ci-alice-manual","lease":"10.66.0.2/32","ip":"10.66.0.2",
      "alias":"WBDWLCLIENTA","port":41031,"tunnel":"102030405060708090a0b0c0d0e0f001",
      "installation":"445566778899aabbccddeeff00112233"},
 "B":{"user":"bob","password":"native-ci-bob-manual","lease":"10.66.0.3/32","ip":"10.66.0.3",
      "alias":"WBDWLCLIENTB","port":41032,"tunnel":"102030405060708090a0b0c0d0e0f002",
      "installation":"445566778899aabbccddeeff00112244"}}
 result["window_client_owners"]={}
 if h1587:result["h1587_client_native_cipher_readback"]={}
 for label in ("A","B"):
  a=config[label]
  wal=out/(a["alias"]+"-owned.json")
  args=[str(cli),"--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443",
      "--source-port",str(a["port"]),"--server-name","wbd-v4.example.test",
      "--route-key-hex-file",str(route_local),"--tls-ca-pem",str(out/"h1382-cert.pem"),
      "--username",a["user"],"--password",a["password"],"--tunnel-id",a["tunnel"],
      "--installation-id",a["installation"],"--lease4",a["lease"],"--adapter",a["alias"],
      "--state-path",str(wal),"--lanes","1","--fec-mode","off",
      "--fec.mode","off","--route-mode","bypass-lan","--outer-repair","on"]
  if h1587:args+=["--record-cipher",
                 "aes-128-gcm" if label=="A" else "chacha20-poly1305"]
  log=(out/("h1382-client-"+label+".log")).open("w");logs.append(log)
  windows[label]=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
  (out/("h1382-client-"+label+"-started.flag")).touch()
  print("H1382_REAL_ORIGINAL_WINDOWS_PRODUCT_PROCESS_STARTED "+label,flush=True)
  log=(out/("h1382-app-"+label+".log")).open("w");logs.append(log)
  senders[label]=subprocess.Popen([sys.executable,str(sender),a["ip"],"10.66.0.1",label,str(out/("h1382-stopapp-"+label+".flag"))],stdout=log,stderr=subprocess.STDOUT)
  marker(out/("h1382-client-"+label+".log"),"WBD_WINDOWS_CLIENT_READY",windows[label],80)
  if h1587:
   cid=2 if label=="A" else 1
   verified="WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION mode=normal auto_lease=false lease="+a["lease"]+" cipher="+str(cid)+" source=original_TLS_Rust_snapshot"
   need(verified in (out/("h1382-client-"+label+".log")).read_text(errors="replace"),
        "H1587 exact Windows protected TLS/Rust AEAD or explicit manual /32 not applied "+label)
   result["h1587_client_native_cipher_readback"][label]=cid
   print("H1587_REAL_WINDOWS_CLIENT_MANUAL_AEAD_APPLIED label="+label+" cipher="+str(cid)+" lease="+a["lease"],flush=True)
  result["window_client_owners"][label]=inspect_real_win_adapter(a["alias"])
  tcp_echo(a["ip"],"10.66.0.1",label+"-INITIAL")
  print("H1382_REAL_WINDOWS_ACCOUNT_AUTHENTICATED_READY_AND_TCP "+label,flush=True)
 marker(out/"h1382-server.log","V4_PUBLIC_MULTI_SESSION_READY role=server",server,10)
 need((out/"h1382-server.log").read_text(errors="replace").count("V4_PUBLIC_MULTI_SESSION_READY role=server")>=2,
      "second original protected independent account not admitted on shared server")
 if h1587:
  server_log=(out/"h1382-server.log").read_text(errors="replace")
  for cipher in (1,2):
   need("V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=off profile=0 cipher="+str(cipher) in server_log,
        "H1587 Linux shared server did not install per-client Rust cipher "+str(cipher))
  result["h1587_server_per_client_cipher_ids"]=[1,2]
  print("H1587_REAL_LINUX_SERVER_PER_CLIENT_CHACHA_AES128_RUST_M4_PASS",flush=True)
 ainfo=result["window_client_owners"]["A"];binfo=result["window_client_owners"]["B"]
 need(str(ainfo["InterfaceGuid"])!=str(binfo["InterfaceGuid"]) and ainfo["InterfaceIndex"]!=binfo["InterfaceIndex"],
      "two aliases are not two actual OS Wintun devices")
 start=time.monotonic()
 while time.monotonic()-start<15:
  if count(out/"h1382-app-A.log")>=8 and count(out/"h1382-app-B.log")>=8:break
  need(all(p.poll() is None for p in windows.values()),"original product client quit before full dual packet")
  time.sleep(.3)
 need(count(out/"h1382-app-A.log")>=8 and count(out/"h1382-app-B.log")>=8,
      "two original Windows authenticated Wintun genuine UDP paths not simultaneously positive")
 result["windows_two_clients"]="REAL_TWO_SIGNED_WINTUN_ORIGINAL_TLS443_RUST_READY"
 result["app_udp"]="PASS_ACTUAL_TWO_WINDOWS_KERNEL_UDP_EACH_LEASE"
 before=count(out/"h1382-app-B.log")
 (out/"h1382-stopapp-A.flag").touch()
 senders["A"].wait(timeout=8)
 stop_win(windows["A"])
 need(windows["A"].poll() is not None,"A exact stop did not exit")
 alog=(out/"h1382-client-A.log").read_text(errors="replace")
 need("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1" in alog,
      "A Stop did not actually finish its native Rust and WAL restore")
 need(windows["B"].poll() is None,"B original Windows product unexpectedly stopped with A")
 tcp_echo(config["B"]["ip"],"10.66.0.1","B-AFTER-A-STOP")
 for _ in range(60):
  after=count(out/"h1382-app-B.log")
  if after-before>=5:break
  need(windows["B"].poll() is None,"B died during A owned recovery")
  time.sleep(.2)
 need(after-before>=5,"actual Windows B UDP did not continue after A exact Stop")
 result["A_Stop_B_survival"]={"result":"PASS_ORIGINAL_B_KERNEL_UDP_TCP_AFTER_A_STOP","B_native_udp_rx_increment":after-before,
                            "A_os_rust_WAL_stop":True}
 result["tcp_echo"]="PASS_REAL_WINDOWS_TCP_ECHO_A_B_AND_B_AFTER_A_STOP"
 (out/"h1382-stopapp-B.flag").touch()
 senders["B"].wait(timeout=8)
 stop_win(windows["B"])
 blog=(out/"h1382-client-B.log").read_text(errors="replace")
 need("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1" in blog,
      "B original native Stop missing")
 pid=(out/"h1382-server.pid").read_text().strip()
 need(pid.isdigit(),"real original shared server PID missing")
 wsl("kill","-TERM",pid,timeout=12)
 server.wait(timeout=25)
 sl=(out/"h1382-server.log").read_text(errors="replace")
 need("V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" in sl,"original shared server Rust TUN not drained")
 need(sl.count("V4_PUBLIC_MULTI_SESSION_READY role=server")>=2,"original server two protected accounts missing")
 result["both_owned_stop"]="PASS_TWO_WINDOWS_RUST_WAL_AND_ONE_SHARED_LINUX_TUN"
 result["original_synchronous_windows_tunnel"]="PASS_TWO_AUTHENTICATED_ORIGINAL_PRODUCTS_BOTH_TRUE_OS"
 result["status"]="PASS_SCOPED_WINDOWS_TWO_REAL_SIGNED_WINTUN_ORIGINAL_TLS443_RUST_M4"
 if h1587:
  need(result["h1587_client_native_cipher_readback"]=={"A":2,"B":1}
       and result["h1587_server_per_client_cipher_ids"]==[1,2]
       and result["app_udp"]=="PASS_ACTUAL_TWO_WINDOWS_KERNEL_UDP_EACH_LEASE"
       and result["tcp_echo"]=="PASS_REAL_WINDOWS_TCP_ECHO_A_B_AND_B_AFTER_A_STOP"
       and result["both_owned_stop"]=="PASS_TWO_WINDOWS_RUST_WAL_AND_ONE_SHARED_LINUX_TUN",
       "H1587 exact two per-client AEADs and owned Stop lost before PASS")
  print("H1587_WINDOWS_A_AES128_B_CHACHA_MANUAL_TWO_SIGNED_WINTUN_UDP_TCP_STOP_PASS_SCOPED",flush=True)
 print("M0_PLAN028_H1382_TWO_ORIGINAL_WINDOWS_GO_TLS_RUST_SIGNED_WINTUN_A_STOP_B_STILL_UDP_TCP_PASS",flush=True)
except Exception as error:
 result["status"]="FAIL_OR_NOT_RUN"
 result["first_failure"]=str(error)[-1300:]
 print("M0_PLAN028_H1382_FIRST_REAL_FAILURE "+str(error)[-900:],file=sys.stderr,flush=True)
 raise
finally:
 for label in ("A","B"):
  (out/("h1382-stopapp-"+label+".flag")).touch()
  (out/("h1382-client-"+label+"-started.flag")).unlink(missing_ok=True)
  if label in senders:
   try:
    if senders[label].poll() is None:senders[label].terminate();senders[label].wait(timeout=5)
   except Exception:pass
 for label,proc in windows.items():
  stop_win(proc)
 if server is not None and server.poll() is None:
  pidfile=out/"h1382-server.pid"
  if pidfile.exists() and pidfile.read_text().strip().isdigit():
   try:wsl("kill","-TERM",pidfile.read_text().strip(),timeout=9)
   except Exception:pass
  try:server.wait(timeout=7)
  except subprocess.TimeoutExpired:server.terminate()
 if echo is not None and echo.poll() is None:
  echo.terminate()
  try:echo.wait(timeout=5)
  except subprocess.TimeoutExpired:echo.kill()
 for f in logs:
  try:f.close()
  except Exception:pass
 for guest in guest_files:
  try:wsl("rm","-f",guest,timeout=8)
  except Exception:pass
 for file in local_secret_files:
  file.unlink(missing_ok=True)
 (out/"h1382-server-key.pem").unlink(missing_ok=True)
 # An original OS WAL is never silently deleted: the actual product Stop
 # must remove it, else retain it as raw evidence and report hard failure.
 for alias in ("WBDWLCLIENTA","WBDWLCLIENTB"):
  base=out/(alias+"-owned.json")
  paths=[pathlib.Path(str(base)+".n4-owned-wal"),
         pathlib.Path(str(base)+".n4-owned-wal.routes")]
  result["original_WAL_remaining_"+alias]=[str(x.name) for x in paths if x.exists()]
 if result["status"].startswith("PASS"):
  need(all(not result["original_WAL_remaining_"+x] for x in ("WBDWLCLIENTA","WBDWLCLIENTB")),
       "actual Windows owned WAL remains after both products stopped")
 (out/"h1382-dual-report.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
 (out/"normal-report.json").write_text(json.dumps({
  "source":source,"mode":"normal","mode_public":result["status"],
  "app_duplex":result["app_udp"],"tcp_duplex":result["tcp_echo"],
  "windows_ready":result["windows_two_clients"],"stop":result["both_owned_stop"],
  "plan028_dual_real_windows":result},indent=2)+"\n",encoding="utf-8")
