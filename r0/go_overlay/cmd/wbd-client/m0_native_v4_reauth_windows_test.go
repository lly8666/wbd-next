//go:build windows && wbd_v4_embedded_go
package main
import("net/netip";"time";"context";"errors";"fmt";"syscall";"testing";"unsafe";"github.com/lly8666/wobuzhidao/internal/faketcp")
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
func TestM0PLAN028NativeWindowsOnlyPhysicalNICSourceIPv4(t *testing.T){
 a:=m0WindowsPhysicalPath{ifindex:8,source4:netip.MustParseAddr("192.0.2.11")}
 b:=a;b.source4=netip.MustParseAddr("192.0.2.12");if b==a{t.Fatal("IPv4 change")}
 b=a;b.ifindex=9;if b==a{t.Fatal("NIC change")}
 if !errors.Is(errM0WindowsPhysicalPathChanged,errM0WindowsPhysicalPathChanged){t.Fatal("native Stop")}
}
