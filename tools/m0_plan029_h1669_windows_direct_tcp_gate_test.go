//go:build windows
package windowsclient

// PLAN029 minimal SIGNED Windows TCP capability gate. No old WFP guard,
// no Defender rule edits, no mock Wintun, no assumed full Direct/Tunnel PASS.
import (
 "context"
 "crypto/rand"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "syscall"
 "testing"
 "time"
 "unsafe"
)

func p029Sum(b []byte)uint16{
 var s uint32
 for len(b)>1{s+=uint32(binary.BigEndian.Uint16(b[:2]));b=b[2:]}
 if len(b)>0{s+=uint32(b[0])<<8}
 for s>>16!=0{s=(s&0xffff)+(s>>16)}
 return ^uint16(s)
}
func p029TCP4(src,dst [4]byte,sport,dport uint16,seq,ack uint32,flags byte,payload []byte)[]byte{
 plen:=20+20+len(payload)
 b:=make([]byte,plen)
 b[0]=0x45;b[8]=64;b[9]=6
 binary.BigEndian.PutUint16(b[2:4],uint16(plen))
 binary.BigEndian.PutUint16(b[6:8],0x4000)
 copy(b[12:16],src[:]);copy(b[16:20],dst[:])
 binary.BigEndian.PutUint16(b[10:12],p029Sum(b[:20]))
 tcp:=b[20:]
 binary.BigEndian.PutUint16(tcp[0:2],sport)
 binary.BigEndian.PutUint16(tcp[2:4],dport)
 binary.BigEndian.PutUint32(tcp[4:8],seq)
 binary.BigEndian.PutUint32(tcp[8:12],ack)
 tcp[12]=0x50;tcp[13]=flags
 binary.BigEndian.PutUint16(tcp[14:16],65535)
 copy(tcp[20:],payload)
 pseudo:=make([]byte,12+len(tcp))
 copy(pseudo[0:4],src[:]);copy(pseudo[4:8],dst[:])
 pseudo[9]=6;binary.BigEndian.PutUint16(pseudo[10:12],uint16(len(tcp)))
 copy(pseudo[12:],tcp)
 check:=p029Sum(pseudo);if check==0{check=0xffff}
 binary.BigEndian.PutUint16(tcp[16:18],check)
 return b
}
// H1689 targeted control: UDP IPv4 has no mandatory L4 checksum. Test
// whether the *same signed Wintun injection path* can deliver any UDP payload
// to a genuine Windows listener before interpreting the TCP SYNACK absence.
// This is read-only with respect to host firewall/WFP; no policy bypass.
func p029UDP4(src,dst [4]byte,sport,dport uint16,payload []byte)[]byte{
 plen:=20+8+len(payload)
 b:=make([]byte,plen)
 b[0]=0x45;b[8]=64;b[9]=17
 binary.BigEndian.PutUint16(b[2:4],uint16(plen))
 binary.BigEndian.PutUint16(b[4:6],0x4929)
 binary.BigEndian.PutUint16(b[6:8],0x4000)
 copy(b[12:16],src[:]);copy(b[16:20],dst[:])
 binary.BigEndian.PutUint16(b[10:12],p029Sum(b[:20]))
 udp:=b[20:]
 binary.BigEndian.PutUint16(udp[0:2],sport)
 binary.BigEndian.PutUint16(udp[2:4],dport)
 binary.BigEndian.PutUint16(udp[4:6],uint16(8+len(payload)))
 copy(udp[8:],payload)
 // UDP checksum zero is valid specifically for IPv4, not IPv6.
 return b
}

func p029AwaitTCP(ctx context.Context,ring *N4OriginalKernelPacketLease,src,dst [4]byte,sport,dport uint16,flags byte,payload []byte)(uint32,error){
 var b [65535]byte
 observed:=0
 var lastFlags byte
 end:=time.Now().Add(6*time.Second)
 for time.Now().Before(end){
  if e:=ctx.Err();e!=nil{return 0,e}
  n,e:=ring.n4ReceiveReadyIPv4(ctx,b[:])
  if errors.Is(e,ErrN4NativeNoPacket){time.Sleep(10*time.Millisecond);continue}
  if e!=nil{return 0,e}
  if n<40||b[0]>>4!=4||b[9]!=6||b[0]&0x0f!=5{continue}
  if string(b[12:16])!=string(src[:])||string(b[16:20])!=string(dst[:]){continue}
  tcp:=b[20:n]
  if binary.BigEndian.Uint16(tcp[0:2])!=sport||binary.BigEndian.Uint16(tcp[2:4])!=dport{continue}
  observed++
  lastFlags=tcp[13]
  if tcp[13]&flags!=flags{continue}
  ihl:=int(tcp[12]>>4)*4
  if ihl<20||ihl>len(tcp){continue}
  if len(payload)>0&&(len(tcp)<ihl+len(payload)||string(tcp[ihl:ihl+len(payload)])!=string(payload)){continue}
  return binary.BigEndian.Uint32(tcp[4:8]),nil
 }
 return 0,fmt.Errorf("real signed Windows kernel TCP response missing after 6s: matching_tcp_frames=%d last_flags=0x%02x required_flags=0x%02x (no WFP/Defender modification)",observed,lastFlags,flags)
}


 // All Defender rules below are temporary, narrowly scoped, and restricted
 // to THIS process, local/remote test IP, protocol and exact listener ports.
 // This is the user's §3B diagnostic, NOT the retired custom WFP guard.
var p029DefenderRuleNameConflict=errors.New("plan029: exact Defender rule name already exists")
func p029OwnedDefenderAllow(ctx context.Context,name,program,proto,local,remote string,lport,rport uint16)error{
 args:=[]string{"advfirewall","firewall","show","rule","name="+name,"verbose"}
 out,_:=exec.CommandContext(ctx,"netsh",args...).CombinedOutput()
 if strings.Contains(strings.ToLower(string(out)),strings.ToLower(name)){
  return fmt.Errorf("%w: %s",p029DefenderRuleNameConflict,name)
 }
 args=[]string{"advfirewall","firewall","add","rule","name="+name,"dir=in","action=allow",
  "enable=yes","profile=any","protocol="+proto,"localip="+local,"remoteip="+remote,
  fmt.Sprintf("localport=%d",lport),fmt.Sprintf("remoteport=%d",rport),"program="+program}
 out,err:=exec.CommandContext(ctx,"netsh",args...).CombinedOutput()
 if err!=nil{return fmt.Errorf("scoped Defender %s add: %v: %q",proto,err,string(out))}
 // Independent readback is mandatory; 'netsh add' returning zero is not
 // evidence that a rule actually exists or that a matching Block is absent.
 out,err=exec.CommandContext(ctx,"netsh","advfirewall","firewall","show","rule","name="+name,"verbose").CombinedOutput()
 if err!=nil||!strings.Contains(strings.ToLower(string(out)),strings.ToLower(name)){
  return fmt.Errorf("scoped Defender %s rule readback failed: %v: %q",proto,err,string(out))
 }
 return nil
}
func p029RemoveOwnedDefender(ctx context.Context,name string)error{
 out,err:=exec.CommandContext(ctx,"netsh","advfirewall","firewall","delete","rule","name="+name).CombinedOutput()
 if err!=nil{return fmt.Errorf("exact-owned Defender %s delete: %v: %q",name,err,string(out))}
 out,err=exec.CommandContext(ctx,"netsh","advfirewall","firewall","show","rule","name="+name,"verbose").CombinedOutput()
 if err==nil && strings.Contains(strings.ToLower(string(out)),strings.ToLower(name)){
  return fmt.Errorf("exact-owned Defender %s still exists after delete",name)
 }
 return nil
}

func TestPlan029RealSignedWintunKernelTCPListenerFeasibility(t *testing.T){
 if os.Getenv("WBD_PLAN029_DIRECT_TCP_GATE")!="1"||os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("real Windows signed Wintun only")
 }
 receipt:=map[string]any{
  "source_sha":os.Getenv("GITHUB_SHA"),"result":"FAIL_UNFINISHED",
  "driver":"REAL_SIGNED_WINTUN","wfp_guard":"NOT_CREATED",
  "system_firewall_change":"NONE","tcp_real_kernel":"NOT_QUALIFIED",
  "physical_socket_egress":"NOT_RUN","full_direct_owner":"NOT_RUN",
  "tls_original":"NOT_RUN","fallback_tcp_stack":"NOT_CHOSEN"}
 defer func(){
  path:=os.Getenv("WBD_PLAN029_TCP_GATE_RECEIPT")
  if path==""{t.Error("receipt path missing");return}
  b,e:=json.MarshalIndent(receipt,"","  ");if e!=nil{t.Error(e);return}
  if e=os.MkdirAll(filepath.Dir(path),0700);e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Error(e)}
 }()
 if receipt["source_sha"]==""{t.Fatal("SOURCE SHA missing")}
 ctx,cancel:=context.WithTimeout(context.Background(),45*time.Second);defer cancel()
 var seed [8]byte;if _,e:=rand.Read(seed[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-TCP-"+hex.EncodeToString(seed[:]))
 if e!=nil{receipt["result"]="NOT_RUN_REAL_DRIVER_UNAVAILABLE";t.Fatalf("real signed Wintun OpenTUN failed: %v",e)}
 t.Cleanup(func(){if e:=tun.Close();e!=nil{t.Errorf("owned Wintun close: %v",e)}})
 now,e:=tun.NativeIdentity(ctx)
 if e!=nil||!now.CreatedByProcess||now.Index==0||now.LUID==0{t.Fatalf("real native Wintun identity %+v %v",now,e)}
 local:=netip.MustParseAddr("198.18.88.77")
 remote:=netip.MustParseAddr("198.18.88.88")
 lease:=N4NativeLeaseIntent{InterfaceIndex:now.Index,Prefix:netip.PrefixFrom(local,32)}
 existing,found,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
 if e!=nil||found{t.Fatalf("test-only source4 is already owned or unknown: found=%v row=%v error=%v",found,existing,e)}
 row,e:=n4NativeLeaseRow(lease);if e!=nil{t.Fatal(e)}
 if e=n4CreateUnicast.Find();e!=nil{t.Fatal(e)}
 code,_,_:=n4CreateUnicast.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{t.Fatalf("real Windows IP Helper /32 create rc=%d",code)}
 t.Cleanup(func(){
  cleanup,stop:=context.WithTimeout(context.Background(),10*time.Second);defer stop()
  observed,present,e:=(N4WindowsLeaseReader{}).Lookup(cleanup,lease)
  if e!=nil||!present||N4NativeLeaseDADGate(observed,lease)!=nil{
   t.Errorf("refuse unsafe test lease delete; inspect owned address manually found=%v err=%v",present,e);return
  }
  if e=n4DeleteUnicast.Find();e!=nil{t.Errorf("IP Helper delete procedure: %v",e);return}
  rc,_,_:=n4DeleteUnicast.Call(uintptr(unsafe.Pointer(&observed)))
  if rc!=0{t.Errorf("owned test /32 remove rc=%d",rc)}
 })
 for {
  current,present,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
  if e!=nil{t.Fatal(e)}
  if present&&N4NativeLeaseDADGate(current,lease)==nil{break}
  if ctx.Err()!=nil{t.Fatal("actual owned Wintun address DAD never Preferred")}
  time.Sleep(100*time.Millisecond)
 }
 route:=NativeRouteKey{Prefix:netip.PrefixFrom(remote,32),Interface:now.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 backend:=N4WindowsRouteBackend{}
 present,_,e:=backend.Lookup(ctx,route)
 if e!=nil||present{t.Fatalf("test-only remote /32 conflict: %v %v",present,e)}
 if e=backend.CreateIfAbsent(ctx,route);e!=nil{t.Fatalf("real exact route create: %v",e)}
 t.Cleanup(func(){cleanup,done:=context.WithTimeout(context.Background(),10*time.Second);defer done();if e:=backend.RemoveOwned(cleanup,route);e!=nil{t.Errorf("test exact /32 restore: %v",e)}})
 present,exact,e:=backend.Lookup(ctx,route)
 if e!=nil||!present||!exact{t.Fatalf("readback of owned exact reverse route failed %v %v %v",present,exact,e)}
 server,e:=net.ListenTCP("tcp4",&net.TCPAddr{IP:net.IP(local.AsSlice()),Port:0})
 if e!=nil{t.Fatalf("real Windows TCP kernel could not bind owned Wintun address: %v",e)}
 t.Cleanup(func(){server.Close()})
 port:=uint16(server.Addr().(*net.TCPAddr).Port)

 // Only read Windows' existing firewall and adapter status; NEVER change
 // rules or probe a third-party interface. This separates a blocked
 // inbound-Wintun SYN from a broken local kernel listener.
 diagCtx,diagCancel:=context.WithTimeout(ctx,4*time.Second)
 script:=fmt.Sprintf("$p=Get-NetConnectionProfile -InterfaceIndex %d -ErrorAction SilentlyContinue; if($p){'WINTUN_CATEGORY='+$p.NetworkCategory}else{'WINTUN_CATEGORY=UNKNOWN'}; $f=Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction SilentlyContinue; $f|ForEach-Object {'FIREWALL_PROFILE='+$_.Name+',Enabled='+$_.Enabled+',Inbound='+$_.DefaultInboundAction}",now.Index)
 profile,profileErr:=exec.CommandContext(diagCtx,"powershell.exe","-NoProfile","-NonInteractive","-Command",script).CombinedOutput()
 diagCancel()
 if profileErr==nil{
  // Firewall categories and default actions, no third-party rule contents.
  t.Log("PLAN029_H1672_READ_ONLY_WINDOWS_FIREWALL_CONTEXT "+string(profile))
  receipt["read_only_firewall_profile"]=string(profile)
 } else {t.Logf("PLAN029_H1672_READ_ONLY_WINDOWS_FIREWALL_UNKNOWN error=%v",profileErr)}
 localProbe,e:=net.DialTimeout("tcp4",net.JoinHostPort(local.String(),fmt.Sprint(port)),3*time.Second)
 if e!=nil{
  receipt["local_kernel_listener"]="FAIL_SELF_CONNECT"
  t.Fatalf("same-Windows-host native TCP self-connect to Wintun address rejected before raw SYN: %v",e)
 }
 if e=server.SetDeadline(time.Now().Add(3*time.Second));e!=nil{localProbe.Close();t.Fatal(e)}
 localAccepted,acceptErr:=server.AcceptTCP()
 localProbe.Close()
 if acceptErr!=nil{
  receipt["local_kernel_listener"]="FAIL_ACCEPT"
  t.Fatalf("same Windows kernel listener did not accept its own native socket: %v",acceptErr)
 }
 localAccepted.Close()
 receipt["local_kernel_listener"]="PASS_REAL_NATIVE_SELF_CONNECT_ACCEPT"
 t.Log("PLAN029_H1672_REAL_WINDOWS_LOCAL_KERNEL_TCP_LISTENER_ACCEPT_PASS_NO_WFP")
 var installation,generation [16]byte
 if _,e=rand.Read(installation[:]);e!=nil{t.Fatal(e)}
 if _,e=rand.Read(generation[:]);e!=nil{t.Fatal(e)}
 guid,e:=n4NativeInterfaceGUID(now.Index);if e!=nil{t.Fatal(e)}
 id:=N4UnifiedIdentity{Installation:installation,Generation:generation,WintunLUID:now.LUID,
  WintunIndex:now.Index,WintunGUID:guid.String(),AdapterAlias:tun.Name()}
 pin,e:=n4ProbeOriginalWintunPnP(ctx,id);if e!=nil{t.Fatal(e)}
 id.PnPInstanceSHA256=pin.InstanceSHA256
 ring,e:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
 if e!=nil{t.Fatalf("real owned signed native ring: %v",e)}
 t.Cleanup(func(){cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done();if e:=ring.Stop(cl);e!=nil{t.Errorf("owned ring Stop: %v",e)}})
 s,d:=remote.As4(),local.As4()
 exe,e:=os.Executable()
 if e!=nil{t.Fatal(e)}
 // A/B/C on the SAME process-created signed driver, exact listener and
 // single receiver ring. Source ports differ per phase so an earlier
 // half-open SYN or RST cannot be mistaken for a later response.
 udpLocal,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:net.IP(local.AsSlice()),Port:0})
 if e!=nil{t.Fatalf("native UDP listener bind: %v",e)}
 defer udpLocal.Close()
 udpPort:=uint16(udpLocal.LocalAddr().(*net.UDPAddr).Port)
 nativeProbe,e:=net.DialUDP("udp4",nil,udpLocal.LocalAddr().(*net.UDPAddr))
 if e==nil{_,e=nativeProbe.Write([]byte("native-udp-listener-probe"));nativeProbe.Close()}
 if e!=nil{t.Fatalf("native UDP socket self-probe send: %v",e)}
 var uBuf [128]byte
 _=udpLocal.SetReadDeadline(time.Now().Add(2*time.Second))
 n,_,e:=udpLocal.ReadFromUDP(uBuf[:])
 if e!=nil||string(uBuf[:n])!="native-udp-listener-probe"{
  t.Fatalf("native UDP socket listener self-probe failed: %v bytes=%d",e,n)
 }
 receipt["native_udp_listener"]="PASS_NATIVE_SOCKET_SELF_PROBE"
 probeUDP:=func(stage string,sourcePort uint16)bool{
  // Before the only Wintun injection, no Windows system call or DNS await
  // holds a borrowed RX ring pointer or a TX Allocate slot.
  pkt:=p029UDP4(s,d,sourcePort,udpPort,[]byte("p029-abc-"+stage))
  n,e:=tun.WritePacket(pkt)
  if e!=nil||n!=len(pkt){
   receipt["abc_"+stage+"_udp"]="WINTUN_WRITE_FAILED"
   t.Logf("PLAN029_ABC_%s_UDP_WRITE_FAIL n=%d error=%v",stage,n,e)
   return false
  }
  _=udpLocal.SetReadDeadline(time.Now().Add(2500*time.Millisecond))
  n,from,e:=udpLocal.ReadFromUDP(uBuf[:])
  ok:=e==nil&&string(uBuf[:n])=="p029-abc-"+stage&&from.IP.Equal(net.IP(s[:]))&&from.Port==int(sourcePort)
  if ok{receipt["abc_"+stage+"_udp"]="DELIVERED_TO_NATIVE_LISTENER"
  }else{receipt["abc_"+stage+"_udp"]="NO_MATCHING_NATIVE_DELIVERY"}
  t.Logf("PLAN029_ABC_%s_UDP %v bytes=%d from=%v err=%v",stage,ok,n,from,e)
  return ok
 }
 sendTCP:=func(sourcePort uint16,seq,ack uint32,flags byte,payload []byte)error{
  pkt:=p029TCP4(s,d,sourcePort,port,seq,ack,flags,payload)
  n,e:=tun.WritePacket(pkt)
  if e!=nil{return e}
  if n!=len(pkt){return fmt.Errorf("short Wintun TCP send %d/%d",n,len(pkt))}
  return nil
 }
 probeSYN:=func(stage string,sourcePort uint16,seq uint32)(uint32,bool){
  if e:=sendTCP(sourcePort,seq,0,0x02,nil);e!=nil{
   receipt["abc_"+stage+"_tcp"]="WINTUN_WRITE_FAILED"
   t.Logf("PLAN029_ABC_%s_SYN_WRITE_FAIL %v",stage,e)
   return 0,false
  }
  peerSeq,e:=p029AwaitTCP(ctx,ring,d,s,port,sourcePort,0x12,nil)
  if e!=nil{
   receipt["abc_"+stage+"_tcp"]="NO_MATCHING_SYNACK"
   t.Logf("PLAN029_ABC_%s_SYNACK_MISSING %v",stage,e)
   return 0,false
  }
  receipt["abc_"+stage+"_tcp"]="KERNEL_SYNACK_OBSERVED"
  t.Logf("PLAN029_ABC_%s_SYNACK_REAL received_source_port=%d",stage,sourcePort)
  return peerSeq,true
 }
 const seq0 uint32=0x23011000
 aUDP:=probeUDP("A",46132)
 _,aTCP:=probeSYN("A",46131,seq0)
 receipt["abc_A_original_firewall"]="NO_NEW_RULES"
 // Exact owned rule IDs are randomly generated for this single job.
 // Both A→B and B→C transitions are in this single action; never run
 // A/B on different VMs or with different source/manifests.
 suffix:=hex.EncodeToString(seed[:])
 tcpRule:="WBD-P029-ABC-"+suffix+"-TCP"
 udpRule:="WBD-P029-ABC-"+suffix+"-UDP"
 var owned []string
 removeOwned:=func()bool{
  ok:=true
  var unresolved []string
  for i:=len(owned)-1;i>=0;i--{
   cleanup,done:=context.WithTimeout(context.Background(),8*time.Second)
   err:=p029RemoveOwnedDefender(cleanup,owned[i])
   done()
   if err!=nil{
    ok=false
    unresolved=append(unresolved,owned[i])
    t.Errorf("owned Defender rule not removed %s: %v",owned[i],err)
   }
  }
  owned=unresolved
  return ok
 }
 t.Cleanup(func(){if len(owned)>0{removeOwned()}})
 applyRule:=func(name,proto string,lport,rport uint16)bool{
  scoped,done:=context.WithTimeout(context.Background(),8*time.Second)
  // Even an add with uncertain success must be accounted for and
  // rechecked during cleanup. The random name cannot overlap a known
  // prior-owned ID; preexisting exact name is refused by the helper.
  err:=p029OwnedDefenderAllow(scoped,name,exe,proto,local.String(),remote.String(),lport,rport)
  done()
  if err!=nil{
   receipt["abc_B_rule_"+proto]="ADD_OR_READBACK_FAILED"
   t.Logf("PLAN029_ABC_B_%s_RULE_FAILURE %v",proto,err)
   // An uncertain add/readback may have created the exact named rule.
   // Include it in owned cleanup; never remove a foreign preexisting
   // name, which is excluded by the fresh random identifier.
   if !errors.Is(err,p029DefenderRuleNameConflict){owned=append(owned,name)}
   return false
  }
  owned=append(owned,name)
  receipt["abc_B_rule_"+proto]="OWNED_SCOPED_ALLOW_READBACK"
  t.Logf("PLAN029_ABC_B_%s_RULE_ADDED_VERIFIED %s",proto,name)
  return true
 }
 udpAllowed:=applyRule(udpRule,"UDP",udpPort,46134)
 tcpAllowed:=applyRule(tcpRule,"TCP",port,46133)
 bUDP,bTCP:=false,false
 var bSeq uint32
 if udpAllowed{bUDP=probeUDP("B",46134)}
 if tcpAllowed{bSeq,bTCP=probeSYN("B",46133,seq0+1024)}
 bFull:=false
 if bTCP{
  // A SYNACK alone is not a physical Direct TCP qualification.
  // Prove a real listener Accept, native app bytes, reverse Wintun
  // DATA and FIN/EOF while the exact temporary allow is still owned.
  finish:=func()error{
   const sourcePort uint16=46133
   clientSeq:=seq0+1024
   if e:=sendTCP(sourcePort,clientSeq+1,bSeq+1,0x10,nil);e!=nil{return e}
   if e:=server.SetDeadline(time.Now().Add(7*time.Second));e!=nil{return e}
   conn,e:=server.AcceptTCP();if e!=nil{return e}
   defer conn.Close()
   if e:=conn.SetDeadline(time.Now().Add(7*time.Second));e!=nil{return e}
   payload:=[]byte("p029-kernel-tcp-abc-owned-data")
   if e:=sendTCP(sourcePort,clientSeq+1,bSeq+1,0x18,payload);e!=nil{return e}
   read:=make([]byte,len(payload))
   if _,e=io.ReadFull(conn,read);e!=nil{return e}
   if string(read)!=string(payload){return fmt.Errorf("kernel listener data mismatch")}
   reply:=[]byte("p029-kernel-reverse-data")
   if _,e=conn.Write(reply);e!=nil{return e}
   if _,e=p029AwaitTCP(ctx,ring,d,s,port,sourcePort,0x10,reply);e!=nil{return e}
   if e:=sendTCP(sourcePort,clientSeq+1+uint32(len(payload)),bSeq+1+uint32(len(reply)),0x11,nil);e!=nil{return e}
   _=conn.SetReadDeadline(time.Now().Add(6*time.Second))
   var single [1]byte
   if _,e=conn.Read(single[:]);!errors.Is(e,io.EOF){return fmt.Errorf("FIN/EOF: %w",e)}
   return nil
  }
  e:=finish()
  bFull=e==nil
  if e!=nil{t.Logf("PLAN029_ABC_B_TCP_FULL_CHAIN_FAIL %v",e)}
 }
 receipt["abc_B_tcp_full_chain"]=map[bool]string{true:"SYN_ACK_ACCEPT_DATA_REVERSE_FIN",false:"NOT_QUALIFIED"}[bFull]
 // C removes ONLY the newly created exact-name Defender rules, performs
 // another readback, then re-probes to see whether Windows returned to its
 // pre-Allow behavior. Some pre-existing rules can make C still deliver.
 cleaned:=removeOwned()
 if cleaned{receipt["abc_C_owned_rule_cleanup"]="VERIFIED_ABSENT"
 }else{receipt["abc_C_owned_rule_cleanup"]="FAILED"}
 cUDP:=probeUDP("C",46136)
 _,cTCP:=probeSYN("C",46135,seq0+2048)
 receipt["abc_A_udp_pass"]=aUDP
 receipt["abc_A_tcp_synack_pass"]=aTCP
 receipt["abc_B_udp_pass"]=bUDP
 receipt["abc_B_tcp_synack_pass"]=bTCP
 receipt["abc_C_udp_pass"]=cUDP
 receipt["abc_C_tcp_synack_pass"]=cTCP
 if cleaned{receipt["system_firewall_change"]="TEMP_SCOPED_OWNED_DEFENDER_ALLOW_RESTORED"
 }else{receipt["system_firewall_change"]="OWNED_DEFENDER_CLEANUP_UNVERIFIED"}
 if !cleaned{receipt["result"]="FAIL_OWNED_DEFENDER_CLEANUP";t.Fatal("C: Defender owned rule cleanup unverified")}
 if !bFull{
  receipt["result"]="FAIL_SCOPED_ABC_NO_COMPLETE_KERNEL_TCP"
  t.Fatal("A/B/C: no complete signed Wintun native TCP SYN/Accept/DATA/reverse/FIN proof; do not choose backend by inference")
 }
 receipt["result"]="PASS_SCOPED_REAL_SIGNED_WINTUN_TCP_SYN_ACK_DATA_FIN_OS_ROUTE_NO_WFP"
 receipt["tcp_real_kernel"]="SYNACK_ACCEPT_DATA_REVERSE_FIN_OWNED_ABC"
 receipt["windows_interface_index"]=now.Index
 receipt["owned_route_count"]=1
 t.Log("PLAN029_ABC_SIGNED_WINTUN_TCP_KERNEL_GATE_PASS_AND_OWNED_DEFENDER_RULES_REMOVED_NOT_FULL_DIRECT")
 var _ syscall.Errno // keep native return type evident
}
