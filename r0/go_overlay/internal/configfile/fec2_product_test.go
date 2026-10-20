package configfile_test

import (
    "errors"
    "flag"
    "strings"
    "testing"
    "github.com/lly8666/wobuzhidao/internal/runtimeentry"
)

func TestPLAN008FEC2ProductStrictFlagAndEffective(t *testing.T) {
    fs:=flag.NewFlagSet("product",flag.ContinueOnError)
    p:=runtimeentry.RegisterFEC2ProductFlags(fs)
    if err:=p.Validate(1);err!=nil{t.Fatal(err)}
    if err:=p.RuntimeReady();err!=nil{t.Fatal(err)}
    status:=map[string]string{}
    p.CheckConfigStatus(status)
    if status["fec.status"]!="disabled"||status["fec.applied_profile"]!="unknown"{t.Fatal(status)}
    if err:=fs.Parse([]string{"-fec.mode=auto","-fec.profile=mild","-fec.auto_policy=aggressive"});err!=nil{t.Fatal(err)}
    if err:=p.Validate(1);err!=nil{t.Fatal(err)}
    if !errors.Is(p.RuntimeReady(),runtimeentry.ErrFEC2ProductUnwired){t.Fatal("unwired FEC2 activated")}
    p.CheckConfigStatus(status)
    if status["fec.status"]!="rejected"||status["fec.applied_revision"]!="unknown"{t.Fatal(status)}
    if err:=p.Validate(2);err==nil||!strings.Contains(err.Error(),"Game auto"){t.Fatal("Game auto accepted",err)}
    for _,c:=range []struct{key,val string}{{"fec.mode","auto-aggressive"},{"fec.profile","r20"},{"fec.auto_policy","unsafe"},{"fec.auto_start_profile","r4"}} {
        other:=flag.NewFlagSet("bad",flag.ContinueOnError)
        selected:=runtimeentry.RegisterFEC2ProductFlags(other)
        if err:=other.Parse([]string{"-"+c.key+"="+c.val});err!=nil{t.Fatal(err)}
        if err:=selected.Validate(1);err==nil{t.Fatal("accepted",c)}
    }
}
func TestPLAN008FEC2ReadbackRevisionIdentityAndStop(t *testing.T) {
    base:=runtimeentry.FEC2Display{Client:"alice",Direction:"c2s",Epoch:"epochA",RequestedRevision:4,RequestedProfile:"strong",Status:"requested"}
    good:=runtimeentry.FEC2Readback{Client:"alice",Direction:"c2s",Epoch:"epochA",Revision:4,Profile:"strong",State:"applied"}
    for _,mutate:=range []func(*runtimeentry.FEC2Readback){
        func(x *runtimeentry.FEC2Readback){x.Client="bob"},
        func(x *runtimeentry.FEC2Readback){x.Direction="s2c"},
        func(x *runtimeentry.FEC2Readback){x.Epoch="old"},
        func(x *runtimeentry.FEC2Readback){x.Revision=3},
        func(x *runtimeentry.FEC2Readback){x.Revision=5},
    } {
        a:=good;mutate(&a)
        if v:=runtimeentry.ProjectVerifiedFEC2Status(base,&a);v!=base{t.Fatalf("cross identity/stale: %+v",v)}
    }
    if v:=runtimeentry.ProjectVerifiedFEC2Status(base,nil);v!=base{t.Fatal("missing applied proof accepted")}
    p:=good;p.State="pending"
    if v:=runtimeentry.ProjectVerifiedFEC2Status(base,&p);v.Status!="pending"||v.AppliedRevision!=0{t.Fatal(v)}
    r:=good;r.State="rejected";r.Reason="native failed"
    if v:=runtimeentry.ProjectVerifiedFEC2Status(base,&r);v.Status!="rejected"||v.AppliedRevision!=0{t.Fatal(v)}
    if v:=runtimeentry.ProjectVerifiedFEC2Status(base,&good);v.Status!="applied"||v.AppliedRevision!=4{t.Fatal(v)}
    bad:=good;bad.Profile="light"
    if v:=runtimeentry.ProjectVerifiedFEC2Status(base,&bad);v.Status!="rejected"||v.AppliedRevision!=0{t.Fatal(v)}
}
