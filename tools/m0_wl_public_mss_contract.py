"""True two-OS V4 SYN/SYNACK MSS receipts, not computed-only logs."""
import re
def one(s,pattern,label):
 rows=re.findall(pattern,s,re.MULTILINE)
 if not rows or len(set(map(str,rows)))!=1:raise ValueError("missing/conflicting "+label)
 return rows[0]
def verified_current_v4_mss(win,linux,outer):
 if outer not in (1280,1400,1460,1500):raise ValueError("bad V4 configured outer")
 receipt=one(win,r"^WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=(\d+) mode=\S+ configured_outer_mtu=(\d+) physical_outer_mtu=(\d+) effective_outer_mtu=(\d+) local_advertised_mss=(\d+) inner_mtu_planned=(\d+) limiting_reason=(\w+) source=RUST_V1_REAL_OS$","Windows cold source")
 generation,configured,physical,effective,win_mss,win_inner=map(int,receipt[:6])
 reason=receipt[6]
 if configured!=outer or physical<576 or effective!=min(outer,physical) or win_mss!=effective-40:
  raise ValueError("Windows SYN MSS not derived from true physical source")
 if reason!=("physical_interface_ipv4" if physical<outer else "configured_outer_ipv4"):
  raise ValueError("untrue Windows MSS limiting reason")
 syn=int(one(win,r"^WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=\d+ local_advertised_mss=(\d+) tcp_option_bytes=[0-9a-f]+$","Windows SYN bytes"))
 synack_peer=int(one(win,r"^WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=\d+ peer_advertised_mss=(\d+) local_advertised_mss=\d+$","Windows decoded peer SYNACK"))
 synack=int(one(linux,r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=\d+ kind=SYNACK local_advertised_mss=(\d+) tcp_option_bytes=[0-9a-f]+","Linux SYNACK bytes"))
 syn_peer=int(one(linux,r"V4_PUBLIC_ACTUAL_PEER_SYN_MSS_V1 side=server peer_advertised_mss=(\d+)","Linux decoded peer SYN"))
 prep=one(linux,r"V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=\d+ outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)","Linux Rust budget+OS")
 svr_outer,svr_physical,svr_mss,svr_record,svr_inner=map(int,prep)
 if svr_outer!=outer or svr_physical<576 or svr_mss!=min(outer,svr_physical)-40:
  raise ValueError("Linux SYNACK MSS not from Rust physical")
 if syn!=win_mss or syn_peer!=win_mss or synack_peer!=synack or synack!=svr_mss:
  raise ValueError("true original SYN/SYNACK direction mismatch")
 if not 536<=win_mss<=1460 or not 536<=svr_mss<=1460:raise ValueError("invalid actual MSS")
 expect_linux_inner=min(min(outer,svr_physical)-40,win_mss)-31
 return {"windows_local_syn_mss":win_mss,"linux_local_synack_mss":svr_mss,
  "linux_received_peer_syn_mss":syn_peer,"windows_received_peer_synack_mss":synack_peer,
  "windows_physical_ip_mtu":physical,"linux_physical_ip_mtu":svr_physical,
  "windows_inner_planned":win_inner,"linux_expected_normal_inner":expect_linux_inner,
  "linux_initial_record_wire_offer":svr_record,"linux_initial_tun_planned":svr_inner,
  "generation":generation,"limiting_reason":reason,"proof":"ACTUAL_GO_TCP_OPTIONS_AND_INBOUND_PEER"}


def verified_plan028_shared_manual_two_generation_v4_mss(win,linux,outer):
 """Exact original Windows SYN / Linux SYNACK bytes for two shared sessions.
 The shared server does not log the legacy singleton decoded-peer-SYN marker;
 never synthesize or claim that unavailable observation.
 """
 if outer not in (1280,1400,1460,1500):raise ValueError("invalid outer")
 cold=re.findall(r"^WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=(\d+) mode=(\S+) configured_outer_mtu=(\d+) physical_outer_mtu=(\d+) effective_outer_mtu=(\d+) local_advertised_mss=(\d+) inner_mtu_planned=(\d+) limiting_reason=(\w+) source=RUST_V1_REAL_OS$",win,re.MULTILINE)
 if len(cold)!=2 or [int(x[0]) for x in cold]!=[1,2]:
  raise ValueError("two Windows generations not authenticated")
 prep=one(linux,r"V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=\d+ outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)","Linux physical budget")
 so,sp,sm,sr,si=map(int,prep)
 if so!=outer or sp<576 or sm!=min(outer,sp)-40 or sr!=sm or si!=sm-31:
  raise ValueError("original Linux MTU/MSS/record budget inconsistent")
 srv_syn=re.findall(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=\d+ kind=SYNACK local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)",linux)
 srv_ready=re.findall(r"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=(\d+) active_detached_flows=(\d+) auto_lease=0 original_TLS=1 Rust_M4=1",linux)
 if len(srv_syn)!=2 or len(re.findall(r"V4_PUBLIC_MULTI_SESSION_READY[^\n]*",linux))!=2 or srv_ready!=[("443","1"),("443","2")]:
  raise ValueError("two original Linux SYNACK/authenticated shared READY receipts missing")
 proof=[]
 for i,(g,mode,oc,physical,effective,mss,inner,reason) in enumerate(cold):
  g=int(g);oc,physical,effective,mss,inner=map(int,(oc,physical,effective,mss,inner))
  if mode!="normal" or oc!=outer or physical<576 or effective!=min(outer,physical) or mss!=effective-40 or inner!=mss-31:
   raise ValueError("Windows generation physical MSS budget mismatch")
  if reason!=("physical_interface_ipv4" if physical<outer else "configured_outer_ipv4"):
   raise ValueError("Windows physical limiting reason incorrect")
  syn=re.findall(r"^WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation="+str(g)+r" local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)$",win,re.MULTILINE)
  peer=re.findall(r"^WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation="+str(g)+r" peer_advertised_mss=(\d+) local_advertised_mss=(\d+)$",win,re.MULTILINE)
  if not syn or len(syn)>8 or len(set(syn))!=1 or len(peer)!=1:
   raise ValueError("missing or conflicting original Windows SYN/SYNACK generation "+str(g))
  server_wire,server_bytes=srv_syn[i]
  if (int(syn[0][0])!=mss or syn[0][1].lower()!="0204"+format(mss,"04x") or
      int(peer[0][0])!=sm or int(peer[0][1])!=mss or
      int(server_wire)!=sm or server_bytes.lower()!="0204"+format(sm,"04x")):
   raise ValueError("genuine two-OS TCP option mismatch generation "+str(g))
  proof.append({"generation":g,"windows_local_syn_mss":mss,
   "windows_actual_syn_tcp_option_bytes":syn[0][1].lower(),
   "windows_received_peer_synack_mss":int(peer[0][0]),
   "linux_local_synack_mss":sm,"linux_actual_synack_tcp_option_bytes":server_bytes.lower(),
   "windows_physical_ip_mtu":physical,"linux_physical_ip_mtu":sp,
   "windows_inner_planned":inner,"linux_initial_record_wire_offer":sr,
   "linux_initial_tun_planned":si,"linux_received_peer_syn_mss":"NOT_LOGGED_SHARED_MANUAL",
   "proof":"REAL_WINDOWS_SYN_AND_LINUX_SYNACK_TWO_PROTECTED_SHARED_READY"})
 return proof
