#!/usr/bin/env python3
"""Run two actual public executables, then true Windows/WSL2 UDP, then Stop."""
import os,sys,subprocess,time,json,hashlib,pathlib,re
root=pathlib.Path.cwd();out=root/"result"/"wl-public";out.mkdir(parents=True,exist_ok=True)
report={"source":os.environ["GITHUB_SHA"],"linux_binary_source":"621bc733becbb4bbcf23bc4b10c6150d22b3a073","normal_public":"NOT_RUN","windows_ready":"NOT_RUN","linux_ready":"NOT_RUN","app_duplex":"NOT_RUN","stop":"NOT_RUN","WL_N0":"NOT_RUN","WL_N1":"NOT_RUN","WL_N5":"NOT_RUN"}
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
w=s=wa=la=None;logs=[]
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
 linux.write_bytes(("#!/bin/sh\nset -eu\necho $$ > '"+result+"/linux-server.pid'\nexec env LD_LIBRARY_PATH='"+server+"' '"+server+"/wbd-v4-server' --raw-interface eth0 --local-ip "+peer+" --local-port 443 --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24 --server-name wbd-v4.example.test --route-key-hex "+route+" --username "+user+" --password "+password+" --tunnel-id "+tunnel+" --tls-cert '"+result+"/cert.pem' --tls-key '"+result+"/key.pem' --mode normal\n").encode("utf-8"))
 log=(out/"server.log").open("w");logs.append(log)
 s=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(linux)],stdout=log,stderr=subprocess.STDOUT)
 # Linux server authenticated READY only AFTER the genuine Windows TLS client starts.
 args=[str(cli),"--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443","--source-port","41031","--server-name","wbd-v4.example.test","--route-key-hex",route,"--username",user,"--password",password,"--tunnel-id",tunnel,"--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDWLMAIN","--state-path",str(out/"owned-wal.json"),"--mtu","1400","--lanes","1","--fec-mode","off","--fec-parity","0","--dns-hijack=false","--route-mode","bypass-lan"]
 log=(out/"client.log").open("w");logs.append(log)
 w=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
 ready(out/"client.log","WBD_WINDOWS_CLIENT_READY",w,30)
 ready(out/"server.log","V4_ORIGINAL_GO_SERVER_NATIVE_READY",s,8);report["linux_ready"]="PASS_REAL_AFTER_ORIGINAL_TLS"
 if "WBD_WINDOWS_OS_APPLIED" not in (out/"client.log").read_text():raise RuntimeError("Windows public READY lacks native OS Applied")
 report["windows_ready"]="PASS_TRUE_TLS_RUST_WINTUN_NPCAP_OS_WAL"
 # Two independent real OS UDP generators, never echo, relay, or mock.
 app=out/"app.py"
 app.write_text("import socket,sys,time,json\na,b=sys.argv[1:3];s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((a,45901));s.settimeout(6);seen=set()\nfor i in range(24):s.sendto(('WBD-PUBLIC-NORMAL-%s-%s'%(a,i)).encode(),(b,45901));time.sleep(.04)\ntry:\n while len(seen)<12: data,addr=s.recvfrom(2048);seen.add(data)\nexcept socket.timeout:pass\nprint(json.dumps({'received':len(seen),'src':a}),flush=True)\nsys.exit(0 if len(seen)>=12 else 8)\n")
 llog=(out/"linux-app.log").open("w");logs.append(llog)
 wlog=(out/"windows-app.log").open("w");logs.append(wlog)
 la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),"10.66.0.1","10.66.0.2"],stdout=llog,stderr=subprocess.STDOUT)
 wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2","10.66.0.1"],stdout=wlog,stderr=subprocess.STDOUT)
 wa.wait(timeout=20);la.wait(timeout=20)
 if wa.returncode or la.returncode:raise RuntimeError("actual UDP app duplex failed win="+str(wa.returncode)+" linux="+str(la.returncode))
 report["app_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_UDP"
 stop_windows(w)
 if w.returncode!=0 or "WBD_WINDOWS_NATIVE_DISCONNECTED_V1" not in (out/"client.log").read_text():raise RuntimeError("Windows native owned WAL Stop missing")
 stop_linux();s.wait(timeout=10)
 if s.returncode or "V4_PUBLIC_NATIVE_STOP_DRAINED role=server" not in (out/"server.log").read_text():raise RuntimeError("Linux original Rust Stop missing")
 report["stop"]="PASS_BOTH_OWNED"
 report["normal_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE"
 print("WBD_WL_TRUE_PUBLIC_NORMAL_OFF_WIN_LINUX_DUPLEX_STOP_PASS")
except Exception as e:
 report["normal_public"]="FAIL_TRUE_PUBLIC_EXECUTION";report["error"]=str(e)[-1100:]
 print("WBD_WL_TRUE_PUBLIC_NORMAL_OFF_FAIL: "+str(e),file=sys.stderr)
 raise
finally:
 for p in (wa,la):
  if p is not None and p.poll() is None:p.terminate()
 stop_windows(w);stop_linux()
 if s and s.poll() is None:
  try:s.wait(timeout=4)
  except subprocess.TimeoutExpired:s.terminate()
 for log in logs:log.close()
 (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
