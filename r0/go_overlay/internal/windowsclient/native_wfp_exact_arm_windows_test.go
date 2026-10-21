//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "testing"
    "os"
    "net/netip"

    "github.com/tailscale/wf"
)

// Hosted Windows CI must run this *pure fail-before-write* contract without
// installing WFP filters. Real TEST-NET installation is a distinct,
 // explicitly isolated native lab and never qualifies host-global Arm.
func TestPLAN010N4ExactWFPArmPlanPreflightDeniesUnowned(t *testing.T) {
    var install [16]byte
    install[0]=7
    valid,err:=n4PlanWFPGuard(install,0x1234)
    if err!=nil{t.Fatal(err)}
    if err:=n4ValidateExactWFPArmPlan(valid);err!=nil{
        t.Fatalf("known native 3-rule plan rejected: %v",err)
    }
    canceled,cancel:=context.WithCancel(context.Background())
    cancel()
    if err:=n4WFPArmExactPlan(canceled,valid);!errors.Is(err,context.Canceled){
        t.Fatalf("canceled batch opened host WFP: %v",err)
    }
    if err:=n4WFPArmExactPlan(nil,valid);!errors.Is(err,ErrNetworkPlan){
        t.Fatalf("nil context bypassed admission: %v",err)
    }
    cases:=[]struct{
        name string
        mutate func(*n4WFPRulePlan)
    }{
        {"missing sublayer",func(p *n4WFPRulePlan){p.Sublayer=nil}},
        {"nonpersistent sublayer",func(p *n4WFPRulePlan){v:=*p.Sublayer;v.Persistent=false;p.Sublayer=&v}},
        {"empty rules",func(p *n4WFPRulePlan){p.Rules=nil}},
        {"duplicate rule",func(p *n4WFPRulePlan){v:=*p.Rules[1];v.ID=p.Rules[0].ID;p.Rules[1]=&v}},
        {"mismatched sublayer",func(p *n4WFPRulePlan){v:=*p.Rules[1];v.Sublayer=wf.SublayerID{};p.Rules[1]=&v}},
        {"nonpersistent rule",func(p *n4WFPRulePlan){v:=*p.Rules[1];v.Persistent=false;p.Rules[1]=&v}},
        {"permit rule",func(p *n4WFPRulePlan){v:=*p.Rules[1];v.Action=wf.ActionPermit;p.Rules[1]=&v}},
        {"empty conditions",func(p *n4WFPRulePlan){v:=*p.Rules[1];v.Conditions=nil;p.Rules[1]=&v}},
    }
    for _,tc:=range cases {
        t.Run(tc.name,func(t *testing.T){
            p,err:=n4PlanWFPGuard(install,0x1234)
            if err!=nil{t.Fatal(err)}
            tc.mutate(&p)
            if err:=n4ValidateExactWFPArmPlan(p);!errors.Is(err,ErrN4NativeGuard){
                t.Fatalf("bad exact-plan shape admitted: %v",err)
            }
            if err:=n4WFPArmExactPlan(context.Background(),p);!errors.Is(err,ErrN4NativeGuard){
                t.Fatalf("bad exact-plan opened WFP engine: %v",err)
            }
        })
    }
    // Correctness of a raw WFP primitive never authorizes native product
    // Apply. This public product barrier must remain closed even on admin.
    if err:=N4NativeNetworkReady(context.Background());!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("unqualified product Arm enabled: %v",err)
    }
}

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
