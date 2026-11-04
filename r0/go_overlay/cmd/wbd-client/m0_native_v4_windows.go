//go:build windows && wbd_v4_embedded_go
package main

// Real PUBLIC native Windows CLI protected FakeTCP/TLS original-Go Rust
// V4 admission. Explicit --native-v4-product opens a PLAN021 network
// test-channel trial after exact-source Actions validation, not automatic
// host activation or any fake Applied result.
import(
 "bufio"
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
 "runtime"
 "sync"
 "sync/atomic"
 "strings"
 "syscall"
 "time"

 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
 "golang.org/x/sys/windows"
)

// One GUI/CLI stdin protocol for live Auto config revision + native
// Disconnect. Only the already-authenticated Rust generation may
// accept the profile request after the real OS Applied readback.
func watchM0NativeV4AutoControl(
 ctx context.Context,in *os.File,cancel context.CancelFunc,
 requests chan<- realityfront.FecV2Profile,
){
 scanner:=bufio.NewScanner(in)
 for scanner.Scan(){
  line:=strings.TrimSpace(scanner.Text())
  if strings.EqualFold(line,"stop"){cancel();return}
  if !strings.HasPrefix(line,"fec.profile="){continue}
  profile,err:=m0WindowsV4Profile(strings.TrimSpace(strings.TrimPrefix(line,"fec.profile=")))
  if err!=nil{
   fmt.Printf("WBD_WINDOWS_AUTO_OPERATOR_REJECTED invalid_profile=%q\n",line)
   continue
  }
  select{case requests<-profile:case <-ctx.Done():return}
 }
 cancel() // Exactly the existing watchGUIControl EOF→owned Stop.
}
// One product interface for cold OS admission; only the legacy Fixed/Auto
// implementations still run the old Go packet loop until their Rust-native
// mode is installed. Normal/off uses exclusively Rust NPF/Wintun workers.
type m0NativeV4ProductPeer interface {
 windowsownerlease.N4NativeAuthenticatedPeerTraffic
 Errors()<-chan error
 RefreshEffective(context.Context)error
 Stats()m0NativeV4PacketStats
 RequestAutoStartProfile(realityfront.FecV2Profile)(realityfront.FecV2State,error)
}
var errM0NativeV4AuthenticatedPeerDead=errors.New("Rust verified authenticated peer dead; cold TLS reauthorization after native Stop")

// Retry only a transient original Go cold transport timeout AFTER the
// previous authenticated Rust-dead verdict and genuine owned Stop. A
// credential reject, driver error, previously applied generation or initial
// connect failure may never be reclassified as an authorized reconnect.
func m0WindowsOriginalColdRetryAllowed(authorized,applied bool,retries int,err error)bool{
 if !authorized||applied||retries>=2||err==nil||errors.Is(err,realityfront.ErrAdmissionAuth){return false}
 if errors.Is(err,context.DeadlineExceeded)||
  errors.Is(err,syscall.ETIMEDOUT)||
  errors.Is(err,faketcp.ErrBootstrapTimeout){return true}
 var ne net.Error
 return errors.As(err,&ne)&&ne.Timeout()
}

// Filtered native source IPv4/ifindex change after exact owned Stop
// authorizes a bounded cold TLS transport retry even for Game. It does not
// make wrong credentials, user Stop, initial connect or an applied OS owner
// eligible. No extra watcher, periodic probe or second recovery controller.
func m0WindowsColdPathRetryAllowed(
 mode m0WindowsV4Mode,authenticatedDead,pathChanged,applied bool,
 retries int,err error,
)bool{
 if (mode==m0WinModeGame2||mode==m0WinModeGame4)&&!pathChanged{
  return false // keep original Game dead90 retry policy unchanged
 }
 return m0WindowsOriginalColdRetryAllowed(
  authenticatedDead||pathChanged,applied,retries,err)
}

// Cold record offer is resolved by Rust's versioned full-IP budget ABI.
// No separate Windows 1400 cap or Go framing arithmetic is authoritative.

// PLAN028: the ONE existing cold Go generation supervisor receives actual
// Windows route/address notifications. No polling, packet callback, new
// Rust owner, or wire-format change. A route event is not authentication:
// compare only selected physical NIC/source4 after 200ms quiet / 500ms max; gateway and MTU-only notifications do not rotate TLS.
var errM0WindowsPhysicalPathChanged=errors.New("original Windows physical path changed; exact owned Stop then new TLS")

type m0WindowsPhysicalPath struct{
 ifindex uint32
 source4 netip.Addr
}
// The first signed WSL source is an initial trust receipt, not a permanent
// address pin when a later cold generation follows an actual OS IPv4 path
// change. Preserve the EXACT authenticated guest/ifindex/MAC conditions.
func m0WindowsVerifiedGuestSourceRebound(
 generation uint64,initial,current netip.Addr,ifindex uint32,selected m0WindowsPhysicalPath,
)bool{
 return generation>1&&initial.Is4()&&current.Is4()&&initial!=current&&
  selected.ifindex==ifindex&&selected.source4==current
}
func m0WindowsSelectedPhysicalPath(peer netip.Addr,tunAlias string)(m0WindowsPhysicalPath,error){
 var zero m0WindowsPhysicalPath
 underlay,err:=windowsclient.DiscoverPhysicalUnderlay(peer,0)
 if err!=nil{return zero,err}
 iface,err:=net.InterfaceByIndex(int(underlay.InterfaceIndex))
 if err!=nil{return zero,err}
 if iface.MTU<576||!underlay.Source4.Is4()||
  strings.EqualFold(iface.Name,tunAlias){
  return zero,windowsclient.ErrN4NativeGuard
 }
 return m0WindowsPhysicalPath{ifindex:underlay.InterfaceIndex,source4:underlay.Source4},nil
}
type m0WindowsPathCoalescer struct{first,last time.Time}
func(c *m0WindowsPathCoalescer) push(now time.Time){
 if c.first.IsZero(){c.first=now}
 c.last=now
}
func(c m0WindowsPathCoalescer) remaining(now time.Time)time.Duration{
 if c.first.IsZero(){return -1}
 quiet:=c.last.Add(200*time.Millisecond).Sub(now)
 hard:=c.first.Add(500*time.Millisecond).Sub(now)
 if quiet>hard{quiet=hard}
 if quiet<0{return 0}
 return quiet
}
func(c *m0WindowsPathCoalescer) clear(){*c=m0WindowsPathCoalescer{}}

// NotifyRouteChange2 and NotifyUnicastIpAddressChange are native asynchronous
// IP Helper subscriptions. Their WinAPI callbacks only wake one buffered
// channel; actual OS readback, TLS, WFP and Stop remain on ordinary Go threads.
func watchM0WindowsOriginalPhysicalPath(
 parent context.Context,peer netip.Addr,tunAlias string,
)(<-chan struct{},func(),error){
 baseline,err:=m0WindowsSelectedPhysicalPath(peer,tunAlias)
 if err!=nil{return nil,nil,err}
 dll:=windows.NewLazySystemDLL("iphlpapi.dll")
 routeProc:=dll.NewProc("NotifyRouteChange2")
 addressProc:=dll.NewProc("NotifyUnicastIpAddressChange")
 cancelProc:=dll.NewProc("CancelMibChangeNotify2")
 for _,p:=range []*windows.LazyProc{routeProc,addressProc,cancelProc}{
  if err=p.Find();err!=nil{return nil,nil,err}
 }
 raw:=make(chan struct{},1)
 cb:=syscall.NewCallback(func(_,_,_ uintptr)uintptr{
  select{case raw<-struct{}{}:default:}
  return 0
 })
 var routeHandle,addressHandle uintptr
 // AF_INET (IPv4); FALSE: do not fake an initial OS path-change event.
 if status,_,_:=routeProc.Call(uintptr(syscall.AF_INET),cb,0,0,
  uintptr(unsafe.Pointer(&routeHandle)));status!=0{
  return nil,nil,syscall.Errno(status)
 }
 if status,_,_:=addressProc.Call(uintptr(syscall.AF_INET),cb,0,0,
  uintptr(unsafe.Pointer(&addressHandle)));status!=0{
  cancelProc.Call(routeHandle)
  return nil,nil,syscall.Errno(status)
 }
 // Cover route transition between baseline and native subscription setup.
 if latest,e:=m0WindowsSelectedPhysicalPath(peer,tunAlias);e==nil&&latest!=baseline{
  select{case raw<-struct{}{}:default:}
 }
 ctx,cancel:=context.WithCancel(parent)
 done:=make(chan struct{})
 changed:=make(chan struct{},1)
 go func(){
  defer close(done)
  defer cancelProc.Call(routeHandle)
  defer cancelProc.Call(addressHandle)
  current:=baseline
  var pending m0WindowsPathCoalescer
  for{
   var timer *time.Timer
   var fire <-chan time.Time
   if delay:=pending.remaining(time.Now());delay>=0{
    timer=time.NewTimer(delay)
    fire=timer.C
   }
   var fired bool
   select{
   case <-ctx.Done():
    if timer!=nil{timer.Stop()}
    return
   case <-raw:
    pending.push(time.Now())
   case <-fire:
    fired=true
   }
   if timer!=nil{timer.Stop()}
   if !fired{continue}
   pending.clear()
   next,e:=m0WindowsSelectedPhysicalPath(peer,tunAlias)
   if e!=nil||next==current{continue}
   current=next
   select{case changed<-struct{}{}:default:}
   fmt.Printf("WBD_WINDOWS_NATIVE_PATH_EFFECTIVE_CHANGED ifindex=%d source4=%s source=os_native_ipv4_notification coalesce_quiet_ms=200 max_ms=500\n",
    next.ifindex,next.source4)
  }
 }()
 stop:=func(){cancel();<-done}
 return changed,stop,nil
}

// An actual OS path change can arrive BEFORE FakeTCP/TLS reaches READY.
// Cancel that cold TLS, but join this exact Rust/WAL Stop before starting
// the next original TLS generation (never the per-packet data path).
func m0WindowsRunPathScopedGeneration(
 parent context.Context,physicalChanged <-chan struct{},
 run func(context.Context,<-chan struct{})error,
)error{
 genCtx,cancel:=context.WithCancel(parent)
 generationChanged:=make(chan struct{},1)
 done:=make(chan struct{})
 go func(){
  defer close(done)
  select{
  case <-physicalChanged:
   select{case generationChanged<-struct{}{}:default:}
   cancel()
  case <-genCtx.Done():
  }
 }()
 err:=run(genCtx,generationChanged) // exact owned Stop is synchronous
 cancel()
 <-done
 if parent.Err()!=nil{return err} // user Stop/sleep cannot reauthorize
 if errors.Is(err,realityfront.ErrAdmissionAuth){return err}
 select{
 case <-generationChanged:return errors.Join(errM0WindowsPhysicalPathChanged,err)
 default:
 }
 select{
 case <-physicalChanged:return errors.Join(errM0WindowsPhysicalPathChanged,err)
 default:
 }
 return err
}

func runM0NativeV4Windows(o m0NativeV4Options)error{
 // Mode-specific original Rust capability is queried before Npcap,
 // FakeTCP, signed Wintun or host-global mutations. Game MUST have its
 // own 2/4-lane original TLS socket group; do not run Normal by mistake.
 if err:=m0CheckWindowsV4NativeMode(o.Mode,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"));err!=nil{return err}
 if !o.ServerIP.Is4()||o.ServerPort==0||o.SourcePort==0||
  o.ServerName==""||len(o.RouteKey)!=32||o.Username==""||o.Password==""||
  o.TunnelID==([16]byte{})||o.Installation==([16]byte{})||
  !o.Lease4.IsValid()||!o.Lease4.Addr().Is4()||o.Lease4.Bits()!=32||
  o.Lease4.Addr().IsUnspecified()||o.TunnelMTU<576||o.TunnelMTU>1500||
  o.ConnectionMTU<576||o.ConnectionMTU>1500||o.TunnelMTU>o.ConnectionMTU{
  return windowsclient.ErrN4NativeGuard
 }
 ctx,cancel:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer cancel()
 var autoOperatorRequests chan realityfront.FecV2Profile
 if o.ControlStdin{
  if o.Mode==m0WinModeAuto{
   autoOperatorRequests=make(chan realityfront.FecV2Profile,2)
   go watchM0NativeV4AutoControl(ctx,os.Stdin,cancel,autoOperatorRequests)
  }else{go watchGUIControl(os.Stdin,cancel)}
 }
 slot,err:=acquireGUIClientSlot()
 if err!=nil{return err}
 defer windows.CloseHandle(slot)
 // One native route/address watcher for all original Normal/FEC/Game modes.
 pathChanged,stopPathWatch,err:=watchM0WindowsOriginalPhysicalPath(ctx,o.ServerIP,o.AdapterAlias)
 if err!=nil{return fmt.Errorf("original Windows route/address subscription: %w",err)}
 defer stopPathWatch()
 reauthAuthorized:=false
 pathRecoveryAuthorized:=false
 coldRetries:=0
 for generation:=uint64(1);;{
  if ctx.Err()!=nil{return nil}
  applied:=false
  err:=m0WindowsRunPathScopedGeneration(ctx,pathChanged,
   func(genCtx context.Context,generationChanged <-chan struct{})error{
    return runM0NativeV4WindowsGeneration(
     genCtx,o,generation,autoOperatorRequests,&applied,generationChanged)
   })
  // Only after exact native OS/WAL Stop may the existing Go cold owner
  // establish the next generation on a DIFFERENT physical kernel route.
  if ctx.Err()==nil&&errors.Is(err,errM0WindowsPhysicalPathChanged){
   reauthAuthorized=false
   pathRecoveryAuthorized=true // filtered actual native OS event
   coldRetries=0
   generation++
   fmt.Printf("WBD_WINDOWS_NATIVE_PATH_REAUTHORIZE generation=%d previous_native_joined=1 source=native_ipv4_notification_200_500\n",generation)
   continue
  }
  // After genuine dead90, a new FakeTCP SYN can precede recovery of a
  // 105s one-way outage. Keep GUI alive and retry only cold timeouts,
  // never bypass TLS authentication or reuse the old Rust generation.
  if ctx.Err()==nil && m0WindowsColdPathRetryAllowed(
   o.Mode,reauthAuthorized,pathRecoveryAuthorized,applied,coldRetries,err){
   coldRetries++
   authority:="authenticated_health90"
   if pathRecoveryAuthorized{authority="native_physical_ipv4_path"}
   fmt.Printf("WBD_WINDOWS_ORIGINAL_GO_TLS_COLD_RETRY generation=%d attempt=%d class=timeout authority=%s previous_owner_drained=1\n",generation,coldRetries,authority)
   timer:=time.NewTimer(2*time.Second)
   select{
   case <-ctx.Done():timer.Stop();return nil
   case <-timer.C:
   }
   continue
  }
  if !errors.Is(err,errM0NativeV4AuthenticatedPeerDead)||ctx.Err()!=nil{return err}
  reauthAuthorized=true
  pathRecoveryAuthorized=false
  coldRetries=0
  fmt.Printf("WBD_WINDOWS_NATIVE_DEAD_RECONNECT_ARMED generation=%d old_owner_drained=1\n",generation)
  timer:=time.NewTimer(time.Second)
  select{
  case <-ctx.Done():timer.Stop();return nil
  case <-timer.C:
  }
  generation++
  fmt.Printf("WBD_WINDOWS_ORIGINAL_GO_TLS_REAUTHORIZE generation=%d\n",generation)
 }
}

// One original-Go credential TLS + Rust NativeOwner generation. The caller
// owns GUI/stop and starts the next epoch only after this one's WAL Stop.
func runM0NativeV4WindowsGeneration(ctx context.Context,o m0NativeV4Options,
 generation uint64,autoOperatorRequests <-chan realityfront.FecV2Profile,applied *bool,
 pathChanged <-chan struct{},
)error{
 underlay,err:=windowsclient.DiscoverPhysicalUnderlay(o.ServerIP,0)
 if err!=nil{return err}
 // The actual OS physical egress path, not the inner Wintun interface.
 // This pure Rust budget is installed BEFORE any original SYN and is
 // renewed only after the previous authenticated generation has stopped.
 physicalIface,err:=net.InterfaceByIndex(int(underlay.InterfaceIndex))
 if err!=nil{return err}
 if physicalIface.MTU<576{return windowsclient.ErrN4NativeGuard}
 physical:=uint32(physicalIface.MTU)
 gameFEC:=(o.Mode==m0WinModeGame2||o.Mode==m0WinModeGame4)&&o.FEC2Mode=="fixed"
 cold,err:=m0WindowsV4LocalSYNBudget(
  filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),
  o.ConnectionMTU,physical,o.Mode,gameFEC)
 if err!=nil{return err}
 if err=faketcp.SetPublicV4AdvertisedMSS(uint16(cold.AdvertisedSynMSS));err!=nil{return err}
 if cold.InnerIPCap<o.TunnelMTU{o.TunnelMTU=cold.InnerIPCap}
 reason:="configured_outer_ipv4"
 if physical<o.ConnectionMTU{reason="physical_interface_ipv4"}
 fmt.Printf("WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=%d mode=%v configured_outer_mtu=%d physical_outer_mtu=%d effective_outer_mtu=%d local_advertised_mss=%d inner_mtu_planned=%d limiting_reason=%s source=RUST_V1_REAL_OS\n",
  generation,o.Mode,o.ConnectionMTU,physical,cold.EffectiveOuterIPMTU,
  cold.AdvertisedSynMSS,o.TunnelMTU,reason)
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
  // Genuine Windows2025+WSL2 full product SOURCE e75c37d proved that
  // GetIpForwardTable may return the Windows vEthernet OWN IPv4 as the
  // original underlay next hop for the Linux guest. Only treat that as
  // an on-link WSL guest route when SendARP also resolved the next hop
  // to the ORIGINAL Windows source MAC. The caller already verified
  // actual Linux eth0 IP/MAC and exact Windows ifindex/source via OS
  // readback; third-party proxy/gateway MACs MUST continue to fail.
  onLinkGuest:=guestIP==underlay.NextHop4
  verifiedHostSelfNextHop:=underlay.NextHop4==underlay.Source4&&
   ncfg.NextHopMAC==ncfg.SourceMAC
  source4Verified:=srcErr==nil&&sourceIP==underlay.Source4
  if !source4Verified&&srcErr==nil&&generation>1{
   // Reauthorize only on the actual selected OS source4 of this same
   // physical ifindex and already verified WSL guest. No cached source
   // or raw TLS packet can authorize a new route.
   if selected,liveErr:=m0WindowsSelectedPhysicalPath(o.ServerIP,o.AdapterAlias);liveErr==nil&&
    m0WindowsVerifiedGuestSourceRebound(generation,sourceIP,underlay.Source4,underlay.InterfaceIndex,selected){
    source4Verified=true
    fmt.Printf("WBD_PLAN028_WINDOWS_VERIFIED_NATIVE_SOURCE4_REBOUND generation=%d ifindex=%d source4=%s source=os_selected_egress_only\n",
     generation,underlay.InterfaceIndex,underlay.Source4)
   }
  }
  if parseErr!=nil||macErr!=nil||ipErr!=nil||srcErr!=nil||
   len(parsedMAC)!=6||uint32(idx)!=underlay.InterfaceIndex||
   guestIP!=o.ServerIP||(!onLinkGuest&&!verifiedHostSelfNextHop)||
   !source4Verified{
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
  if verifiedHostSelfNextHop&&!onLinkGuest{
   fmt.Printf("WBD_PLAN024_NATIVE_WSL_GUEST_MAC_OVER_HOST_SELF_NEXTHOP_VERIFIED ifindex=%d guest=%s host_gateway=%s original_self_mac=%x\\n",idx,guestIP,underlay.NextHop4,ncfg.SourceMAC)
  }
  ncfg.NextHopMAC=actual
  fmt.Printf("WBD_PLAN024_NATIVE_ORIGINAL_NPCAP_NEXT_HOP_BOUND ifindex=%d guest_ip=%s mac=%s source=verified_WSL2_eth0\\n",idx,guestIP,guestMAC)
 }
 if o.Mode==m0WinModeGame2||o.Mode==m0WinModeGame4{
  open:=func(local,remote uint16)(*faketcp.NpcapEndpoint,error){
   config,e:=underlay.NpcapConfig(local,remote,1,faketcp.PacketPersonaWindows11)
   if e!=nil{return nil,e}
   config.NextHopMAC=ncfg.NextHopMAC
   return faketcp.OpenNpcapEndpoint(config)
  }
  planForGame:=func()(windowsclient.NetworkPlan,error){
   physical,e:=underlay.PhysicalPath()
   if e!=nil{return windowsclient.NetworkPlan{},e}
   if guestMAC!=""&&physical.NextHop4==underlay.Source4{physical.NextHop4=o.ServerIP}
   return windowsclient.BuildCompactNetworkPlan(windowsclient.Config{
    AdapterAlias:o.AdapterAlias,TunnelMTU:o.TunnelMTU,
    Lease4:o.Lease4,Server4:o.ServerIP,Physical:physical,
    DNSServers4:append([]netip.Addr(nil),o.DNSServers4...),
    Direct4:append([]netip.Prefix(nil),o.Direct4...),
    Bypass4:append([]netip.Prefix(nil),o.Bypass4...),
    StatePath:o.StatePath,
   })
  }
  return runM0NativeV4WindowsGame(ctx,o,underlay.Source4.As4(),physical,open,planForGame,pathChanged)
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
   if seg.Flags&faketcp.FlagSYN!=0{
    wire:=faketcp.MarshalSegment(seg,1,faketcp.PacketPersonaWindows11)
    decoded,decodeErr:=faketcp.ParseIPv4TCP(wire)
    if decodeErr!=nil||!decoded.MSSSet||decoded.MSS!=uint16(cold.AdvertisedSynMSS){
     return windowsclient.ErrN4NativeGuard
    }
    fmt.Printf("WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=%d local_advertised_mss=%d tcp_option_bytes=%x\n",
     generation,decoded.MSS,wire[40:44])
   }
   _,e:=endpoint.WriteSegment(1,seg)
   return e
  })
 if err!=nil{return err}
 defer assoc.Close()
 failure:=make(chan error,2)
 nativeFrames:=make(chan faketcp.Segment,64)
 // Closed exactly at the Go→Rust capture handoff; suppress expected Go
 // ErrNpcapClosed from the departing cold bootstrap reader.
 rustHandoff:=make(chan struct{})
 // Explicit local pre-auth carrier pressure, not WAN loss or authenticated success.
 var ingressLocalDrops atomic.Uint64
 var readers sync.WaitGroup
 readers.Add(1)
 go func(){
  defer readers.Done()
  for{
   seg,_,e:=endpoint.ReadSegment(1)
   if e!=nil{
    select{case <-rustHandoff:return;default:}
    select{case failure<-fmt.Errorf("native NPF ReadSegment failed: %w",e):default:}
    return
   }
   if assoc.State()==faketcp.ClientAssociationDetached{
    // Fixed 64-slot original NPF ingress, Rust M3 remains the sole authenticator.
    // A full pre-auth queue is an explicit LOCAL packet drop, not a valid
    // Rust receipt, TCP carrier acknowledgement or connection-wide Stop.
    select{case nativeFrames<-seg:
    default:
     if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
      select{case failure<-fmt.Errorf("%w: real peer FIN/RST on saturated original NPF ingress",windowsclient.ErrN4NativeGuard):default:}
      return
     }
     ingressLocalDrops.Add(1)
    }
    continue
   }
   if seg.Flags&(faketcp.FlagSYN|faketcp.FlagACK)==(faketcp.FlagSYN|faketcp.FlagACK){
    if !seg.MSSSet||seg.MSS<536||seg.MSS>1460{
     select{case failure<-windowsclient.ErrN4NativeGuard:default:}
     return
    }
    fmt.Printf("WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=%d peer_advertised_mss=%d local_advertised_mss=%d\n",
     generation,seg.MSS,cold.AdvertisedSynMSS)
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
   // Frozen Linux original-Go V3 carrier envelope uses fixed parity 4;
   // this is NOT W168 FEC2 Maximum profile 6. Native Rust FixedStream
   // independently selects profile6 under authenticated feature7.
   1,"fixed",4,4,20,realityfront.CipherChaCha)
 case m0WinModeAuto:
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   1,"auto",0,4,20,realityfront.CipherChaCha)
 default:
  return windowsclient.ErrN4NativeGuard
 }
 if err!=nil{return err}
 // This same DLL has already passed the mode-capability gate. No TLS or
 // WFP mutation occurs until this pure cold result is accepted.
 recordOffer,err:=m0WindowsV4ColdRecordOffer(
  filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),
  o.ConnectionMTU,physical,o.TunnelMTU,o.Mode,false,
 )
 if err!=nil{return err}
 auth:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{ServerName:o.ServerName,
    RouteKey:append([]byte(nil),o.RouteKey...),VerifyServer:true,RootCAs:o.TrustedServerRoots,Timeout:15*time.Second},
  AutoLease:false,DesiredLanes:1,InstallationID:o.Installation[:],
  Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:recordOffer,
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
 fmt.Printf("WBD_WINDOWS_ORIGINAL_GO_TLS_RECORD_CAP_AUTHENTICATED mode=%v requested_tun_mtu=%d client_record_offer=%d original_tls=1\n",o.Mode,o.TunnelMTU,auth.ClientLimit)
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
 physicalPath,e:=underlay.PhysicalPath()
 if e!=nil{return e}
 // Original Go GetIpForwardTable on actual WSL2 returned the host's own
 // vEthernet IPv4 as the next hop; the same scoped OS verified guest-MAC
 // handoff above has already proved real guest IP, source, ifindex and L2
 // identity. For THIS verified route only, use the real guest's IPv4
 // for the Windows persistent underlay /32 escape; never install a route
 // with Windows' own source IP as its gateway. The actual Npcap original
 // link already emits genuine authenticated TCP443 frames to the guest.
 if guestMAC!="" && physicalPath.NextHop4==underlay.Source4{
  physicalPath.NextHop4=o.ServerIP
  fmt.Printf("WBD_PLAN024_NATIVE_WSL_PUBLIC_OS_ROUTE_GUEST_NEXT_HOP scope=verified_guest_ethernet guest=%s ifindex=%d\\n",o.ServerIP,physicalPath.InterfaceIndex)
 }
 plan,e:=windowsclient.BuildCompactNetworkPlan(windowsclient.Config{
  AdapterAlias:o.AdapterAlias,TunnelMTU:o.TunnelMTU,
  Lease4:o.Lease4,Server4:o.ServerIP,Physical:physicalPath,
  DNSServers4:append([]netip.Addr(nil),o.DNSServers4...),
  Direct4:append([]netip.Prefix(nil),o.Direct4...),
  Bypass4:append([]netip.Prefix(nil),o.Bypass4...),
  StatePath:o.StatePath,
 })
 if e!=nil{return e}
 if plan.StatePath==""{return windowsclient.ErrN4NativeGuard}
 var transport m0NativeV4ProductPeer
 // Only explicit CI measurement chooses the retained original Go packet pump.
 // The product default remains the Rust-only Wintun/Npcap NativeOwner; the
 // override does not change original credential TLS, OS WAL or session scope.
 goSteadyAB:=o.Mode==m0WinModeNormal&&os.Getenv("GITHUB_ACTIONS")=="true"&&
  os.Getenv("WBD_WL_PERF_AB_GO_STEADY")=="1"
 if goSteadyAB{fmt.Println("WL_PERF_V2_AB_PATH_GO_STEADY_SOURCE_LOCKED")}
 if !goSteadyAB{
  initial:=realityfront.FecV2Maximum
  autoStart:=realityfront.FecV2Strong
  autoPolicy:=realityfront.FecV2Conservative
  switch o.Mode{
  case m0WinModeNormal:
  case m0WinModeFixed:
   initial,e=m0WindowsV4Profile(o.FEC2Profile)
  case m0WinModeAuto:
   autoStart,e=m0WindowsV4Profile(o.FEC2AutoStartProfile)
   initial=autoStart
   if o.FEC2AutoPolicy=="aggressive"{
    autoPolicy=realityfront.FecV2Aggressive
    if initial<realityfront.FecV2Maximum{initial++}
   }
  default:return windowsclient.ErrN4NativeGuard
  }
  if e!=nil{return e}
  nativePeer:=newM0WinRustNativePeer(owner,endpoint,ncfg,flow,
   nativeFrames,rustHandoff,&readers,o.Mode,initial,autoStart,autoPolicy)
  nativePeer.healthInterval=o.HealthIntervalSeconds
  nativePeer.healthDead=o.HealthDeadSeconds
  nativePeer.healthDormant=o.HealthDormantSeconds
  nativePeer.disableOuterRepair=o.DisableOuterRepair
  transport=nativePeer
 }else{
  // Explicit source-locked A/B only. Never a product Fixed/Auto fallback.
  legacy,legacyErr:=newM0NativeV4PeerForMode(
   owner,endpoint,flow,nativeFrames,m0WinModeNormal)
  if legacyErr!=nil{return legacyErr}
  transport=legacy
 }
 product,e:=windowsownerlease.PrepareOriginalTLSNativeProduct(
  ctx,owner,tun,plan,o.Installation,session.Epoch,transport,
  o.ConnectionMTU,o.TunnelMTU)
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
 // The five-stage OS/WAL receipt alone has no numeric inner MTU. Before
 // publishing READY, run the existing current-generation native MTU CAS
 // inspection and demand equality to the Rust-derived Wintun plan.
 // This read occurs only on cold activation (and existing low-frequency
 // drift checks), never on the packet/FFI hot path.
 actualInner,e:=product.RuntimeMTU(ctx)
 if e!=nil||actualInner!=o.TunnelMTU{
  return errors.Join(fmt.Errorf("Windows owned Wintun OS MTU not applied planned=%d inspected=%d: %w",
   o.TunnelMTU,actualInner,windowsclient.ErrN4NativeGuard),e,cleanup())
 }
 fmt.Printf("WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=%d applied=%d outer_config=%d\n",
  o.TunnelMTU,actualInner,o.ConnectionMTU)
 // If the OS path changed during cold TLS/WFP Apply, do not announce a
 // stale generation as Ready; Stop it before this caller re-authenticates.
 select{
 case <-pathChanged:return errors.Join(errM0WindowsPhysicalPathChanged,cleanup())
 default:
 }
 fmt.Println("WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1")
 // Native OS readback and original Rust M3 peer first+reverse proved.
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 if applied!=nil{*applied=true}
 // Read-only producer counters are emitted at 1 Hz (never per packet)
 // for isolated Windows sustained harness accounting. They do not grant
 // application goodput, CPU/RSS, WFP or product OS receipt.
 // The expensive Go heap/GC JSON telemetry is a test diagnostic, not a
 // production steady heartbeat. A quiet product only checks OS MTU/owner
 // effective state at a coarse cold-control interval.
 diagnostic:=os.Getenv("GITHUB_ACTIONS")=="true"||
  os.Getenv("WBD_NATIVE_TELEMETRY")=="1"
 interval:=30*time.Second
 if diagnostic{interval=time.Second}
 metricsTicker:=time.NewTicker(interval)
 defer metricsTicker.Stop()
 var runtimeErr error
waitNative:
 for{
  select{
  case <-ctx.Done():break waitNative
  case <-pathChanged:
   runtimeErr=errM0WindowsPhysicalPathChanged
   break waitNative
  case runtimeErr=<-failure:runtimeErr=fmt.Errorf("native NPF reader: %w",runtimeErr);break waitNative
  case runtimeErr=<-transport.Errors():runtimeErr=fmt.Errorf("native original Rust peer worker: %w",runtimeErr);break waitNative
  case requested:=<-autoOperatorRequests:
   state,changeErr:=transport.RequestAutoStartProfile(requested)
   if changeErr!=nil{
    fmt.Printf("WBD_WINDOWS_AUTO_REVISION_REJECTED profile=%d reason=%v\n",requested,changeErr)
   }else{
    fmt.Printf("WBD_WINDOWS_AUTO_REVISION_REQUESTED_NOT_APPLIED revision=%d profile=%d\n",
     state.RequestedRevision,state.Desired)
   }
  case <-metricsTicker.C:
   actualMTU,mtuErr:=product.RuntimeMTU(ctx)
   if mtuErr!=nil||actualMTU!=o.TunnelMTU{
    runtimeErr=fmt.Errorf("original M4 OS interface MTU drift/invalid WAL expected=%d actual=%d: %w",
     o.TunnelMTU,actualMTU,errors.Join(windowsclient.ErrN4NativeGuard,mtuErr))
    break waitNative
   }
   if readErr:=transport.RefreshEffective(ctx);readErr!=nil{
    runtimeErr=fmt.Errorf("original Rust M2 effective readback: %w",readErr)
    break waitNative
   }
   if !diagnostic{continue}
   metrics:=transport.Stats()
   // Precisely one Go runtime heap/GC snapshot per second only when
   // opt-in telemetry is enabled. These
   // counters DO NOT represent Rust DLL or kernel allocator activity:
   // the same original Windows EXE process CPU/RSS is sampled separately.
   var goHeap runtime.MemStats
   runtime.ReadMemStats(&goHeap)
   metrics.GoHeapAllocBytes=goHeap.HeapAlloc
   metrics.GoHeapObjects=goHeap.HeapObjects
   metrics.GoMallocsTotal=goHeap.Mallocs
   metrics.GoNumGC=goHeap.NumGC
   metrics.NPFIngressLocalDrops=ingressLocalDrops.Load()
   if line,mErr:=json.Marshal(metrics);mErr==nil{
    fmt.Println("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+string(line))
   }
  }
 }
 if runtimeErr!=nil{
  metrics:=transport.Stats()
  metrics.NPFIngressLocalDrops=ingressLocalDrops.Load()
  if snapshot,marshalErr:=json.Marshal(metrics);marshalErr==nil{
   fmt.Println("WBD_WINDOWS_NATIVE_FAILURE_SOURCE "+runtimeErr.Error()+" stats="+string(snapshot))
  }else{fmt.Println("WBD_WINDOWS_NATIVE_FAILURE_SOURCE "+runtimeErr.Error())}
 }
 stopErr:=cleanup()
 if stopErr!=nil{
  return fmt.Errorf("native owned Stop failed after %v: %w",runtimeErr,stopErr)
 }
 fmt.Println("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")
 return runtimeErr
}

func m0WindowsV4Profile(name string)(realityfront.FecV2Profile,error){
 switch name{
 case "light":return realityfront.FecV2Light,nil
 case "mild":return realityfront.FecV2Mild,nil
 case "medium":return realityfront.FecV2Medium,nil
 case "balanced":return realityfront.FecV2Balanced,nil
 case "high":return realityfront.FecV2High,nil
 case "strong":return realityfront.FecV2Strong,nil
 case "maximum":return realityfront.FecV2Maximum,nil
 default:return 0,fmt.Errorf("unsupported original Linux FEC2 profile %q",name)
 }
}
