#!/usr/bin/env python3
"""Run actual original-TLS Windows and Linux native public UDP/TCP, then Stop."""
import os,sys,subprocess,time,json,hashlib,pathlib,re,threading,faulthandler,atexit,secrets
from m0_wl_native_resource_sampler import sample_windows_original_process
from m0_wl_windows_cpu_audit import summarize_windows_cpu
from m0_wl_mode_runtime_report import source_locked_observability,summarize_auto_udp_progress,native_auto_true_applied_snapshots
from m0_wl_native_mtu_contract import configured_native_test_mtu,native_outer_choice,verified_native_windows_inner_mtu,verified_native_windows_two_generation_inner_mtus
from m0_wl_n0_drop_delta import latest_counter, measured_delta
from m0_wl_impairment_profile import get_profile
from m0_wl_lock_profile import parse_native_lock_profile
from m0_wl_plan027_linux_tun_fq import fq_delta
from m0_wl_plan027_linux_tun_link import link_delta,tun_queue_identity
root=pathlib.Path.cwd();out=root/"result"/"wl-public";out.mkdir(parents=True,exist_ok=True)
mode=os.environ.get("WBD_WL_PUBLIC_MODE","normal")
# The signed 4×5 Game matrix validates its FEC suffix before booting WSL2;
# derive this from the selected original mode BEFORE parsing the case.
game_fixed=mode.endswith("-fec")
configured_mtu=configured_native_test_mtu()
native_outer=native_outer_choice(os.environ.get('WBD_WL_NATIVE_OUTER_MTU_REQUEST','legacy1400'))
plan028_owned_switch=os.environ.get('WBD_PLAN028_WSL_OWNED_SWITCH','0')=='1'
plan028_owned_mtu_only=os.environ.get('WBD_PLAN028_WSL_OWNED_MTU_ONLY','0')=='1'
# One new SOURCE-locked real signed Wintun NativeOwner scene. H1743
# pure Tunnel remains a separate immutable qualification record.
p029_direct=os.environ.get("WBD_PLAN029_V3_DIRECT_SCENE")=="1"
p029_p1_policy=os.environ.get("WBD_PLAN029_P1_POLICY_ABBA_SCENE")=="1"
p029_p1_cn=os.environ.get("WBD_PLAN029_P1_POLICY_CN_ARM")=="1"
if p029_p1_policy and not (
    os.environ.get("GITHUB_ACTIONS")=="true" and
    os.environ.get("WBD_PLAN029_P1_AB_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("WBD_WL_V2_SCENARIO")=="scenarios/plan029-p1-normal-50m-25ms0-60s.json" and
    os.environ.get("WBD_WL_PUBLIC_MODE","normal")=="normal" and not p029_direct):
 raise RuntimeError("H1934 original signed same-Rust V3 policy ABBA only")
if p029_p1_cn and not p029_p1_policy:
 raise RuntimeError("H1934 CN policy arm without scoped signed test")
# H1840 tests the REAL user-selected cold split with all private CI trial
# switches off in the launched original Go process. One source, one signed
# Wintun and one Rust owner; no simulated GUI or routing Applied receipt.
p029_product=os.environ.get("WBD_PLAN029_PRODUCT_SPLIT_SCENE")=="1"
p029b_b0=os.environ.get("WBD_PLAN029B_B0_DNS_SCENE")=="1"
p029b_b2=os.environ.get("WBD_PLAN029B_B2_ORDINARY_SCENE")=="1"
p029b_b3=os.environ.get("WBD_PLAN029B_B3_IPV6_SCENE")=="1"
p029b_b4=os.environ.get("WBD_PLAN029B_B4_GUI_THREE_GEN_SCENE")=="1"
p029b_b5=os.environ.get("WBD_PLAN029B_B5_SAMEVM_SCENE")=="1"
p029_gui=os.environ.get("WBD_PLAN029_GUI_REAL_SCENE")=="1"
p029_gui_padding=os.environ.get("WBD_PLAN029_GUI_PADDING_EFFECTIVE_SCENE")=="1"
p029_gui_reconnect=os.environ.get("WBD_PLAN029_GUI_NORMAL_RECONNECT_SCENE")=="1"
p029_boot_tc=os.environ.get("WBD_PLAN029_BOOTSTRAP_TC_SCENE")=="1"
p029_three_case=os.environ.get("WBD_PLAN029_THREE_CASE","none")
if p029_three_case not in ("none","gui_reconnect","domain_reconnect","dns_ttl_restart"):
 raise RuntimeError("unknown bounded PLAN029 ordinary scene")
p029_boot_reconnect=p029_three_case=="domain_reconnect"
p030_managed=os.environ.get("WBD_PLAN030_MANAGED_COMBO")=="1"
if p030_managed and not p029_boot_reconnect:raise RuntimeError("PLAN030 requires original domain reconnect scene")
p029_dns_ttl=p029_three_case=="dns_ttl_restart"
p029_server_rx_diag=os.environ.get("WBD_PLAN029_SERVER_RX_DIAG")=="1"
if p029_server_rx_diag and not (p029_gui_reconnect and p029_three_case=="gui_reconnect"):
 raise RuntimeError("H2070 raw server observer only on one real GUI reconnect scene")
if p029_boot_tc and not (p029_product and p029_direct and (not p029_gui or p029_boot_reconnect) and mode=="normal" and native_outer=="default1460"):
 raise RuntimeError("real same-endpoint bootstrap requires original Normal CN default1460")
if p029_gui and not ((p029_product and p029_direct or p029b_b4) and mode=="normal" and native_outer=="default1460"):
 raise RuntimeError("true GUI original signed CN default1460 needed")
if p029_gui_padding and not (
    p029_gui and not p029_boot_tc and p029_direct and p029_product and
    native_outer=="default1460" and mode=="normal"):
 raise RuntimeError("H2059 GUI flows requires only original nonCI CN/1460 GUI; no private trial")
if p029_gui_reconnect and not (
    p029_gui and (not p029_boot_tc or p029_boot_reconnect) and not p029_gui_padding and
    p029_product and p029_direct and mode=="normal" and
    native_outer=="default1460"):
 raise RuntimeError("H2061 only ordinary original WinForms GUI normal Stop and fresh Connect")
if p029_boot_reconnect and not(p029_boot_tc and p029_gui_reconnect and p029_gui):
 raise RuntimeError("domain TC reconnect requires original GUI and two generations")
if p029_dns_ttl and not(p029_gui and p029_gui_reconnect and not p029_boot_tc):
 raise RuntimeError("TTL FakeIP restart requires original GUI and no physical bootstrap listener")
p029_ipv6=os.environ.get("WBD_PLAN029_D4_IPV6_SCENE")=="1"
ipv6_probe_before=None
ipv6_probe_active=None
p029_tunnel_alias="203.0.113.77"
p029_converse_cn4="198.19.254.2"
p029_tcp53=os.environ.get("WBD_PLAN029_APP_TCP53_SCENE")=="1"
p029_cdn=os.environ.get("WBD_PLAN029_SHARED_CDN_SCENE")=="1"
p029_padding=os.environ.get("WBD_PLAN029_STARTUP_PADDING_SCENE")=="1"
p029b_game2_cn=os.environ.get("WBD_PLAN029B_GAME2_CN_SCENE")=="1"
p029b_game_case=os.environ.get("WBD_PLAN029B_GAME_MATRIX_CASE","")
p029b_game_padding=os.environ.get("WBD_PLAN029B_GAME_PADDING_MODE","")
p029b_game_policy=p029b_game_case.removesuffix("_fixed")
if p029b_game_case and not (
    p029b_game_policy in ("off","all","lan","ordinary","advanced") and
    p029b_game_case==(p029b_game_policy+("_fixed" if game_fixed else "")) and
    os.environ.get("WBD_PLAN029B_GAME_MATRIX_SCENE")=="1" and
    mode in ("game2","game4","game2-fec","game4-fec") and
    os.environ.get("GITHUB_ACTIONS")=="true" and
    not p029b_game2_cn):
 raise RuntimeError("PLAN029B Game matrix exact signed source/mode/case required")
if p029b_game_case.endswith("_fixed") and not game_fixed:
 raise RuntimeError("PLAN029B Game fixed split arm lacks original FEC")
if p029b_game_case and game_fixed and not p029b_game_case.endswith("_fixed"):
 raise RuntimeError("PLAN029B Game off-only arm must retain original FEC off")
if p029b_game_padding and not (
    p029b_game_padding in ("off","tls","flows") and
    p029b_game_policy=="all" and
    os.environ.get("WBD_PLAN029B_GAME_MATRIX_SCENE")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and
    mode in ("game2","game4-fec")):
 raise RuntimeError("Game-padding source-locked all-Tunnel cold scene required")
p029_game4_cn=(os.environ.get("WBD_PLAN029_GAME4_CN_SCENE")=="1" or p029b_game2_cn or
               p029b_game_policy=="advanced")
p029_outer1460=os.environ.get("WBD_PLAN029_REAL_DEFAULT_OUTER1460")=="1"
p029_cache=os.environ.get("WBD_PLAN029_DNS_CACHE_SCENE")=="1"
p029_pressure=os.environ.get("WBD_PLAN029_DIRECT_PRESSURE")=="1"
p029_multia=os.environ.get("WBD_PLAN029_D3_MULTIA_SCENE")=="1"
p029_p2=os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")=="1"
p029_udp_rtt=os.environ.get("WBD_PLAN029_DIRECT_UDP_RTT_SCENE")=="1"
if p029_udp_rtt and not (p029_direct and not p029_p2 and mode=="normal" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true"):
 raise RuntimeError("H1999 only original signed Normal Direct UDP RTT")
p029_abba=os.environ.get("WBD_PLAN029_P2_ABBA_SCENE")=="1"
p029_tcp128=os.environ.get("WBD_PLAN029_TCP128_SCENE")=="1"
p029_tcp128_control=os.environ.get("WBD_PLAN029_TCP128_CONTROL_SCENE")=="1"
p029_sustain=os.environ.get("WBD_PLAN029_P2_SUSTAIN_SCENE")=="1"
p029_highrate=os.environ.get("WBD_PLAN029_P2_HIGH_RATE_SCENE")=="1"
p029_longrate=os.environ.get("WBD_PLAN029_P2_LONG_RATE_SCENE")=="1"
p029_smalltcp=os.environ.get("WBD_PLAN029_P2_SMALL_TCP_SCENE")=="1"
# H2030: all referenced p029_* flags must exist BEFORE evaluating Game4.
# This scene is exclusive; it never silently admits Normal trial mode.
if p029_game4_cn and not ((
    mode in ("game2","game4","game2-fec","game4-fec")
    if p029b_game_case else
    (mode=="game2" if p029b_game2_cn else mode=="game4")) and not (
    p029_direct or p029_padding or p029_product or p029_p2 or
    p029_p1_policy or p029_tcp53 or p029_cdn or p029_cache or
    p029_pressure)):
 raise RuntimeError("H2030 only signed Game4 off four-lane CN split with owned Stop")
if p029_game4_cn:
 print("PLAN029_H2030_GAME4_CN_EXCLUSIVE_REAL_FOUR_LANE_SCENE_ARMED",flush=True)
if p029_smalltcp and not (
    p029_p2 and p029_direct and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal" and
    not (p029_sustain or p029_abba or p029_tcp128 or
         p029_tcp128_control or (p029_highrate and not p029_longrate))):
 raise RuntimeError("H1931 small kernel TCP may join only a signed long P2 owner")
if p029_longrate and not (p029_highrate and p029_p2 and p029_direct and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal" and
    not (p029_sustain or p029_abba or p029_tcp128 or p029_tcp128_control)):
 raise RuntimeError("H1903 long 2GiB/1.5GiB physical-vs-Direct only in original signed Normal")
if p029_highrate and not (p029_p2 and p029_direct and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal" and
    not (p029_sustain or p029_abba or p029_tcp128 or p029_tcp128_control)):
 raise RuntimeError("H1898 only original signed Normal 500/700Mb/s load")
if p029_sustain and not (p029_p2 and p029_direct and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal" and
    not p029_abba and not p029_tcp128 and not p029_tcp128_control):
 raise RuntimeError("H1896 only one original signed Normal 4MiB+30s Direct source, never 128/ABBA")
if p029_tcp128_control and not (p029_tcp128 and p029_p2 and not p029_abba and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal"):
 raise RuntimeError("H1894 original signed exact SOURCE pre128 CPU/UDP comparison required")
if p029_tcp128 and not (p029_p2 and p029_direct and not p029_abba and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true" and mode=="normal"):
 raise RuntimeError("H1892 only original signed Normal 4MiB P2 with 128 true Wintun TCP")
if p029_abba and not (p029_p2 and p029_direct and
    os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1" and
    os.environ.get("GITHUB_ACTIONS")=="true"):
 raise RuntimeError("H1884 only signed private Normal 4MiB Direct A-B-B-A allowed")
if p029_ipv6 and (not p029_product or not p029_direct or mode!="normal"):
 raise RuntimeError("D4 real IPv6 route observation requires one explicit signed Normal CN product scene")
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
if p029_cdn and not (p029_direct and p029_tcp53 and mode=="normal" and
    not (p029_padding or p029_pressure or p029_multia or p029_udp_rtt or p029_p2)):
 raise RuntimeError("H2010 shared overseas CDN requires one signed Normal Direct+TCP53 scene")
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
# B0 uses the original Normal/Tunnel owner with zero business Direct. It is
# one source-locked genuine Windows+WSL2 run, never a private V3 trial or
# a second DNS thread/adapter in the shipping product.
if p029b_b3 and (mode!="normal" or p029b_b0 or p029b_b2 or
    p029_direct or p029_product or p029_gui or p029_ipv6 or
    p029_padding or p029_p2 or p029_p1_policy or p029_game4_cn or
    p029_boot_tc or p029_tcp53 or p029_cdn or p029_cache or
    p029_pressure or native_outer!="default1460" or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0" or
    os.environ.get("GITHUB_ACTIONS")!="true"):
 raise RuntimeError("029B B3 requires one exclusive real Normal/off 1460 signed IPv6/IPv4 mixed original owner")
if p029b_b0 and (mode!="normal" or p029_direct or p029_product or
    p029_gui or p029_padding or p029_p2 or p029_p1_policy or
    p029_game4_cn or p029_boot_tc or p029_tcp53 or p029_cdn or
    p029_cache or p029_pressure or p029_ipv6 or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0" or
    os.environ.get("GITHUB_ACTIONS")!="true"):
 raise RuntimeError("029B B0 only one signed original Normal/off DNS A/AAAA UDP/TCP53")
# H2090 B2: one original signed Normal CN ordinary/real-A trial. No
# FakeIP, no old advanced/H2077 scenario, no legacy private trial.
if p029b_b2 and (mode!="normal" or native_outer!="default1460" or
    p029b_b0 or p029_product or p029_direct or p029_gui or p029_p2 or
    p029_p1_policy or p029_game4_cn or p029_padding or p029_tcp53 or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0" or
    os.environ.get("GITHUB_ACTIONS")!="true"):
 raise RuntimeError("029B B2 ordinary CN requires exclusive signed real Normal V3")
if p029b_b5 and not (
    mode=="normal" and native_outer=="default1460" and
    os.environ.get("GITHUB_ACTIONS")=="true" and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="0" and
    os.environ.get("WBD_WL_V2_SCENARIO")==
     "scenarios/plan027a-h941-normal-1460-10m-25ms-loss0-60s.json" and
    os.environ.get("WBD_PLAN029B_B5_ARM") in ("off","requested_all") and
    not (p029b_b4 or p029b_b0 or p029b_b2 or p029b_b3 or p029_direct or
         p029_gui or p029_product or p029_game4_cn or p029_p1_policy or
         p029_padding or p029_p2)):
 raise RuntimeError("B5 exact source-pinned one Normal 10Mbps V3 all/off arm required")
if p029b_b4 and not (
    mode=="normal" and native_outer=="default1460" and
    p029_gui and not (p029_direct or p029_product or p029_gui_reconnect or
    p029b_b0 or p029b_b2 or p029b_b3 or p029_padding or
    p029_p1_policy or p029_game4_cn or p029_cdn or p029_tcp53 or
    p029_boot_tc or p029_dns_ttl or p029_p2 or plan028_owned_switch) and
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="0" and
    os.environ.get("GITHUB_ACTIONS")=="true"):
 raise RuntimeError("B4 requires exclusive original WinForms three-generation Normal 1460 signed scene")
if plan028_owned_mtu_only and (not plan028_owned_switch or mode!='normal' or native_outer!='default1460'):
 raise RuntimeError('PLAN028 true physical MTU-only original Windows WSL2 test requires owned source IP, Normal Off and default1460')
if plan028_owned_switch and (mode not in ('normal','fixed','auto','game4','game4-fec') or native_outer!='default1460'):
 raise RuntimeError('PLAN028 owned source4 switch supports Normal off, fixed6, auto, Game4 off or Game4FEC6 with default1460 only')
if mode not in ("normal","fixed","auto","game2","game4","game2-fec","game4-fec","auto-revision","auto-adaptive"):
 raise RuntimeError("unknown exact native Windows public mode "+mode)
fixed6=mode=="fixed"
is_game=mode.startswith("game")
# The early game_fixed binding remains unchanged through the cold mode.
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
report={"source":os.environ["GITHUB_SHA"],"linux_binary_source":os.environ["LINUX_BINARY_SRC"],
 "product_binary_source":os.environ.get("WBD_WL_BINARY_SOURCE",os.environ["GITHUB_SHA"]),
 "fixture_source":os.environ["GITHUB_SHA"],"mode":mode,
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

def h1775_owned_apply(host,peer,target=None,tag="h1775"):
 if target is None:target=p029_converse_cn4
 if tag not in ("h1775","h2010"):raise RuntimeError("unknown owned test route")
 side=out/("plan029-"+tag+"-owned-route-alias.json")
 if side.exists():raise RuntimeError(tag+" foreign owner file")
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

def h1775_owned_cleanup(target=None,tag="h1775"):
 if target is None:target=p029_converse_cn4
 if tag not in ("h1775","h2010"):raise RuntimeError("unknown owned test cleanup")
 side=out/("plan029-"+tag+"-owned-route-alias.json")
 if not side.exists():return
 owner=json.loads(side.read_text())
 if (owner.get("source_sha")!=os.environ["GITHUB_SHA"] or
     owner.get("target")!=target or
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
  try:p.stdin.write("stop\n");p.stdin.flush();p.wait(timeout=40 if p029_gui else 15)
  except Exception:
   p.terminate()
   try:p.wait(timeout=4)
   except subprocess.TimeoutExpired:p.kill()
w=s=wa=la=wt=lt=tls_capture=p029_alias_proc=p029_guest_proc=p029_client_proc=p029_tun_dns_guest=p029_tun_dns_win=p029_dns_blackhole_guest=p029_dns_blackhole_win=p029_d2_tun_guest=p029_d2_tun_win=p029_d2_cn_guest=p029_d2_cn_win=p029_pressure_guest=p029_pressure_win=p029_tcp53_guest=p029_tcp53_win=None;logs=[]
p029_cdn_guest=p029_cdn_win=None
p029_boot_tc_guest=p029_ttl_guest=p029b_guest=None
padding_capture=None
padding_capture_source=None
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
def end_padding_capture():
 if padding_capture is None:return
 pid=out/"plan029-padding-capture.pid"
 if pid.exists() and pid.read_text().strip().isdigit():
  try:wsl("kill","-INT",pid.read_text().strip(),timeout=10)
  except Exception:pass
 try:padding_capture.wait(timeout=10)
 except subprocess.TimeoutExpired:
  padding_capture.terminate()
  try:padding_capture.wait(timeout=4)
  except subprocess.TimeoutExpired:padding_capture.kill()
resource_stop=threading.Event();resource_worker=None
try:
 cli=out/"wbd-client-embedded.exe";lib=out/"wbd_engine.dll"
 for f in (cli,lib,out/"wintun.dll",root/"linux-product"/"wbd-v4-server",root/"linux-product"/"libwbd_engine.so"):
  if not f.exists() or f.stat().st_size<10000:raise RuntimeError("missing actual public native binary "+str(f))
 gui_root=None
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
 # H2070 single-run, existing read-only native Rust M4 observer. It emits
 # per *actual* source port, before tuple/AEAD. No unfiltered RX fallback,
 # no debug packet capture or new product thread in release defaults.
 server_rx_diag=" WBD_PLAN028_EXTERNAL_STAGE_DIAG=1" if p029_server_rx_diag else ""
 if p030_managed:
  managed_cfg={"listen":peer+":443","server-name":"wbd-v4.example.test","raw-interface":"eth0",
      "tun-name":"wbdwl4","tun-ipv4":"10.66.0.1/24","lease-pool":"10.66.0.128/25",
      "route-key-hex-file":route_guest,"tls-cert":result+"/cert.pem","tls-key":result+"/key.pem",
      "users":[{"username":user,"password":password}],"manual-client-leases":{user:"10.66.0.2/32"},
      "peer-persona":"windows11"}
  cfg_local=out/"plan030-private-config.json"
  cfg_local.write_text(json.dumps(managed_cfg),encoding="utf-8")
  cfg_guest="/run/wbd-plan030-"+os.environ["GITHUB_RUN_ID"]+".json"
  sock_guest="/run/wbd-plan030-"+os.environ["GITHUB_RUN_ID"]+".sock"
  wsl("install","-m","600",unix(cfg_local),cfg_guest)
  cfg_local.unlink()
  linux.write_bytes(("#!/bin/sh\nset -eu\necho $$ > '"+result+"/linux-server.pid'\nexec env LD_LIBRARY_PATH='"+server+"' '"+server+"/wbd-v4-server' --manage serve --config '"+cfg_guest+"' --socket '"+sock_guest+"'\n").encode("utf-8"))
 else:
  linux.write_bytes(("#!/bin/sh\nset -eu\necho $ > '"+result+"/linux-server.pid'\nexec env LD_LIBRARY_PATH='"+server+"' WBD_WL_RX_TUPLE_DIAG=1"+egress_diag+server_rx_diag+" '"+server+"/wbd-v4-server' --raw-interface eth0 --local-ip "+peer+" --local-port 443 --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24 --server-name wbd-v4.example.test --route-key-hex-file "+route_guest+" --username "+user+" --password "+password+" --tunnel-id "+tunnel+(" --manual-client-lease4 10.66.0.2/32" if (plan028_owned_switch or p029_gui_reconnect or p029b_b4) else "")+" --tls-cert '"+result+"/cert.pem' --tls-key '"+result+"/key.pem' --mode "+server_mode+" --outer-repair "+outer_repair+peer_persona+(" --outer-mtu "+str(configured_mtu) if native_outer in ("1280","1460","1500") else "")+"\n").encode("utf-8"))
 log=(out/"server.log").open("w");logs.append(log)
 s=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(linux)],stdout=log,stderr=subprocess.STDOUT)
 if p029_direct or p029_p1_policy or p029_game4_cn or p029b_b2 or p029b_b4 or p029b_game_case:
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
  if p029_p1_policy:
   # H1937 proved CGNAT 100.64/10 is folded into LAN: only 8
   # effective CN rows despite 4096 /32 inputs. Test-only non-LAN
   # 11.42.0.0/19 avoids this normalization and guest 203.0.113.77.
   cn=out/"plan029-h1934-cn4096.txt"
   cn.write_text("".join("11.42."+str(i//128)+"."+str((i%128)*2)+"/32\n"
                         for i in range(4096)),encoding="ascii")
   rules.write_text("".join("cn%05d.bench.invalid\n"%i
                                 for i in range(8192)),encoding="ascii")
  else:
   rules.write_text("cn.example\n",encoding="ascii")
  os.environ["WBD_PLAN029_CN_RULES_FILE"]=str(rules)
  (out/"plan029-h1775-cn-one32.txt").write_text(p029_converse_cn4+"/32\n",encoding="ascii")
 if p029b_b4:
  # Owner-only test /32 first: the WSL original TUN is created by TLS
  # server lifecycle and must not be awaited before the real client starts.
  host=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host:raise RuntimeError("B4 signed physical Windows source unknown")
  h1775_owned_apply(host,peer,target=p029_tunnel_alias,tag="h2010")
 # One genuine WSL2 eth0 physical packet capture starts before the
 # original Normal Go TLS/NPF client. It stays active through actual
 # Tunnel TCP/UDP apps, then is stopped at owned Stop; only bounded
 # length histogram is published, never raw authenticated ciphertext.
 if p029_padding:
  padding_capture_source=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not padding_capture_source:
   raise RuntimeError("H2019 original Windows Npcap physical source missing")
  wsl("sh","-c",
      "command -v tcpdump >/dev/null || (apt-get update -qq && apt-get install -y -qq tcpdump)",
      timeout=120)
  pid=out/"plan029-padding-capture.pid"
  if pid.exists():raise RuntimeError("foreign H2019 pcap owner PID")
  capture_script=out/"plan029-padding-capture.sh"
  capture_script.write_bytes(("#!/bin/sh\nset -eu\necho "+chr(36)*2+
    " > '"+result+"/plan029-padding-capture.pid'\nexec tcpdump -i eth0 -n -s 4096 -U -w '"+
    result+"/plan029-padding-real-eth0.pcap' 'tcp dst port 443 and src host "+
    padding_capture_source+" and dst host "+peer+"'\n").encode("ascii"))
  cf=(out/"plan029-padding-capture-stderr.log").open("w");logs.append(cf)
  padding_capture=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "sh",unix(capture_script)],stdout=subprocess.DEVNULL,stderr=cf)
  for _ in range(100):
   cf.flush()
   if padding_capture.poll() is not None:
    raise RuntimeError("H2019 original physical tcpdump did not start: "+
      (out/"plan029-padding-capture-stderr.log").read_text(errors="replace")[-450:])
   if "listening on eth0" in (out/"plan029-padding-capture-stderr.log").read_text(errors="replace"):
    break
   time.sleep(.1)
  else:raise RuntimeError("H2019 physical tcpdump missing real kernel listener")
  report["plan029_padding_pcap_start"]={
   "source":"ORIGINAL_WSL2_ETH0_REAL_PHYSICAL_TCP443",
   "host":padding_capture_source,"server":peer,
   "raw_pcap_retained":False}
  print("PLAN029_H2019_REAL_PHYSICAL_TUNNEL_PADDING_TCPDUMP_READY",flush=True)
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
 game_route={"off":"bypass-lan-cn","all":"all","lan":"bypass-lan",
             "ordinary":"bypass-lan-cn","advanced":"bypass-lan-cn"}.get(p029b_game_policy)
 args=[str(cli),"--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443","--source-port","41031","--server-name","wbd-v4.example.test","--route-key-hex-file",str(route_local),"--tls-ca-pem",str(out/"cert.pem"),"--username",user,"--password",password,"--tunnel-id",tunnel,"--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDWLMAIN","--state-path",str(out/"owned-wal.json"),"--mtu",str(configured_mtu),"--lanes",str(lanes),"--fec-mode",("fixed" if fixed6 else "off"),
  "--fec-parity",("4" if fixed6 else "0"),"--fec.mode",client_fec,
  "--fec.profile",("maximum" if fixed6 or game_fixed else "strong"),"--route-mode",(game_route if p029b_game_case else "bypass-lan-cn" if p029_direct or p029_p1_cn or p029_game4_cn or p029b_b2 or p029b_b4 else "all" if p029_v3 or p029b_b5 else "bypass-lan"),"--outer-repair",outer_repair]
 if p029b_game_padding:
  # Signed original Game V5 selector; never bypass Go saved cold config.
  args.extend(["--startup-padding",p029b_game_padding])
 if p029_padding:
  # Same default Normal original Windows Wintun pipeline; no new test
  # sender or artificial packet shape. Only the selected mode changes.
  args.extend(["--startup-padding","flows"])
 if p029b_game_case:
  # Real original Go 2/4 TLS -> Rust V4 cold; all/off keeps public DNS,
  # but must not allocate any business Direct/FakeIP or stale route.
  args.extend(["--dns.direct",peer,"--dns.tunnel","10.66.0.1"])
  if p029b_game_policy!="off":
   args.append("--split-enable")
  if p029b_game_policy in ("ordinary","advanced"):
   args.extend(["--cn-domain-direct="+("false" if p029b_game_policy=="ordinary" else "true"),
                "--cn-rules-file",str(rules),
                "--china-ip-file",str(out/"plan029-h1775-cn-one32.txt")])
 if p029b_b5:
  # User-facing V3 cold config on BOTH legs. No private CI trial bit.
  # The only requested difference is split=false vs split=true while
  # route-mode=all; neither may allocate business Direct or Fake writer.
  args.extend(["--dns.direct",peer,"--dns.tunnel","10.66.0.1"])
  if os.environ["WBD_PLAN029B_B5_ARM"]=="requested_all":
   args.extend(["--split-enable","--cn-domain-direct=false"])
 if p029b_b4:
  args.extend(["--split-enable","--cn-domain-direct=true",
               "--cn-rules-file",str(rules),
               "--dns.direct",peer,"--dns.tunnel","10.66.0.1",
               "--china-ip-file",str(out/"plan029-h1775-cn-one32.txt")])
 if p029b_b2:
  # New fresh CN default: direct DNS for CN only, but real overseas A
  # business must remain Tunnel without an advanced FakeIP journal.
  args.extend(["--split-enable","--cn-domain-direct=false",
               "--cn-rules-file",str(rules),
               "--dns.direct",peer,"--dns.tunnel","10.66.0.1",
               "--china-ip-file",str(out/"plan029-h1775-cn-one32.txt")])
 if p029b_b0:
  # The actual Linux original server TUN address is the sole dns.tunnel
  # endpoint; no CN/direct resolver or system fallback is added.
  args.extend(["--dns.tunnel","10.66.0.1"])
 if p029_direct or p029_p1_cn or (p029_game4_cn and not p029b_game_case):
  # The exact Linux guest is the ONLY direct resolver for this controlled
  # scene; it also hosts an independent real physical business UDP socket.
  args.extend(["--dns.direct",peer,"--dns.tunnel","1.1.1.1",
               "--china-ip-file",str(out/("plan029-h1934-cn4096.txt" if p029_p1_cn else "plan029-h1775-cn-one32.txt"))])
 if p029_game4_cn and not p029b_game_case:
  # 029B fresh profiles default ordinary CN (real A). This original
  # Game4 signed FakeIP test intentionally selects the ONE advanced
  # cn-domain-direct option, exactly as its physical Direct oracle needs.
  # No legacy missing-key/default-true assumption and no test-only Rust bit.
  args.extend(["--split-enable","--cn-domain-direct=true",
               "--cn-rules-file",str(rules)])
 if p029_product:
  # Same Next-Connect CLI fields a portable user enters in real WinForms,
  # not WBD_PLAN029_CN_RULES_FILE or any GITHUB_ACTIONS test switch.
  # Retain the historical H2077 signed GUI FakeIP scenario explicitly:
  # fresh PLAN029B profiles otherwise default ordinary CN real-A mode.
  args.extend(["--split-enable","--cn-domain-direct=true",
               "--cn-rules-file",str(rules)])
 if p029_pressure:
  args.extend(["--direct-flow-hard","8"])
 if p029_tcp128:
  # Own the real TCP NAT hard cap across 128 simultaneous sockets PLUS
  # existing 32KiB P2 probe and bounded 60s FIN grace. Never widen
  # a production default; source-locked CI-only argument.
  args.extend(["--direct-flow-hard","256"])
 if p029_boot_tc:
  # Real server host DNS resolved before Go/Rust TLS, no Go package mocks.
  args[args.index("--server-ip")+1]="vpn.edge.cn.example"
  host4=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host4:raise RuntimeError("no verified physical host source")
  bootlog=(out/"plan029-bootstrap-tc-guest.log").open("w");logs.append(bootlog)
  p029_boot_tc_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
   "python3","-u",unix(root/"tools"/"m0_plan029_bootstrap_tc_real_guest.py"),
   peer,host4,*(["reconnect"] if p029_boot_reconnect else [])],
   stdout=bootlog,stderr=subprocess.STDOUT)
  ready(out/"plan029-bootstrap-tc-guest.log","PLAN029_BOOTSTRAP_TC_GUEST_READY",p029_boot_tc_guest,12)
 if p029_dns_ttl:
  host4=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host4:raise RuntimeError("H2063 physical host source missing")
  ttl_log=(out/"plan029-h2063-ttl-guest.log").open("w");logs.append(ttl_log)
  p029_ttl_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3","-u",unix(root/"tools"/"m0_plan029_h2063_ttl_real_guest.py"),
    peer,host4],stdout=ttl_log,stderr=subprocess.STDOUT)
  ready(out/"plan029-h2063-ttl-guest.log","PLAN029_H2063_TTL_GUEST_READY",p029_ttl_guest,12)
 if native_outer=="default1460":
  # Prove both real defaults by OMITTING their explicit user MTU flags.
  index=args.index("--mtu");del args[index:index+2]
 # Exact original user CLI before adapting transport to the real
 # WinForms process argv. H1845 must check the frozen user config,
 # never mistake GUI parent process flags for the Go child flags.
 product_user_args=tuple(args)
 if p029_gui:
  from m0_plan029_gui_real_bridge import prepare
  args,gui_root=prepare(root,out,cli,lib,args,rules)
  report["original_client_entry"]="WINFORMS_REAL_BUTTON_GO_RUST"
 log=(out/"client.log").open("w");logs.append(log)
 # Original signed Windows Go passes one cold diagnostic bit to Rust only
 # for this P2 scene; ordinary users never incur socket-byte telemetry.
 client_env=os.environ.copy()
 if p029b_b4:
  client_env["WBD_PLAN029B_B4_GUEST_READY_PATH"]=str(gui_root/"data/plan029b-b4-guest-ready.flag")
 if p029_p2:client_env["WBD_PLAN029_P2_RELAY_DIAG"]="1"
 if p029_abba:client_env["WBD_PLAN029_P2_ABBA_SCENE"]="1"
 if p029_tcp128:client_env["WBD_PLAN029_TCP128_SCENE"]="1"
 if p029_product:
  client_env["GITHUB_ACTIONS"]="false"
  client_env["WBD_PLAN029_NATIVE_V3_TRIAL"]="0"
  client_env.pop("WBD_PLAN029_CN_RULES_FILE",None)
  # H1845: freeze exact user-facing CLI *and* child environment before
  # spawning the genuine original Go product. Only then can real signed
  # OS Applied/Ready and Stop prove non-CI activation. No trial fallback.
  if (product_user_args.count("--split-enable")!=1 or product_user_args.count("--cn-domain-direct=true")!=1 or
      product_user_args.count("--cn-rules-file")!=1 or
      client_env.get("GITHUB_ACTIONS")!="false" or
      client_env.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0" or
      "WBD_PLAN029_CN_RULES_FILE" in client_env):
   raise RuntimeError("H1845 explicit product CN source still depends on private trial")
  owned_cn=pathlib.Path(product_user_args[product_user_args.index("--cn-rules-file")+1])
  if (not owned_cn.is_absolute() or
      owned_cn.resolve()!=rules.resolve() or
      # Python Windows write_text translates LF into CRLF. Compare the
      # canonical one-line domain rule, not platform-dependent bytes.
      owned_cn.read_text(encoding="ascii").splitlines()!=["cn.example"]):
   raise RuntimeError("H1845 user CN source snapshot missing or changed")
  print("PLAN029_H1845_NONCI_PRODUCT_CLI_SOURCE_AND_ENV_EXACT_PRESTART",flush=True)
 if p029_ipv6:
  # Snapshot before the exact original Go/Wintun four-stage owned Apply.
  # A read-only route probe must NOT add an IPv6 route or WFP rule.
  from m0_plan029_d4_ipv6_route_probe import snapshot as ipv6_route_snapshot
  ipv6_probe_before=ipv6_route_snapshot("pre_original_os_apply")
 w=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,
                    text=True,env=client_env)
 game_cold_stage("COLD_CLIENT_SPAWNED")
 if not p029_gui:
  resource_worker=threading.Thread(
   target=sample_windows_original_process,
   args=(w,out/"windows-original-go-rust-process-1hz.jsonl",resource_stop),
   daemon=True)
  resource_worker.start()
 else:
  report["windows_process_cpu"]="NOT_SAMPLED_GO_RUST_GUI_PARENT_ONLY"
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
runtime_cap=float(sys.argv[6]) if len(sys.argv)>6 else 0.
deadline=start+max(65. if os.environ.get("WBD_PLAN028_WSL_OWNED_SWITCH")=="1" else 35.,hold+9.,runtime_cap)
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
 if p029_p1_policy or p029_game4_cn or p029b_b4 or p029b_game_case:
  if p029_alias_proc is None or p029_alias_proc.wait(timeout=25)!=0 or not (
      out/"plan029-h1745-owned-tun-alias.txt").is_file():
   raise RuntimeError("H1934 Linux original public TUN alias never applied")
 linux_app4=p029_tunnel_alias if p029_direct or p029_p1_policy or p029_game4_cn or p029b_b2 or p029b_b4 or p029b_game_case else "10.66.0.1"
 # Keep the same two real kernel app generators alive while the human GUI
 # performs its ordinary first Disconnect / second Connect. The second
 # generation is separately proved by later CN Direct and Tunnel apps.
 app_runtime=["2",".09","220"] if p029b_b4 else ["2",".09","130"] if p029_gui_reconnect else []
 la=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3",unix(app),linux_app4,"10.66.0.2",unix(done),*app_runtime],stdout=llog,stderr=subprocess.STDOUT)
 wa=subprocess.Popen([sys.executable,str(app),"10.66.0.2",linux_app4,str(done),*app_runtime],stdout=wlog,stderr=subprocess.STDOUT)
 if p029b_b4:
  if p029_alias_proc is None or p029_alias_proc.wait(timeout=25)!=0 or not (
      out/"plan029-h1745-owned-tun-alias.txt").is_file():
   raise RuntimeError("B4 genuine server TUN public alias not ready")
  guest_log=(out/"plan029b-b4-guest.log").open("w");logs.append(guest_log)
  p029b_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3","-u",unix(root/"tools/m0_plan029b_b4_guest.py"),
    peer,host,"10.66.0.2","10.66.0.1",p029_tunnel_alias],
    stdout=guest_log,stderr=subprocess.STDOUT)
  ready(out/"plan029b-b4-guest.log","PLAN029B_B4_LINUX_DNS_AND_BUSINESS_READY",
        p029b_guest,25)
  (gui_root/"data/plan029b-b4-guest-ready.flag").write_text(os.environ["GITHUB_SHA"])

 # This READY remains owned exclusively by the unmodified real product.
 game_cold_stage("COLD_READY_WAIT")
 if p029b_b4:
  # The first signed GUI Stop authorizes removal of the test-owned
  # physical /32 before allowing ordinary CN to use the same real A.
  ready(out/"client.log","PLAN029B_B4_PHASE1_STOP_ROUTE_RELEASE_REQUIRED",w,110)
  h1775_owned_cleanup(target=p029_tunnel_alias,tag="h2010")
  if (out/"plan029-h2010-owned-route-alias.json").exists():
   raise RuntimeError("B4 physical /32 present before ordinary CN")
  w.stdin.write("continue-ordinary\n");w.stdin.flush()
  ready(out/"client.log","PLAN029B_B4_THIRD_APPLIED",w,145)
 else:
  ready(out/"client.log",
       ("PLAN029_H2061_NORMAL_GUI_RECONNECT_SECOND_APPLIED"
        if p029_gui_reconnect else "WBD_WINDOWS_CLIENT_READY"),
       w,110 if p029_gui_reconnect else 30)
 if p030_managed:
  # GUI second native READY may precede server-side authenticated B
  # publication; wait only for the real management snapshot, not a marker.
  until=time.monotonic()+12
  while True:
   snapshot=json.loads(wsl("env","LD_LIBRARY_PATH="+server,server+"/wbd-v4-server","--manage","clients","--json","--socket",sock_guest))
   rows=snapshot["clients"]
   if len(rows)==1 and rows[0]["remote_port"]==41032 and rows[0]["state"]=="online":break
   if time.monotonic()>=until:raise RuntimeError("PLAN030 second actual native owner not published "+repr(snapshot))
   time.sleep(.2)
  row=rows[0]
  assert row["account"]==user and row["tunnel_ip"].split("/")[0]=="10.66.0.2" and row["mode"]=="normal" and row["lanes"]==1,row
  assert row["negotiated_inner_cap"]==1389 and row["session"]!="0000000000000000",row
  report["plan030_actual_second_gui_managed_snapshot"]=snapshot
  (out/"plan030-domain-snapshot.json").write_text(json.dumps(snapshot,indent=2)+"\n")
  print("PLAN030_WINDOWS_DOMAIN_RECONNECT_MANAGED_SNAPSHOT_PASS",flush=True)
 if p029b_b0:
  # A real Windows Winsock application probes the original Wintun lease.
  # Only its two A tickets reach the genuine Linux kernel TUN resolver;
  # both AAAA (UDP/TCP53) MUST be locally answered NOERROR/NODATA.
  guest_path=out/"plan029b-b0-dns-guest.log"
  guest_log=guest_path.open("w");logs.append(guest_log)
  p029b_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3","-u",unix(root/"tools"/"m0_plan029b_b0_dns_guest.py"),
    "10.66.0.1","10.66.0.2"],stdout=guest_log,stderr=subprocess.STDOUT)
  ready(guest_path,"PLAN029B_B0_REAL_LINUX_TUN_DNS_READY",p029b_guest,12)
  win_path=out/"plan029b-b0-dns-windows.log"
  with win_path.open("w") as win_log:
   result=subprocess.run([sys.executable,str(root/"tools"/"m0_plan029b_b0_dns_windows.py"),
      "10.66.0.2","10.66.0.1"],stdout=win_log,stderr=subprocess.STDOUT,
      timeout=55,check=False)
  if result.returncode!=0:
   raise RuntimeError("real Windows Winsock app B0 DNS failed: "+
                      win_path.read_text(errors="replace")[-1300:])
  if p029b_guest.wait(timeout=9)!=0:
   raise RuntimeError("real Linux TUN DNS A-only upstream failed: "+
                      guest_path.read_text(errors="replace")[-1000:])
  def b0_receipt(path,marker):
   rows=[json.loads(line.split(" ",1)[1]) for line in
      path.read_text(errors="replace").splitlines()
      if line.startswith(marker+" ")]
   if len(rows)!=1:raise RuntimeError("missing exact B0 original receipt "+marker)
   return rows[0]
  win_dns=b0_receipt(win_path,"PLAN029B_B0_REAL_WINDOWS_APP_DNS_UDP_TCP_A_AAAA")
  guest_dns=b0_receipt(guest_path,"PLAN029B_B0_REAL_LINUX_TUN_DNS_RECEIPT")
  if (win_dns.get("result")!="PASS_REAL_WIN_WINTUN_UDP_TCP53_A_AAAA" or
      guest_dns.get("result")!="PASS_REAL_TUN_UDP_AND_TCP53_A_ONLY" or
      set(guest_dns.get("upstream_a",{}))!={"udp","tcp"} or
      guest_dns.get("leaked_aaaa")!=0 or
      set(win_dns.get("results",{}))!={"udp_a","udp_aaaa","tcp_aaaa","tcp_a"} or
      [win_dns["results"][k]["result"] for k in
       ("udp_a","udp_aaaa","tcp_aaaa","tcp_a")]!=
      ["REAL_A_TTL2_NOT_FAKEIP","NOERROR_NODATA_LOCAL",
       "NOERROR_NODATA_LOCAL","REAL_A_TTL2_NOT_FAKEIP"]):
   raise RuntimeError("signed 029B B0 app A/AAAA on two real DNS sockets did not match")
  cold=(out/"client.log").read_text(errors="replace")
  if ("WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=0" not in cold or
      "business_split=false" not in cold or
      "cn_domain_fakeip=false" not in cold or
      "WBD_PLAN029B_PUBLIC_DNS_TCP_ONLY_ENABLED_COLD" not in cold or
      "direct_business_nat=0" not in cold or
      "WBD_WINDOWS_OS_APPLIED" not in cold):
   raise RuntimeError("B0 actual original Rust/OS DNS-only resource and Applied missing")
  report["plan029b_b0_real_managed_dns"]={
    "source_sha":os.environ["GITHUB_SHA"],
    "status":"PENDING_GENUINE_BOTH_OWNED_STOP",
    "windows_actual_winsock":win_dns,
    "linux_actual_tun_dns":guest_dns,
    "fakeip_journal":"NO_ADVANCED_WRITER_SOURCE_V2_OFF",
    "direct_business_nat":"ABSENT_RUST_DNS_TCP_ONLY_SOURCE",
    "stop":"NOT_RUN_UNTIL_BOTH_OWNED"}
  print("PLAN029B_B0_REAL_WINDOWS_WSL2_UDP_TCP53_A_FROM_TUN_AAAA_LOCAL_PASS_PRE_STOP",
        flush=True)
 if p029b_b2 or p029b_game_policy=="ordinary":
  if p029_alias_proc is None or p029_alias_proc.wait(timeout=6)!=0 or not (
      out/"plan029-h1745-owned-tun-alias.txt").exists():
   raise RuntimeError("B2 real original Linux TUN overseas public /32 not owned")
  host4=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host4:raise RuntimeError("B2 physical Windows source missing")
  guest_path=out/"plan029b-b2-ordinary-guest.log"
  guest_log=guest_path.open("w");logs.append(guest_log)
  p029b_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3","-u",unix(root/"tools"/"m0_plan029b_b2_cn_guest.py"),
    peer,host4,"10.66.0.2","10.66.0.1",p029_tunnel_alias],
    stdout=guest_log,stderr=subprocess.STDOUT)
  ready(guest_path,"PLAN029B_B2_REAL_LINUX_DNS_AND_TUNNEL_READY",p029b_guest,12)
  win_path=out/"plan029b-b2-ordinary-windows.log"
  with win_path.open("w") as win_log:
   completed=subprocess.run([sys.executable,str(root/"tools"/"m0_plan029b_b2_cn_windows.py"),
      "10.66.0.2",p029_tunnel_alias,"10.66.0.1"],stdout=win_log,
      stderr=subprocess.STDOUT,timeout=65,check=False)
  if completed.returncode!=0:
   raise RuntimeError("B2 original Windows real-A CN app failed: "+
                      win_path.read_text(errors="replace")[-1100:])
  if p029b_guest.wait(timeout=8)!=0:
   raise RuntimeError("B2 independent physical/TUN socket trace failed: "+
                      guest_path.read_text(errors="replace")[-1200:])
  def b2_receipt(path,marker):
   rows=[json.loads(line.split(" ",1)[1]) for line in path.read_text(
     errors="replace").splitlines() if line.startswith(marker+" ")]
   if len(rows)!=1:raise RuntimeError("B2 original app/kernel evidence missing "+marker)
   return rows[0]
  wr=b2_receipt(win_path,"PLAN029B_B2_REAL_WINDOWS_ORDINARY_CN_REAL_A_BOTH_TUNNEL")
  gr=b2_receipt(guest_path,"PLAN029B_B2_REAL_LINUX_CN_PHYSICAL_DNS_AND_BOTH_TUNNEL_DATA")
  if (wr.get("result")!="PASS_ORIGINAL_WIN_WINTUN_REAL_A_CNAME_TTL2_AND_TUNNEL" or
      not wr.get("no_fakeip") or
      gr.get("result")!="PASS_REAL_PHYSICAL_CN_DNS_OVERSEAS_BOTH_TUNNEL" or
      gr.get("physical_business_packets")!=0 or
      wr["events"]["cn"]["real_a"]!=p029_tunnel_alias or
      wr["events"]["global"]["real_a"]!=p029_tunnel_alias or
      set(gr["events"])!={"cn_dns","global_dns","P29B-CN-TUNNEL",
                          "P29B-GLOBAL-TUNNEL"}):
   raise RuntimeError("B2 actual ordinary CN vs same overseas global dual DNS/TUN mismatch")
  cold=(out/"client.log").read_text(errors="replace")
  marker=("WBD_PLAN029B_GAME_V3_COLD_EFFECTIVE lanes="+str(lanes) if
          p029b_game_policy=="ordinary" else
          "WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=2")
  if (marker not in cold or
      "business_split=true cn_domain_fakeip=false" not in cold or
      "WBD_WINDOWS_OS_APPLIED" not in cold):
   raise RuntimeError("B2/Game original Go/Rust ordinary CN effective/OS missing")
  report["plan029b_b2_ordinary_cn_real"]={
   "status":"PENDING_GENUINE_BOTH_OWNED_STOP",
   "source_sha":os.environ["GITHUB_SHA"],
   "real_windows_app":wr,"real_linux_physical_and_tun":gr,
   "fakeip":"NO_FAKE_WRITER_ON_ORDINARY_SOURCE","stop":"NOT_RUN"}

 if p029b_b3:
  # Existing true original TLS/Wintun OS Applied and Linux TUN already
  # qualified by the same Normal owner. One test-only Wintun /128 IPv6.
  guest_path=out/"plan029b-b3-guest.log"
  guest_log=guest_path.open("w");logs.append(guest_log)
  p029b_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
    "python3","-u",unix(root/"tools"/"m0_plan029b_b3_ipv4_guest.py"),
    "10.66.0.1","10.66.0.2"],stdout=guest_log,stderr=subprocess.STDOUT)
  ready(guest_path,"PLAN029B_B3_LINUX_TUN_IPV4_READY",p029b_guest,12)
  win_path=out/"plan029b-b3-windows.log"
  with win_path.open("w") as wf:
   result=subprocess.run([sys.executable,
       str(root/"tools"/"m0_plan029b_b3_ipv6_windows.py"),
       "--execute",str(out)],stdout=wf,stderr=subprocess.STDOUT,timeout=85,check=False)
  if result.returncode:
   raise RuntimeError("B3 real Windows AF_INET6/IPv4 sender route first failure: "+
                      win_path.read_text(errors="replace")[-1100:])
  if p029b_guest.wait(timeout=10):
   raise RuntimeError("B3 true Linux TUN IPv4 echo missing: "+
                      guest_path.read_text(errors="replace")[-950:])
  def b3r(path,marker):
   found=[json.loads(line.split(" ",1)[1]) for line in
          path.read_text(errors="replace").splitlines()
          if line.startswith(marker+" ")]
   if len(found)!=1:raise RuntimeError("B3 exact original kernel receipt missing "+marker)
   return found[0]
  wr=b3r(win_path,"PLAN029B_B3_ORIGINAL_WINDOWS_REAL_IPV6_IPV4")
  gr=b3r(guest_path,"PLAN029B_B3_ORIGINAL_LINUX_TUN_IPV4")
  owned=json.loads((out/"plan029b-b3-owned-ipv6-route.json").read_text())
  if (wr.get("result")!="PASS_PRE_STOP_AF_INET6_WINTUN_ROUTE_AND_IPV4" or
      wr.get("source_sha")!=os.environ["GITHUB_SHA"] or
      wr.get("ipv6_sent")!=16 or wr.get("ipv4_echo")!=12 or
      gr.get("result")!="PASS_REAL_LINUX_IPV4_TUN_MIX" or
      gr.get("unique_echo")!=12 or
      owned.get("cleanup")!="PASS_EXACT_TEST_OWNED_IPV6_ADDRESS_ROUTE_ABSENT" or
      owned.get("source_sha")!=os.environ["GITHUB_SHA"]):
   raise RuntimeError("B3 AF_INET6 source route, IPv4 echo or test-owned Stop cleanup missing")
  report["plan029b_b3_ipv6_actual"]={
   "source_sha":os.environ["GITHUB_SHA"],
   "status":"PENDING_GENUINE_RUST_WINTUN_IPV6_AND_BOTH_OWNED_STOP",
   "win_original_kernel":wr,"linux_original_tun":gr,
   "test_owned_ipv6":owned,"physical_bound_onlink_ipv6":"NOT_PROVEN_BLOCKED",
   "global_ipv6_leak_claim":False,"owned_stop":"NOT_RUN"}
  print("PLAN029B_B3_GENUINE_WINDOWS_KERNEL_AF_INET6_INTERLEAVED_IPV4_PRE_STOP",flush=True)
 if p029_boot_tc:
  if p029_boot_tc_guest.wait(timeout=8)!=0:
   raise RuntimeError("physical same endpoint bootstrap failed: "+(out/"plan029-bootstrap-tc-guest.log").read_text(errors="replace")[-900:])
  recs=[json.loads(v.split(" ",1)[1]) for v in (out/"plan029-bootstrap-tc-guest.log").read_text().splitlines()
        if v.startswith("PLAN029_BOOTSTRAP_TC_GUEST_RECEIPT ")]
  expected=2 if p029_boot_reconnect else 1
  txt=(out/"client.log").read_text(errors="replace")
  if (len(recs)!=expected or not all(
       p["udp_tc"]==1 and p["tcp_a"]==1 and p["physical_host"]==host4
       and p["guest"]==peer and p["ordinal"]==i+1 for i,p in enumerate(recs)) or
      txt.count("WBD_PLAN029_BOOTSTRAP_DNS_SELECTED")<expected or
      txt.count("host=vpn.edge.cn.example")<expected or
      txt.count("resolver4="+peer)<expected or
      txt.count("selected4="+peer)<expected):
   raise RuntimeError("Go physical TC/TCP selected4 in each true cold generation missing")
  report["plan029_physical_bootstrap_tc"]={
   "status":"PASS_REAL_WINDOWS_NPCAP_LINUX_KERNEL_UDP_TC_TCP53",
   "linux_dns":recs[0] if expected==1 else recs,
   "generation_count":expected,"product_binary_source":report["product_binary_source"],
   "tls_sni_unchanged":"wbd-v4.example.test",
   "reconnect":"PASS_TWO_TRUE_COLD_GENERATIONS" if expected==2 else "NOT_RUN",
   "no_cross_dns":True}
  print("PLAN029_REAL_PHYSICAL_BOOTSTRAP_UDP_TC_TCP53_SAME_ENDPOINT_PASS generations="+str(expected),flush=True)
 if p029_dns_ttl:
  if p029_ttl_guest.wait(timeout=8)!=0:
   raise RuntimeError("H2063 real physical TTL DNS guest failed: "+
       (out/"plan029-h2063-ttl-guest.log").read_text(errors="replace")[-900:])
  receipts=[json.loads(v.split(" ",1)[1]) for v in
       (out/"plan029-h2063-ttl-guest.log").read_text().splitlines()
       if v.startswith("PLAN029_H2063_TTL_GUEST_RECEIPT ")]
  phases=re.findall(r"^PLAN029_H2063_TTL_APP_REPLY phase=(\d+) fake4=(198\.18\.\d+\.\d+) txid=(\w+)$",
       (out/"client.log").read_text(errors="replace"),re.MULTILINE)
  if (len(receipts)!=1 or receipts[0].get("count")!=3 or
      receipts[0].get("ttl_s")!=2 or
      [int(v[0]) for v in phases]!=[1,2,3] or
      [v[2] for v in phases]!=["2961","2962","2963"]):
   raise RuntimeError("H2063 real TTL expiration/normal GUI reconnect DNS app/physical three-phase mismatch")
  physical_tuples=[(q.get("source_port"),q["id"]) for q in receipts[0]["queries"]]
  if len(physical_tuples)!=3 or len(set(physical_tuples))!=3:
   raise RuntimeError("H2063 three distinct physical socket+DNS ID transactions absent")
  # App and physical DNS ID namespaces differ; after reconnect Rust can
  # restart its upstream ID counter, so compare unique socket+ID tuples.
  report["plan029_dns_ttl_restart"]={
   "source_sha":os.environ["GITHUB_SHA"],
   "product_binary_source":report["product_binary_source"],
   "status":"PENDING_POST_RECONNECT_DIRECT_BUSINESS_AND_STOP",
   "physical_queries":receipts[0],"app_fakeip_phases":phases,
   "ttl_expiration":"PASS_SECOND_TRUE_PHYSICAL_DNS_QUERY_AFTER_2800MS",
   "normal_restart":"PASS_THIRD_TRUE_PHYSICAL_DNS_QUERY_AFTER_SECOND_OS_APPLIED",
   "post_restart_direct_business":"PENDING","stop":"NOT_RUN"}
  print("PLAN029_H2063_REAL_CN_TTL_EXPIRE_THEN_GUI_RECONNECT_THREE_DNS_PASSES",flush=True)
 if p029_ipv6:
  # Only after the REAL original owner has emitted READY/Applied,
  # and while it is live; no fake receipt supplied by this fixture.
  ipv6_probe_active=ipv6_route_snapshot("active_signed_original_product")
 if p029_product:
  cold_log=(out/"client.log").read_text(errors="replace")
  if ("WBD_PLAN029B_V3_COLD_EFFECTIVE" not in cold_log or
      "cn_domain_fakeip=true" not in cold_log or
      "business_split=true" not in cold_log or
      "readiness=AWAIT_REAL_OS_RUST_RECEIPT" not in cold_log):
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
   "V4_PUBLIC_MIXED_NORMAL_READY role=server" if p030_managed else
   "V4_PUBLIC_MULTI_SESSION_READY role=server" if (plan028_owned_switch or p029_gui_reconnect or p029b_b4) and not is_game else
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
  if p029b_b4:
   receipts=re.findall(
    r"WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=(\d+) applied=(\d+) outer_config=(\d+)",
    winlog)
   if len(receipts)!=3 or any(tuple(map(int,row))!=(1389,1389,1460) for row in receipts):
    raise RuntimeError("B4 three actual Windows Wintun OS MTU receipts absent")
   windows_inner=1389
   report["plan029b_b4_three_original_windows_inner_mtu"]=receipts
  elif plan028_owned_switch or p029_gui_reconnect:
   # Both native OS generations are real. The old single-receipt verifier
   # correctly refuses concatenated logs, but GUI Disconnect->Connect has
   # two independent Go child processes even without PLAN028 MTU mutation.
   # Parse precisely two numeric receipts, each checked against outer MTU.
   try:
    per_gen_inner=verified_native_windows_two_generation_inner_mtus(winlog,configured_mtu)
   except ValueError as exc:
    kind="PLAN028" if plan028_owned_switch else "PLAN029_GUI_RECONNECT"
    raise RuntimeError(kind+" requires exactly two genuine OS MTU receipts") from exc
   windows_inner=per_gen_inner[-1]
   report["plan028_actual_windows_two_generation_os_inner_mtu" if plan028_owned_switch
          else "plan029_actual_windows_two_generation_os_inner_mtu"]=per_gen_inner
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
   elif p029b_b4:
    from m0_wl_public_mss_contract import verified_plan029b_b4_three_gui_child_mss
    budget_and_wire=verified_plan029b_b4_three_gui_child_mss(
     winlog,linux_log,configured_mtu)
    report["plan029b_b4_three_original_syn_synack_mss"]=budget_and_wire
   elif p029_gui_reconnect:
    # H2067: two *different* original WinForms Go child processes both
    # start internal generation=1, but use physical ports 41031 then
    # 41032. The original shared server has two authenticated M4 owners.
    # A singleton one() MSS auditor is not capable of proving this case.
    from m0_wl_public_mss_contract import verified_plan029_gui_two_child_shared_manual_mss
    budget_and_wire=verified_plan029_gui_two_child_shared_manual_mss(
     winlog,linux_log,configured_mtu,managed=p030_managed)
    report["plan029_two_gui_child_real_syn_synack_mss"]=budget_and_wire
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

 if p029b_game_policy=="lan":
  # Original Windows Wintun sends an ACTUAL IPv4 UDP socket to Linux
  # eth0/46117. Rust Direct NAT must produce the real original Windows
  # physical-source address, not only a parsed CIDR or synthetic receipt.
  host_source=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host_source:raise RuntimeError("Game LAN real original host physical source missing")
  name="plan029b-game-lan-guest.log"
  win_name="plan029b-game-lan-windows.log"
  g=(out/name).open("w");logs.append(g)
  proc=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029b_game_lan_probe.py"),
      "guest",peer,host_source,os.environ["GITHUB_SHA"][:16]],
      stdout=g,stderr=subprocess.STDOUT)
  try:
   ready(out/name,"PLAN029B_GAME_REAL_LINUX_PHYSICAL_LAN_READY",proc,15)
   with (out/win_name).open("w") as win_log:
    result=subprocess.run([sys.executable,
      str(root/"tools"/"m0_plan029b_game_lan_probe.py"),
      "windows","10.66.0.2",peer,os.environ["GITHUB_SHA"][:16]],
      stdout=win_log,stderr=subprocess.STDOUT,timeout=38,check=False)
   if result.returncode or proc.wait(timeout=8):
    raise RuntimeError("Game LAN true physical Wintun/eth0 UDP failure "+
      (out/win_name).read_text(errors="replace")[-550:]+" "+
      (out/name).read_text(errors="replace")[-550:])
  finally:
   if proc.poll() is None:proc.terminate()
  def lan_receipt(file,mark):
   events=[json.loads(line.split(" ",1)[1]) for line in
     (out/file).read_text(errors="replace").splitlines()
     if line.startswith(mark+" ")]
   if len(events)!=1:raise RuntimeError("Game LAN missing exact original kernel "+mark)
   return events[0]
  win=lan_receipt(win_name,"PLAN029B_GAME_REAL_WINDOWS_LAN_DIRECT_UDP")
  linux=lan_receipt(name,"PLAN029B_GAME_REAL_LINUX_LAN_DIRECT_UDP")
  if (win.get("result")!="PASS_ORIGINAL_WINTUN_PHYSICAL_LAN_UDP" or
      win.get("src")!="10.66.0.2" or win.get("physical_guest")!=peer or
      linux.get("result")!="PASS_ORIGINAL_LINUX_KERNEL_PHYSICAL_LAN_UDP" or
      linux.get("original_windows_physical")!=host_source or
      linux.get("guest")!=peer):
   raise RuntimeError("Game LAN wrong physical kernel source or peer")
  report["plan029b_game_lan_real"]={
   "source_sha":os.environ["GITHUB_SHA"],"windows":win,"linux":linux,
   "status":"PENDING_GENUINE_BOTH_OWNED_STOP"}
  print("PLAN029B_GAME_REAL_LAN_KERNEL_DIRECT_PRE_STOP",flush=True)

 if p029_game4_cn:
  # H2017: one original four-lane Game4/Go TLS group; Rust GameAdapter
  # remains the Tunnel authority while shared split handles physical DNS
  # and real Direct UDP/TCP via the very same Wintun loan.
  if p029_alias_proc is None or p029_alias_proc.wait(timeout=4)!=0 or not (
      out/"plan029-h1745-owned-tun-alias.txt").exists():
   raise RuntimeError("Game4 CN real Linux Tunnel alias not owned")
  host_source=os.environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
  if not host_source:raise RuntimeError("Game4 CN physical source missing")
  gn="plan029-h2017-game4-physical-udp-dns.log"
  wn="plan029-h2017-game4-app-dns-udp.log"
  gf=(out/gn).open("w");logs.append(gf)
  p029_guest_proc=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1745_guest_dns_direct.py"),
      peer,host_source,"0"],stdout=gf,stderr=subprocess.STDOUT)
  ready(out/gn,"PLAN029_H1745_LINUX_REAL_DNS53_AND_UDP46111_READY",
        p029_guest_proc,12)
  wf=(out/wn).open("w");logs.append(wf)
  p029_client_proc=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h1745_win_client_dns_direct.py"),
      "10.66.0.2",peer],stdout=wf,stderr=subprocess.STDOUT)
  if p029_client_proc.wait(timeout=50)!=0 or p029_guest_proc.wait(timeout=8)!=0:
   raise RuntimeError("Game4 CN physical DNS/FakeIP/Direct UDP app FAIL win="+
      (out/wn).read_text(errors="replace")[-800:]+" guest="+
      (out/gn).read_text(errors="replace")[-800:])
  proof={}
  for who,file,mark in (
   ("windows",wn,"PLAN029_H1745_REAL_WINDOWS_CN_DNS_FAKE_DIRECT_UDP "),
   ("linux",gn,"PLAN029_H1745_REAL_LINUX_GUEST_DIRECT ")):
   vals=[line.split(" ",1)[1] for line in (out/file).read_text().splitlines()
        if line.startswith(mark)]
   if len(vals)!=1:raise RuntimeError("Game4 missing real "+who+" Direct UDP receipt")
   proof[who]=json.loads(vals[0])
  ww,ll=proof["windows"],proof["linux"]
  if not (ww["fake4"].startswith("198.18.") and ww["direct_resolver"]==peer
      and ll["dns"] is True and ll["direct_business"] is True
      and ll["dns_client_physical"]==host_source
      and ll["business_client_physical"]==host_source):
   raise RuntimeError("Game4 CN DNS/physical UDP actual receipt invalid")
  # Reuse exact ordinary native kernel TCP 32KiB + FIN/half-close scene.
  gt="plan029-h2017-game4-physical-tcp.log"
  wt="plan029-h2017-game4-windows-tcp.log"
  gf=(out/gt).open("w");logs.append(gf)
  tcp_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h1760_guest_physical_direct_tcp.py"),
      peer,host_source],stdout=gf,stderr=subprocess.STDOUT)
  try:
   ready(out/gt,"PLAN029_H1760_PHYSICAL_KERNEL_TCP46112_READY",tcp_guest,12)
   wf=(out/wt).open("w");logs.append(wf)
   tcp_win=subprocess.Popen([sys.executable,
       str(root/"tools"/"m0_plan029_h1760_windows_fakeip_direct_tcp.py"),
       "10.66.0.2",ww["fake4"]],stdout=wf,stderr=subprocess.STDOUT)
   try:
    if tcp_win.wait(timeout=25)!=0 or tcp_guest.wait(timeout=8)!=0:
     raise RuntimeError("Game4 CN real TCP half-close FAIL win="+
      (out/wt).read_text(errors="replace")[-650:]+" linux="+
      (out/gt).read_text(errors="replace")[-650:])
   finally:
    if tcp_win.poll() is None:tcp_win.terminate()
  finally:
   if tcp_guest.poll() is None:tcp_guest.terminate()
  tw=[line.split(" ",1)[1] for line in (out/wt).read_text().splitlines()
      if line.startswith("PLAN029_H1760_WINDOWS_FAKEIP_DIRECT_TCP_ECHO ")]
  tl=[line.split(" ",1)[1] for line in (out/gt).read_text().splitlines()
      if line.startswith("PLAN029_H1760_LINUX_PHYSICAL_TCP_ECHO ")]
  if len(tw)!=1 or len(tl)!=1:raise RuntimeError("Game4 CN real 32K TCP receipt missing")
  tw,tl=json.loads(tw[0]),json.loads(tl[0])
  if not (tw["app_bytes_echoed"]==32768 and tw["tcp_half_close"] is True
      and tw["presented_peer"]==ww["fake4"] and
      tl["source_physical"]==host_source and tl["received_bytes"]==32768):
   raise RuntimeError("Game4 CN physical TCP original two kernel legs mismatch")
  report["plan029_game4_cn_real"]={
      "source_sha":os.environ["GITHUB_SHA"],
      "mode":mode,"lanes":lanes,"fec":("fixed" if game_fixed else "off"),
      "normal_tunnel_udp":report["app_duplex"],
      "cn_real_direct_udp":{"windows":ww,"linux":ll},
      "cn_real_direct_tcp":{"windows":tw,"linux":tl},
      "single_wintun":"ORIGINAL_GAME2_OR_GAME4_SIGNED_RUST_NATIVE",
      "tunnel_tcp":"NOT_RUN_UNTIL_ORIGINAL_TUN_TCP",
      "stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
  print("PLAN029_H2017_GAME4_CN_REAL_DIRECT_TCP_UDP_AND_TUNNEL_UDP_PRE_STOP",flush=True)
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
      peer,host_source,"3" if p029_udp_rtt else "2" if p029_multia else "1" if p029_cache else "0"],stdout=guest_log,stderr=subprocess.STDOUT)
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
  if p029_udp_rtt:
   result=wdata.get("udp_p99_results",{})
   if (wdata.get("udp_p99_real_samples")!=720 or gdata.get("ping_unique")!=720 or
       set(result)!={"96","512","1200"}):
    raise RuntimeError("H1999 real two-OS UDP sample receipts absent")
   for size in ("96","512","1200"):
    for arm in ("physical","direct"):
     vals=result[size][arm]
     if (vals["unique"]!=120 or vals["loss"]!=0 or not (
         0<=vals["p50_ms"]<=vals["p95_ms"]<=vals["p99_ms"]<=vals["max_ms"])):
      raise RuntimeError("H1999 real UDP p99 values invalid")
   print("PLAN029_H1999_REAL_WINDOWS_DIRECT_UDP_3SIZE_720_RTT_PRE_STOP",flush=True)
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
   if p029_sustain or p029_highrate:
    # Passed only to the test orchestrator; product environment was
    # already frozen at its original Popen(), without a new CLI option.
    os.environ["WBD_PLAN029_P2_ORIGINAL_PID"]=str(w.pid)
   from m0_plan029_h1815_p2_real_mixed import run_p2
   report["plan029_p2_mixed_real"]=run_p2(root,out,peer,host_source,linux_app4,
                                          wdata["fake4"],unix,ready)
   print("PLAN029_H1815_P2_PHYSICAL1M_DIRECT1M_AND_CONCURRENT_TUNNEL_SMALL_UDP_PRE_STOP",flush=True)
 # Functional-only *real TCP* over the same original authenticated public
 # Wintun/TUN. For PLAN029B B4, require the existing original real kernel
 # Windows->Linux Tunnel TCP with a source-locked Linux listener/echo.
 # The historical PLAN028 Linux->Windows inbound comparator is not a B4
 # requirement; never disguise its known independent FAIL as B4 product FAIL.
 if p029_direct or p029b_b4 or p029b_game_case:
  # H2159: Game2/4 original kernel Windows->Linux TCP+echo is REQUIRED
  # for all five source-locked business policies. The old Linux-initiated
  # Windows inbound TCP comparator is a separate PLAN028 capability;
  # it is not evidence of the Game2/4 cold split data plane. Do NOT
  # replace the genuine two-ended socket echo with a synthetic receipt.
  # Same genuine one-way TCP test already required for PLAN029 Direct.
  # Normal B4 has three actual GUI generations; the final all generation
  # remains OS Applied until external Stop after this TCP proof.
  app=root/"tools"/"m0_plan029_h1762_oneway_tunnel_tcp.py"
  ltlog=(out/"linux-tcp-app.log").open("w");logs.append(ltlog)
  wtlog=(out/"windows-tcp-app.log").open("w");logs.append(wtlog)
  tls_prefix=["tls-startup"] if p029b_game_padding=="tls" else []
  lt=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(app),"server",linux_app4,"10.66.0.2",*tls_prefix],
      stdout=ltlog,stderr=subprocess.STDOUT)
  ready(out/"linux-tcp-app.log","PLAN029_H1762_REAL_LINUX_TUN_TCP_READY",lt,20)
  wt=subprocess.Popen([sys.executable,str(app),"client","10.66.0.2",linux_app4,*tls_prefix],
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
  # H2010: same overseas CDN IP on eth0 and original Linux TUN.
  # Two independent physical/Tunnel DNS services and kernel business
  # recipients check src AND ingress ifindex; no classifier-only PASS.
  if p029_cdn:
   h1775_owned_apply(host_source,peer,target=p029_tunnel_alias,tag="h2010")
   try:
    gn="plan029-h2010-guest-shared-cdn.log"
    wn="plan029-h2010-windows-shared-cdn.log"
    gf=(out/gn).open("w");logs.append(gf)
    p029_cdn_guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
      "python3","-u",unix(root/"tools"/"m0_plan029_h2010_shared_cdn_guest.py"),
      peer,"1.1.1.1",p029_tunnel_alias,host_source,"10.66.0.2"],
      stdout=gf,stderr=subprocess.STDOUT)
    ready(out/gn,"PLAN029_H2010_SHARED_CDN_FOUR_KERNEL_SOCKETS_READY",p029_cdn_guest,12)
    wf=(out/wn).open("w");logs.append(wf)
    p029_cdn_win=subprocess.Popen([sys.executable,
      str(root/"tools"/"m0_plan029_h2010_shared_cdn_windows.py"),
      "10.66.0.2","8.8.8.8",p029_tunnel_alias],
      stdout=wf,stderr=subprocess.STDOUT)
    if p029_cdn_win.wait(timeout=54)!=0 or p029_cdn_guest.wait(timeout=8)!=0:
     raise RuntimeError("H2010 same CDN opposite-exit FAIL windows="+
       (out/wn).read_text(errors="replace")[-700:]+
       " guest="+(out/gn).read_text(errors="replace")[-700:])
    witnesses={}
    for who,name,marker in (
      ("windows",wn,"PLAN029_H2010_WINDOWS_REAL_SHARED_CDN "),
      ("linux",gn,"PLAN029_H2010_LINUX_REAL_SHARED_CDN ")):
     values=[x.split(" ",1)[1] for x in (out/name).read_text().splitlines()
             if x.startswith(marker)]
     if len(values)!=1:raise RuntimeError("H2010 missing unique "+who+" receipt")
     witnesses[who]=json.loads(values[0])
    wrec,lrec=witnesses["windows"],witnesses["linux"]
    counts=lrec["counts"]
    if not (wrec["shared_real_a"]==p029_tunnel_alias and
       wrec["noncn_real_a"]==wrec["shared_real_a"] and
       wrec["cn_fakeip"].startswith("198.18.") and
       wrec["cn_fakeip"]!=p029_tunnel_alias and
       wrec["business"]["cn_direct"]["dst"]==wrec["cn_fakeip"] and
       wrec["business"]["noncn_tunnel"]["dst"]==p029_tunnel_alias and
       lrec["real_a"]==p029_tunnel_alias and
       lrec["physical_src"]==host_source and
       lrec["tunnel_src"]=="10.66.0.2" and
       lrec["kernel_eth0_and_tun_distinct"] is True and
       counts["cn_business_physical"]==1 and
       counts["noncn_business_tunnel"]==1 and
       1<=counts["cn_dns_physical"]<=3 and
       1<=counts["noncn_dns_tunnel"]<=3):
     raise RuntimeError("H2010 same-real-CDN FakeIP/nonCN two actual exits not evidenced")
    report["plan029_h2010_shared_cdn_opposite_exits"]={
       "source_sha":os.environ["GITHUB_SHA"],
       "scope":"REAL_SAME_OVERSEAS_A_CN_FAKEIP_PHYSICAL_VS_NONCN_REAL_TUNNEL",
       "windows":wrec,"linux":lrec,
       "alias_cleanup":"NOT_RUN","stop":"NOT_RUN_UNTIL_BOTH_OWNED_STOP"}
    print("PLAN029_H2010_REAL_SHARED_CDN_DNS_TWO_ACTUAL_EXITS_PRE_STOP",flush=True)
   finally:
    h1775_owned_cleanup(target=p029_tunnel_alias,tag="h2010")
   report["plan029_h2010_shared_cdn_opposite_exits"]["alias_cleanup"]="PASS_EXACT_OWNED_ALIAS_ROUTE"
   print("PLAN029_H2010_SHARED_CDN_EXACT_ALIAS_AND_ROUTE_CLEANUP_PASS",flush=True)
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
   p1_rate_tunnel_ip=p029_tunnel_alias if p029_p1_policy else "10.66.0.1"
   linuxrate=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
       "python3","-u",rate,p1_rate_tunnel_ip,"10.66.0.2",
       "linux",unix(out/"wl-n0-start.flag"),output,seconds,profile_name]+
       ([unix(v2_path)] if scenario else []),stdout=lrate,stderr=subprocess.STDOUT)
   windowsrate=subprocess.Popen([sys.executable,"-u",str(root/"tools"/"m0_wl_public_rate_app.py"),
       "10.66.0.2",p1_rate_tunnel_ip,"windows",str(out/"wl-n0-start.flag"),str(out),seconds,profile_name]+
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
 if p030_managed:wsl("rm","-f",cfg_guest,sock_guest)
 stop_marker=("V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close" if is_game and plan028_owned_switch else
  "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server" if is_game else
  "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" if (plan028_owned_switch or p029_gui_reconnect or p029b_b4) else
  "V4_PUBLIC_NATIVE_STOP_DRAINED role=server")
 if s.returncode or stop_marker not in (out/"server.log").read_text():raise RuntimeError("Linux original Rust Stop missing")
 report["stop"]="PASS_BOTH_OWNED"
 if p029b_b4:
  # Signed source-locked proof: no synthetic OS/Ready, no single- or
  # two-generation Go check-config substituted for three REAL button
  # connections, three original Rust Stops and one Linux kernel observer.
  from m0_plan029_gui_real_bridge import receipt_and_cleanup
  gui=receipt_and_cleanup(gui_root)
  client_text=(out/"client.log").read_text(errors="replace")
  server_text=(out/"server.log").read_text(errors="replace")
  def exact(prefix):
   return sum(row.startswith(prefix) for row in client_text.splitlines())
  if (exact("PLAN029B_B4_REAL_GUI_GENERATION_APPLIED ordinal=")!=3 or
      exact("PLAN029B_B4_REAL_GUI_OWNED_STOP_WAL_CLEAN ordinal=")!=3 or
      exact("WBD_WINDOWS_OS_APPLIED")!=3 or
      exact("WBD_WINDOWS_CLIENT_READY")!=3 or
      exact("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS")!=3 or
      exact("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")!=3 or
      "PLAN029B_B4_THREE_REAL_GUI_GENERATIONS_AND_STOPS_COMPLETE" not in client_text or
      server_text.count("V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443")!=3 or
      (gui_root/"data/network-state.json.n4-owned-wal").exists() or
      (gui_root/"data/network-state.json.n4-owned-wal.routes").exists() or
      (gui_root/"data/network-state.json.plan029-defender-tcp").exists() or
      (out/"plan029-h2010-owned-route-alias.json").exists()):
   raise RuntimeError("B4 signed genuine three-GUI OS/M4/Stop/WAL proof absent")
  p029b_guest.wait(timeout=12)
  if p029b_guest.returncode:
   raise RuntimeError("B4 original Linux physical/tunnel DNS/data witness failed")
  rows=[line.split("PLAN029B_B4_REAL_LINUX_EGRESS ",1)[1]
        for line in (out/"plan029b-b4-guest.log").read_text(errors="replace").splitlines()
        if "PLAN029B_B4_REAL_LINUX_EGRESS " in line]
  if len(rows)!=1:raise RuntimeError("B4 original Linux kernel scene receipt absent")
  guest=json.loads(rows[0])
  if (guest.get("result")!="PASS_THREE_REAL_GUI_GENERATION_EGRESS" or
      guest.get("stale_old_fake_business")!=0 or
      guest.get("raw_old_fake_ipv4_egress")!=0):
   raise RuntimeError("B4 real egress violated ordinary/all/old FakeIP")
  report["plan029b_b4_three_real_gui"]={
   "source_sha":os.environ["GITHUB_SHA"],
   "original_gui":gui,"original_linux":guest,
   "windows_applied":3,"windows_owned_stops":3,
   "linux_authenticated_sessions":3,
   "actual_MTU_MSS":report.get("plan029b_b4_three_original_syn_synack_mss"),
   "status":"PASS_SCOPED_ORIGINAL_THREE_GENERATION_REAL_GUI_AND_STOP"}
  print("PLAN029B_B4_SIGNED_REAL_WINFORMS_ADVANCED_ORDINARY_ALL_OWNED_STOP_PASS_SCOPED",flush=True)
 if p029b_b0:
  b0=report.get("plan029b_b0_real_managed_dns",{})
  text=(out/"client.log").read_text(errors="replace")
  wal=out/"owned-wal.json.n4-owned-wal"
  routes=out/"owned-wal.json.n4-owned-wal.routes"
  defender=out/"owned-wal.json.plan029-defender-tcp"
  if (b0.get("source_sha")!=os.environ["GITHUB_SHA"] or
      b0.get("status")!="PENDING_GENUINE_BOTH_OWNED_STOP" or
      "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS" not in text or
      "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1" not in text or
      wal.exists() or routes.exists() or defender.exists()):
   raise RuntimeError("B0 original Rust DNS-only native owned Stop/WAL cleanup missing")
  b0["status"]="PASS_SCOPED_SIGNED_B0_DNS_A_AAAA_UDP_TCP_AND_STOP"
  b0["stop"]="PASS_BOTH_OWNED"
  print("PLAN029B_B0_SIGNED_REAL_DNS_A_AAAA_UDP_TCP53_AND_OWNED_STOP_PASS_SCOPED",
        flush=True)
 if p029b_game_policy=="lan":
  proof=report.get("plan029b_game_lan_real",{})
  if (proof.get("source_sha")!=os.environ["GITHUB_SHA"] or
      proof.get("status")!="PENDING_GENUINE_BOTH_OWNED_STOP" or
      report.get("stop")!="PASS_BOTH_OWNED" or
      proof.get("windows",{}).get("result")!="PASS_ORIGINAL_WINTUN_PHYSICAL_LAN_UDP" or
      proof.get("linux",{}).get("result")!="PASS_ORIGINAL_LINUX_KERNEL_PHYSICAL_LAN_UDP"):
   raise RuntimeError("Game LAN true physical source and original Stop not qualified")
  proof["status"]="PASS_SCOPED_REAL_PHYSICAL_LAN_UDP_AND_BOTH_OWNED_STOP"
  print("PLAN029B_GAME_REAL_PHYSICAL_LAN_DIRECT_AND_BOTH_OWNED_STOP_PASS",flush=True)
 if p029b_b2 or p029b_game_policy=="ordinary":
  proof=report.get("plan029b_b2_ordinary_cn_real",{})
  text=(out/"client.log").read_text(errors="replace")
  markers=(("M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=PASS",
            "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes="+str(lanes))
           if p029b_game_policy=="ordinary" else
           ("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",
            "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1"))
  if (proof.get("source_sha")!=os.environ["GITHUB_SHA"] or
      proof.get("status")!="PENDING_GENUINE_BOTH_OWNED_STOP" or
      any(mark not in text for mark in markers) or
      (out/"owned-wal.json.n4-owned-wal").exists() or
      (out/"owned-wal.json.n4-owned-wal.routes").exists() or
      (out/"owned-wal.json.plan029-defender-tcp").exists()):
   raise RuntimeError("B2 ordinary CN actual original Rust/OS/WAL owned Stop failed")
  proof["status"]="PASS_SCOPED_GENUINE_CN_REAL_A_AND_SHARED_OVERSEAS_TUNNEL"
  proof["stop"]="PASS_BOTH_OWNED"
  print("PLAN029B_B2_SIGNED_REAL_ORDINARY_CN_VS_GLOBAL_SAME_CDN_TUNNEL_OWNED_STOP_PASS",
        flush=True)
 if p029b_b3:
  proof=report.get("plan029b_b3_ipv6_actual",{})
  original=(out/"client.log").read_text(errors="replace")
  skips=re.findall(r"PLAN029B_WINTUN_IPV6_SKIPPED_STOP packets=(\d+) joined=true",original)
  if (proof.get("source_sha")!=os.environ["GITHUB_SHA"] or
      proof.get("status")!="PENDING_GENUINE_RUST_WINTUN_IPV6_AND_BOTH_OWNED_STOP" or
      len(skips)!=1 or int(skips[0])<16 or
      "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS" not in original or
      "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1" not in original or
      (out/"owned-wal.json.n4-owned-wal").exists() or
      (out/"owned-wal.json.n4-owned-wal.routes").exists() or
      (out/"owned-wal.json.plan029-defender-tcp").exists()):
   raise RuntimeError("B3 original Wintun must genuinely skip IPv6 and preserve IPv4/Stop")
  proof["wintun_ipv6_skipped"]=int(skips[0])
  proof["owned_stop"]="PASS_BOTH_OWNED"
  proof["status"]="PASS_SCOPED_REAL_AF_INET6_WINTUN_IPV4_MIX_AND_STOP"
  print("PLAN029B_B3_SIGNED_REAL_AF_INET6_WINTUN_SKIP_IPV4_PROGRESS_BOTH_STOP_PASS_SCOPED",flush=True)
 if p029_game4_cn:
  g4=report.get("plan029_game4_cn_real",{})
  expected_tcp=("PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP"
                if p029b_game_case else "PASS_ACTUAL_TWO_OS_KERNEL_TCP")
  tcp=report.get("actual_kernel_tcp",{})
  if (g4.get("source_sha")!=os.environ["GITHUB_SHA"] or
      report.get("tcp_duplex")!=expected_tcp or
      (p029b_game_case and not (
       tcp.get("windows",{}).get("client_echo") is True and
       tcp.get("linux",{}).get("received_bytes",0)>0 and
       tcp.get("linux",{}).get("client_ip")=="10.66.0.2"))):
   raise RuntimeError("Game CN real physical Direct and actual two-kernel Tunnel TCP echo missing")
  native=(out/"client.log").read_text(errors="replace")
  markers=(("WBD_PLAN029B_GAME_V3_COLD_EFFECTIVE lanes=2",
            "WBD_PLAN029B_GAME_NATIVE_DNS_TCP_ENABLED lanes=2")
           if (p029b_game2_cn or (p029b_game_case and game_mode=="game2")) else
           ("WBD_PLAN029_GAME4_CN_COLD_EFFECTIVE",
            "WBD_PLAN029_GAME4_CN_NATIVE_TCP_ENABLED"))
  if any(marker not in native for marker in markers) or (
      "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" not in native):
   raise RuntimeError("Game CN Rust V4 cold attach, exact Defender or owned Stop absent")
  g4["tunnel_tcp"]=report["tcp_duplex"]
  g4["stop"]="PASS_BOTH_OWNED"
  if p029b_game2_cn or (p029b_game_case and game_mode=="game2"):
   report["plan029b_game2_advanced_real"]={
    "source_sha":os.environ["GITHUB_SHA"],"mode":"game2","lanes":2,
    "original_go_rust_v4":True,
    "cn_real_direct_udp":g4["cn_real_direct_udp"],
    "cn_real_direct_tcp":g4["cn_real_direct_tcp"],
    "tunnel_udp":report["app_duplex"],
    "tunnel_tcp":report["tcp_duplex"],"owned_stop":"PASS_BOTH_OWNED"}
   print("PLAN029B_GAME2_ADVANCED_REAL_TWO_TLS_LANES_DIRECT_AND_TUNNEL_TCP_UDP_STOP_PASS",flush=True)
  else:
   print("PLAN029_H2017_GAME4_CN_DIRECT_TUNNEL_TCP_UDP_AND_OWNED_STOP_PASS_SCOPED",flush=True)
 if p029_product:
  # Not a private trial: the same real original Go/Rust owner and OS WAL
  # must have independently shown Windows+Linux Stop and exact route/
  # Defender cleanup after true two-OS business, not just READY.
  win_native=(out/"client.log").read_text(errors="replace")
  required=("WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=2 requested_route_mode=bypass-lan-cn business_split=true cn_domain_fakeip=true",
            "readiness=AWAIT_REAL_OS_RUST_RECEIPT",
            "WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1",
            "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",
            "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")
  missing=[mark for mark in required if mark not in win_native]
  wal=(gui_root/"data/network-state.json.n4-owned-wal" if p029_gui else out/"owned-wal.json.n4-owned-wal")
  routes=(gui_root/"data/network-state.json.n4-owned-wal.routes" if p029_gui else out/"owned-wal.json.n4-owned-wal.routes")
  tcp_sidecar=(gui_root/"data/network-state.json.plan029-defender-tcp" if p029_gui else out/"owned-wal.json.plan029-defender-tcp")
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
  if p029_dns_ttl:
   proof=report.get("plan029_dns_ttl_restart")
   if proof is None or report.get("plan029_private_v3_cn_direct_udp",{}).get(
       "stop")!="PASS_NO_WFP_V2_WAL_ABSENT":
    raise RuntimeError("H2063 post-restart CN Direct physical/Stop not proven")
   proof["post_restart_direct_business"]="PASS_REAL_FAKEIP_UDP_REPLY_AND_TCP_32768_AFTER_RESTART"
   proof["stop"]="PASS_BOTH_OWNED"
   proof["status"]="PASS_SCOPED_REAL_TTL_EXPIRE_FAKEIP_NORMAL_RESTART_AND_DIRECT_TUNNEL"
   print("PLAN029_H2063_REAL_TTL_RESTART_FAKEIP_DIRECT_TWO_OS_OWNED_STOP_PASS",flush=True)
  if p029_gui:
   from m0_plan029_gui_real_bridge import receipt_and_cleanup
   report["plan029_gui_live"]=receipt_and_cleanup(gui_root)
   text=(out/"client.log").read_text(errors="replace")
   if "PLAN029_REAL_GUI_WINFORMS_BUTTON_CONNECT_APPLIED_PASS" not in text or "PLAN029_REAL_GUI_WINFORMS_BUTTON_STOP_WAL_ABSENT_PASS" not in text:
    raise RuntimeError("original native GUI marker missing despite separate kernel business")
   if p029_gui_reconnect:
    # H2066: the normal manual /32 server must retain one listening AF_PACKET
    # socket across both genuine GUI child generations. Singleton Normal
    # deliberately refuses ALL SYN after the first Rust handoff; using that
    # path as a reconnect test was a false prerequisite.
    server_text=(out/"server.log").read_text(errors="replace")
    client_text=(out/"client.log").read_text(errors="replace")
    server_markers={
     "listener_ready":server_text.count("V4_PUBLIC_MULTI_SERVER_READY role=server port=443"),
     "real_synack":server_text.count("V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK"),
     "authenticated_sessions":server_text.count("V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443"),
     "native_stop":server_text.count("V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason="),
     "shared_tun_stop":server_text.count("V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server"),
    }
    if p030_managed:
     server_markers.update(listener_ready=server_text.count("V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443"),authenticated_sessions=server_text.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")+server_text.count("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server"),native_stop=server_text.count("V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason="))
    selected_ports=re.findall(
     r"WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=1 configured_port=41031 source_port=(\d+) original_peer_port=443 same_ip_reauth_safe_tuple=(?:true|false)",
     client_text)
    if (server_markers!={"listener_ready":1,"real_synack":2,
         "authenticated_sessions":2,"native_stop":2,"shared_tun_stop":1}
        or selected_ports!=["41031","41032"]):
     raise RuntimeError("H2066 original server one-port continuous admission/old-vs-new native Stop missing "+
       repr((server_markers,selected_ports)))
    report["plan029_server_continuous_accept"]={
     "status":"PASS_REAL_ONE_AF_PACKET_LISTENER_TWO_NEW_SOURCE_PORT_SYNACK_TLS_M4_AND_OLD_NEW_STOP",
     "product_binary_source":report["product_binary_source"],
     "server_mode":"MANAGED_SHARED_MANUAL_ACCOUNT" if p030_managed else "NORMAL_ORIGINAL_SHARED_MANUAL_AUTHENTICATED_32",
     "original_kernel_listener_count":1,
     "windows_source_ports":[41031,41032],
     "physical_synack_count":2,
     "authenticated_server_native_sessions":2,
     "generation_scoped_server_native_stop":2,
     "one_shared_tun_stop":True}
    print("PLAN029_H2066_REAL_SERVER_CONTINUOUS_SYN_ACCEPT_AND_TWO_NATIVE_STOPS_PASS",flush=True)
    receipt=report["plan029_gui_live"]
    lines=text.splitlines()
    def exact_count(prefix):
     return sum(1 for row in lines if row.startswith(prefix))
    if (not receipt["normal_reconnect_completed"] or
        exact_count("WBD_WINDOWS_CLIENT_READY")!=2 or
        exact_count("WBD_WINDOWS_OS_APPLIED")!=2 or
        exact_count("WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=1389 applied=1389 outer_config=1460")!=2 or
        exact_count("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS")!=2 or
        exact_count("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")!=2 or
        "PLAN029_H2061_NORMAL_GUI_FIRST_DISCONNECT_WAL_ABSENT_PASS" not in text or
        "PLAN029_H2061_NORMAL_GUI_RECONNECT_SECOND_APPLIED" not in text or
        report["stop"]!="PASS_BOTH_OWNED" or
        report["app_duplex"]!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
        report["tcp_duplex"]!="PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP"):
     raise RuntimeError("H2061 ordinary GUI 2-generation OS Applied, both owned Stops and kernel business not proven")
    report["plan029_gui_normal_reconnect"]={
     "source_sha":os.environ["GITHUB_SHA"],
     "status":"PASS_SCOPED_REAL_WINFORMS_NORMAL_DISCONNECT_RECONNECT",
     "first_os_applied":True,"first_owned_wal_stop":True,
     "second_os_applied":True,"second_kernel_direct_tunnel_tcp_udp":True,
     "second_owned_wal_stop":True,"outer_configured":1460,
     "inner_os_applied":1389,
     "cold_physical_domain_dns_TC_after_reconnect":"NOT_RUN_SEPARATE_H2056_FIRST_COLD",
     "injected_faults":"NONE"}
    print("PLAN029_H2061_REAL_WINFORMS_TWO_NORMAL_CONNECTED_GENERATIONS_AND_OS_STOP_PASS",flush=True)
   if p029_gui_padding:
    # Separate source-locked GUI selector vs original Go effective config
    # vs post-business Rust M1 actual NPF wire copy. No ciphertext or
    # simulated NPF observer. H2031 physical capture already independent.
    receipt=report["plan029_gui_live"]
    copies=re.findall(
     r"WBD_PLAN029_M1_STARTUP_PADDING_NPF_RECEIPT mode=flows copied_records=(\d+) copied_bytes=(\d+) source=original_Rust_M1_authenticated_NPF_accepted",
     text)
    if (len(copies)!=1 or receipt["startup_padding_mode"]!="flows" or
        int(copies[0][0])<1 or int(copies[0][1])<1 or
        receipt["npf_copied_records"]!=int(copies[0][0]) or
        receipt["npf_copied_bytes"]!=int(copies[0][1]) or
        report["stop"]!="PASS_BOTH_OWNED" or
        report["app_duplex"]!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
        report["tcp_duplex"]!="PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP"):
     raise RuntimeError("H2059 original GUI flows effective/Rust signed M1 NPF/OS duplex Stop missing")
    report["plan029_gui_startup_padding_effective"]={
     "source_sha":os.environ["GITHUB_SHA"],
     "status":"PASS_SCOPED_ORIGINAL_GUI_FLOWS_M1_NPF_AND_OWNED_STOP",
     "saved_gui":"flows","go_effective":"flows",
     "npf_copied_records":int(copies[0][0]),
     "npf_copied_bytes":int(copies[0][1]),
     "original_approved_business":"CN_DIRECT_AND_TUNNEL_TCP_UDP",
     "stop":"PASS_BOTH_OWNED",
     "cpu_rss_ab":"NOT_MEASURED",
     "physical_padding_pcap":"H2031_HISTORICAL_SOURCE_ONLY_NOT_REPEATED"}
    print("PLAN029_H2059_ORIGINAL_GUI_FLOWS_M1_NPF_SAME_SOURCE_KERNEL_AND_STOP_PASS",flush=True)
   print("PLAN029_REAL_GUI_WINTUN_TWO_EGRESS_STOP_PASS_SCOPED",flush=True)
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
  # Stop the independently owned eth0 packet capture after real
  # Windows/Linux kernel business and both product Stop confirmations.
  end_padding_capture()
  pc=out/"plan029-padding-real-eth0.pcap"
  if not pc.exists():raise RuntimeError("H2019 real physical pcap missing")
  from m0_plan029_h2019_wire_padding_pcap import assess
  cap=assess(pc.read_bytes(),padding_capture_source,peer,configured_mtu)
  pc.unlink() # never publish raw encrypted user data
  if cap["tls_looking_exact_record_count"]<5 or cap["record_length_spread_bytes"]<50:
   raise RuntimeError("H2019 genuine eth0 M1 ciphertext lengths insufficient")
  report["plan029_normal_startup_padding"]={
   "source_sha":os.environ["GITHUB_SHA"],
   "mode":"flows","driver_copied_records":int(rows[0][1]),
   "driver_copied_bytes":int(rows[0][2]),
   "record":"SAME_ORIGINAL_RUST_M1_AUTHENTICATED_NPF_PREFIX",
   "original_physical_eth0_tcpdump":cap,
   "record_padding_policy":"INDEPENDENT_0_TO_MIN_500_AND_ACTUAL_MTU_NO_PER_FLOW_BUDGET",
   "ordinary_windows_linux_udp":report["app_duplex"],
   "ordinary_windows_linux_tcp":report["tcp_duplex"],
   "stop":"PASS_BOTH_OWNED"}
  print("PLAN029_H2019_REAL_WSL2_ETH0_ENCRYPTED_M1_LENGTH_DISTRIBUTION_PLUS_NPF_PAD_AND_OWNED_STOP_PASS",flush=True)
  print("PLAN029_H1799_SIGNED_NORMAL_FLOWS_M1_NPF_PAD_AND_BOTH_OS_STOP_PASS_SCOPED",flush=True)
 if os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1":
  # These are actual current-source original TLS/Rust/OS receipts.
  # Do not promote a pure-Tunnel trial to DNS/Direct/D1-D5 evidence.
  win_native=(out/"client.log").read_text(errors="replace")
  required=(
   ("WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=2 "
    if p029_direct or p029_p1_cn else "WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=0 "),
   "WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1",
   "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",
   "WBD_WINDOWS_NATIVE_DISCONNECTED_V1",
  )
  missing=[marker for marker in required if marker not in win_native]
  wal=(gui_root/"data/network-state.json.n4-owned-wal" if p029_gui else out/"owned-wal.json.n4-owned-wal")
  routes=(gui_root/"data/network-state.json.n4-owned-wal.routes" if p029_gui else out/"owned-wal.json.n4-owned-wal.routes")
  tcp_sidecar=(gui_root/"data/network-state.json.plan029-defender-tcp" if p029_gui else out/"owned-wal.json.plan029-defender-tcp")
  if missing or wal.exists() or routes.exists() or (p029_direct and tcp_sidecar.exists()):
   raise RuntimeError("PLAN029 private V3 signed Tunnel/Stop oracle FAILED "+
                      json.dumps({"missing":missing,"wal":wal.exists(),
                                  "route_sidecar":routes.exists(),"tcp_defender_sidecar":tcp_sidecar.exists()}))
  if p029_direct:
   if p029_cdn:
    proof=report.get("plan029_h2010_shared_cdn_opposite_exits",{})
    if (proof.get("source_sha")!=os.environ["GITHUB_SHA"] or
        proof.get("alias_cleanup")!="PASS_EXACT_OWNED_ALIAS_ROUTE"):
     raise RuntimeError("H2010 missing real shared CDN/owned alias receipt at Stop")
    proof["stop"]="PASS_BOTH_OWNED"
    print("PLAN029_H2010_SHARED_CDN_TWO_EXITS_AND_BOTH_OWNED_STOP_PASS_SCOPED",flush=True)
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
    # On signed P2 only: collect once after original owner teardown.
    # Missing/invalid original Rust terminal counters fail this scene,
    # rather than allowing a green 4MiB receipt with no bottleneck data.
    from m0_plan029_h1815_p2_real_mixed import parse_kernel_io_final
    original_stop_log=(out/"client.log").read_text(errors="replace")
    p2["tcp_kernel_io_diagnostic"]=parse_kernel_io_final(original_stop_log)
    print("PLAN029_H1888_SIGNED_ORIGINAL_TCP_KERNEL_IO_FINAL_TYPED_AFTER_STOP",flush=True)
    if os.environ.get("WBD_PLAN029_P2_STEADY_QPC_SCENE")=="1":
     from m0_plan029_h1966_steady_qpc import analyze
     steady=p2.get("steady_tcp_qpc")
     if not isinstance(steady,dict):
      raise RuntimeError("H1966 actual established TCP app data missing before Stop")
     # Source/Stop verified; write a separate true-boundary diagnostic
     # BEFORE the existing H1966 strict exactly-1024B qualifier. Four real
     # repeat TCP segments must still leave that original run FAIL, not PASS.
     if os.environ.get("WBD_PLAN029_P2_BOUNDARY_QPC_SCENE")=="1":
      from m0_plan029_h1977_boundary_qpc import analyze as boundary
      detail=boundary(original_stop_log,steady,os.environ["GITHUB_SHA"])
      (out/"plan029-h1977-boundary-qpc.json").write_text(
          json.dumps(detail,sort_keys=True,indent=2)+"\\n",encoding="utf-8")
      steady["h1977_boundary_diagnostic"]=detail
      print("PLAN029_H1977_ORIGINAL_TX_RX_WINTUN_FD_READ_QPC_DIAGNOSTIC_ONLY",flush=True)
     steady["same_source_steady_windows_qpc"]=analyze(
         original_stop_log,steady,os.environ["GITHUB_SHA"])
     if os.environ.get("WBD_PLAN029_P2_POST_INGRESS_FLUSH_SCENE")=="1":
      from m0_plan029_h1972_gap_attribution import analyze as gaps
      steady["same_source_steady_gap_qpc"]=gaps(
          original_stop_log,steady,os.environ["GITHUB_SHA"])
      markers=[row for row in original_stop_log.splitlines() if
          row.startswith("PLAN029_H1972_POST_INGRESS_DIRECT_FINAL ")]
      if len(markers)!=1:
       raise RuntimeError("H1972 original joined post-ingress delivery receipt absent")
      m=re.fullmatch(
          r"PLAN029_H1972_POST_INGRESS_DIRECT_FINAL delivered=(\d+) max_per_turn=8 sole_original_rx_owner=1 joined=true source=signed_original_native_only",
          markers[0])
      if m is None or not 0<int(m.group(1))<=8192:
       raise RuntimeError("H1972 fresh Direct delivery never used original RX FIFO")
      steady["same_turn_post_ingress"]={
          "source_sha":os.environ["GITHUB_SHA"],
          "delivered":int(m.group(1)),
          "max_per_turn":8,
          "sole_original_wintun_rx_owner":True,
          "stop":"PASS_BOTH_OWNED",
          "status":"PASS_SCOPED_POST_INGRESS_DELIVERY_AND_REAL_QPC_JOIN"}
      print("PLAN029_H1972_ORIGINAL_SAME_TURN_DIRECT_RX_2048_QPC_STOP",flush=True)
     steady["stop"]="PASS_BOTH_OWNED"
     print("PLAN029_H1966_SIGNED_2048_STEADY_1K_REAL_WINDOWS_QPC_BOTH_OS_OWNED_STOP",flush=True)
    if os.environ.get("WBD_PLAN029_P2_REPLY_QPC_SCENE")=="1":
     from m0_plan029_h1945_reply_qpc import analyze
     measured=p2.get("small_tcp_latency")
     if not isinstance(measured,dict):
      raise RuntimeError("H1945 signed small TCP receipt missing")
     measured["same_windows_reply_qpc"]=analyze(
         original_stop_log,measured,os.environ["GITHUB_SHA"])
     print("PLAN029_H1945_SIGNED_RUST_INNER_WRITE_WINDOWS_APP_RECV_QPC",flush=True)
     if os.environ.get("WBD_PLAN029_P2_REPLY_PATH_QPC_SCENE")=="1":
      from m0_plan029_h1945_reply_qpc import analyze_path
      measured["same_windows_reply_path_qpc"]=analyze_path(
          original_stop_log,measured,os.environ["GITHUB_SHA"])
      print("PLAN029_H1948_SIGNED_RUST_PHYSICAL_WRITE_READ_INNER_WRITE_QPC",flush=True)
      if os.environ.get("WBD_PLAN029_P2_PREWRITE_QPC_SCENE")=="1":
       from m0_plan029_h1945_reply_qpc import analyze_prewrite
       measured["same_windows_prephysical_qpc"]=analyze_prewrite(
           original_stop_log,measured,os.environ["GITHUB_SHA"])
       print("PLAN029_H1953_SIGNED_RUST_PREPHYSICAL_TCP_REQUEST_QPC",flush=True)
       if os.environ.get("WBD_PLAN029_P2_PRECONNECT_AB_SCENE")=="1":
        from m0_plan029_h1945_reply_qpc import analyze_preconnect
        measured["same_source_preconnect_ab_qpc"]=analyze_preconnect(
            original_stop_log,measured,os.environ["GITHUB_SHA"])
        print("PLAN029_H1955_SIGNED_SAME_SOURCE_EARLY_PHYSICAL_TCP_A_B",flush=True)
        if os.environ.get("WBD_PLAN029_P2_PRECONNECT_BULK_ABBA_SCENE")=="1":
         from m0_plan029_h1945_reply_qpc import analyze_preconnect_bulk
         original_bulk=p2.get("same_vm_preconnect_bulk")
         measured["same_source_preconnect_bulk_abba"]=analyze_preconnect_bulk(
             original_stop_log,measured,p2,os.environ["GITHUB_SHA"])
         original_bulk["preconnect_real_QPC_join"]="PASS_4_OF_4_ORIGINAL_WINDOWS"
         original_bulk["status"]="PASS_SCOPED_ORIGINAL_ON_OFF_OFF_ON_SHA_FIN_STOP"
         print("PLAN029_H1956_SIGNED_ONE_SOURCE_FOUR_4MIB_DIRECT_EARLY_CONNECT_ABBA",flush=True)
    if p029_tcp128:
     from m0_plan029_h1892_real_tcp128 import parse_rust_128,idle_cpu_window
     stress=p2.get("tcp128")
     if not isinstance(stress,dict) or not p2.get("tunnel_udp_covers_all_128"):
      raise RuntimeError("H1892 signed TCP128 not fully overlapped by Tunnel UDP")
     signed_log=(out/"client.log").read_text(errors="replace")
     stress["rust_admission"]=parse_rust_128(signed_log)
     times=stress["windows"]
     stress["cpu_idle_128"]=idle_cpu_window(
         out/"windows-original-go-rust-process-1hz.jsonl",
         times["idle_start_monotonic_s"],times["idle_end_monotonic_s"])
     if p029_tcp128_control:
      from m0_plan029_h1892_real_tcp128 import compare_original_cpu_idle
      pre=stress.get("pre128_control")
      if not isinstance(pre,dict) or pre.get("scope")!=(
          "PRE128_NO_NEW_TCP_PROBE_SOCKETS_POST_P2") or not (
          pre["end_monotonic_s"]<=times["idle_start_monotonic_s"]):
       raise RuntimeError("H1894 original pre128 control not before actual 128 TCP idle")
      before=idle_cpu_window(
          out/"windows-original-go-rust-process-1hz.jsonl",
          pre["start_monotonic_s"],pre["end_monotonic_s"],phase="pre128")
      delta=compare_original_cpu_idle(before,stress["cpu_idle_128"])
      udp_phases=stress.get("matched_phase_udp")
      if (not isinstance(udp_phases,dict) or
          set(udp_phases)!={"pre128","tcp128"} or any(
          phase.get("unique_delivered",0)<25 or
          phase.get("scope")!=
              "ACTUAL_WINDOWS_KERNEL_TUNNEL_UDP_WITHIN_ORIGINAL_IDLE_WINDOW"
          for phase in udp_phases.values())):
       raise RuntimeError("H1894 no true phase-specific original Tunnel UDP p99")
      stress["same_vm_cpu_control"]={
          "scope":"SAME_WINDOWS_PROCESS_TWO_CONSECUTIVE_IDLE_PHASES",
          "pre128":before,"tcp128":stress["cpu_idle_128"],
          "comparison":delta
      }
      stress["same_vm_udp_control"]=udp_phases
      stress["matched_control_status"]="PASS_SIGNED_SAME_OWNER_PRE128_VS128_PROCESS_CPU_AND_TUNNEL_UDP_P99_SCOPED"
      print("PLAN029_H1894_SAME_VM_PRE128_VS128_IDLE_USER_KERNEL_CPU_AND_TUNNEL_UDP_P99_WITH_STOP_PASS_SCOPED",flush=True)
     stress["stop"]="PASS_BOTH_OWNED"
     stress["status"]="PASS_SIGNED_TRUE_WINTUN_128_IDLE2_ACTIVE_SAME_SHARD_AND_CPU_SCOPE"
     print("PLAN029_H1892_SIGNED_128_REAL_WINTUN_TCP_126_IDLE_2_SAME_SHARD_ACTIVE_AND_IDLE_CPU_STOP_PASS_SCOPED",flush=True)
    if p029_highrate:
     rate=p2.get("highrate_direct_tcp")
     if (not isinstance(rate,dict) or
         rate.get("source_sha")!=os.environ["GITHUB_SHA"] or
         rate.get("status")!="PENDING_UDP_AND_STOP" or
         rate.get("owner_stop")!="NOT_RUN" or
         not rate.get("tunnel_udp_covers_rate") or
         rate.get("scope")!=(
           "REAL_SAME_VM_PHYSICAL_AND_WINTUN_2GIB_UP_1P5GIB_EACH_DUPLEX"
           if p029_longrate else
           "REAL_FAKEIP_WIN_LINUX_512M_UP_AND_256M_EACH_FULL_DUPLEX") or
         not rate.get("windows",{}).get("one_real_full_duplex_tcp_socket") or
         not rate.get("windows",{}).get("windows_half_close") or
         not rate.get("linux",{}).get("half_close")):
      raise RuntimeError("H1898 signed real 500/700 throughput CPU/Stop proof absent")
     for name,target in (("oneway_500mbps",500),
                         ("duplex_700mbps_aggregate",700)):
      stage=rate["windows"]["stages"].get(name,{})
      udp=rate["tunnel_udp_per_stage"].get(name,{})
      if (stage.get("target_aggregate_mbps")!=target or
          not (30 if p029_longrate else 2)<=stage.get("elapsed_s",0)<=(180 if p029_longrate else 100) or
          stage.get("actual_aggregate_mbps",0)<=0 or
          stage.get("original_process_cpu",{}).get(
             "original_process_total_cpu_s_per_gib",-1)<0 or
          stage.get("load_generator_cpu",{}).get(
             "original_process_total_cpu_s_per_gib",-1)<0 or
          stage.get("windows_host_cpu",{}).get(
             "host_all_logical_cpu_busy_pct",-1)<0 or
          udp.get("unique_delivered",0)<25 or
          udp.get("rtt_p99_ms",-1)<0):
       raise RuntimeError("H1898 true high-rate SHA/CPU/Tunnel 96B p99 absent")
     if p029_longrate:
      baseline=rate.get("physical_control")
      inc=rate.get("same_vm_original_process_cpu_increment")
      sessions=rate.get("linux",{}).get("sessions",[])
      phases=rate.get("tunnel_udp_per_stage",{})
      expected={"physical_oneway_500mbps",
                "physical_duplex_700mbps_aggregate"}
      valid=(isinstance(baseline,dict) and
             baseline.get("source_sha")==os.environ["GITHUB_SHA"] and
             baseline.get("path")=="physical" and
             baseline.get("windows_half_close") is True and
             baseline.get("original_pid")==rate["windows"]["original_pid"] and
             isinstance(inc,dict) and
             set(inc)=={"oneway_500mbps","duplex_700mbps_aggregate"} and
             len(sessions)==2 and [x.get("path") for x in sessions]==
                 ["physical","direct"] and
             all(x.get("half_close") is True for x in sessions) and
             set(phases)==expected|{"pre","post",
                 "oneway_500mbps","duplex_700mbps_aggregate"} and
             all(phases[k].get("unique_delivered",0)>=750 for k in
                 expected|{"oneway_500mbps","duplex_700mbps_aggregate"}))
      for k in ("oneway_500mbps","duplex_700mbps_aggregate"):
       stage=baseline.get("stages",{}).get(k,{}) if isinstance(baseline,dict) else {}
       if (not 30<=stage.get("elapsed_s",0)<=180 or
           stage.get("actual_aggregate_mbps",0)<=0 or
           not isinstance(inc.get(k) if isinstance(inc,dict) else None,dict)):
        valid=False
      if not valid:
       raise RuntimeError("H1903 same Windows owner signed long physical/Direct SHA/CPU/UDP all stage witnesses absent")
      rate["owner_stop"]="PASS_BOTH_OWNED"
      rate["status"]="PASS_SIGNED_LONG_SAME_VM_PHYSICAL_VS_DIRECT_CPU_UDP_STOP"
      print("PLAN029_H1903_SIGNED_LONG_2GIB_500MBPS_1P5GIB_EACH_700MBPS_SAMEVM_PHYSICAL_VS_DIRECT_AND_OWNED_STOP_PASS_SCOPED",flush=True)
     else:
      rate["owner_stop"]="PASS_BOTH_OWNED"
      rate["status"]="PASS_SIGNED_REAL_500_TARGET_AND_700_AGGREGATE_MEASURED"
      print("PLAN029_H1898_SIGNED_TRUE_500MBPS_ONEWAY_700MBPS_SIMULTANEOUS_TCP_SHA_CPU_UDP_STOP_PASS_SCOPED",flush=True)
    if p029_sustain:
     st=p2.get("sustained_direct_tcp")
     if (not isinstance(st,dict) or
         st.get("source_sha")!=os.environ["GITHUB_SHA"] or
         st.get("status")!="PENDING_UDP_AND_OWNED_STOP" or
         st.get("scope")!=
         "REAL_WINDOWS_FAKEIP_TO_WSL2_PHYSICAL_TCP_30S_EACH_DIRECTION" or
         set(st.get("tunnel_udp_per_phase",{}))!={"upload","download"} or
         not st.get("windows",{}).get("one_persistent_socket") or
         not st.get("linux",{}).get("half_close") or
         not st.get("windows",{}).get("windows_half_close")):
      raise RuntimeError("H1896 signed 30+30s sustained original CPU/UDP delivery missing")
     for phase in ("upload","download"):
      stage=st["windows"]["phases"][phase]
      sample=st["tunnel_udp_per_phase"][phase]
      cpu=stage.get("cpu",{})
      if (stage.get("delivered_bytes")!=251658240 or
          not 29.5<=stage.get("elapsed_s",0)<=55 or
          stage.get("throughput_mib_s",0)<=0 or
          sample.get("unique_delivered",0)<250 or
          sample.get("rtt_p99_ms",-1)<0 or
          cpu.get("cpu_scope")!=
          "WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC" or
          cpu.get("original_process_total_cpu_s_per_gib",-1)<0 or
          cpu.get("original_process_kernel_cpu_s_per_gib",-1)<0 or
          cpu.get("original_process_user_cpu_s_per_gib",-1)<0):
       raise RuntimeError("H1896 original 240MiB per-leg delivery/CPU/p99 receipt invalid")
     st["owner_stop"]="PASS_BOTH_OWNED"
     st["status"]="PASS_SIGNED_REAL_30S_UP_AND_DOWN_CPU_GIB_UDP_AND_STOP"
     print("PLAN029_H1896_SIGNED_REAL_30S_UPLOAD_DOWNLOAD_ORIGINAL_CPU_GIB_UDP_P99_AND_OWNED_STOP_PASS_SCOPED",flush=True)
    if p029_abba:
     chosen=p2.get("same_vm_abba",{})
     win_diag_text=(out/"client.log").read_text(errors="replace")
     expected=("copy","bypass","bypass","copy")
     valid=(chosen.get("order")==list(expected) and
            chosen.get("test_port")==46116 and
            len(chosen.get("trials",[]))==4 and
            chosen.get("scope")==
             "FOUR_REAL_FAKEIP_DIRECT_TCP_ONE_VM_ONE_BINARY_ONE_WINTUN_GENERATION" and
            all(("PLAN029_H1884_ABBA_ADMITTED source=real_wintun_direct ordinal="+
                 str(index+1)+" mode="+mode) in win_diag_text
                for index,mode in enumerate(expected)))
     if not valid:
      raise RuntimeError("H1884 missing original Rust exact per-flow ABBA proof at owned Stop")
     chosen["rust_admission_verified"]=True
     chosen["stop"]="PASS_BOTH_OWNED"
     chosen["status"]="PASS_SIGNED_REAL_ONE_WINTUN_ABBA_AFTER_STOP"
     print("PLAN029_H1884_SAME_VM_SAME_BINARY_COPY_VS_BYPASS_ABBA_AND_OWNED_STOP_PASS_SCOPED",flush=True)
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
  if p029b_b4:
   win_rows=re.findall(r"WBD_WINDOWS_OUTER_REPAIR_EFFECTIVE enabled=(\d+) shadow_limit=(\d+) source=original_rust_owner",win_text)
   linux_rows=re.findall(r"V4_PUBLIC_M2_OUTER role=server [^\n]*repair_enabled=(\d+) ",linux_text)
   win_ok=len(win_rows)==3 and all(int(v)==expected for v,limit in win_rows)
   linux_ok=len(linux_rows)==3 and all(int(v)==expected for v in linux_rows)
   report["original_outer_repair_effective"]={
    "windows":win_ok,"linux":linux_ok,"enabled":expected,"generations":3}
  elif plan028_owned_switch:
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
 if padding_capture is not None and padding_capture.poll() is None:
  try:end_padding_capture()
  except Exception as exc:
   print("PLAN029_H2019_REAL_PCAP_STOP_INCOMPLETE "+str(exc)[-220:],flush=True)
 (out/"plan029-padding-real-eth0.pcap").unlink(missing_ok=True)
 if padding_capture is not None and padding_capture.poll() is not None:
  (out/"plan029-padding-capture.pid").unlink(missing_ok=True)
 resource_stop.set()
 if resource_worker is not None:resource_worker.join(timeout=3)
 for p in (wa,la,wt,lt,p029b_guest,p029_guest_proc,p029_client_proc,p029_alias_proc,p029_tun_dns_guest,p029_tun_dns_win,p029_dns_blackhole_guest,p029_dns_blackhole_win,p029_d2_tun_guest,p029_d2_tun_win,p029_d2_cn_guest,p029_d2_cn_win,p029_pressure_guest,p029_pressure_win,p029_tcp53_guest,p029_tcp53_win,p029_cdn_guest,p029_cdn_win):
  if p is not None and p.poll() is None:p.terminate()
 if (p029_cdn or p029b_b4) and (out/"plan029-h2010-owned-route-alias.json").exists():
  try:h1775_owned_cleanup(target=p029_tunnel_alias,tag="h2010")
  except Exception as exc:
   report["plan029_h2010_owned_cleanup"]="FAIL_OWNED_ROUTE_ALIAS"
   print("PLAN029_H2010_OWNED_CLEANUP_FAILED "+str(exc)[-300:],flush=True)
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
 if (p029_direct or p029_p1_policy or p029_game4_cn or p029b_b2 or p029b_b4 or p029b_game_case) and (out/"plan029-h1745-owned-tun-alias.txt").exists():
  # Exact ephemeral TUN alias only: cleanup is idempotent even after the
  # server has already removed its own interface on normal Stop.
  try:
   attached=wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8)
   if p029_tunnel_alias+"/32" in attached:
    wsl("ip","addr","del",p029_tunnel_alias+"/32","dev","wbdwl4",timeout=8)
  except Exception:pass
 if p029b_b3 and (out/"plan029b-b3-owned-ipv6-route.json").exists():
  # ALWAYS exact generation/CAS cleanup, including an aborted application.
  # Test route/address have no business underlay/global host ownership.
  try:
   cleared=subprocess.run([sys.executable,str(root/"tools"/"m0_plan029b_b3_ipv6_windows.py"),
     "--cleanup",str(out)],capture_output=True,text=True,timeout=35,check=False)
   if cleared.returncode:
    report["plan029b_b3_cleanup_failure"]=(cleared.stderr or cleared.stdout)[-700:]
    print("PLAN029B_B3_TEST_ROUTE_FINAL_CLEANUP_FAIL "+
          report["plan029b_b3_cleanup_failure"],flush=True)
  except Exception as issue:
   report["plan029b_b3_cleanup_failure"]=str(issue)[-700:]
 stop_windows(w);stop_linux()
 for guest in (p029_boot_tc_guest,p029_ttl_guest):
  if guest is not None and guest.poll() is None:
   guest.terminate()
   try:guest.wait(timeout=4)
   except subprocess.TimeoutExpired:guest.kill()
 if p029_ipv6:
  try:
   from m0_plan029_d4_ipv6_route_probe import evaluate as ipv6_evaluate
   if ipv6_probe_before is None or ipv6_probe_active is None:
    raise RuntimeError("missing exact pre/active original OS IPv6 readback")
   ipv6_probe_after=ipv6_route_snapshot("after_exact_owned_stop")
   assessed=ipv6_evaluate(ipv6_probe_before,ipv6_probe_active,ipv6_probe_after)
   report["plan029_d4_ipv6_route_scope"]={
     "result":"OBSERVED_ROUTE_SCOPE_NOT_IPV6_PACKET_PROOF",
     "before":ipv6_probe_before,"active":ipv6_probe_active,
     "after_stop":ipv6_probe_after,"assessment":assessed}
   print("PLAN029_D4_IPV6_REAL_OS_ROUTE_SCOPE "+
         json.dumps(assessed,separators=(",",":")),flush=True)
  except Exception as ipv6_error:
   # Stop cleanup always runs first. Never manufacture an IPv6 PASS.
   report["plan029_d4_ipv6_route_scope"]={
      "result":"NOT_MEASURED_OR_FIRST_ERROR",
      "error":str(ipv6_error)[-700:]}
   print("PLAN029_D4_IPV6_ROUTE_READBACK_FIRST_ERROR "+
         str(ipv6_error)[-500:],flush=True)
 if tls_capture is not None:
  try:end_tls_capture()
  except Exception:pass
 if route_guest:
  try:wsl("rm","-f",route_guest,timeout=10)
  except Exception:pass
 if route_local and route_local.exists():route_local.unlink()
 if p029_gui and gui_root is not None:
  for name in ("route-key.hex","gui-seed.json","profiles.json","active.json","pending.json"):
   (gui_root/"data"/name).unlink(missing_ok=True)
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
