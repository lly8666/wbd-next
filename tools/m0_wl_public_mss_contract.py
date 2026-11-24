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


def verified_plan029_gui_two_child_shared_manual_mss(win,linux,outer,managed=False):
 """Two distinct WinForms child PIDs both report internal generation=1.
 The authenticated Linux shared server proves two 443 SYNACK and M4 Ready;
 never interpret those two separate processes as one Go generation 1+2.
 """
 if outer!=1460:raise ValueError("normal GUI two cold outer must be 1460")
 cold=re.findall(r"^WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=(\d+) mode=(\S+) configured_outer_mtu=(\d+) physical_outer_mtu=(\d+) effective_outer_mtu=(\d+) local_advertised_mss=(\d+) inner_mtu_planned=(\d+) limiting_reason=(\w+) source=RUST_V1_REAL_OS$",win,re.MULTILINE)
 ports=re.findall(r"^WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=1 configured_port=41031 source_port=(\d+) original_peer_port=443 same_ip_reauth_safe_tuple=(true|false)$",win,re.MULTILINE)
 syn=re.findall(r"^WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=1 local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)$",win,re.MULTILINE)
 seen=re.findall(r"^WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=1 peer_advertised_mss=(\d+) local_advertised_mss=(\d+)$",win,re.MULTILINE)
 server_syn=re.findall(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)",linux)
 server_ready=re.findall(r"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=(\d+) active_detached_flows=(\d+) auto_lease=0 original_TLS=1 Rust_M4=1",linux)
 prep=one(linux,r"V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=\d+ outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)","Linux shared original MTU")
 if (len(cold)!=2 or ports!=[("41031","false"),("41032","true")] or
     len(syn)!=2 or len(seen)!=2 or (not managed and len(server_syn)!=2) or
     (not managed and (server_ready!=[("443","1"),("443","2")] or
      len(re.findall(r"V4_PUBLIC_MULTI_SESSION_READY[^\n]*",linux))!=2)) or
     (managed and (len(re.findall(r"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443[^\n]*client_port=41031[^\n]*protected_TLS=1 Rust_M4=1",linux))!=1 or len(re.findall(r"V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port=41032 source=authenticated_client_native_Health promoted=1",linux))!=1))):
  raise ValueError("two distinct true GUI child SYN/SYNACK/M4 proof absent")
 so,sp,sm,sr,si=map(int,prep)
 if (so!=outer or sp<576 or sm!=min(outer,sp)-40 or
     sr!=sm or si!=sm-31):
  raise ValueError("original shared Linux physical MTU/MSS budget drift")
 rows=[]
 for i,(g,mode,oc,physical,effective,mss,inner,reason) in enumerate(cold):
  oc,physical,effective,mss,inner=map(int,(oc,physical,effective,mss,inner))
  if (g!="1" or mode!="normal" or oc!=outer or physical<576 or
      effective!=min(outer,physical) or mss!=effective-40 or
      inner!=mss-31 or
      reason!=("physical_interface_ipv4" if physical<outer else "configured_outer_ipv4")):
   raise ValueError("real GUI child physical MSS budget mismatch")
  ws,wb=syn[i];peer,peer_local=seen[i]
  # The mixed server has no legacy per-SYNACK byte log. Both actual
  # client-side inbound peer MSS receipts are still required, along with
  # the port-specific authenticated server Ready/promotion above.
  if (int(ws)!=mss or wb.lower()!="0204"+format(mss,"04x") or
      int(peer)!=sm or int(peer_local)!=mss):
   raise ValueError("real per-child SYN or received peer SYNACK mismatch")
  if not managed and (int(server_syn[i][0])!=sm or
      server_syn[i][1].lower()!="0204"+format(sm,"04x")):
   raise ValueError("real per-child original TCP SYN vs Linux SYNACK mismatch")
  rows.append({"windows_child_ordinal":i+1,"source_port":int(ports[i][0]),
    "windows_cold_internal_generation":1,"windows_local_syn_mss":mss,
    "linux_local_synack_mss":None if managed else sm,"windows_received_peer_synack_mss":int(peer),"windows_physical_ip_mtu":physical,
    "windows_inner_planned":inner,"linux_physical_ip_mtu":sp,
    "linux_record_offer":sr,
    "proof":"TWO_REAL_GUI_CHILDREN_RECEIVED_SYNACK_MSS_MIXED_AUTHENTICATED_M4" if managed else "TWO_REAL_GUI_CHILDREN_TWO_LINUX_AUTHENTICATED_M4_TCP_OPTION_BYTES"})
 return {"generations":rows,"shared_original_server_port":443,
   "source_port_distinct":True,"real_server_synack_count":None if managed else 2,
   "windows_received_synack_count":2,
   "real_server_m4_ready_count":2,
   "linux_peer_syn_mss":"NOT_LOGGED_SHARED_MANUAL"}


def verified_plan029b_b4_three_gui_child_mss(win, linux, outer):
 """Require three true original Go TLS child processes, not three printouts.

 Each child has internal generation=1; the real protected Linux server
 continuously admits three one-port 443 authenticated M4 sessions.
 """
 if outer!=1460:raise ValueError("B4 GUI outer must be native 1460")
 cold=re.findall(r"^WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=(\d+) mode=(\S+) configured_outer_mtu=(\d+) physical_outer_mtu=(\d+) effective_outer_mtu=(\d+) local_advertised_mss=(\d+) inner_mtu_planned=(\d+) limiting_reason=(\w+) source=RUST_V1_REAL_OS$",win,re.MULTILINE)
 ports=re.findall(r"^WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=1 configured_port=41031 source_port=(\d+) original_peer_port=443 same_ip_reauth_safe_tuple=(true|false)$",win,re.MULTILINE)
 syn=re.findall(r"^WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=1 local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)$",win,re.MULTILINE)
 peer=re.findall(r"^WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=1 peer_advertised_mss=(\d+) local_advertised_mss=(\d+)$",win,re.MULTILINE)
 server_syn=re.findall(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=(\d+) tcp_option_bytes=([0-9a-fA-F]+)",linux)
 server_ready=re.findall(r"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=(\d+) active_detached_flows=(\d+) auto_lease=0 original_TLS=1 Rust_M4=1",linux)
 prep=one(linux,r"V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=\d+ outer_config=(\d+) interface=(\d+) advertised_mss=(\d+) record_offer=(\d+) tun_planned=(\d+)","B4 real Linux MTU")
 if (len(cold)!=3 or len(ports)!=3 or len(set(p[0] for p in ports))!=3 or
     ports[0]!=("41031","false") or any(x[1]!="true" for x in ports[1:]) or
     len(syn)!=3 or len(peer)!=3 or len(server_syn)!=3 or
     len(server_ready)!=3 or any(x[0]!="443" for x in server_ready) or
     len(re.findall(r"V4_PUBLIC_MULTI_SESSION_READY[^\n]*",linux))!=3):
  raise ValueError("B4 three independent original Go child/SYNACK/M4 receipts missing")
 so,sp,sm,sr,si=map(int,prep)
 if so!=outer or sp<576 or sm!=min(outer,sp)-40 or sr!=sm or si!=sm-31:
  raise ValueError("B4 original Linux shared MTU/MSS/record drift")
 rows=[]
 for i,(g,mode,oc,physical,effective,mss,inner,reason) in enumerate(cold):
  oc,physical,effective,mss,inner=map(int,(oc,physical,effective,mss,inner))
  if (g!="1" or mode!="normal" or oc!=outer or physical<576 or
      effective!=min(outer,physical) or mss!=effective-40 or
      inner!=mss-31 or
      reason!=("physical_interface_ipv4" if physical<outer else "configured_outer_ipv4")):
   raise ValueError("B4 real original Windows child "+str(i+1)+" MSS budget invalid")
  ws,wb=syn[i];remote,local=peer[i];svr,svr_bytes=server_syn[i]
  if (int(ws)!=mss or wb.lower()!="0204"+format(mss,"04x") or
      int(remote)!=sm or int(local)!=mss or int(svr)!=sm or
      svr_bytes.lower()!="0204"+format(sm,"04x")):
   raise ValueError("B4 true peer MSS/TCP options mismatch child "+str(i+1))
  rows.append({"ordinal":i+1,"windows_source_port":int(ports[i][0]),
    "windows_local_SYN_MSS":mss,"linux_local_SYNACK_MSS":sm,
    "windows_real_inner_mtu":inner,"windows_physical_mtu":physical,
    "linux_real_physical_mtu":sp,
    "real_TCP_options":wb.lower(),
    "source":"ORIGINAL_GO_TCP_SYN_PROTECTED_LINUX_RUST_M4"})
 return {"generations":rows,"one_original_server_port":443,
   "original_real_tls_children":3,"original_server_m4_admissions":3,
   "original_linux_synack_count":3,
   "source_port_distinct":True,"linux_peer_syn_mss":"NOT_LOGGED_SHARED_MANUAL"}
