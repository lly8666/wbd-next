//go:build windows && wbd_v4_embedded_go
package main
import("net/netip";"time";"context";"errors";"fmt";"syscall";"testing";"unsafe";"github.com/lly8666/wobuzhidao/internal/faketcp";"github.com/lly8666/wobuzhidao/internal/realityfront")
func TestM0PLAN027WindowsColdRetryRequiresAuthenticatedDeadAndNoAppliedOS(t *testing.T){
 timeout:=fmt.Errorf("original cold FakeTCP: %w",faketcp.ErrBootstrapTimeout)
 for _,e:=range []error{timeout,fmt.Errorf("network timed out: %w",context.DeadlineExceeded),syscall.ETIMEDOUT}{
  if !m0WindowsOriginalColdRetryAllowed(true,false,0,e){
   t.Fatalf("post-dead transient cold transport must retry: %v",e)
  }
 }
 for _,row:=range []struct{
  name string
  authorized,applied bool
  retry int
  err error
 }{
  {"initial_cold",false,false,0,timeout},
  {"already_applied",true,true,0,timeout},
  {"limit",true,false,2,timeout},
  {"auth_rejection",true,false,0,errors.New("credentials rejected")},
  {"tls_invariant",true,false,0,errors.New("certificate mismatch")},
  {"no_error",true,false,0,nil},
 }{
  t.Run(row.name,func(t *testing.T){
   if m0WindowsOriginalColdRetryAllowed(row.authorized,row.applied,row.retry,row.err){
    t.Fatal("must remain fail-closed")
   }
  })
 }
}

func TestM0PLAN027WindowsNativeAuthDeadOnlyAfterOriginalRustHealth(t *testing.T){
 if !errors.Is(m0WindowsRustNativeWorkerError(6),errM0NativeV4AuthenticatedPeerDead){
  t.Fatal("Rust authenticated dead90 must reauthorize Go cold TLS after owned Stop")
 }
 for _,code:=range []int32{1,2,3,4,5,7,9}{
  if errors.Is(m0WindowsRustNativeWorkerError(code),errM0NativeV4AuthenticatedPeerDead){
   t.Fatalf("nonauthenticated failure code=%d must remain fatal",code)
  }
 }
}

// Windows native Go no longer carries a duplicate 31/14/16/15 formula
// or hidden 1400 cap. Production cold TLS consumes the versioned Rust ABI.
// These tests validate only C layout and mode mapping; numerical vectors
// live in Rust v4_mtu_budget_ffi::receive_tests.
func TestM0PLAN027AWindowsColdBudgetABIShapeAndModes(t *testing.T){
 if n:=unsafe.Sizeof(m0RustColdBudgetInput{});n!=36{
  t.Fatalf("Rust cold input layout changed: %d",n)
 }
 if n:=unsafe.Sizeof(m0RustColdReceiveInput{});n!=40{
  t.Fatalf("Rust cold receiving input layout changed: %d",n)
 }
 if n:=unsafe.Sizeof(m0RustColdBudgetOutput{});n!=32{
  t.Fatalf("Rust cold output layout changed: %d",n)
 }
 for _,row:=range []struct{mode m0WindowsV4Mode;fec bool;want uint32}{
  {m0WinModeNormal,false,0},
  {m0WinModeFixed,false,1},
  {m0WinModeAuto,false,1},
  {m0WinModeGame2,false,2},
  {m0WinModeGame4,false,2},
  {m0WinModeGame2,true,3},
  {m0WinModeGame4,true,3},
 }{
  got,err:=m0WindowsV4BudgetMode(row.mode,row.fec)
  if err!=nil||got!=row.want{
   t.Fatalf("mode=%s gameFEC=%v Rust kind=%d err=%v want=%d",
    row.mode,row.fec,got,err,row.want)
  }
 }
 for _,row:=range []m0WindowsV4Mode{"",m0WindowsV4Mode("future"),m0WinModeFixed,m0WinModeNormal}{
  fec:=row==m0WinModeFixed||row==m0WinModeNormal
  if _,err:=m0WindowsV4BudgetMode(row,fec);err==nil{
   t.Fatalf("unknown/unsupported FEC mode=%s must reject",row)
  }
 }
}


func TestM0PLAN028NativeWindowsIPv4CallbackCoalescer(t *testing.T){
 start:=time.Unix(1000,0);var c m0WindowsPathCoalescer
 if c.remaining(start)!=-1{t.Fatal("not armed")}
 c.push(start)
 if c.remaining(start)!=200*time.Millisecond{t.Fatal("200ms quiet")}
 c.push(start.Add(190*time.Millisecond))
 if c.remaining(start.Add(200*time.Millisecond))!=190*time.Millisecond{t.Fatal("no coalescing")}
 for ms:=210;ms<=490;ms+=20{c.push(start.Add(time.Duration(ms)*time.Millisecond))}
 if c.remaining(start.Add(495*time.Millisecond))!=5*time.Millisecond||c.remaining(start.Add(500*time.Millisecond))!=0{t.Fatal("no 500ms absolute bound")}
 c.clear();if c.remaining(start.Add(time.Second))!=-1{t.Fatal("not cleared")}
}
// Win32 MIB_IPINTERFACE_ROW is an actual x64 IP-layer NlMtu receipt,
// unlike net.Interface.MTU (physical adapter MTU). The donor pins x/sys
// v0.33.0 before its GetIpInterfaceEntry wrapper; verify our local ABI.
func TestM0PLAN028WindowsIPv4NlMtuMIBRowABI(t *testing.T){
 var row m0WindowsIPInterfaceRow
 if unsafe.Sizeof(row)!=176||unsafe.Offsetof(row.InterfaceLuid)!=8||
  unsafe.Offsetof(row.InterfaceIndex)!=16||
  unsafe.Offsetof(row.NlMtu)!=152||
  unsafe.Offsetof(row.DisableDefaultRoutes)!=172{
  t.Fatalf("original Win32 MIB_IPINTERFACE_ROW layout mismatch size=%d NlMtuOffset=%d",
   unsafe.Sizeof(row),unsafe.Offsetof(row.NlMtu))
 }
 if mtu,err:=m0WindowsPhysicalIPv4NLMTU(0);err==nil||mtu!=0{
  t.Fatal("invalid physical index must fail closed without Win32 API call")
 }
}

func TestM0PLAN028NativeWindowsOnlyPhysicalNICSourceIPv4(t *testing.T){
 a:=m0WindowsPhysicalPath{ifindex:8,source4:netip.MustParseAddr("192.0.2.11"),physicalMTU:1500}
 b:=a;b.source4=netip.MustParseAddr("192.0.2.12");if b==a{t.Fatal("IPv4 change")}
 b=a;b.ifindex=9;if b==a{t.Fatal("NIC change")}
 b=a;b.physicalMTU=1280;if b==a{t.Fatal("same NIC/source with real OS MTU contraction must reauthorize cold TLS")}
 b=a;b.physicalMTU=1500;if b!=a{t.Fatal("identical physical snapshot must not reauthorize")}
 // The selected physical NIC fingerprint must not depend on the separate
 // Wintun inner MTU, gateway noise, other accounts or route metric alone.
 if !errors.Is(errM0WindowsPhysicalPathChanged,errM0WindowsPhysicalPathChanged){t.Fatal("native Stop")}
}

func TestM0PLAN028WindowsNativePathChangeCancelsColdTLSNotWholeClient(t *testing.T){
 physical:=make(chan struct{},1)
 started:=make(chan struct{})
 result:=make(chan error,1)
 go func(){
  result<-m0WindowsRunPathScopedGeneration(context.Background(),physical,
   func(ctx context.Context,_ <-chan struct{})error{
    close(started)
    <-ctx.Done()
    return fmt.Errorf("original TLS pre-ready aborted: %w",ctx.Err())
   })
 }()
 <-started
 physical<-struct{}{}
 select{
 case err:=<-result:
  if !errors.Is(err,errM0WindowsPhysicalPathChanged)||!errors.Is(err,context.Canceled){
   t.Fatalf("physical event must cancel TLS and request new generation: %v",err)
  }
 case <-time.After(3*time.Second):t.Fatal("cold path change waited dead90")
 }
}
func TestM0PLAN028WindowsUserStopDuringColdTLSNeverRestarts(t *testing.T){
 physical:=make(chan struct{},1)
 parent,stop:=context.WithCancel(context.Background())
 started:=make(chan struct{})
 result:=make(chan error,1)
 go func(){
  result<-m0WindowsRunPathScopedGeneration(parent,physical,
   func(ctx context.Context,_ <-chan struct{})error{
    close(started)
    <-ctx.Done()
    return ctx.Err()
   })
 }()
 <-started
 stop()
 select{
 case err:=<-result:
  if errors.Is(err,errM0WindowsPhysicalPathChanged)||!errors.Is(err,context.Canceled){
   t.Fatalf("user Stop cannot reauthorize a cold generation: %v",err)
  }
 case <-time.After(3*time.Second):t.Fatal("Stop failed to cancel in-flight cold TLS")
 }
}
func TestM0PLAN028WindowsNativePathChangeDoesNotOverrideAuthReject(t *testing.T){
 physical:=make(chan struct{},1)
 physical<-struct{}{}
 err:=m0WindowsRunPathScopedGeneration(context.Background(),physical,
  func(context.Context,<-chan struct{})error{return realityfront.ErrAdmissionAuth})
 if !errors.Is(err,realityfront.ErrAdmissionAuth)||errors.Is(err,errM0WindowsPhysicalPathChanged){
  t.Fatalf("path event cannot turn invalid credentials into new owner: %v",err)
 }
}

func TestM0PLAN028WindowsVerifiedPhysicalIPv4ColdTimeoutRetryDoesNotReviveStopOrAuth(t *testing.T){
 timeout:=fmt.Errorf("new physical path fakeTCP TLS: %w",context.DeadlineExceeded)
 for _,mode:=range []m0WindowsV4Mode{
  m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,m0WinModeGame2,m0WinModeGame4,
 }{
  if !m0WindowsColdPathRetryAllowed(mode,false,true,false,0,timeout){
   t.Fatalf("OS-verified physical IPv4 event should permit exact stopped cold TLS timeout retry: %v",mode)
  }
  for _,row:=range []struct{
   name string
   path,applied bool
   retries int
   err error
  }{
   {"initial_attempt_without_event",false,false,0,timeout},
   {"already_applied_owner",true,true,0,timeout},
   {"bounded_attempts_exhausted",true,false,2,timeout},
   {"wrong_tls_password",true,false,0,realityfront.ErrAdmissionAuth},
   {"joined_auth_and_timeout",true,false,0,errors.Join(realityfront.ErrAdmissionAuth,context.DeadlineExceeded)},
   {"user_stop",true,false,0,context.Canceled},
   {"driver_failure",true,false,0,errors.New("Npcap driver error")},
  }{
   if m0WindowsColdPathRetryAllowed(mode,false,row.path,row.applied,row.retries,row.err){
    t.Fatalf("mode %v case %s must not rearm old owner",mode,row.name)
   }
  }
 }
 // The existing authenticated-dead90 retries for Normal/FEC are intact,
 // while Game health90 remains its own separate managed health policy.
 if !m0WindowsColdPathRetryAllowed(m0WinModeNormal,true,false,false,0,timeout){
  t.Fatal("prior authenticated Normal dead90 recovery stopped working")
 }
 if m0WindowsColdPathRetryAllowed(m0WinModeGame4,true,false,false,0,timeout){
  t.Fatal("Game dead90 retry authorization widened without OS event")
 }
}


// Scope the real test-owned WSL MTU-only source-reuse exception to an
// unchanged selected IPv4/NIC and exact OS-readback 1280, never a generic
// credential, path or MAC authorization.
func TestM0PLAN028WindowsOwnedWSLMTUShrinkNeverAllowsForeignOrSourceRebind(t *testing.T){
 guest:=netip.MustParseAddr("198.19.254.2")
 host:=netip.MustParseAddr("198.19.254.1")
 selected:=m0WindowsPhysicalPath{ifindex:25,source4:host,physicalMTU:1280}
 allow:=m0WindowsVerifiedOwnedWSLMTUShrink
 if !allow(true,true,2,guest,guest,host,host,25,selected){
  t.Fatal("new signed WSL generation on actual owned physical MTU shrink denied")
 }
 for _,row:=range []struct{
  name string;owned,mtuOnly bool;generation uint64
  guest,peer,initial,current netip.Addr;idx uint32;selected m0WindowsPhysicalPath
 }{
  {"unowned",false,true,2,guest,guest,host,host,25,selected},
  {"no_MTU_only_intent",true,false,2,guest,guest,host,host,25,selected},
  {"old_generation",true,true,1,guest,guest,host,host,25,selected},
  {"foreign_guest",true,true,2,netip.MustParseAddr("198.19.254.3"),guest,host,host,25,selected},
  {"foreign_peer",true,true,2,guest,netip.MustParseAddr("198.19.254.3"),host,host,25,selected},
  {"wrong_initial",true,true,2,guest,guest,netip.MustParseAddr("198.19.254.9"),host,25,selected},
  {"source_switch_not_MTU_only",true,true,2,guest,guest,host,netip.MustParseAddr("198.19.254.9"),25,selected},
  {"foreign_ifindex",true,true,2,guest,guest,host,host,26,selected},
  {"foreign_selected_ip",true,true,2,guest,guest,host,host,25,m0WindowsPhysicalPath{ifindex:25,source4:netip.MustParseAddr("198.19.254.9"),physicalMTU:1280}},
  {"foreign_selected_ifindex",true,true,2,guest,guest,host,host,25,m0WindowsPhysicalPath{ifindex:26,source4:host,physicalMTU:1280}},
  {"no_real_MTU_shrink",true,true,2,guest,guest,host,host,25,m0WindowsPhysicalPath{ifindex:25,source4:host,physicalMTU:1500}},
 }{
  t.Run(row.name,func(t *testing.T){
   if allow(row.owned,row.mtuOnly,row.generation,row.guest,row.peer,row.initial,row.current,row.idx,row.selected){
    t.Fatal("foreign or untriggered MTU-only native WSL route exception")
   }
  })
 }
}

func TestM0PLAN028VerifiedGuestSourceReboundAfterGenuineOSChangeOnly(t *testing.T){
 original:=netip.MustParseAddr("198.19.254.1")
 after:=netip.MustParseAddr("198.19.254.9")
 valid:=m0WindowsPhysicalPath{ifindex:17,source4:after}
 if m0WindowsVerifiedGuestSourceRebound(1,original,after,17,valid){
  t.Fatal("first generation cannot use a new host source under cached WSL MAC override")
 }
 if !m0WindowsVerifiedGuestSourceRebound(2,original,after,17,valid){
  t.Fatal("new cold generation must admit exactly OS selected source4 of verified ifindex")
 }
 for _,row:=range []m0WindowsPhysicalPath{
  {ifindex:18,source4:after},
  {ifindex:17,source4:original},
 }{
  if m0WindowsVerifiedGuestSourceRebound(2,original,after,17,row){
   t.Fatal("stale/foreign NIC or source must not authorize the new physical path")
  }
 }
 if m0WindowsVerifiedGuestSourceRebound(2,original,original,17,valid){
  t.Fatal("unchanged source is not a verified source4 change")
 }
}

func TestM0PLAN028OwnedWSLNextHopOnlyForExactNativeAlias(t *testing.T){
 guest:=netip.MustParseAddr("198.19.254.2")
 initial:=netip.MustParseAddr("198.19.254.1")
 newSource:=netip.MustParseAddr("198.19.254.9")
 old:=m0WindowsPhysicalPath{ifindex:25,source4:initial}
 fresh:=m0WindowsPhysicalPath{ifindex:25,source4:newSource}
 allow:=m0WindowsVerifiedOwnedWSLRoute
 if !allow(true,1,guest,guest,initial,initial,25,old)||
    !allow(true,2,guest,guest,initial,newSource,25,fresh){
  t.Fatal("real native OS-selected same-owned WSL guest must be permitted")
 }
 for _,row:=range []struct{
  name string;own bool;gen uint64;guest,peer,initial,current netip.Addr;idx uint32;path m0WindowsPhysicalPath
 }{
  {"unowned",false,2,guest,guest,initial,newSource,25,fresh},
  {"initial_misbound",true,1,guest,guest,initial,newSource,25,fresh},
  {"stale_new_generation",true,2,guest,guest,initial,initial,25,old},
  {"foreign_guest",true,2,netip.MustParseAddr("198.19.254.3"),guest,initial,newSource,25,fresh},
  {"foreign_peer",true,2,guest,netip.MustParseAddr("198.19.254.3"),initial,newSource,25,fresh},
  {"foreign_original_source",true,2,guest,guest,newSource,newSource,25,fresh},
  {"foreign_ifindex",true,2,guest,guest,initial,newSource,26,fresh},
  {"stale_OS_readback",true,2,guest,guest,initial,newSource,25,old},
 }{
  t.Run(row.name,func(t *testing.T){
   if allow(row.own,row.gen,row.guest,row.peer,row.initial,row.current,row.idx,row.path){
    t.Fatal("unexpected route override")
   }
  })
 }
}
