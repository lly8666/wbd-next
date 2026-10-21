//go:build windows
package windowsclient

// PLAN020 M0 ONLY: tests for a TEST-NET scoped real native WFP Arm and a
// separately qualified exact guard-only crash-recovery extension. The pinned
// original Windows donor test source remains byte-for-byte unchanged.
import (
 "context"
 "encoding/json"
 "errors"
 "net/netip"
 "os"
 "testing"
 "time"

 "github.com/tailscale/wf"
)

// Real native Windows2022 WFP writes restricted to a random TEST-NET/unused
// port filter. Never run against global IPv6/DNS, default routes or a user
// system. This proves M0's actual persistent Arm/foreign-CAS/Stop primitive,
// NOT a production WFP/whole-product release receipt.
func TestM0PLAN020RealScopedWFPArmAndForeignCAS(t *testing.T) {
 if os.Getenv("WBD_N4_WFP_ISOLATED_LAB")!="1" {
  t.Skip("real native TEST-NET scoped WFP writes need explicit isolated CI")
 }
 ctx:=context.Background()
 subID:=wf.SublayerID(n4WFPTestGUID(t))
 ruleID:=wf.RuleID(n4WFPTestGUID(t))
 sub:=&wf.Sublayer{
  ID:subID,Name:"WBD M0 PLAN020 TEST-NET limited Arm lab",
  Description:"Native scoped WFP source gate, NOT host-global protection",
  Persistent:true,Weight:11,
 }
 rule:=&wf.Rule{
  ID:ruleID,Name:"WBD M0 native scoped TEST-NET deny",
  Layer:wf.LayerALEAuthConnectV4,Sublayer:subID,
  Persistent:true,Weight:1,Action:wf.ActionBlock,
  Conditions:[]*wf.Match{
   {Field:wf.FieldIPRemoteAddress,Op:wf.MatchTypeEqual,
    Value:netip.MustParseAddr("203.0.113.254")},
   {Field:wf.FieldIPRemotePort,Op:wf.MatchTypeEqual,Value:uint16(65530)},
  },
 }
 plan:=n4WFPRulePlan{Sublayer:sub,Rules:[]*wf.Rule{rule}}
 // Cleanup is registered BEFORE first OS mutation. On an interrupted Arm
 // preserve the original FAIL if exact owned policy cannot be reclaimed.
 // Only these two randomized TEST-NET keys may ever be removed.
 t.Cleanup(func(){
  cleanup, cancel:=context.WithTimeout(context.Background(),15*time.Second)
  defer cancel()
  if err:=n4WFPDisarmExactPlan(cleanup,plan,true);err!=nil{
   t.Errorf("scoped native WFP cleanup failed; do not claim isolated host clean: %v",err)
  }
 })
 if err:=n4WFPArmExactPlan(ctx,plan);err!=nil{
  t.Fatalf("exact native scoped TEST-NET Arm failed: %v",err)
 }
 verify,err:=wf.New(&wf.Options{Dynamic:false})
 if err!=nil{t.Fatal(err)}
 present,matches,err:=n4WFPReadOwned(verify,plan)
 closeErr:=verify.Close()
 if err!=nil||closeErr!=nil||!present||!matches[ruleID]{
  t.Fatalf("native WFP persistence not independently observed: sub=%v rule=%v errors=%v / %v",
   present,matches[ruleID],err,closeErr)
 }
 if err:=n4WFPArmExactPlan(ctx,plan);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("duplicate scoped native WFP Arm mutated host: %v",err)
 }
 foreignRule:=*rule
 foreignRule.Conditions=[]*wf.Match{
  {Field:wf.FieldIPRemoteAddress,Op:wf.MatchTypeEqual,
   Value:netip.MustParseAddr("203.0.113.254")},
  {Field:wf.FieldIPRemotePort,Op:wf.MatchTypeEqual,Value:uint16(65529)},
 }
 foreign:=n4WFPRulePlan{Sublayer:sub,Rules:[]*wf.Rule{&foreignRule}}
 if err:=n4WFPDisarmExactPlan(ctx,foreign,false);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign route CAS wrongly removed exact owned WFP: %v",err)
 }
 if err:=n4WFPDisarmExactPlan(ctx,plan,false);err!=nil{
  t.Fatalf("exact native WFP Stop failed: %v",err)
 }
 if err:=n4WFPDisarmExactPlan(ctx,plan,false);err!=nil{
  t.Fatalf("native WFP Stop not idempotent: %v",err)
 }
 check,err:=wf.New(&wf.Options{Dynamic:false})
 if err!=nil{t.Fatal(err)}
 present,matches,err=n4WFPReadOwned(check,plan)
 closeErr=check.Close()
 if err!=nil||closeErr!=nil||present||len(matches)!=0{
  t.Fatalf("fresh engine observed scoped native WFP leak after Stop: present=%v matches=%v errors=%v / %v",
   present,matches,err,closeErr)
 }
 t.Log("M0_PLAN020_REAL_NATIVE_SCOPED_TESTNET_WFP_ARM_FOREIGN_CAS_STOP_PASS host_global_WFP=NOT_RUN default_routes=NOT_RUN")
}


// Real WFP Arm is a multi-object persisted write: process death between
// sublayer/rules and confirmation can strand a known subset. The sole guard
// WAL intent may roll back that exact subset, never a foreign rule or a
// partial guard protecting any later route, lease, MTU or DNS stage.
type n4M0QualifiedUnitGuard struct{ *n4UnifiedTestStage }
func(n4M0QualifiedUnitGuard) n4IsQualifiedPersistentWFPGuard() bool{return true}
func TestM0PLAN020GuardOnlyInterruptedArmPartialWALRecovery(t *testing.T) {
 ctx:=context.Background()
 tx,st,_,_:=n4UnifiedTestTxn(t)
 tx.Stages[0]=n4M0QualifiedUnitGuard{st[0]}
 j:=n4UnifiedJournal{Schema:n4UnifiedSchema,Identity:tx.Identity,Phase:"applying",
  Records:[]n4UnifiedRecord{
   {Name:"guard",State:"intent",Before:json.RawMessage(`{"absent":true}`)},
  },
 }
 if err:=n4UnifiedWrite(tx.Path,j,true);err!=nil{t.Fatal(err)}
 st[0].state=N4UnifiedPartial
 if err:=tx.n4RecoverQualifiedGuardOnlyIntent(ctx);err!=nil{
  t.Fatalf("exact guard-only partial WFP intent never cleaned: %v",err)
 }
 if st[0].state!=N4UnifiedAbsent||st[0].undoCount!=1{
  t.Fatalf("partial WFP guard-only recovery did not use exact Undo: %+v",st[0])
 }
 if _,err:=os.Stat(tx.Path);!os.IsNotExist(err){
  t.Fatalf("guard-only WAL not durably retired: %v",err)
 }
 if err:=tx.n4RecoverQualifiedGuardOnlyIntent(ctx);err!=nil{t.Fatalf("retry Stop failed: %v",err)}
 // Foreign WFP must not be mistaken for crash-owned sublayer/rules.
 other,foreign,_,_:=n4UnifiedTestTxn(t)
 other.Stages[0]=n4M0QualifiedUnitGuard{foreign[0]}
 j.Identity=other.Identity
 if err:=n4UnifiedWrite(other.Path,j,true);err!=nil{t.Fatal(err)}
 foreign[0].state=N4UnifiedForeign
 if err:=other.n4RecoverQualifiedGuardOnlyIntent(ctx);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign guard unexpectedly reclaimed: %v",err)
 }
 if foreign[0].undoCount!=0{t.Fatal("foreign WFP mutated")}
 if _,err:=os.Stat(other.Path);err!=nil{t.Fatal("foreign WFP WAL erased")}
 // A partial guard with an actual lease WAL remains a hard stop BEFORE
 // any OS Undo. The journal shape enforces that a predecessor cannot
 // remain "intent" once a later stage is recorded; use a LEGAL guard-owned
 // entry, then independently simulate partial WFP loss on the host.
 blocked,bs,_,_:=n4UnifiedTestTxn(t)
 blocked.Stages[0]=n4M0QualifiedUnitGuard{bs[0]}
 j.Identity=blocked.Identity
 j.Records[0].State="owned"
 j.Records=append(j.Records,n4UnifiedRecord{
  Name:"lease",State:"owned",Before:json.RawMessage(`{"absent":true}`),
 })
 if err:=n4UnifiedWrite(blocked.Path,j,true);err!=nil{t.Fatal(err)}
 bs[0].state=N4UnifiedPartial
 bs[1].state=N4UnifiedOwned
 if err:=blocked.n4RecoverQualifiedGuardOnlyIntent(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("partial WFP with a following owned lease wrongly recovered: %v",err)
 }
 if bs[0].undoCount!=0||bs[1].undoCount!=0{
  t.Fatal("mutated host network state under a partial protective guard")
 }
}
