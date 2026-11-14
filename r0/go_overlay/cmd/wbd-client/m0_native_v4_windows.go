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
// Windows route/address notifications, with one 1Hz OS interface liveness
// sample in THIS cold watcher when virtual NICs omit MTU-only callbacks.
// No packet callback, second controller, TLS/wire or Rust owner change.
// An OS event or sample is not authentication:
// compare selected physical NIC/source4/real interface IPv4 MTU after 200ms
// quiet / 500ms max; gateway noise and our Wintun's MTU do not rotate TLS.
var errM0WindowsPhysicalPathChanged=errors.New("original Windows physical path changed; exact owned Stop then new TLS")

type m0WindowsPhysicalPath struct{
 ifindex uint32
 source4 netip.Addr
 physicalMTU uint32 // OS-selected underlay NIC, never inner Wintun
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
// Only the explicitly owned CI Windows/WSL2 /24 can reconcile the
// stale GetIpForwardTable next hop with a real OS-selected direct guest.
// All normal native source/ifindex and MAC restrictions remain unchanged.
func m0WindowsVerifiedOwnedWSLRoute(owned bool,generation uint64,
 guest,peer,initial,current netip.Addr,ifindex uint32,selected m0WindowsPhysicalPath,
)bool{
 if !owned||guest.String()!="198.19.254.2"||peer!=guest||
  initial.String()!="198.19.254.1"||
  selected.ifindex!=ifindex||selected.source4!=current{return false}
 if generation==1{return current.String()=="198.19.254.1"}
 return current.String()=="198.19.254.9"
}
// The existing owned-WSL2 test may reauthenticate with exactly the same
// selected host IPv4 after a real interface MTU contraction. Keep this
// exception restricted to the GitHub-owned guest, unchanged NIC and actual
// 1280-byte OS MTU: no broad MAC/route override for unowned interfaces.
func m0WindowsVerifiedOwnedWSLMTUShrink(owned,mtuOnly bool,generation uint64,
 guest,peer,initial,current netip.Addr,ifindex uint32,selected m0WindowsPhysicalPath,
)bool{
 return owned&&mtuOnly&&generation==2&&
  guest.String()=="198.19.254.2"&&peer==guest&&
  initial.String()=="198.19.254.1"&&current==initial&&
  selected.ifindex==ifindex&&selected.source4==current&&
  selected.physicalMTU==1280
}
// Go 1.23's net.Interface.MTU reads GetAdaptersAddresses adapter MTU.
// It is NOT the IPv4 IP-interface NlMtu changed by Set-NetIPInterface.
// Original Go pins golang.org/x/sys/windows v0.33.0, which predates its
// GetIpInterfaceEntry wrapper; retain the documented x64 Win32 row layout
// locally only for this COLD OS readback. No new packet / polling loop.
type m0WindowsIPInterfaceRow struct{
 Family uint16
 InterfaceLuid uint64
 InterfaceIndex uint32
 MaxReassemblySize uint32
 InterfaceIdentifier uint64
 MinRouterAdvertisementInterval uint32
 MaxRouterAdvertisementInterval uint32
 AdvertisingEnabled uint8
 ForwardingEnabled uint8
 WeakHostSend uint8
 WeakHostReceive uint8
 UseAutomaticMetric uint8
 UseNeighborUnreachabilityDetection uint8
 ManagedAddressConfigurationSupported uint8
 OtherStatefulConfigurationSupported uint8
 AdvertiseDefaultRoute uint8
 RouterDiscoveryBehavior uint32
 DadTransmits uint32
 BaseReachableTime uint32
 RetransmitTime uint32
 PathMtuDiscoveryTimeout uint32
 LinkLocalAddressBehavior uint32
 LinkLocalAddressTimeout uint32
 ZoneIndices [16]uint32
 SitePrefixLength uint32
 Metric uint32
 NlMtu uint32
 Connected uint8
 SupportsWakeUpPatterns uint8
 SupportsNeighborDiscovery uint8
 SupportsRouterDiscovery uint8
 ReachableTime uint32
 TransmitOffload uint32
 ReceiveOffload uint32
 DisableDefaultRoutes uint8
}
func m0WindowsPhysicalIPv4NLMTU(ifindex uint32)(uint32,error){
 row:=m0WindowsIPInterfaceRow{Family:uint16(syscall.AF_INET),InterfaceIndex:ifindex}
 if ifindex==0||unsafe.Sizeof(row)!=176||
  unsafe.Offsetof(row.InterfaceIndex)!=16||
  unsafe.Offsetof(row.NlMtu)!=152{
  return 0,windowsclient.ErrN4NativeGuard
 }
 proc:=windows.NewLazySystemDLL("iphlpapi.dll").NewProc("GetIpInterfaceEntry")
 if err:=proc.Find();err!=nil{return 0,err}
 status,_,_:=proc.Call(uintptr(unsafe.Pointer(&row)))
 if status!=0{return 0,syscall.Errno(status)}
 if row.Family!=uint16(syscall.AF_INET)||
  row.InterfaceIndex!=ifindex||row.NlMtu<576||row.NlMtu>65535{
  return 0,windowsclient.ErrN4NativeGuard
 }
 return row.NlMtu,nil
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
 ipv4NLMTU,err:=m0WindowsPhysicalIPv4NLMTU(underlay.InterfaceIndex)
 if err!=nil{return zero,err}
 return m0WindowsPhysicalPath{ifindex:underlay.InterfaceIndex,source4:underlay.Source4,physicalMTU:ipv4NLMTU},nil
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

// Some Windows WSL2 IPv4 IP-interface NlMtu writes do not emit a native
// NotifyIpInterfaceChange after the caller receives successful OS readback.
// Only the already selected physical NIC/IP+MTU is eligible. The cold
// controller must still coalesce and verify a second OS read before Stop;
// errors, missing source or our own Wintun never authorize new TLS.
// Original NPF/TLS server owns a raw 4-tuple through detached Rust M4
// cleanup, potentially beyond the client's exact owned Stop. A new
// credential-TLS generation on the SAME physical IP must NOT reuse its
// old TCP client tuple. Preserve user-configured source port on generation1;
// only cold successor Normal/FEC starts on a new local port. No wire/ABI
// change, server still listens on the ONE original port443.
//
// Wrap into the dynamic/private range rather than ever generating port0.
// The collision/multi-client boundary remains subject to L0 coverage;
// this helper is not a platform-wide reservation service.
func m0WindowsOriginalColdClientPort(configured uint16,generation uint64)(uint16,error){
 if configured==0||generation==0{return 0,windowsclient.ErrN4NativeGuard}
 if generation==1{return configured,nil}
 step:=(generation-1)%65535
 candidate:=uint64(configured)+step
 if candidate>65535{candidate=49152+(candidate-65536)%16384}
 if candidate==uint64(configured){return 0,windowsclient.ErrN4NativeGuard}
 return uint16(candidate),nil
}
func m0WindowsPhysicalPathLivenessChanged(current,next m0WindowsPhysicalPath,err error)bool{
 return err==nil&&next.ifindex!=0&&next.source4.Is4()&&
  next.physicalMTU>=576&&next!=current
}

// Native route, unicast-address, and IP-interface (including NlMtu) change
// notifications are asynchronous IP Helper subscriptions. Their WinAPI callbacks only wake one buffered
// channel; actual OS readback, TLS, WFP and Stop remain on ordinary Go threads.
func watchM0WindowsOriginalPhysicalPath(
 parent context.Context,peer netip.Addr,tunAlias string,
)(<-chan struct{},func(),error){
 baseline,err:=m0WindowsSelectedPhysicalPath(peer,tunAlias)
 if err!=nil{return nil,nil,err}
 dll:=windows.NewLazySystemDLL("iphlpapi.dll")
 routeProc:=dll.NewProc("NotifyRouteChange2")
 addressProc:=dll.NewProc("NotifyUnicastIpAddressChange")
 interfaceProc:=dll.NewProc("NotifyIpInterfaceChange")
 cancelProc:=dll.NewProc("CancelMibChangeNotify2")
 for _,p:=range []*windows.LazyProc{routeProc,addressProc,interfaceProc,cancelProc}{
  if err=p.Find();err!=nil{return nil,nil,err}
 }
 raw:=make(chan struct{},1)
 cb:=syscall.NewCallback(func(_,_,_ uintptr)uintptr{
  select{case raw<-struct{}{}:default:}
  return 0
 })
 var routeHandle,addressHandle,interfaceHandle uintptr
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
 if status,_,_:=interfaceProc.Call(uintptr(syscall.AF_INET),cb,0,0,
  uintptr(unsafe.Pointer(&interfaceHandle)));status!=0{
  cancelProc.Call(addressHandle)
  cancelProc.Call(routeHandle)
  return nil,nil,syscall.Errno(status)
 }
 // Cover NIC/source/MTU transition between baseline and native subscription setup.
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
  defer cancelProc.Call(interfaceHandle)
  current:=baseline
  var pending m0WindowsPathCoalescer
  liveness:=time.NewTicker(time.Second)
  defer liveness.Stop()
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
   case <-liveness.C:
    // Same goroutine, cold path only: no second watcher or new callback.
    next,e:=m0WindowsSelectedPhysicalPath(peer,tunAlias)
    if os.Getenv("WBD_PLAN028_WSL_OWNED_MTU_ONLY")=="1"&&
     os.Getenv("GITHUB_ACTIONS")=="true"{
     fmt.Printf("WBD_WINDOWS_NATIVE_IPV4_NLMTU_LIVENESS_SAMPLE ifindex=%d current_mtu=%d observed_mtu=%d observed_source4=%s error=%t source=GetIpInterfaceEntry_1Hz\n",
      current.ifindex,current.physicalMTU,next.physicalMTU,next.source4,e!=nil)
    }
    if m0WindowsPhysicalPathLivenessChanged(current,next,e){
     // A sampled MTU delta does not authorize a path: arm the SAME
     // bounded coalescer and re-read the complete selected OS path.
     pending.push(time.Now())
     fmt.Printf("WBD_WINDOWS_NATIVE_IPV4_NLMTU_LIVENESS_CHANGED ifindex=%d old_mtu=%d observed_mtu=%d source=one_existing_cold_watcher\n",
      current.ifindex,current.physicalMTU,next.physicalMTU)
    }
   case <-fire:
    fired=true
   }
   if timer!=nil{timer.Stop()}
   if !fired{continue}
   pending.clear()
   next,e:=m0WindowsSelectedPhysicalPath(peer,tunAlias)
   if os.Getenv("WBD_PLAN028_WSL_OWNED_MTU_ONLY")=="1"&&
    os.Getenv("GITHUB_ACTIONS")=="true"{
    fmt.Printf("WBD_WINDOWS_NATIVE_IPV4_NLMTU_EVENT_RECHECK ifindex=%d old_mtu=%d new_mtu=%d error=%t source=GetIpInterfaceEntry\n",
     current.ifindex,current.physicalMTU,next.physicalMTU,e!=nil)
   }
   if e!=nil||next==current{continue}
   current=next
   select{case changed<-struct{}{}:default:}
   fmt.Printf("WBD_WINDOWS_NATIVE_PATH_EFFECTIVE_CHANGED ifindex=%d source4=%s physical_mtu=%d source=os_native_ipv4_notification_or_cold_liveness coalesce_quiet_ms=200 max_ms=500 observed_unix_ns=%d\n",
    next.ifindex,next.source4,next.physicalMTU,time.Now().UnixNano())
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

// Production GUI remains one machine-wide original native owner. The prior
// H1381 two-Wintun witness and H1515 five-Wintun witness are disjoint,
// GitHub-Actions-only named OS event scopes. An account, independent /32,
// exact adapter alias and owned WAL filename must ALL agree before TLS.
// There is no CLI/config or remote-peer bypass of the production singleton.
func m0Plan028WindowsNativeClientSlot(o m0NativeV4Options)(windows.Handle,error){
 ci:=os.Getenv("GITHUB_ACTIONS")=="true"
 two:=ci&&os.Getenv("WBD_PLAN028_TWO_REAL_CLIENTS")=="1"
 five:=ci&&!two&&os.Getenv("WBD_PLAN028_FIVE_REAL_CLIENTS")=="1"
 if !two&&!five{return acquireGUIClientSlot()}
 expectedUser:=""
 expectedLease:=""
 if two{
  switch o.AdapterAlias{
  case "WBDWLCLIENTA":expectedUser="alice";expectedLease="10.66.0.2/32"
  case "WBDWLCLIENTB":expectedUser="bob";expectedLease="10.66.0.3/32"
  default:return 0,windowsclient.ErrN4NativeGuard
  }
 }else{
  switch o.AdapterAlias{
  case "WBDWL5A0":expectedUser="alice";expectedLease="10.66.0.2/32"
  case "WBDWL5B1":expectedUser="bob";expectedLease="10.66.0.3/32"
  case "WBDWL5C2":expectedUser="carol";expectedLease="10.66.0.4/32"
  case "WBDWL5D3":expectedUser="dave";expectedLease="10.66.0.5/32"
  case "WBDWL5E4":expectedUser="erin";expectedLease="10.66.0.6/32"
  default:return 0,windowsclient.ErrN4NativeGuard
  }
 }
 state:=strings.ToLower(o.StatePath)
 if o.Username!=expectedUser||!o.Lease4.IsValid()||
    !(o.Lease4.String()==expectedLease||
      (o.AutoLease&&o.Lease4.String()=="0.0.0.0/32"))||len(o.StatePath)<12||
    !strings.HasSuffix(state,".json")||
    (two&&!strings.Contains(state,strings.ToLower(o.AdapterAlias)))||
    (five&&!strings.EqualFold(filepath.Base(state),"h1506-owned-"+expectedUser+".json")){
    return 0,windowsclient.ErrN4NativeGuard
 }
 name,e:=windows.UTF16PtrFromString("Local\\WBD-NEXT-PLAN028-ORIGINAL-V4-"+o.AdapterAlias)
 if e!=nil{return 0,e}
 h,e:=windows.CreateEvent(nil,1,0,name)
 if e!=nil{
  if h!=0{_ = windows.CloseHandle(h)}
  return 0,errors.New("original Windows product device already owned or cleaning up")
 }
 fmt.Printf("WBD_PLAN028_CI_NATIVE_DEVICE_SLOT_OWNED adapter=%s lease=%s owner=one_alias_only\n",o.AdapterAlias,o.Lease4)
 return h,nil
}
func runM0NativeV4Windows(o m0NativeV4Options)error{
 // Game2/Game4 still use their original Game Rust owner. Explicit CN
 // split cannot be silently accepted without a corresponding Game actor.
 if o.SplitEnable&&(o.Mode==m0WinModeGame2||o.Mode==m0WinModeGame4){
  return fmt.Errorf("PLAN029 CN split Game2/4 not wired; no OS Apply attempted")
 }
 // Mode-specific original Rust capability is queried before Npcap,
 // FakeTCP, signed Wintun or host-global mutations. Game MUST have its
 // own 2/4-lane original TLS socket group; do not run Normal by mistake.
 if err:=m0CheckWindowsV4NativeMode(o.Mode,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"));err!=nil{return err}
 if (o.ServerHost==""&&!o.ServerIP.Is4())||o.ServerPort==0||o.SourcePort==0||
  o.ServerName==""||len(o.RouteKey)!=32||o.Username==""||o.Password==""||
  o.TunnelID==([16]byte{})||o.Installation==([16]byte{})||
  !o.Lease4.IsValid()||!o.Lease4.Addr().Is4()||o.Lease4.Bits()!=32||
  (o.AutoLease!=o.Lease4.Addr().IsUnspecified())||
  (o.RecordCipher!=realityfront.CipherChaCha&&o.RecordCipher!=realityfront.CipherAES128&&o.RecordCipher!=realityfront.CipherAES256)||
  o.TunnelMTU<576||o.TunnelMTU>1500||
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
 slot,err:=m0Plan028WindowsNativeClientSlot(o)
 if err!=nil{return err}
 defer windows.CloseHandle(slot)
 // Numeric IPv4 preserves its old original watcher. DNS hostname re-resolves
 // after the previous WAL Stop has joined, before each NEW cold TLS epoch.
 var pathChanged <-chan struct{}
 var stopPathWatch func()
 defer func(){if stopPathWatch!=nil{stopPathWatch()}}()
 reauthAuthorized:=false
 pathRecoveryAuthorized:=false
 coldRetries:=0
 for generation:=uint64(1);;{
  if ctx.Err()!=nil{return nil}
  if stopPathWatch==nil||o.ServerHost!=""{
   if stopPathWatch!=nil{stopPathWatch();stopPathWatch=nil}
   if o.ServerHost!=""{
    resolved,e:=windowsclient.ResolveServerAFromOriginalPhysical(ctx,o.ServerHost,o.AdapterAlias,o.DirectDNS4)
    if e!=nil{return fmt.Errorf("PLAN029 physical DNS server address: %w",e)}
    o.ServerIP=resolved.Selected4
    fmt.Printf("WBD_PLAN029_BOOTSTRAP_DNS_SELECTED generation=%d host=%s selected4=%s physical_source4=%s physical_ifindex=%d resolver4=%s candidates=%d source=physical_Npcap_dns_A\n",
     generation,o.ServerHost,o.ServerIP,resolved.PhysicalSource4,resolved.PhysicalIfIndex,resolved.Resolver4,len(resolved.Candidate4))
   }
   var e error
   pathChanged,stopPathWatch,e=watchM0WindowsOriginalPhysicalPath(ctx,o.ServerIP,o.AdapterAlias)
   if e!=nil{return fmt.Errorf("original Windows route/address subscription: %w",e)}
  }
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
 selected,err:=m0WindowsSelectedPhysicalPath(o.ServerIP,o.AdapterAlias)
 if err!=nil{return err}
 if selected.ifindex!=underlay.InterfaceIndex||selected.source4!=underlay.Source4{
  return windowsclient.ErrN4NativeGuard
 }
 physical:=selected.physicalMTU // EXACT IPv4 NlMtu also used by native path watcher
 fmt.Printf("WBD_WINDOWS_COLD_PHYSICAL_IPV4_NLMTU_READBACK generation=%d ifindex=%d source4=%s physical_mtu=%d source=Win32_GetIpInterfaceEntry\n",
  generation,selected.ifindex,selected.source4,physical)
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
 // A successor with the same source IPv4 cannot reuse the exact old
 // detached Linux raw 4-tuple. Game already manages its own multi-lane
 // local tuple set, so only Normal/Fixed/Auto use this cold port.
 coldSourcePort:=o.SourcePort
 if o.Mode!=m0WinModeGame2&&o.Mode!=m0WinModeGame4{
  coldSourcePort,err=m0WindowsOriginalColdClientPort(o.SourcePort,generation)
  if err!=nil{return err}
  fmt.Printf("WBD_WINDOWS_COLD_TLS_CLIENT_PORT generation=%d configured_port=%d source_port=%d original_peer_port=%d same_ip_reauth_safe_tuple=%t\n",
   generation,o.SourcePort,coldSourcePort,o.ServerPort,coldSourcePort!=o.SourcePort)
 }
 ncfg,err:=underlay.NpcapConfig(coldSourcePort,o.ServerPort,1,faketcp.PacketPersonaWindows11)
 if err!=nil{return err}
 // PLAN024 original public Windows↔WSL2 real-NPF correction. Genuine
 // SendARP returned the WINDOWS vEthernet source MAC for a real WSL2
 // guest destination. This would send a SYN to ourselves, not the server.
 // Only the single CI-owned, OS-readback-verified guest MAC may override
 // that self resolution, and only when peer/interface/source all match.
 // Original production discovery remains the default outside that scope.
 guestMAC := os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC")
 ownedGuestOnLink:=false
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
  // The CI fixture already OS-verified guest IP/MAC, selected host
  // source and same ifindex; third-party routes stay fail-closed.
  if os.Getenv("GITHUB_ACTIONS")=="true"&&
   os.Getenv("WBD_PLAN028_WSL_OWNED_SWITCH")=="1"&&
   parseErr==nil&&ipErr==nil&&srcErr==nil{
   if selected,e:=m0WindowsSelectedPhysicalPath(o.ServerIP,o.AdapterAlias);e==nil{
    ownedGuestOnLink=m0WindowsVerifiedOwnedWSLRoute(true,generation,
     guestIP,o.ServerIP,sourceIP,underlay.Source4,underlay.InterfaceIndex,selected)||
     m0WindowsVerifiedOwnedWSLMTUShrink(true,
      os.Getenv("WBD_PLAN028_WSL_OWNED_MTU_ONLY")=="1",generation,
      guestIP,o.ServerIP,sourceIP,underlay.Source4,underlay.InterfaceIndex,selected)
   }
  }
  if parseErr!=nil||macErr!=nil||ipErr!=nil||srcErr!=nil||
   len(parsedMAC)!=6||uint32(idx)!=underlay.InterfaceIndex||
   guestIP!=o.ServerIP||(!onLinkGuest&&!verifiedHostSelfNextHop&&!ownedGuestOnLink)||
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
  if ncfg.NextHopMAC!=ncfg.SourceMAC&&ncfg.NextHopMAC!=actual&&!ownedGuestOnLink{
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
  planForGame:=func(verifiedLease netip.Prefix)(windowsclient.NetworkPlan,error){
   physical,e:=underlay.PhysicalPath()
   if e!=nil{return windowsclient.NetworkPlan{},e}
   if guestMAC!=""&&(physical.NextHop4==underlay.Source4||ownedGuestOnLink){physical.NextHop4=o.ServerIP}
   return windowsclient.BuildCompactNetworkPlan(windowsclient.Config{
    AdapterAlias:o.AdapterAlias,TunnelMTU:o.TunnelMTU,
    Lease4:verifiedLease,Server4:o.ServerIP,Physical:physical,
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
  LocalPort:coldSourcePort,PeerPort:o.ServerPort,
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
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   1,"off",0,4,20,o.RecordCipher)
 case m0WinModeFixed:
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   // Frozen Linux original-Go V3 carrier envelope uses fixed parity 4;
   // this is NOT W168 FEC2 Maximum profile 6. Native Rust FixedStream
   // independently selects profile6 under authenticated feature7.
   1,"fixed",4,4,20,o.RecordCipher)
 case m0WinModeAuto:
  policy,err=realityfront.PolicyForClientWithInitialAndCipher(
   1,"auto",0,4,20,o.RecordCipher)
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
  AutoLease:o.AutoLease,DesiredLanes:1,InstallationID:o.Installation[:],
  Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:recordOffer,
  LaneID:1,Policy:policy,
 }
 dll:=filepath.Join(windowsExecutableDir(),"wbd_engine.dll")
 if !filepath.IsAbs(dll){return windowsclient.ErrN4NativeGuard}
 // The SYN retransmission tick above used to STOP being consumed when
 // WaitEstablished succeeded. During original credential TLS the FakeTCP
 // sender can still have unacknowledged real ClientHello/admission bytes.
 // On a physically lossy 200ms path, a lost bootstrap payload otherwise
 // never gets RetransmitDue and the old 15s candidate deadline expires.
 // Drive the SAME original association/Sender, not another TCP stack,
 // while protected TLS runs. Stop/join before Rust Detach/native M3 takes
 // over the encrypted data path. Default TLS deadline stays 15s.
 coldPumpStop:=make(chan struct{})
 coldPumpDone:=make(chan struct{})
 coldPumpError:=make(chan error,1)
 var coldRetransmits uint32
 go func(){
  defer close(coldPumpDone)
  for{
   select{
   case <-ctx.Done():return
   case <-coldPumpStop:return
   case <-ticker.C:
    if assoc.State()!=faketcp.ClientAssociationEstablished{return}
    resent,e:=assoc.EmitRetransmitDue(time.Now())
    if e!=nil{
     select{case coldPumpError<-e:default:}
     assoc.Close() // Fail closed and unblock genuine TLS on kernel TX failure.
     return
    }
    if resent{coldRetransmits++}
   }
  }
 }()
 coldPumpStopped:=false
 stopColdPump:=func(){
  if !coldPumpStopped{
   close(coldPumpStop)
   <-coldPumpDone
   coldPumpStopped=true
  }
 }
 defer stopColdPump()
 // Validate Fixed profile BEFORE entering the protected TLS call; no
 // early-return path may leave the original cold retransmit pump alive.
 fixedProfilePlusOne:=uint8(0)
 if o.Mode==m0WinModeFixed{
  selected,profileErr:=m0WindowsV4Profile(o.FEC2Profile)
  if profileErr!=nil{return profileErr}
  fixedProfilePlusOne=uint8(selected)+1
 }
 var owner *realityfront.V4WindowsAuthenticatedClientOwner
 var session *realityfront.V4ClientSession
 if o.Mode==m0WinModeNormal{
  owner,session,err=realityfront.V4WindowsEstablishOriginalClientOwner(ctx,dll,assoc,auth)
 }else{
  // Protected feature7 and the server's exact authenticated profile are
  // unchanged; this worker only retransmits original Go bootstrap segments.
  owner,session,err=realityfront.V4WindowsEstablishOriginalFEC2ClientOwner(ctx,dll,assoc,auth,fixedProfilePlusOne)
 }
 stopColdPump()
 fmt.Printf("WBD_WINDOWS_ORIGINAL_TLS_COLD_FAKETCP_RETRANSMIT copied=%d joined_before_Rust_M3=1 source=original_Go_Sender_RTO\n",coldRetransmits)
 select{
 case retryErr:=<-coldPumpError:
  var stopErr error
  if owner!=nil{
   stop,c:=context.WithTimeout(context.Background(),15*time.Second)
   stopErr=owner.StopScopedOwner(stop)
   c()
  }
  return errors.Join(err,fmt.Errorf("original Windows cold TLS FakeTCP retransmit kernel failure: %w",retryErr),stopErr)
 default:
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
 // A protected server reply is the ONLY source of an automatic /32.
 // The manual path still pins the explicit OS lease. No unverified local
 // lease may ever reach the owned Wintun/WFP/route transaction.
 trustedLease,e:=session.AuthenticatedLeaseIPv4()
 if e!=nil{return fmt.Errorf("protected Windows lease readback: %w",e)}
 snapshot,e:=session.ColdSnapshot()
 if e!=nil||snapshot.Cipher()!=o.RecordCipher{
  return fmt.Errorf("%w: protected Windows per-client record cipher mismatch: %v",windowsclient.ErrN4NativeGuard,e)
 }
 if o.AutoLease{
  assigned,parseErr:=netip.ParsePrefix(trustedLease)
  if parseErr!=nil||!assigned.IsValid()||!assigned.Addr().Is4()||
   assigned.Bits()!=32||assigned.Addr().IsUnspecified()||
   assigned.Addr().IsMulticast(){
   return fmt.Errorf("%w: server did not authenticate a usable auto IPv4 /32: %v",windowsclient.ErrN4NativeGuard,parseErr)
  }
  o.Lease4=assigned
 }else if trustedLease!=""&&trustedLease!=o.Lease4.String(){
  return fmt.Errorf("%w: server protected lease conflicts with configured manual Wintun /32",windowsclient.ErrN4NativeGuard)
 }
 fmt.Printf("WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION mode=%v auto_lease=%t lease=%s cipher=%d source=original_TLS_Rust_snapshot\n",
  o.Mode,o.AutoLease,o.Lease4,snapshot.Cipher())
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
 if guestMAC!="" && (physicalPath.NextHop4==underlay.Source4||ownedGuestOnLink){
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
 var tcpSynthetic netip.Addr
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
  // PLAN029 cold source: explicit saved opt-in OR source-locked CI trial.
  // Actual signed driver/OS/owner receipt below determines Applied/Ready.
  trial,e:=m0Plan029TrialCold(o,underlay.Source4,
   physicalPath.InterfaceIndex,o.Lease4.Addr(),o.TunnelMTU,session.Epoch)
  if e!=nil{return fmt.Errorf("PLAN029 original Go cold V3 rejected: %w",e)}
  if trial!=nil{
   nativePeer.plan029Cold=trial
   if trial.TCPSynthetic4!=[4]byte{}{tcpSynthetic=netip.AddrFrom4(trial.TCPSynthetic4)}
   fmt.Printf("WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=%s direct_dns=%v tunnel_dns=%v cn_rows=%d domain_bytes=%d inner_mtu=%d single_original_owner=1 source=%s readiness=AWAIT_REAL_OS_RUST_RECEIPT\\n",
    o.RouteMode,trial.DirectDNS,trial.TunnelDNS,len(trial.CN),len(trial.Domains),trial.InnerMTU,
    map[bool]string{true:"explicit_config",false:"source_locked_CI_trial"}[o.SplitEnable])
  }
  transport=nativePeer
 }else{
  // Explicit source-locked A/B only. Never a product Fixed/Auto fallback.
  legacy,legacyErr:=newM0NativeV4PeerForMode(
   owner,endpoint,flow,nativeFrames,m0WinModeNormal)
  if legacyErr!=nil{return legacyErr}
  transport=legacy
 }
 var product *windowsownerlease.OriginalTLSNativeProductSession
 if tcpSynthetic.IsValid(){
  product,e=windowsownerlease.PrepareOriginalTLSNativeProductWithSyntheticTCP(
   ctx,owner,tun,plan,o.Installation,session.Epoch,transport,
   tcpSynthetic,o.ConnectionMTU,o.TunnelMTU)
 }else{
  product,e=windowsownerlease.PrepareOriginalTLSNativeProduct(
   ctx,owner,tun,plan,o.Installation,session.Epoch,transport,
   o.ConnectionMTU,o.TunnelMTU)
 }
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
 if tcpSynthetic.IsValid(){
  // A cold-only, authenticated same-Rust-owner transition after actual
  // four-stage Win32 Applied. Do not publish TCP Ready from source proof.
  port,tcpErr:=owner.Plan029PrepareNativeTCPAfterOSApply(ctx)
  if tcpErr!=nil{return errors.Join(fmt.Errorf("PLAN029 post-Apply TCP PREPARE: %w",tcpErr),cleanup())}
  if tcpErr=product.Plan029ArmOwnedDirectTCP(ctx,port);tcpErr!=nil{
   return errors.Join(fmt.Errorf("PLAN029 exact owned Defender Allow: %w",tcpErr),cleanup())
  }
  if tcpErr=owner.Plan029EnableNativeTCPAfterDefender(ctx,port);tcpErr!=nil{
   return errors.Join(fmt.Errorf("PLAN029 Rust TCP ENABLE: %w",tcpErr),cleanup())
  }
  fmt.Printf("WBD_PLAN029_NATIVE_DIRECT_TCP_ENABLED_COLD port=%d synthetic=%s exact_owned_allow=1 product_e2e=NOT_RUN\n",port,tcpSynthetic)
  select{
  case <-pathChanged:return errors.Join(errM0WindowsPhysicalPathChanged,cleanup())
  default:
  }
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
