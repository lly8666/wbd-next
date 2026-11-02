//go:build windows && wbd_v4_embedded_go
package main
import("context";"errors";"fmt";"syscall";"testing";"github.com/lly8666/wobuzhidao/internal/faketcp")
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

// This uses the original Linux deriveMTUBudget: wire - (31 + FEC14
// + Game16 + GameFEC15) may never exceed this Windows TUN configuration.
// An unchanged 1400 default must preserve all previous authentic modes.
func TestM0PLAN027WindowsOriginalNativeRecordOfferRespectsTLSTunnelBudget(t *testing.T){
 rows:=[]struct{
  mtu uint32
  mode m0WindowsV4Mode
  gameFEC bool
  record uint16
 }{
  {1280,m0WinModeNormal,false,1311},
  {1280,m0WinModeFixed,false,1325},
  {1280,m0WinModeAuto,false,1325},
  {1280,m0WinModeGame2,false,1327},
  {1280,m0WinModeGame4,false,1327},
  {1280,m0WinModeGame2,true,1342},
  {1280,m0WinModeGame4,true,1342},
  {1400,m0WinModeNormal,false,1400},
  {1400,m0WinModeFixed,false,1400},
  {1400,m0WinModeGame4,true,1400},
  {1500,m0WinModeNormal,false,1400},
  {576,m0WinModeNormal,false,607},
 }
 for _,r:=range rows{
  actual:=m0WindowsV4PeerRecordCap(r.mtu,r.mode,r.gameFEC)
  if actual!=r.record{
   t.Fatalf("native MTU %d mode=%v gameFEC=%v original TLS limit actual=%d want=%d",
    r.mtu,r.mode,r.gameFEC,actual,r.record)
  }
  reserve:=uint32(31)
  if r.mode==m0WinModeFixed||r.mode==m0WinModeAuto{reserve+=14}
  if r.mode==m0WinModeGame2||r.mode==m0WinModeGame4{
   reserve+=16
   if r.gameFEC{reserve+=15}
  }
  if uint32(actual)>reserve&&uint32(actual)-reserve>r.mtu{
   t.Fatal("peer Linux real TUN may exceed local Windows configured MTU")
  }
 }
}
