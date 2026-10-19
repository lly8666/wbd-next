package runtimeentry

import (
    "errors"
    "flag"
    "strings"
    "testing"
)
func TestR0ProductFEC2ParametersAndNoSyntheticApplied(t *testing.T) {
    fs:=flag.NewFlagSet("product",flag.ContinueOnError)
    p:=RegisterFEC2ProductFlags(fs)
    if err:=p.Validate(1);err!=nil{t.Fatal(err)}
    if err:=p.RuntimeReady();err!=nil{t.Fatal(err)}
    status:=map[string]string{}
    p.CheckConfigStatus(status)
    if status["fec.status"]!="disabled" || status["fec.applied_profile"]!="unknown" {t.Fatal(status)}
    if err:=fs.Parse([]string{"-fec.mode=auto","-fec.profile=mild","-fec.auto_policy=aggressive"});err!=nil{t.Fatal(err)}
    if err:=p.Validate(1);err!=nil{t.Fatal(err)}
    if !errors.Is(p.RuntimeReady(),ErrFEC2ProductUnwired) {t.Fatal("unwired auto activated")}
    p.CheckConfigStatus(status)
    if status["fec.status"]!="rejected" || status["fec.applied_revision"]!="unknown" {t.Fatal(status)}
    if err:=p.Validate(2);err==nil || !strings.Contains(err.Error(),"Game auto") {t.Fatal("Game auto accepted",err)}
    for _,c:=range []struct{key,val string}{{"fec.mode","auto-aggressive"},{"fec.profile","r20"},{"fec.auto_policy","unsafe"},{"fec.auto_start_profile","r4"}} {
        other:=flag.NewFlagSet("bad",flag.ContinueOnError)
        selected:=RegisterFEC2ProductFlags(other)
        if err:=other.Parse([]string{"-"+c.key+"="+c.val});err!=nil{t.Fatal(err)}
        if err:=selected.Validate(1);err==nil{t.Fatal("accepted",c)}
    }
}
func TestR0ProductFEC2ReadbackScoped(t *testing.T) {
    base:=FEC2Display{Client:"alice",Direction:"c2s",Epoch:"epochA",RequestedRevision:4,RequestedProfile:"strong",Status:"requested"}
    good:=FEC2Readback{Client:"alice",Direction:"c2s",Epoch:"epochA",Revision:4,Profile:"strong",State:"applied"}
    for _,mutate:=range []func(*FEC2Readback){
        func(x *FEC2Readback){x.Client="bob"},
        func(x *FEC2Readback){x.Direction="s2c"},
        func(x *FEC2Readback){x.Epoch="old"},
        func(x *FEC2Readback){x.Revision=3},
        func(x *FEC2Readback){x.Revision=5},
    } {
        a:=good;mutate(&a)
        if v:=ProjectVerifiedFEC2Status(base,&a);v!=base {t.Fatalf("cross identity/stale ack: %+v",v)}
    }
    if v:=ProjectVerifiedFEC2Status(base,nil);v!=base {t.Fatal("missing ACK counted")}
    pending:=good;pending.State="pending"
    if v:=ProjectVerifiedFEC2Status(base,&pending);v.Status!="pending"||v.AppliedRevision!=0 {t.Fatal(v)}
    reject:=good;reject.State="rejected";reject.Reason="native failed"
    if v:=ProjectVerifiedFEC2Status(base,&reject);v.Status!="rejected"||v.AppliedRevision!=0 {t.Fatal(v)}
    if v:=ProjectVerifiedFEC2Status(base,&good);v.Status!="applied"||v.AppliedRevision!=4 {t.Fatal(v)}
    mismatch:=good;mismatch.Profile="light"
    if v:=ProjectVerifiedFEC2Status(base,&mismatch);v.Status!="rejected"||v.AppliedRevision!=0 {t.Fatal(v)}
}
