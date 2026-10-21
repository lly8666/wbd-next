//go:build windows
package windowsclient

import (
 "context"
 "errors"
 "encoding/json"
 "os"
 "testing"
)

func TestM0PLAN020LiveFiveStageOSAppliedAndDisconnectedReadbacks(t *testing.T){
 ctx:=context.Background()
 tx,st,_,owner:=n4UnifiedTestTxn(t)
 if _,err:=tx.VerifyLiveOSApplied(ctx);!errors.Is(err,os.ErrNotExist){
  t.Fatalf("unwritten WAL illegally granted Applied: %v",err)
 }
 if err:=tx.Apply(ctx);err!=nil{t.Fatal(err)}
 good,err:=tx.VerifyLiveOSApplied(ctx)
 if err!=nil||!good.AllNativeOSApplied||!good.GuardOwned||
   !good.LeaseOwned||!good.MTUOwned||!good.DNSOwned||
   !good.RoutesOwned||good.WintunIndex!=tx.Identity.WintunIndex{
  t.Fatalf("five native stages not independently certified: %+v %v",good,err)
 }
 // A valid checksum-protected active WAL without all live host policies
 // cannot represent Applied.
 st[3].state=N4UnifiedAbsent
 bad,err:=tx.VerifyLiveOSApplied(ctx)
 if !errors.Is(err,ErrN4NativeGuard)||bad.AllNativeOSApplied{
  t.Fatalf("missing OS DNS stage falsely Applied: %+v %v",bad,err)
 }
 st[3].state=N4UnifiedForeign
 if _,err:=tx.VerifyLiveOSApplied(ctx);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign DNS stage not rejected: %v",err)
 }
 st[3].state=N4UnifiedOwned
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("active WAL falsely disconnected: %v",err)
 }
 if err:=tx.Recover(ctx);err!=nil{t.Fatal(err)}
 if err:=tx.VerifyLiveOSDisconnected(ctx);err!=nil{t.Fatal(err)}
 // Exact OS readback never considers a deleted WAL enough when someone
 // installs unexpected host WFP after Stop.
 st[0].state=N4UnifiedForeign
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign persistent WFP after Stop not refused: %v",err)
 }
 st[0].state=N4UnifiedAbsent
 if owner.count<4{t.Fatalf("actual owner was not checked for live reads: %d",owner.count)}
 tx.assemblyOnly=true
 if _,err:=tx.VerifyLiveOSApplied(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("assembly-only native stage bypass: %v",err)
 }
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("assembly-only Disconnected bypass: %v",err)
 }
}

 // The original DNS stage can return a valid post-Stop snapshot even when
 // a static setting remains. Simulate that independent read-only behavior:
 // Snapshot succeeds; only Inspect can reject the surviving OS state.
type n4M0PermissiveDisconnectedSnapshot struct{ *n4UnifiedTestStage }
func(s *n4M0PermissiveDisconnectedSnapshot) Snapshot(_ context.Context,_ N4UnifiedIdentity)(json.RawMessage,error){
 return json.RawMessage(`{"post_stop_readable":true}`),nil
}
func TestM0PLAN020DisconnectedRequiresRealAbsentStageReadback(t *testing.T){
 ctx:=context.Background()
 tx,st,_,_:=n4UnifiedTestTxn(t)
 tx.Stages[3]=&n4M0PermissiveDisconnectedSnapshot{st[3]}
 if err:=tx.VerifyLiveOSDisconnected(ctx);err!=nil{
  t.Fatalf("clean native OS state rejected: %v",err)
 }
 st[3].state=N4UnifiedOwned
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("orphan static DNS with readable Snapshot falsely disconnected: %v",err)
 }
 st[3].state=N4UnifiedPartial
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("partial native OS state falsely disconnected: %v",err)
 }
 st[3].state=N4UnifiedForeign
 if err:=tx.VerifyLiveOSDisconnected(ctx);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign native OS state falsely disconnected: %v",err)
 }
 st[3].state=N4UnifiedAbsent
 if err:=tx.VerifyLiveOSDisconnected(ctx);err!=nil{
  t.Fatalf("native OS state not clean after regression reset: %v",err)
 }
}
