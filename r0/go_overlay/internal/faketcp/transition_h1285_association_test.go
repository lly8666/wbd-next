package faketcp

import (
    "bytes"
    "errors"
    "testing"
    "time"
)

// Real original server association, not a StageTransition-only simulation.
// After protected TLS request bytes were consumed, 64 authentic-looking
// post-boundary raw DATA records may arrive while the last TLS reply ACK
// is still pending. The 65th must not abort the authenticated cold session.
func TestPLAN028OriginalServerFakeTCPDetachAfterBoundedM4Burst(t *testing.T){
    a,syn:=establishP2(t,func(Segment)error{return nil})
    defer a.Close()
    boundary,err:=a.PrepareTransition(128)
    if err!=nil{t.Fatal(err)}
    for i:=0;i<MaxTransitionRecords+3;i++{
        seg:=syn
        seg.Flags=FlagACK|FlagPSH
        seg.Seq=boundary+uint32(128*i)
        seg.Ack=a.SenderNext()
        seg.Payload=bytes.Repeat([]byte{byte(i)},128)
        result,e:=a.HandleSegment(seg,time.Now())
        if i<MaxTransitionRecords{
            if e!=nil||result.Disposition!=RouteQueuedRecord{
                t.Fatalf("auth early DATA record %d disposition=%d error=%v",i,result.Disposition,e)
            }
        }else if !errors.Is(e,ErrTransitionOverflow){
            t.Fatalf("excess early DATA %d wrong error=%v",i,e)
        }
    }
    state,ok:=a.TransitionState()
    if !ok||state!=TransitionPrepared{t.Fatalf("authenticated server transition lost before detach: state=%d ok=%t",state,ok)}
    queued,err:=a.DetachTransition()
    if err!=nil||len(queued)!=MaxTransitionRecords{
        t.Fatalf("original server M4 handoff failed despite bounded overflow: queued=%d error=%v",len(queued),err)
    }
    if state,ok=a.TransitionState();!ok||state!=TransitionDetached{
        t.Fatalf("original server not detached: state=%d ok=%t",state,ok)
    }
}

// Final ACK repair must preserve the frozen original sequence boundary
// without feeding a duplicate TLS payload into Rust.
func TestH2402GameColdFinalACKRespondsOnlyBelowDetachedBoundary(t *testing.T){
    flow:=ClientFlow{LocalIP:[4]byte{10,0,0,2},PeerIP:[4]byte{10,0,0,1},LocalPort:41031,PeerPort:443}
    var emitted []Segment
    a,err:=NewClientAssociation(flow,100,time.Second,func(s Segment)error{emitted=append(emitted,s);return nil})
    if err!=nil{t.Fatal(err)}
    defer a.Close()
    if err=a.Start(time.Now());err!=nil{t.Fatal(err)}
    synack:=Segment{SrcIP:flow.PeerIP,DstIP:flow.LocalIP,SrcPort:flow.PeerPort,DstPort:flow.LocalPort,Seq:200,Ack:101,Flags:FlagSYN|FlagACK,Window:65535}
    if err=a.HandleSegment(synack,time.Now());err!=nil{t.Fatal(err)}
    data:=synack;data.Flags=FlagACK|FlagPSH;data.Seq=201;data.Payload=[]byte{1,2,3}
    if err=a.HandleSegment(data,time.Now());err!=nil{t.Fatal(err)}
    h,err:=a.Detach();if err!=nil{t.Fatal(err)}
    before:=len(emitted)
    ok,err:=a.RepeatGameColdFinalACK(&data)
    if !ok||err!=nil||len(emitted)!=before+1{t.Fatalf("duplicate ACK handled=%t err=%v",ok,err)}
    ack:=emitted[len(emitted)-1]
    if ack.Flags!=FlagACK||ack.Seq!=h.SendNext||ack.Ack!=h.ReceiveNext||ack.Window!=h.AdvertisedWindow||len(ack.Payload)!=0{t.Fatalf("wrong frozen ACK %+v",ack)}
    data.Seq=h.ReceiveNext
    if ok,err=a.RepeatGameColdFinalACK(&data);ok||err!=nil{t.Fatalf("fresh native DATA mistaken for TLS duplicate")}
}
