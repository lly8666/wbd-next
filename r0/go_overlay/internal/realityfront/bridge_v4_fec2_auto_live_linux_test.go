//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

import (
    "testing"
    "time"
)

// Only native counters from genuine M4 first-copied DATA and authenticated
// reverse M2 can enter the decision. Missing or ambiguous stay unknown.
func TestV4FecAutoMatureDeltaNeverConvertsUnknownToNoLoss(t *testing.T) {
    var older,newer [30]uint64
    older[0],older[1],older[2],older[3],older[4]=100,80,10,7,3
    newer[0],newer[1],newer[2],newer[3],newer[4]=1100,950,70,67,13
    w,ok:=v4FecAutoWindow(newer,older,0)
    if !ok||w.FirstSent!=1000||w.Observed!=930||w.Missing!=60||
        w.Unknown!=70||w.Censored!=0||!w.sane(){
        t.Fatalf("unverified MatureFirstSend cohort was hidden %+v ok=%v",w,ok)
    }
    // Cumulative reset must be UNKNOWN, never a manufactured zero loss.
    reset:=newer
    reset[3]=1
    if _,ok:=v4FecAutoWindow(reset,older,0);ok{
        t.Fatal("native M2 counter reset accepted as an observation")
    }
    reset=newer
    reset[4]=1000
    if _,ok:=v4FecAutoWindow(reset,older,0);ok{
        t.Fatal("impossible mature numerator accepted")
    }
    // W70 host pressure is native sender-side capacity censorship, NOT a
    // permanent bit. A historic native count must not immortal-freeze Auto.
    older[11],newer[11]=17,18
    if d,ok:=v4FecAutoRecentHostCapacity(newer,older);!ok||d!=1{
        t.Fatalf("new genuine capacity censorship must freeze: %d %t",d,ok)
    }
    older[11]=18
    if d,ok:=v4FecAutoRecentHostCapacity(newer,older);!ok||d!=0{
        t.Fatalf("stale historical host drop must not freeze recovery: %d %t",d,ok)
    }
    older[11]=19
    if _,ok:=v4FecAutoRecentHostCapacity(newer,older);ok{
        t.Fatal("native capacity counter reset forged healthy observation")
    }
    older[11],newer[11]=0,^uint64(0)
    if d,ok:=v4FecAutoRecentHostCapacity(newer,older);!ok||d==0{
        t.Fatal("saturated capacity counter must fail closed")
    }
}

func TestV4Fec2OriginalPositiveConfirmationLagNoFakeRTT(t *testing.T) {
    var native [30]uint64
    // Without native unambiguous positive, no RTT or zero-lag sample
    // exists, even if genuine reverse control records exist elsewhere.
    native[10]=123
    lag,n,mean,known:=v4Fec2PositiveConfirmation(native)
    if lag!=0||n!=0||mean!=0||known {
        t.Fatalf("no authenticated DATA positive sample: %d/%d/%d known=%t",lag,n,mean,known)
    }
    // Native field indexes 12/13 are 8s mature positive lag ns
    // and unambiguous actual FIRST-send DATA sample count.
    native[12],native[13]=1_207_000_000,2
    lag,n,mean,known=v4Fec2PositiveConfirmation(native)
    if lag!=1_207_000_000||n!=2||mean!=603500||!known {
        t.Fatalf("original positive lag not preserved: %d/%d/%d known=%t",lag,n,mean,known)
    }
    // Saturating an absolute u64 sum must not overflow conversion or
    // divide-by-zero; even a true zero-latency positive stays KNOWN.
    native[12],native[13]=0,1
    _,n,mean,known=v4Fec2PositiveConfirmation(native)
    if n!=1||mean!=0||!known{t.Fatal("real zero positive mistaken as UNKNOWN")}
    native[12],native[13]=^uint64(0),1
    _,n,mean,known=v4Fec2PositiveConfirmation(native)
    if n!=1||mean!=^uint64(0)/1000||!known{t.Fatal("large native lag overflow")}
}


// Source k histogram and matured original FIRST-send M2 counters are
// generation-scoped, not per-profile. Only an actually APPLIED downward
// revision on the exact same owner can retain the bounded rolling history;
// initial, upward, pending, changed config/client and OFF must not.
func TestV4FecAutoAppliedDownRetainsOnlyAuthenticHistory(t *testing.T) {
    base:=FecV2State{
        Initialized:true,Client:"client-A",Direction:FecV2C2S,
        ConfigRevision:9,Mode:FecV2Auto,
        Desired:FecV2Strong,AppliedProfile:FecV2Maximum,
        AppliedRevision:3,RequestedRevision:4,
    }
    down:=base
    down.AppliedRevision=4
    down.AppliedProfile=FecV2Strong
    if !v4FecAutoKeepHistoryAfterApplied(base,down) {
        t.Fatal("genuine same-owner applied one-step down must retain native history")
    }
    for _,broken:=range []struct{name string; mutate func(*FecV2State)}{
        {"unapplied",func(s *FecV2State){s.AppliedRevision=3}},
        {"stale_ack",func(s *FecV2State){s.AppliedRevision=5}},
        {"rise",func(s *FecV2State){s.AppliedProfile=FecV2Maximum}},
        {"other_client",func(s *FecV2State){s.Client="client-B"}},
        {"other_direction",func(s *FecV2State){s.Direction=FecV2S2C}},
        {"other_config",func(s *FecV2State){s.ConfigRevision=10}},
        {"off",func(s *FecV2State){s.AppliedOff=true}},
        {"fixed",func(s *FecV2State){s.Mode=FecV2Fixed}},
    } {
        t.Run(broken.name,func(t *testing.T){
            test:=down;broken.mutate(&test)
            if v4FecAutoKeepHistoryAfterApplied(base,test) {
                t.Fatalf("unsafe history carried across %s",broken.name)
            }
        })
    }
}

// Native M2's 8s-mature cohort was copied ~8..16s ago; real FEC
// copied-k must be from the SAME actual clock interval, not independent
// 2s floor samples (which were 2-4s off in source7e real Linux).
func TestV4FecAutoNearestGenuineCohortNotStaleFloor(t *testing.T){
    sec:=time.Second
    mk:=func(at time.Duration,n uint64)v4AutoQualitySample{
        var c [30]uint64
        c[5],c[6]=n,n
        c[14]=n
        return v4AutoQualitySample{at:at,counters:c}
    }
    now:=24*sec
    samples:=[]v4AutoQualitySample{
        mk(8*sec,3200),mk(16*sec,6400),mk(22*sec,8800),
    }
    fast,ok:=v4FecAutoNearestCohort(samples,now-2*sec)
    if !ok||fast[14]!=8800{t.Fatal("missing true recent 2s cohort")}
    slow,ok:=v4FecAutoNearestCohort(samples,now-8*sec)
    if !ok||slow[14]!=6400{t.Fatal("missing true 8s cohort")}
    old,ok:=v4FecAutoNearestCohort(samples,now-16*sec)
    if !ok||old[14]!=3200{t.Fatal("missing true 16s cohort")}
    // The native 8s-mature FIRST-data snapshot and independent copied
    // k histogram span exactly the same *actual* 8s interval.
    raw:=mk(now,9600).counters
    mature,ok:=v4FecAutoWindow(raw,slow,5)
    if !ok||mature.FirstSent!=3200||slow[14]-old[14]!=3200{
        t.Fatalf("real mature vs real k source intervals diverged: %+v",mature)
    }
    if _,ok:=v4FecAutoNearestCohort([]v4AutoQualitySample{
        mk(13*sec,5200),mk(5*sec,2000)},now-8*sec);ok{
        t.Fatal("old 2-4s stale floor cohort must not forge VALID")
    }
    near:=[]v4AutoQualitySample{mk(16*sec-300*time.Millisecond,1),
                                 mk(16*sec+200*time.Millisecond,2)}
    selected,ok:=v4FecAutoNearestCohort(near,now-8*sec)
    if !ok||selected[14]!=2{t.Fatal("must choose closest actual timestamp, not stale floor")}
}
