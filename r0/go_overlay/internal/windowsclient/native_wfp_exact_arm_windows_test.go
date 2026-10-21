//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "testing"

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
