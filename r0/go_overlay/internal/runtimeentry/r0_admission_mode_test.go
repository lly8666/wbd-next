package runtimeentry

import (
    "context"
    "errors"
    "testing"

    "github.com/lly8666/wobuzhidao/internal/realityfront"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

func r0Policy() realityfront.AdmissionPolicy {
    return realityfront.AdmissionPolicy{
        Schema:1, Transport:realityfront.TransportNormal,
        DesiredLanes:1, FECMode:realityfront.FECOff,
        Cipher:realityfront.CipherChaCha,
    }
}

func TestR0EffectiveAdmissionDefaultsAndV3(t *testing.T) {
    for _,tc:=range []struct {
        requested uint16
        policy realityfront.AdmissionPolicy
        expected uint16
    }{
        {0,realityfront.AdmissionPolicy{},realityfront.RecordVersionV2},
        {0,r0Policy(),realityfront.RecordVersionV3},
        {realityfront.RecordVersionV3,r0Policy(),realityfront.RecordVersionV3},
    } {
        v,err:=R0EffectiveClientAdmission(tc.requested,tc.policy)
        if err!=nil||v!=tc.expected {
            t.Fatalf("client mode %d policy=%+v got=%d err=%v",tc.requested,tc.policy,v,err)
        }
    }
    for _,tc:=range []struct {
        requested uint16
        requireV3 bool
        expected uint16
    }{
        {0,false,realityfront.RecordVersionV2},
        {0,true,realityfront.RecordVersionV3},
        {realityfront.RecordVersionV3,true,realityfront.RecordVersionV3},
    } {
        v,err:=R0EffectiveServerAdmission(tc.requested,tc.requireV3)
        if err!=nil||v!=tc.expected{t.Fatalf("server mode %+v got %d %v",tc,v,err)}
    }
}

func TestR0V4RequestFailsClosedBeforeClientLaneOpen(t *testing.T) {
    called:=0
    _,err:=DialTunnelClient(context.Background(),TunnelClientConfig{
        RequestedRecordVersion:realityfront.V4RecordVersion,
        OpenLane:func(uint8,uint64)(SegmentIO,faketcp.ClientFlow,error){
            called++
            return SegmentIO{},faketcp.ClientFlow{},nil
        },
    })
    if !errors.Is(err,ErrR0V4DataPlaneUnavailable) || called!=0 {
        t.Fatalf("V4 started old data plane: err=%v opened=%d",err,called)
    }
}

func TestR0V4RequestFailsClosedBeforeServerResources(t *testing.T) {
    _,err:=NewLifecycleServer(LifecycleServerConfig{
        RequestedRecordVersion:realityfront.V4RecordVersion,
    })
    if !errors.Is(err,ErrR0V4DataPlaneUnavailable) {
        t.Fatalf("V4 attempted old listener setup: %v",err)
    }
}

func TestR0InvalidOrDowngradedAdmissionVersionRejected(t *testing.T) {
    for _,version:=range []uint16{1,2,5,65535} {
        _,err:=R0EffectiveClientAdmission(version,r0Policy())
        if !errors.Is(err,ErrR0AdmissionVersion){t.Fatalf("invalid client version %d %v",version,err)}
        _,err=R0EffectiveServerAdmission(version,true)
        if !errors.Is(err,ErrR0AdmissionVersion){t.Fatalf("invalid server version %d %v",version,err)}
    }
    if _,err:=R0EffectiveClientAdmission(3,realityfront.AdmissionPolicy{});!errors.Is(err,ErrR0AdmissionVersion){
        t.Fatalf("explicit V3 silently selected old V2: %v",err)
    }
    if _,err:=R0EffectiveServerAdmission(3,false);!errors.Is(err,ErrR0AdmissionVersion){
        t.Fatalf("explicit V3 without RequireV3: %v",err)
    }
    for _,name:=range []string{"client","server"}{
        var err error
        if name=="client"{_,err=R0EffectiveClientAdmission(4,r0Policy())} else {_,err=R0EffectiveServerAdmission(4,true)}
        if !errors.Is(err,ErrR0V4DataPlaneUnavailable){t.Fatalf("%s V4 downgraded: %v",name,err)}
    }
}
