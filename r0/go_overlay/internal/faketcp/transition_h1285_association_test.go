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
