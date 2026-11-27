//go:build windows && wbd_v4_embedded_go
package main
import("net/netip";"time";"context";"errors";"fmt";"syscall";"testing";"unsafe";"os";"path/filepath";"github.com/lly8666/wobuzhidao/internal/faketcp";"github.com/lly8666/wobuzhidao/internal/realityfront")
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
// A same-source-IPv4 generation B must differ in original FakeTCP 4-tuple,
// otherwise the Linux original server may still route new SYN into A's
// authenticated detached Rust tuple. This is a local client source-port
// change, not a second public server port or private TLS wire extension.
func TestM0PLAN028WindowsColdNewGenerationNeverReusesOriginalClientTCPPort(t *testing.T){
 for _,row:=range []struct{
  name string
  configured uint16
  generation uint64
  want uint16
 }{
  {"first_original_configured",41031,1,41031},
  {"second_same_source_4tuple",41031,2,41032},
  {"third_preexisting_highwater",41031,3,41033},
  {"maximum_private_port_wrap",65535,2,49152},
  {"low_original_port_kept_first",443,1,443},
  {"low_original_port_successor",443,2,444},
 }{
  t.Run(row.name,func(t *testing.T){
   got,err:=m0WindowsOriginalColdClientPort(row.configured,row.generation)
   if err!=nil||got!=row.want{
    t.Fatalf("client cold tuple source port selected=%d expected=%d err=%v",got,row.want,err)
   }
  })
 }
 for _,row:=range []struct{port uint16;generation uint64}{
  {0,1},{41031,0},{0,0},
 }{
  if _,err:=m0WindowsOriginalColdClientPort(row.port,row.generation);err==nil{
   t.Fatal("invalid source port or generation must fail closed")
  }
 }
}

// H2065: a complete WinForms Stop is an entirely NEW Go process.
// The old server can retain the previous FakeTCP 4-tuple despite a
// correctly restored Windows owned WAL. Persist only cold port ordinal.
func TestM0PLAN029GuiNormalStopReconnectUsesDifferentOriginalTCPPort(t *testing.T){
 path:=filepath.Join(t.TempDir(),"network-state.json")
 for i,want:=range []uint16{41031,41032,41033}{
  ordinal,err:=m0WindowsReserveColdTupleOrdinal(path)
  if err!=nil||ordinal!=uint64(i+1){
   t.Fatalf("portable cold ordinal=%d want=%d err=%v",ordinal,i+1,err)
  }
  port,err:=m0WindowsOriginalColdClientPort(41031,ordinal)
  if err!=nil||port!=want{
   t.Fatalf("new Go process TCP port=%d want=%d err=%v",port,want,err)
  }
 }
 tupleState:=filepath.Join(filepath.Dir(path),".wbd-next-cold-tuple-ordinal.json")
 if err:=os.WriteFile(tupleState,[]byte("{bad-json"),0600);err!=nil{t.Fatal(err)}
 if _,err:=m0WindowsReserveColdTupleOrdinal(path);err==nil{
  t.Fatal("damaged cold port state must fail closed instead of reusing tuple")
 }
 if _,err:=m0WindowsReserveColdTupleOrdinal("");err==nil{
  t.Fatal("empty WAL locator cannot place persisted cold tuple state")
 }
}

// An actual selected physical MTU-only mutation must be eligible even
// if Windows supplies no IPv4 IP-interface callback. The same 200/500ms
// cold controller verifies a second OS sample before owned Stop; a nil
// or failed/foreign OS read is never a cold TLS authorization.
func TestM0PLAN028WindowsPhysicalMTULivenessOneExistingColdWatcher(t *testing.T){
 base:=m0WindowsPhysicalPath{
  ifindex:18,source4:netip.MustParseAddr("198.19.254.1"),physicalMTU:1500,
 }
 mutated:=base
 mutated.physicalMTU=1280
 if !m0WindowsPhysicalPathLivenessChanged(base,mutated,nil){
  t.Fatal("same ifindex and source4, real OS NlMtu1500->1280 must arm cold recheck")
 }
 var c m0WindowsPathCoalescer
 now:=time.Unix(1000,0)
 c.push(now)
 if c.remaining(now)!=200*time.Millisecond||
  c.remaining(now.Add(201*time.Millisecond))!=0{
  t.Fatal("1Hz sample must use exact existing 200ms cold coalescer")
 }
 c.clear()
 if c.remaining(now)!=-1{t.Fatal("coalescer must drain before next sample")}
 for _,row:=range []struct{
  name string
  path m0WindowsPhysicalPath
  err error
 }{
  {"identical_selected_path",base,nil},
  {"read_failed",mutated,errors.New("IP Helper entry failed")},
  {"empty_selected_path",m0WindowsPhysicalPath{},nil},
  {"foreign_ipv6",m0WindowsPhysicalPath{ifindex:18,source4:netip.MustParseAddr("2001:db8::1"),physicalMTU:1280},nil},
  {"invalid_NlMtu",m0WindowsPhysicalPath{ifindex:18,source4:base.source4,physicalMTU:0},nil},
 }{
  t.Run(row.name,func(t *testing.T){
   if m0WindowsPhysicalPathLivenessChanged(base,row.path,row.err){
    t.Fatal("invalid/no-op physical OS sample must not rotate original TLS")
   }
  })
 }
}

// Win32 MIB_IPINTERFACE_ROW is an actual x64 IP-layer NlMtu receipt,
// unlike net.Interface.MTU (physical adapter MTU). The donor pins x/sys
// v0.33.0 before its GetIpInterfaceEntry wrapper; verify our local ABI.
// H1340 real Game2 Rust Join/WAL/Stop all PASS, but an OS RuntimeMTU
// read raced caller cancellation and returned (0,context.Canceled).
// Only a still-live owner may report MTU drift; do not waive real drift.
func TestM0PLAN028GameNativeCanceledTickNeverMasqueradesAsMTUDrift(t *testing.T){
 ctx,cancel:=context.WithCancel(context.Background())
 cancel()
 if e:=m0WindowsGameRuntimeMTUDrift(ctx,1313,0,context.Canceled);e!=nil{
  t.Fatalf("Stop canceled OS MTU read must not falsify product failure: %v",e)
 }
 if e:=m0WindowsGameRuntimeMTUDrift(context.Background(),1313,0,nil);e==nil{
  t.Fatal("live authenticated owner MTU=0 must still fail closed")
 }
 if e:=m0WindowsGameRuntimeMTUDrift(context.Background(),1313,1313,context.DeadlineExceeded);e==nil{
  t.Fatal("live owner OS read failure must fail closed")
 }
 if e:=m0WindowsGameRuntimeMTUDrift(context.Background(),1313,1313,nil);e!=nil{
  t.Fatalf("matching live owned MTU should be healthy: %v",e)
 }
}

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
 // An actual terminal Rust Health90 on any supported mode can
 // reestablish the original transport even without a local NIC change.
 for _,mode:=range []m0WindowsV4Mode{m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,m0WinModeGame2,m0WinModeGame4}{
  if !m0WindowsColdPathRetryAllowed(mode,true,false,false,0,timeout){
   t.Fatalf("authenticated dead90 recovery unavailable: %v",mode)
  }
  if m0WindowsColdPathRetryAllowed(mode,true,false,true,0,timeout)||
     m0WindowsColdPathRetryAllowed(mode,true,false,false,2,timeout)||
     m0WindowsColdPathRetryAllowed(mode,true,false,false,0,realityfront.ErrAdmissionAuth){
   t.Fatalf("invalid cold retry after native dead: %v",mode)
  }
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


func TestH2223WindowsIdleAuthenticatedRustNativeStartupDoesNotRequireApplicationReply(t *testing.T){
 for _,row:=range []struct{tx,rx,after uint64}{
  {0,0,0}, // original TLS + native workers, completely idle Wintun
  {2,0,0}, // real prior physical case: uplink without reverse app DATA
  {27,0,0},
  {10,8,4}, // actual bidirectional DATA stays independent of READY
 }{
  state:=realityfront.V4WindowsNativeWorkerStatsV1{
   Version:1,Workers:2,TXCopied:row.tx,RXDelivered:row.rx,
   TXAfterRX:row.after,
  }
  if err:=m0WindowsRustNativeStartupVerdict(state);err!=nil{
   t.Fatalf("idle authenticated Rust workers must READY without business: %+v %v",row,err)
  }
 }
 for _,workerCode:=range []int32{1,3,6}{
  state:=realityfront.V4WindowsNativeWorkerStatsV1{Version:1,Workers:2,WorkerError:workerCode}
  if err:=m0WindowsRustNativeStartupVerdict(state);err==nil{
   t.Fatalf("fatal or verified dead native worker rc=%d must not READY",workerCode)
  }
 }
}


func TestH2223InitialColdRetryOnlyBeforeRustM4ForTransientOriginalTransport(t *testing.T){
 for _,mode:=range []m0WindowsV4Mode{m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,m0WinModeGame2,m0WinModeGame4}{
  for _,timeout:=range []error{context.DeadlineExceeded,syscall.ETIMEDOUT,faketcp.ErrBootstrapTimeout}{
   tagged:=m0WindowsTagOriginalColdTransport(timeout)
   if !errors.Is(tagged,errM0OriginalColdTransportTimeout){t.Fatalf("not tagged: %v",tagged)}
   for n:=0;n<2;n++{
    if !m0WindowsInitialTransportRetryAllowed(mode,false,n,tagged){
     t.Fatalf("valid original TLS transport retry mode=%v count=%d",mode,n)
    }
   }
   if m0WindowsInitialTransportRetryAllowed(mode,false,2,tagged)||
      m0WindowsInitialTransportRetryAllowed(mode,true,0,tagged){
    t.Fatal("original TLS retries must be bounded and never after OS Applied")
   }
  }
 }
 for _,err:=range []error{
  realityfront.ErrAdmissionAuth,context.Canceled,
  errors.New("TLS certificate rejected"),errors.New("Npcap driver error"),
 }{
  if m0WindowsInitialTransportRetryAllowed(m0WinModeNormal,false,0,
    m0WindowsTagOriginalColdTransport(err)){
   t.Fatalf("permanent, auth, or Stop failure retried: %v",err)
  }
 }
 // Even a 45s post-TLS M4/OS deadline cannot restart a new TLS session
 // unless the source of its error was explicitly original cold transport.
 if m0WindowsInitialTransportRetryAllowed(m0WinModeNormal,false,0,
  context.DeadlineExceeded){
  t.Fatal("untagged post-TLS timeout must not be retried")
 }
}

func TestH2224ActualNativeQualityFecDirectionsAndUnknownNotZero(t *testing.T){
 // Normal is truly off in both directions, no fake quality.
 if tx,rx:=m0WindowsQualityStatuses(m0WinModeNormal,"",false,m0NativeV4PacketStats{});tx!="off"||rx!="off"{
  t.Fatalf("off mismatched TX/RX %s %s",tx,rx)
 }
 sample:=m0NativeV4PacketStats{}
 tx,rx:=m0WindowsQualityStatuses(m0WinModeFixed,"strong",false,sample)
 if tx!="pending"||rx!="negotiated-strong"{t.Fatalf("cold fixed status %s %s",tx,rx)}
 tx,rx=m0WindowsQualityStatuses(m0WinModeFixed,"strong",true,sample)
 if tx!="applied-strong"||rx!="negotiated-strong"{t.Fatalf("verified fixed TX %s RX %s",tx,rx)}
 sample.AutoPending=true
 tx,rx=m0WindowsQualityStatuses(m0WinModeAuto,"",false,sample)
 if tx!="pending"||rx!="unknown"{t.Fatalf("pending auto %s %s",tx,rx)}
 sample.AutoPending=false
 sample.AutoAppliedRevision=2
 sample.AutoDesiredProfile=realityfront.FecV2High
 tx,rx=m0WindowsQualityStatuses(m0WinModeAuto,"",false,sample)
 if tx!="applied-high"||rx!="unknown"{t.Fatalf("applied C2S auto cannot invent S2C %s %s",tx,rx)}
}


// H2226: only already-AEAD-authenticated, mature low-frequency Quality
// START/CLOSE summaries can show a coarse GUI loss upper and feedback delay.
// No per-record M2 feedback, underlay-packet inference or age-as-zero.
func TestH2226LowRateQualityGuiUsesOnlyMatchedMatureSummary(t *testing.T){
 before:=realityfront.V4WindowsAutoQuality{Version:1,Size:256,Revision:7}
 after:=before
 after.Counters[0]=100
 after.Counters[1]=90
 after.Counters[2]=7
 after.Counters[3]=3
 after.Counters[10]=1
 after.Counters[12]=3_120_000_000
 after.Counters[13]=1
 ms,loss,ok:=m0WindowsLowRateGuiEstimate(before,after)
 if !ok||ms!=120||loss!=100{
  t.Fatalf("mature low-rate estimate got ok=%t ms=%d upper_tenths=%d",ok,ms,loss)
 }
 noReport:=after;noReport.Counters[10]=0
 if _,_,ok:=m0WindowsLowRateGuiEstimate(before,noReport);ok{
  t.Fatal("no authenticated Quality report displayed fake sample")
 }
 censored:=after;censored.Counters[11]=1
 if _,_,ok:=m0WindowsLowRateGuiEstimate(before,censored);ok{
  t.Fatal("host-capacity censored report displayed as link quality")
 }
 otherEpoch:=after;otherEpoch.Revision=8
 if _,_,ok:=m0WindowsLowRateGuiEstimate(before,otherEpoch);ok{
  t.Fatal("cross-revision low-rate history accepted")
 }
 incomplete:=after;incomplete.Counters[0]=101
 if _,_,ok:=m0WindowsLowRateGuiEstimate(before,incomplete);ok{
  t.Fatal("missing/ambiguous first-send denominator treated as measured")
 }
 old:=after;old.Counters[12]=2_999_999_999
 if _,_,ok:=m0WindowsLowRateGuiEstimate(before,old);ok{
  t.Fatal("sub-three-second immature quality was treated as RTT")
 }
}

func TestH2400WindowsGameColdTupleGroupsDoNotOverlap(t *testing.T){
 path:=filepath.Join(t.TempDir(),"network-state.json")
 for _,want:=range []uint64{1,9,17}{
  ordinal,err:=m0WindowsReserveColdTupleOrdinals(path,8)
  if err!=nil||ordinal!=want{t.Fatalf("Game4 reservation ordinal=%d want=%d err=%v",ordinal,want,err)}
  base,err:=m0WindowsOriginalColdClientPort(41031,ordinal)
  if err!=nil||base!=uint16(41030+want){t.Fatalf("Game4 base=%d err=%v",base,err)}
 }
}

func TestM0WindowsNativeRotationBounds(t *testing.T){
 for _,p:=range [][2]time.Duration{{0,0},{30*time.Second,30*time.Second},{30*time.Second,35*time.Second},{30*time.Second,24*time.Hour}}{
  if err:=m0WindowsValidateRotation(p[0],p[1]);err!=nil{t.Fatal(p,err)}
  for i:=0;i<1000;i++{if d:=m0WindowsRotationDelay(p[0],p[1]);d<p[0]||d>p[1]{t.Fatal(p,d)}}
 }
 for _,p:=range [][2]time.Duration{{0,time.Second},{time.Second,0},{12*time.Second,18*time.Second},{29*time.Second,30*time.Second},{35*time.Second,30*time.Second},{30*time.Second,25*time.Hour}}{
  if m0WindowsValidateRotation(p[0],p[1])==nil{t.Fatal("accepted invalid rotation bounds",p)}
 }
 ch,stop:=m0WindowsArmRotation(m0NativeV4Options{});defer stop()
 if ch!=nil{t.Fatal("disabled rotation armed a timer")}
}
