package faketcp

import (
    "bytes"
    "errors"
    "testing"
)

// Reproduce the real original TLS->M4 race: after receiving a protected
// admission reply the client can send >64 M4 records before the server's
// last protected FakeTCP reply ACK unblocks Write/Detach. A bounded buffer
// must not revoke the authenticated new lane simply because more native
// packets are arriving; only those excess early packets may be dropped.
func TestPLAN028PreDetachBurstOverflowPreservesAuthenticatedSuccessor(t *testing.T) {
    tr,err:=NewStageTransition(128)
    if err!=nil{t.Fatal(err)}
    if err=tr.Prepare(190001);err!=nil{t.Fatal(err)}
    payload:=bytes.Repeat([]byte{0x5a},128)
    for i:=0;i<MaxTransitionRecords;i++{
        kind,e:=tr.Route(190001+uint32(i*128),payload)
        if e!=nil||kind!=RouteQueuedRecord{t.Fatalf("queued record=%d kind=%d err=%v",i,kind,e)}
    }
    for i:=MaxTransitionRecords;i<MaxTransitionRecords+512;i++{
        _,e:=tr.Route(190001+uint32(i*128),payload)
        if !errors.Is(e,ErrTransitionOverflow){t.Fatalf("excess record=%d err=%v",i,e)}
    }
    if tr.State()!=TransitionPrepared{t.Fatalf("candidate aborted by expected pre-detach burst: state=%d",tr.State())}
    n,used:=tr.QueueUsage()
    if n!=MaxTransitionRecords||used!=128*MaxTransitionRecords{
        t.Fatalf("pre-detach bounded queue packets=%d bytes=%d",n,used)
    }
    kind,err:=tr.Route(190001,payload)
    if err!=nil||kind!=RouteQueuedDuplicate{t.Fatalf("original queued retransmit lost: kind=%d err=%v",kind,err)}
    queued,err:=tr.Detach()
    if err!=nil||len(queued)!=MaxTransitionRecords{t.Fatalf("server native detach failed: queued=%d err=%v",len(queued),err)}
    for i,p:=range queued{
        if p.Seq!=190001+uint32(i*128)||!bytes.Equal(p.Payload,payload){
            t.Fatalf("transferred early record=%d lost or mutated",i)
        }
    }
    kind,err=tr.Route(190001+uint32((MaxTransitionRecords+512)*128),payload)
    if err!=nil||kind!=RouteRecord{t.Fatalf("native owner post-detach data route kind=%d err=%v",kind,err)}
}

func TestPLAN028PreDetachMalformedRecordStillAborts(t *testing.T) {
    t.Run("cross_bootstrap_boundary",func(t *testing.T){
        tr,_:=NewStageTransition(32)
        if err:=tr.Prepare(1000);err!=nil{t.Fatal(err)}
        if _,err:=tr.Route(999,[]byte{1,2});!errors.Is(err,ErrTransitionOverlap){t.Fatal(err)}
        if tr.State()!=TransitionAborted{t.Fatal("malformed transition must be fail-closed")}
        if _,err:=tr.Detach();!errors.Is(err,ErrTransitionState){t.Fatal(err)}
    })
    t.Run("conflicting_retransmit",func(t *testing.T){
        tr,_:=NewStageTransition(32)
        _=tr.Prepare(1000)
        if _,err:=tr.Route(1000,[]byte{1});err!=nil{t.Fatal(err)}
        if _,err:=tr.Route(1000,[]byte{2});!errors.Is(err,ErrTransitionConflict){t.Fatal(err)}
        if tr.State()!=TransitionAborted{t.Fatal("conflicting TCP sequence must be fail-closed")}
    })
    t.Run("oversized_record",func(t *testing.T){
        tr,_:=NewStageTransition(32)
        _=tr.Prepare(1000)
        if _,err:=tr.Route(1000,bytes.Repeat([]byte{1},33));!errors.Is(err,ErrTransitionRecordSize){t.Fatal(err)}
        if tr.State()!=TransitionAborted{t.Fatal("oversized record must be fail-closed")}
    })
}
