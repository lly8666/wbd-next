//go:build windows && wbd_v4_embedded_go
package main

// Real PUBLIC native Windows CLI protected FakeTCP/TLS original-Go Rust
// V4 admission. Explicit --native-v4-product opens a PLAN021 network
// test-channel trial after exact-source Actions validation, not automatic
// host activation or any fake Applied result.
import(
 "context"
 "crypto/rand"
 "encoding/binary"
 "encoding/json"
 "errors"
 "fmt"
 "net"
 "net/netip"
 "strconv"
 "os"
 "os/signal"
 "path/filepath"
 "sync"
 "syscall"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
 "golang.org/x/sys/windows"
)

func runM0NativeV4Windows(o m0NativeV4Options)error{
 // Mode-specific original Rust capability is queried before Npcap,
 // FakeTCP, signed Wintun or host-global mutations. Game MUST have its
 // own 2/4-lane original TLS socket group; do not run Normal by mistake.
 if err:=m0CheckWindowsV4NativeMode(o.Mode,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"));err!=nil{return err}
 if o.Mode==m0WinModeGame2||o.Mode==m0WinModeGame4{
  return fmt.Errorf("%w: public Windows Game group requires 2/4 genuine simultaneous Npcap/TLS lanes and OS Stop; single-owner runtime is forbidden",windowsclient.ErrN4NativeGuard)
 }
 if !o.ServerIP.Is4()||o.ServerPort==0||o.SourcePort==0||
  o.ServerName==""||len(o.RouteKey)<16||o.Username==""||o.Password==""||
  o.TunnelID==([16]byte{})||o.Installation==([16]byte{})||
  !o.Lease4.IsValid()||!o.Lease4.Addr().Is4()||o.Lease4.Bits()!=32||
  o.Lease4.Addr().IsUnspecified()||o.TunnelMTU<576||o.TunnelMTU>1500{
  return windowsclient.ErrN4NativeGuard
 }
 ctx,cancel:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer cancel()
 if o.ControlStdin{go watchGUIControl(os.Stdin,cancel)}
 slot,err:=acquireGUIClientSlot()
 if err!=nil{return err}
 defer windows.CloseHandle(slot)
 underlay,err:=windowsclient.DiscoverPhysicalUnderlay(o.ServerIP,0)
 if err!=nil{return err}
 ncfg,err:=underlay.NpcapConfig(o.SourcePort,o.ServerPort,1,faketcp.PacketPersonaWindows11)
 if err!=nil{return err}
 // PLAN024 original public Windows↔WSL2 real-NPF correction. Genuine
 // SendARP returned the WINDOWS vEthernet source MAC for a real WSL2
 // guest destination. This would send a SYN to ourselves, not the server.
 // Only the single CI-owned, OS-readback-verified guest MAC may override
 // that self resolution, and only when peer/interface/source all match.
 // Original production discovery remains the default outside that scope.
 guestMAC := os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC")
 if guestMAC!=""{
  idx,parseErr:=strconv.ParseUint(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"),10,32)
  parsedMAC,macErr:=net.ParseMAC(guestMAC)
  guestIP,ipErr:=netip.ParseAddr(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"))
  sourceIP,srcErr:=netip.ParseAddr(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"))
  // Runtime identities are only diagnostic here; the same exact guard
  // remains fail-closed. This is the real public product run, not a unit
  // fixture; a mismatched original route must never be silently replaced.
  if parseErr!=nil||macErr!=nil||ipErr!=nil||srcErr!=nil||
   len(parsedMAC)!=6||uint32(idx)!=underlay.InterfaceIndex||
   guestIP!=o.ServerIP||guestIP!=underlay.NextHop4||
   sourceIP!=underlay.Source4{
    return fmt.Errorf("%w: refused unscoped Windows original Npcap guest MAC override verified_ifindex=%d original_ifindex=%d verified_guest=%s original_peer=%s original_next_hop=%s verified_source=%s original_source=%s verified_mac=%s parse_if=%v parse_mac=%v parse_guest=%v parse_source=%v",
     windowsclient.ErrN4NativeGuard,idx,underlay.InterfaceIndex,
     guestIP,o.ServerIP,underlay.NextHop4,sourceIP,underlay.Source4,
     guestMAC,parseErr,macErr,ipErr,srcErr)
  }
  var actual [6]byte
  copy(actual[:],parsedMAC)
  if actual==([6]byte{})||actual==ncfg.SourceMAC||actual[0]&1!=0{
   return fmt.Errorf("%w: real WSL guest unicast MAC invalid",windowsclient.ErrN4NativeGuard)
  }
  // Genuine SendARP may already return the correct Linux MAC after
  // Windows neighbor ownership changed. Both the previously proven
  // host-self defect and an already correct same-guest resolution are
  // acceptable. Any third, unverified Ethernet next hop remains denied.
  if ncfg.NextHopMAC!=ncfg.SourceMAC&&ncfg.NextHopMAC!=actual{
   return fmt.Errorf("%w: original Npcap next-hop differs from verified WSL guest",windowsclient.ErrN4NativeGuard)
  }
  ncfg.NextHopMAC=actual
  fmt.Printf("WBD_PLAN024_NATIVE_ORIGINAL_NPCAP_NEXT_HOP_BOUND ifindex=%d guest_ip=%s mac=%s source=verified_WSL2_eth0\\n",idx,guestIP,guestMAC)
 }
 endpoint,err:=faketcp.OpenNpcapEndpoint(ncfg)
 if err!=nil{return err}
 defer endpoint.Close()
 flow:=faketcp.ClientFlow{
  LocalIP:underlay.Source4.As4(),PeerIP:o.ServerIP.As4(),
  LocalPort:o.SourcePort,PeerPort:o.ServerPort,
 }
 var seed [4]byte
 if _,err=rand.Read(seed[:]);err!=nil{return err}
 assoc,err:=faketcp.NewClientAssociation(flow,binary.BigEndian.Uint32(seed[:]),time.Second,
  func(seg faketcp.Segment)error{
   _,e:=endpoint.WriteSegment(1,seg)
   return e
  })
 if err!=nil{return err}
 defer assoc.Close()
 failure:=make(chan error,2)
 nativeFrames:=make(chan faketcp.Segment,64)
 var readers sync.WaitGroup
 readers.Add(1)
 go func(){
  defer readers.Done()
  for{
   seg,_,e:=endpoint.ReadSegment(1)
   if e!=nil{
    select{case failure<-e:default:}
    return
   }
   if assoc.State()==faketcp.ClientAssociationDetached{
    // Verified original TLS hands the bounded real TCP frame to Rust M3.
    select{case nativeFrames<-seg:
    default:
     select{case failure<-windowsclient.ErrN4NativeGuard:default:}
     return
    }
    continue
   }
   if e=assoc.HandleSegment(seg,time.Now());e!=nil{
    select{case failure<-e:default:}
    return
   }
  }
 }()
 defer func(){ _=endpoint.Close();readers.Wait() }()
 if err=assoc.Start(time.Now());err!=nil{return err}
 ticker:=time.NewTicker(100*time.Millisecond)
 defer ticker.Stop()
 handshaked:=make(chan error,1)
 go func(){handshaked<-assoc.WaitEstablished(ctx)}()
 waitHandshake:
 for{
  select{
  case <-ctx.Done():return ctx.Err()
  case e:=<-failure:return fmt.Errorf("original V4 TCP bootstrap failed: %w",e)
  case e:=<-handshaked:
   if e!=nil{return e}
   break waitHandshake
  case <-ticker.C:
   if _,e:=assoc.EmitRetransmitDue(time.Now());e!=nil{return e}
  }
 }
 // Original pinned TLS handshake, protected credentials, exact
 // FakeTCP Detach and native Rust M1/M3 Commit: no synthetic cold key.
 var policy realityfront.AdmissionPolicy
 switch o.Mode{
 case m0WinModeNormal:
  policy,err=realityfront.FixedPolicyForClient(1,0)
 case m0WinModeFixed:
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   1,"fixed",4,4,20,realityfront.CipherChaCha)
 case m0WinModeAuto:
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   1,"auto",0,4,20,realityfront.CipherChaCha)
 default:
  return windowsclient.ErrN4NativeGuard
 }
 if err!=nil{return err}
 auth:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{ServerName:o.ServerName,
    RouteKey:append([]byte(nil),o.RouteKey...),Timeout:15*time.Second},
  AutoLease:false,DesiredLanes:1,InstallationID:o.Installation[:],
  Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:1400,
  LaneID:1,Policy:policy,
 }
 dll:=filepath.Join(windowsExecutableDir(),"wbd_engine.dll")
 if !filepath.IsAbs(dll){return windowsclient.ErrN4NativeGuard}
 var owner *realityfront.V4WindowsAuthenticatedClientOwner
 var session *realityfront.V4ClientSession
 if o.Mode==m0WinModeNormal{
  owner,session,err=realityfront.V4WindowsEstablishOriginalClientOwner(ctx,dll,assoc,auth)
 }else{
  // Protected feature7 is real original credential TLS->Rust M1/M3,
  // not a caller-selected FEC switch. The release capability gate still
  // denies production Fixed/Auto pending genuine M2 applied revision.
  owner,session,err=realityfront.V4WindowsEstablishOriginalFEC2ClientOwner(ctx,dll,assoc,auth)
 }
 if err!=nil{return fmt.Errorf("original credential TLS→mode-specific native Rust V4 owner rejected: %w",err)}
 // After TLS+Rust, either the same native product service assumes
 // full ownership or we retire Rust FIRST; never return GUI Applied
 // because the Wintun alias/process exists.
 defer func(){
  stop,c:=context.WithTimeout(context.Background(),15*time.Second)
  defer c()
  _=owner.StopScopedOwner(stop)
 }()
 if session==nil||session.Epoch==[16]byte{}{
  return windowsclient.ErrN4NativeGuard
 }
 tun,e:=windowsclient.OpenTUN(o.AdapterAlias)
 if e!=nil{return e}
 defer tun.Close()
 // The sole typed product owns the exact Rust↔Wintun native hold,
 // instead of a separate pre-binding that could outlive OS WAL.
 physical,e:=underlay.PhysicalPath()
 if e!=nil{return e}
 plan,e:=windowsclient.BuildCompactNetworkPlan(windowsclient.Config{
  AdapterAlias:o.AdapterAlias,TunnelMTU:o.TunnelMTU,
  Lease4:o.Lease4,Server4:o.ServerIP,Physical:physical,
  DNSServers4:append([]netip.Addr(nil),o.DNSServers4...),
  Direct4:append([]netip.Prefix(nil),o.Direct4...),
  Bypass4:append([]netip.Prefix(nil),o.Bypass4...),
  StatePath:o.StatePath,
 })
 if e!=nil{return e}
 if plan.StatePath==""{return windowsclient.ErrN4NativeGuard}
 transport,e:=newM0NativeV4PeerForMode(owner,endpoint,flow,nativeFrames,o.Mode)
 if e!=nil{return e}
 product,e:=windowsownerlease.PrepareOriginalTLSNativeProduct(
  ctx,owner,tun,plan,o.Installation,session.Epoch,transport)
 if e!=nil{return e}
 cleanup:=func()error{
  stop,c:=context.WithTimeout(context.Background(),60*time.Second)
  defer c()
  return product.Stop(stop)
 }
 // PLAN021 explicit user authorization: exact-source GitHub Actions
 // functional PASS admits opt-in --native-v4-product NETWORK TRIALS.
 // The old frozen N4NativeNetworkReady is an unconditional V3 product
 // barrier and cannot decide whether this V4 product's real per-session
 // original TLS/Rust/Wintun/WFP/route WAL owner is valid. Do not call it.
 // This is NOT an Applied grant: Apply/LiveReceipt/Stop remain the sole
 // native generation/OS/crypto authorities, and an unsupported WFP, /1
 // route, bad owner or failed packet remains a real error and retained WAL.
 receipt,e:=product.Apply(ctx)
 if e!=nil{return errors.Join(e,cleanup())}
 if !receipt.AllNativeOSApplied{return errors.Join(windowsclient.ErrN4NativeGuard,cleanup())}
 observed,e:=product.LiveReceipt(ctx)
 if e!=nil||!observed.AllNativeOSApplied{
  return errors.Join(e,windowsclient.ErrN4NativeGuard,cleanup())
 }
 fmt.Println("WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1")
 // Native OS readback and original Rust M3 peer first+reverse proved.
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 // Read-only producer counters are emitted at 1 Hz (never per packet)
 // for isolated Windows sustained harness accounting. They do not grant
 // application goodput, CPU/RSS, WFP or product OS receipt.
 metricsTicker:=time.NewTicker(time.Second)
 defer metricsTicker.Stop()
 var runtimeErr error
waitNative:
 for{
  select{
  case <-ctx.Done():break waitNative
  case runtimeErr=<-failure:break waitNative
  case runtimeErr=<-transport.Errors():break waitNative
  case <-metricsTicker.C:
   if line,mErr:=json.Marshal(transport.Stats());mErr==nil{
    fmt.Println("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+string(line))
   }
  }
 }
 stopErr:=cleanup()
 if stopErr!=nil{return errors.Join(runtimeErr,stopErr)}
 fmt.Println("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")
 return runtimeErr
}
