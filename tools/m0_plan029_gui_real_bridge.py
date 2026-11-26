"""One same-SOURCE original WinForms button, real Go/Rust child and owned Stop.
Only called by the existing original signed Windows/WSL2 kernel business test.
Never creates a fake network, fake GUI IClientSession or readiness receipt.
"""
import hashlib,json,os,pathlib,shutil,subprocess

def prepare(root,out,client,rust,original_args,rules):
 gui=out/"gui"
 if os.environ.get("WBD_WINXDP_PACKAGED_GUI")=="1":
  gui.mkdir(parents=True,exist_ok=True)
  for name in ("WBD.exe","WBD.exe.config","gui-fields.json","PARAMETERS.json","gui-overlay-source.json"):
   shutil.copy2(out/name,gui/name)
  # Resolve compiler for the test harness only; WBD.exe is from the actual package.
  vswhere=pathlib.Path(os.environ["ProgramFiles(x86)"])/"Microsoft Visual Studio/Installer/vswhere.exe"
  vs=subprocess.check_output([str(vswhere),"-latest","-products","*","-property","installationPath"],text=True).strip()
  csc=str(pathlib.Path(vs)/"MSBuild/Current/Bin/Roslyn/csc.exe")
 else:
  subprocess.run(["pwsh","-NoProfile","-File",
    str(root/"tools"/"m0_plan028_h1640_win_gui_compile.ps1"),
    "-LegacyRoot",str(root/"legacy"),"-OutputDirectory",str(gui),
    "-SourceSHA",os.environ["GITHUB_SHA"],"-Version","plan029-native-gui"],
    cwd=root,check=True,timeout=130)
  csc=(gui/"roslyn-path.txt").read_text().strip()
 fx=pathlib.Path(os.environ.get("ProgramFiles(x86)","C:/Program Files (x86)"))/"Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8"
 refs=["/reference:"+str(fx/(n+".dll")) for n in
   ("mscorlib","System","System.Core","System.Drawing","System.Windows.Forms",
    "System.Web.Extensions","System.ServiceProcess")]
 subprocess.run([csc,"/nologo","/noconfig","/nostdlib+",
   "/langversion:latest","/target:exe","/platform:x64","/utf8output",
   "/codepage:65001","/out:"+str(gui/"GuiReal.exe"),
   "/reference:"+str(gui/"WBD.exe"),*refs,
   str(root/"tools"/("m0_plan029b_b4_real_gui.cs" if os.environ.get("WBD_PLAN029B_B4_GUI_THREE_GEN_SCENE")=="1" else "m0_plan029_gui_real_network_harness.cs"))],
   cwd=root,check=True,timeout=60)
 # Same actual WinXDP DLL and installed original Wintun; no pcap files.
 for src,dst in ((client,gui/"wbd-client.exe"),(rust,gui/"wbd_engine.dll"),
                 (out/"wintun.dll",gui/"wintun.dll")):
  if not src.is_file() or src.stat().st_size<10000:
   raise RuntimeError("missing exact installed original driver/user DLL "+src.name)
  shutil.copy2(src,dst)
  if hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256(dst.read_bytes()).digest():
   raise RuntimeError("GUI linked product binary differs from exact SOURCE")
 overlay=json.loads((gui/"gui-overlay-source.json").read_text(encoding="utf-8-sig"))
 if overlay["source_sha"]!=os.environ["GITHUB_SHA"]:
  raise RuntimeError("GUI/Go/Rust binary SOURCE drift")
 # Preserve the user-visible canonical schema. Never pass opaque CLI flags
 # or a test-only app Ready key through the actual PortableStore profile.
 fields=json.loads((gui/"gui-fields.json").read_text(encoding="utf-8-sig"))
 seed={}
 flags=original_args[1:]
 j=0
 while j<len(flags):
  k=flags[j]
  if not k.startswith("--"):raise RuntimeError("unpaired original CLI argument")
  name=k[2:]
  if name.startswith("cn-domain-direct="):
   # The original Go Bool flag accepts =true/=false, not a separate
   # positional boolean argument. Preserve the exact real user flag.
   key,encoded=name.split("=",1)
   if encoded not in ("true","false"):
    raise RuntimeError("invalid original advanced CN Bool")
   name=key;value=(encoded=="true");j+=1
  elif name in ("native-v4-product","control-stdin","split-enable"):
   value=True;j+=1
  else:
   if j+1>=len(flags):raise RuntimeError("missing original CLI value")
   value=flags[j+1];j+=2
  if name in ("native-v4-product","control-stdin","state-path",
              "fec-mode","fec-parity","mtu"):continue
  if name not in fields:
   raise RuntimeError("original Go client flag absent from real GUI schema "+name)
  if name in ("server-port","source-port","lanes","direct-flow-hard"):
   value=int(value)
  seed[name]=value
 if seed.get("split-enable") is not True or seed.get("route-mode")!="bypass-lan-cn" or seed.get("cn-domain-direct") is not True:
  raise RuntimeError("no explicit GUI CN union")
 data=gui/"data";data.mkdir(parents=True,exist_ok=True)
 owned={"route-key-hex-file":"route-key.hex","tls-ca-pem":"server-ca.pem",
        "china-ip-file":"china-ip.txt","cn-rules-file":"cn-domains.txt"}
 for key,basename in owned.items():
  src=pathlib.Path(seed[key])
  dst=data/basename
  if not src.is_file():raise RuntimeError("missing original owned seed file "+key)
  shutil.copy2(src,dst)
  seed[key]=(str(dst) if key in ("tls-ca-pem","route-key-hex-file")
             else "data/"+basename)
 if (data/"cn-domains.txt").read_text(encoding="ascii").splitlines()!=["cn.example"]:
  raise RuntimeError("test-owned GUI CN domain source drift")
 # Original WinForms user field default MUST be tested, not the CLI --mtu.
 assert "mtu" not in seed
 # Real WinForms selection is the ONLY cold source; don't inject a
 # private Rust enable flag or modify the NPF capture path.
 gui_flows=os.environ.get("WBD_PLAN029_GUI_PADDING_EFFECTIVE_SCENE")=="1"
 seed["startup-padding"]="flows" if gui_flows else "off"
 (data/"gui-seed.json").write_text(json.dumps(seed,separators=(",",":")),encoding="utf-8")
 print("PLAN029_GUI_EXACT_GO_RUST_WINFORMS_WINXDP_WINTUN_PASS",flush=True)
 return [str(gui/"GuiReal.exe"),str(gui),str(data/"gui-seed.json")],gui

def receipt_and_cleanup(gui):
 if os.environ.get("WBD_PLAN029B_B4_GUI_THREE_GEN_SCENE")=="1":
  receipt=gui/"data/plan029b-b4-three-real-receipt.json"
  if not receipt.is_file():raise RuntimeError("B4 genuine three-generation WinForms receipt absent")
  state=json.loads(receipt.read_text())
  if not(state.get("original_gui") is True and
         state.get("generations")==3 and state.get("real_applied")==3 and
         state.get("owned_stop")==3 and state.get("mtu")==1460 and
         state.get("inner")==1389 and
         state.get("cn_dns_physical")==2 and state.get("all_dns_tunnel")==1 and
         state.get("advanced_fakeip") is True and
         state.get("ordinary_real_a") is True and
         state.get("all_real_a") is True and
         state.get("stale_fake_app_attempts")==2 and
         state.get("stale_fake_journal_unchanged") is True):
   raise RuntimeError("B4 signed WinForms three-generation state mismatched")
  for secret in ("route-key.hex","gui-seed.json","server-ca.pem",
                 "profiles.json","active.json","pending.json"):
   (gui/"data"/secret).unlink(missing_ok=True)
  return {"status":"PASS_ORIGINAL_GUI_THREE_GENERATIONS_AFTER_NATIVE_VERIFICATION",
          "real_applied":3,"owned_stop":3,
          "physical_cn_dns":2,"tunnel_all_dns":1,
          "retired_fake_attempts":2,
          "source":os.environ["GITHUB_SHA"]}
 receipt=gui/"data/plan029-gui-real-receipt.json"
 if not receipt.is_file():raise RuntimeError("original WinForms signed Stop receipt absent")
 status=json.loads(receipt.read_text())
 if not(status.get("original_buttons") and status.get("source_locked_go_rust")
        and status.get("outer")==1460 and status.get("inner_os_applied")==1389
        and status.get("real_native_ready") and status.get("owned_stop")):
  raise RuntimeError("GUI actual OS Applied/Stop not qualified")
 expected="flows" if os.environ.get("WBD_PLAN029_GUI_PADDING_EFFECTIVE_SCENE")=="1" else "off"
 if status.get("startup_padding_mode")!=expected:
  raise RuntimeError("GUI padding effective receipt != original saved selector")
 if expected=="flows" and not (
  status.get("padding_npf_copied_records",0)>0 and
  status.get("padding_npf_copied_bytes",0)>0):
  raise RuntimeError("GUI flows has no real Rust M1 NPF copied bytes")
 reconnect=os.environ.get("WBD_PLAN029_GUI_NORMAL_RECONNECT_SCENE")=="1"
 if bool(status.get("normal_reconnect_completed"))!=reconnect:
  raise RuntimeError("real original second GUI Connect receipt missing")
 ttl=os.environ.get("WBD_PLAN029_DNS_TTL_RESTART_SCENE")=="1"
 if bool(status.get("dns_ttl_restart_completed"))!=ttl:
  raise RuntimeError("real physical TTL+reconnect GUI receipt absent or unexpected")
 for secret in ("route-key.hex","gui-seed.json","server-ca.pem",
                "profiles.json","active.json","pending.json"):
  (gui/"data"/secret).unlink(missing_ok=True)
 return {"status":"PASS_SCOPED_ORIGINAL_GUI_SOURCE_LOCKED",
   "outer":1460,"inner_os":1389,"stop":"PASS_BOTH_OWNED",
   "cpu_scope":"GUI_PARENT_ONLY_GO_RUST_NOT_SAMPLED",
   "startup_padding_mode":expected,
   "normal_reconnect_completed":reconnect,
   "dns_ttl_restart_completed":ttl,
   "product_binary_source":os.environ.get("WBD_WL_BINARY_SOURCE",os.environ["GITHUB_SHA"]),
   "fixture_source":os.environ["GITHUB_SHA"],
   "npf_copied_records":status.get("padding_npf_copied_records",0),
   "npf_copied_bytes":status.get("padding_npf_copied_bytes",0)}
