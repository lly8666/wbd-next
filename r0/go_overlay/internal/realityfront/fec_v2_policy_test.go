package realityfront

import (
    "errors"
    "testing"
    "time"
)

func f2Config(client string, dir FecV2Direction, mode FecV2Mode, policy FecV2AutoPolicy) FecV2Config {
    return FecV2Config{Client:client,Direction:dir,Transport:FecV2Normal,
        Mode:mode,Profile:FecV2Strong,AutoPolicy:policy,ConfigRevision:1}
}
func f2Window(n,loss uint64) FecV2Window {
    return FecV2Window{FirstSent:n,Observed:n,Missing:loss}
}
func f2Snapshot(client string,dir FecV2Direction,at time.Duration,fast,slow uint64) FecV2Snapshot {
    v:=FecV2Snapshot{Client:client,Direction:dir,At:at,
        Validity:FecV2Valid,Fast:f2Window(1024,fast),
        Slow:f2Window(6000,slow)}
    v.ActualK[15]=375
    return v
}
func TestF2ControlAllSevenProfilesActualPartial(t *testing.T) {
    want:=[7]uint8{2,4,6,8,12,16,20}
    for p:=FecV2Light;p<=FecV2Maximum;p++ {
        if !p.Valid() || p.String()=="invalid" {t.Fatal(p)}
        r,e:=FecV2Parity(p,16)
        if e!=nil || r!=want[p] {t.Fatalf("k16 %s got %d %v",p,r,e)}
        for k:=uint8(1);k<=16;k++ {
            r,e=FecV2Parity(p,k)
            if e!=nil || r<1 || r>20 {t.Fatalf("%s k%d r%d %v",p,k,r,e)}
        }
        r,_=FecV2Parity(p,1)
        if r!=1 && !(p==FecV2Maximum && r==2) {t.Fatalf("sparse %s r%d",p,r)}
    }
    for _,bad:=range []uint8{0,17,255} {
        if _,e:=FecV2Parity(FecV2Light,bad);e==nil {t.Fatal("bad k",bad)}
    }
    if _,e:=FecV2Parity(7,16);e==nil {t.Fatal("bad profile")}
}
func TestF2ControlOffFixedGameAndStrictRevisions(t *testing.T) {
    cfg:=f2Config("alice",FecV2C2S,FecV2Auto,FecV2Conservative)
    cfg.Transport=FecV2Game
    _,i,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if !errors.Is(e,ErrFecV2GameAuto) || i.Send {t.Fatalf("Game auto=%+v %v",i,e)}
    cfg.Mode=FecV2Off
    s,i,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if e!=nil||!i.Send||i.Mode!=FecV2Off||!s.DesiredOff {t.Fatal(i,e)}
    s2,i,e:=FecV2Step(cfg,s,FecV2Snapshot{},time.Hour)
    if e!=nil||i.Send||s2.RequestedRevision!=s.RequestedRevision {t.Fatal("off woke auto",i,e)}
    cfg.Mode=FecV2Fixed
    cfg.Profile=FecV2Medium
    cfg.ConfigRevision=2
    s,i,e=FecV2Step(cfg,s,FecV2Snapshot{},time.Hour)
    if e!=nil||!i.Send||i.Profile!=FecV2Medium||i.Revision<=s.AppliedRevision {t.Fatal(i,e)}
    _,_,e=FecV2Step(f2Config("alice",FecV2C2S,FecV2Off,""),s,FecV2Snapshot{},time.Hour)
    if !errors.Is(e,ErrFecV2Revision) {t.Fatal("rolled back config",e)}
    old:=FecV2Ack{Client:"alice",Direction:FecV2C2S,Revision:1,Applied:true,Off:true,Profile:FecV2Light}
    s2,ok,e:=FecV2Apply(s,old)
    if ok||e!=nil||s2.AppliedRevision!=0 {t.Fatal("late ack repainted UI",e)}
    wrong:=FecV2Ack{Client:"bob",Direction:FecV2C2S,Revision:i.Revision,Applied:true,Profile:i.Profile}
    _,ok,e=FecV2Apply(s,wrong)
    if ok||!errors.Is(e,ErrFecV2Scope) {t.Fatal("wrong client ack",e)}
    accepted:=FecV2Ack{Client:"alice",Direction:FecV2C2S,Revision:i.Revision,Applied:true,Profile:i.Profile}
    s,ok,e=FecV2Apply(s,accepted)
    if e!=nil||!ok||s.AppliedRevision!=i.Revision||s.AppliedProfile!=FecV2Medium {t.Fatal("ack",e)}
}
func TestF2ControlIsolationAndAggressiveStartup(t *testing.T) {
    a:=f2Config("alice",FecV2C2S,FecV2Auto,FecV2Conservative)
    b:=f2Config("alice",FecV2S2C,FecV2Auto,FecV2Aggressive)
    c:=f2Config("bob",FecV2C2S,FecV2Auto,FecV2Conservative)
    sa,ia,e:=FecV2Step(a,FecV2State{},FecV2Snapshot{},0)
    if e!=nil||ia.Profile!=FecV2Strong {t.Fatal(ia,e)}
    sb,ib,e:=FecV2Step(b,FecV2State{},FecV2Snapshot{},0)
    if e!=nil||ib.Profile!=FecV2Maximum {t.Fatal(ib,e)}
    _,ic,e:=FecV2Step(c,FecV2State{},FecV2Snapshot{},0)
    if e!=nil||ic.Profile!=FecV2Strong {t.Fatal(ic,e)}
    if _,_,e=FecV2Step(b,sa,f2Snapshot("alice",FecV2S2C,2*time.Second,0,0),2*time.Second);!errors.Is(e,ErrFecV2Scope) {t.Fatal("C2S leaked into S2C",e)}
    if _,_,e=FecV2Step(a,sb,f2Snapshot("alice",FecV2C2S,2*time.Second,0,0),2*time.Second);!errors.Is(e,ErrFecV2Scope) {t.Fatal("S2C leaked into C2S",e)}
    start:=FecV2Balanced
    b.StartProfile=&start
    b.ConfigRevision=2
    _,ib,e=FecV2Step(b,sb,FecV2Snapshot{},time.Second)
    if e!=nil||ib.Profile!=FecV2High {t.Fatal("custom aggressive start not +1",ib,e)}
}
func TestF2ControlSampleValidityAndFrozenHost(t *testing.T) {
    cfg:=f2Config("x",FecV2S2C,FecV2Auto,FecV2Conservative)
    s,_,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    checks:=[]struct{
        name string; alter func(*FecV2Snapshot); want FecV2Validity
    }{
        {"zero",func(v *FecV2Snapshot){v.Fast=FecV2Window{}},FecV2Unknown},
        {"lost_feedback",func(v *FecV2Snapshot){v.Validity=FecV2Unknown},FecV2Unknown},
        {"censored",func(v *FecV2Snapshot){v.Validity=FecV2Censored;v.Slow.Censored=1000;v.Slow.Observed=5000},FecV2Censored},
        {"coverage",func(v *FecV2Snapshot){v.Slow.Observed=4000},FecV2Unknown},
        {"whole_group_disappeared",func(v *FecV2Snapshot){v.ActualK=[16]uint64{}},FecV2Unknown},
        {"host_drop",func(v *FecV2Snapshot){v.HostDrops=1},FecV2HostCapacity},
        {"queue",func(v *FecV2Snapshot){v.QueueGrowing=true},FecV2HostCapacity},
        {"denominator",func(v *FecV2Snapshot){v.UnexplainedDenominatorJump=true},FecV2Unknown},
        {"stale",func(v *FecV2Snapshot){v.At=0},FecV2Unknown},
    }
    for _,test:=range checks {
        t.Run(test.name,func(t *testing.T){
            v:=f2Snapshot("x",FecV2S2C,time.Second,100,300)
            test.alter(&v)
            now:=4*time.Second
            if test.name=="stale" { now=8*time.Second }
            state,decision,e:=FecV2Step(cfg,s,v,now)
            if e!=nil||decision.Validity!=test.want||decision.Send||state.Desired!=FecV2Strong {
                t.Fatalf("%s -> %+v %v",test.name,decision,e)
            }
        })
    }
    // A report that advances no window cannot be repeatedly counted towards lowering.
    v:=f2Snapshot("x",FecV2S2C,2*time.Second,0,0)
    s,_,e=FecV2Step(cfg,s,v,2*time.Second)
    if e!=nil {t.Fatal(e)}
    _,decision,e:=FecV2Step(cfg,s,v,4*time.Second)
    if e!=nil||decision.Send||decision.Validity!=FecV2Unknown {t.Fatal(decision,e)}
}
func TestF2ControlHysteresisEscalateLowerAndPartialWeight(t *testing.T) {
    cfg:=f2Config("flow",FecV2C2S,FecV2Auto,FecV2Conservative)
    s,_,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    down:=0
    for sec:=2;sec<=180;sec+=2 {
        now:=time.Duration(sec)*time.Second
        v:=f2Snapshot("flow",FecV2C2S,now,0,0)
        next,out,e:=FecV2Step(cfg,s,v,now)
        if e!=nil {t.Fatal(e)}
        if out.Send {
            if next.Desired>=s.Desired {t.Fatal("wrong down direction",out)}
            down++
        }
        s=next
    }
    if s.Desired!=FecV2Light||down!=5 {t.Fatalf("down=%d desired=%s",down,s.Desired)}
    for j,sec:=range []int{182,184} {
        now:=time.Duration(sec)*time.Second
        v:=f2Snapshot("flow",FecV2C2S,now,310,1800)
        next,out,e:=FecV2Step(cfg,s,v,now)
        if e!=nil {t.Fatal(e)}
        if out.Send!=(j==1) {t.Fatalf("up before two windows j=%d %+v",j,out)}
        s=next
    }
    if s.Desired!=FecV2Maximum {t.Fatalf("IID30%% expected ceiling, got %v",s.Desired)}
    var sparse [16]uint64
    sparse[0]=6000
    if base,unreachable,_:=fecV2Base(sparse,0.20);base!=FecV2Maximum||!unreachable {
        t.Fatal("k1/high loss must report unattainable target")
    }
    var full [16]uint64
    full[15]=375
    if base,unreachable,_:=fecV2Base(full,0.05);base!=FecV2Mild||unreachable {
        t.Fatal("full k16 5% wrong baseline",base,unreachable)
    }
    if q:=fecV2Mix(full,FecV2Mild,0.05);q<=0||q>0.001 {
        t.Fatal("unexpected IID partial model",q)
    }
}
func TestF2ControlSparseEmergencyBurstAndIdleIsolation(t *testing.T) {
    cfg:=f2Config("sparse",FecV2S2C,FecV2Auto,FecV2Conservative)
    start:=FecV2Light
    cfg.StartProfile=&start
    s,_,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    v:=FecV2Snapshot{Client:"sparse",Direction:FecV2S2C,
        Validity:FecV2Unknown,At:2*time.Second,TrustedMissingOrLate:2}
    s,out,e:=FecV2Step(cfg,s,v,2*time.Second)
    if e!=nil||!out.Send||s.Desired!=FecV2Mild {t.Fatal("bounded sparse up",out,e)}
    v.At=4*time.Second
    s,out,e=FecV2Step(cfg,s,v,4*time.Second)
    if e!=nil||out.Send {t.Fatal("sparse surged without 10s",out,e)}
    v.At=12*time.Second
    s,out,e=FecV2Step(cfg,s,v,12*time.Second)
    if e!=nil||out.Send {t.Fatal("old sparse events replayed as fresh",out,e)}
    v.At=14*time.Second
    v.TrustedMissingOrLate=4 // two newly confirmed events since the prior rise
    s,out,e=FecV2Step(cfg,s,v,14*time.Second)
    if e!=nil||!out.Send||s.Desired!=FecV2Medium {t.Fatal("sparse cooldown",out,e)}
    v.At=22*time.Second
    v.HostDrops=10
    s,out,e=FecV2Step(cfg,s,v,22*time.Second)
    if e!=nil||out.Send||out.Validity!=FecV2HostCapacity {t.Fatal("capacity must freeze",out,e)}
    // A pure Step does not own any payload activity/idle clock. No callbacks,
    // network probes, keepalives or hidden scheduling occur in off/fixed/auto.
}

func TestF2ControlActualKSourceWeightAndBurstBound(t *testing.T) {
    var partial [16]uint64
    partial[7]=100
    partial[15]=100
    got:=fecV2Mix(partial,FecV2Mild,0.05)
    q8:=fecV2Residual(8,2,0.05)
    q16:=fecV2Residual(16,4,0.05)
    want:=(800*q8+1600*q16)/2400
    if d:=got-want;d>1e-12||d< -1e-12 {t.Fatalf("not source-weighted %g != %g",got,want)}
    var onlyK8 [16]uint64
    onlyK8[7]=750
    if profile,unreachable,_:=fecV2Base(onlyK8,0.05);profile!=FecV2Medium||unreachable {
        t.Fatalf("k8 should need medium at IID5%%: %v %v",profile,unreachable)
    }
    cfg:=f2Config("burst",FecV2C2S,FecV2Auto,FecV2Conservative)
    start:=FecV2Light
    cfg.StartProfile=&start
    state,_,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    for _,sec:=range []int{2,4,6} {
        at:=time.Duration(sec)*time.Second
        snap:=f2Snapshot("burst",FecV2C2S,at,0,0)
        if sec<6 {snap.ConsecutiveMatureGaps=3}
        next,intent,e:=FecV2Step(cfg,state,snap,at)
        if e!=nil {t.Fatal(e)}
        if sec==2 && intent.Send {t.Fatal("burst rose before 2 windows")}
        if sec==4 && (!intent.Send||intent.Profile!=FecV2Mild) {
            t.Fatalf("burst must add at most one: %+v",intent)
        }
        if sec==6 && intent.Send {t.Fatal("burst stacked another profile")}
        state=next
    }
}

func TestF2ControlAggressiveStableOneProfileAboveNormal(t *testing.T) {
    plain:=f2Config("customer",FecV2C2S,FecV2Auto,FecV2Conservative)
    aggressive:=f2Config("customer",FecV2S2C,FecV2Auto,FecV2Aggressive)
    a,_,e:=FecV2Step(plain,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    b,_,e:=FecV2Step(aggressive,FecV2State{},FecV2Snapshot{},0)
    if e!=nil {t.Fatal(e)}
    for sec:=2;sec<=180;sec+=2 {
        now:=time.Duration(sec)*time.Second
        a,_,e=FecV2Step(plain,a,f2Snapshot("customer",FecV2C2S,now,0,0),now)
        if e!=nil {t.Fatal(e)}
        b,_,e=FecV2Step(aggressive,b,f2Snapshot("customer",FecV2S2C,now,0,0),now)
        if e!=nil {t.Fatal(e)}
    }
    if a.Desired!=FecV2Light || b.Desired!=FecV2Mild {
        t.Fatalf("steady targets normal=%s aggressive=%s (one level required)",a.Desired,b.Desired)
    }
}

 
// W52 real Auto (8 Mbps original ARM64 owner, outer DATA OFF) had genuine
// 1%-loss low-stage VALID observations interleaved with independently
// larger authentic full-k cohorts, which no longer invalidate PN samples.
// Retain only bounded, authenticated VALID proof; no synthetic ACK or clean
// sample is permitted, and UNKNOWN must never itself issue a downshift.
func TestF2ControlW52IntermittentActualKNoFakeCleanDown(t *testing.T) {
    cfg:=f2Config("w52",FecV2C2S,FecV2Auto,FecV2Conservative)
    state,_,err:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if err!=nil {t.Fatal(err)}
    // Two independently measured high-loss fast cohorts legitimately rise.
    for _,sec:=range []int{2,4} {
        now:=time.Duration(sec)*time.Second
        state,_,err=FecV2Step(cfg,state,f2Snapshot("w52",FecV2C2S,now,310,1800),now)
        if err!=nil {t.Fatal(err)}
    }
    if state.Desired!=FecV2Maximum {t.Fatalf("no legitimate high-loss rise: %+v",state)}
    var observedValid,observedUnknown int
    stepped:=false
    for _,stage:=range []struct{sec int; misaligned bool}{
        {6,false},{8,true},{10,false},{12,false},
        {14,true},{16,false},{18,false},{20,true},{22,false},
        {24,false},{26,false},{28,false},{30,false},
        {32,false},{34,false},{36,false},
    } {
        now:=time.Duration(stage.sec)*time.Second
        snap:=f2Snapshot("w52",FecV2C2S,now,12,70)
        if stage.misaligned {
            // Full k counts exceed sampled FIRST: normalize k within
            // its own cohort, rather than inventing missing or zero-loss.
            snap.ActualK[15]=400
        }
        next,intent,e:=FecV2Step(cfg,state,snap,now)
        if e!=nil {t.Fatal(e)}
        observedValid++
        if intent.Validity!=FecV2Valid {
            t.Fatalf("independent actual-k distribution rejected at %ds: %+v",stage.sec,intent)
        }
        if intent.Send {
            if intent.Profile!=FecV2Strong {
                t.Fatalf("bad downshift from genuine proof: %+v",intent)
            }
            stepped=true
        }
        state=next
    }
    if observedUnknown!=0||observedValid!=16||!stepped||state.Desired!=FecV2Strong {
        t.Fatalf("bounded W52 hold did not downshift: valid=%d unknown=%d stepped=%t profile=%s",
            observedValid,observedUnknown,stepped,state.Desired)
    }
}

func TestF2ControlW52CensoredCapacityAndLongUnknownResetDownProof(t *testing.T) {
    cfg:=f2Config("isolation",FecV2C2S,FecV2Auto,FecV2Conservative)
    for _,fault:=range []struct{name string; mutate func(*FecV2Snapshot)}{
        {"feedback_lost",func(s *FecV2Snapshot){s.Validity=FecV2Unknown}},
        {"capacity",func(s *FecV2Snapshot){s.HostDrops=1}},
        {"censored",func(s *FecV2Snapshot){s.Validity=FecV2Censored}},
        {"long_k_unknown",func(s *FecV2Snapshot){s.ActualK=[16]uint64{}}}, // no observed block type
    } {
        t.Run(fault.name,func(t *testing.T){
            state,_,e:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
            if e!=nil {t.Fatal(e)}
            for _,sec:=range []int{2,4} {
                now:=time.Duration(sec)*time.Second
                state,_,e=FecV2Step(cfg,state,f2Snapshot("isolation",FecV2C2S,now,310,1800),now)
                if e!=nil {t.Fatal(e)}
            }
            first:=f2Snapshot("isolation",FecV2C2S,6*time.Second,12,70)
            state,_,e=FecV2Step(cfg,state,first,6*time.Second)
            if e!=nil||state.DownValidWindows!=1 {t.Fatalf("no valid anchor %+v %v",state,e)}
            faultAt:=8*time.Second
            if fault.name=="long_k_unknown" {faultAt=14*time.Second}
            bad:=f2Snapshot("isolation",FecV2C2S,faultAt,12,70)
            fault.mutate(&bad)
            state,intent,e:=FecV2Step(cfg,state,bad,faultAt)
            if e!=nil||intent.Send||state.DownValidWindows!=0||state.DownSources!=0 {
                t.Fatalf("invalid evidence not cleared: state=%+v intent=%+v err=%v",state,intent,e)
            }
            // A later good cohort cannot spend the invalidated earlier time.
            when:=faultAt+2*time.Second
            state,intent,e=FecV2Step(cfg,state,f2Snapshot("isolation",FecV2C2S,when,12,70),when)
            if e!=nil||intent.Send||state.DownValidWindows!=1 {
                t.Fatalf("stale down proof reused: %+v %+v %v",state,intent,e)
            }
        })
    }
}


// Full closed-block k can outnumber an independent sampled first-send
// cohort. It supplies a normalized block mix, not another loss denominator.
// Missing feedback/host capacity and empty k remain UNKNOWN.
func TestF2ControlW56AuthenticKWindowSkewRiskEnvelope(t *testing.T){
    cfg:=f2Config("w56",FecV2C2S,FecV2Auto,FecV2Conservative)
    snap:=f2Snapshot("w56",FecV2C2S,2*time.Second,10,60)
    snap.ActualK[15]=386 // 6176 genuine k sources vs 6000 mature FIRST
    validity,reason,p:=fecV2Quality(2*time.Second,snap)
    if validity!=FecV2Valid || reason!="matched sampled first-send and normalized actual-k"{
        t.Fatalf("small native cohort overhang discarded: %s %q",validity,reason)
    }
    for prof:=FecV2Light;prof<=FecV2Maximum;prof++{
        old:=fecV2Mix(snap.ActualK,prof,p)
        conservative:=fecV2GuardedMix(snap,prof,p)
        if conservative<old || conservative>1 {
            t.Fatalf("false optimistic bound profile=%s q=%g guarded=%g",prof,old,conservative)
        }
    }
    snap.ActualK[15]=395 // independent full k distribution can exceed PN sample
    validity,reason,_=fecV2Quality(2*time.Second,snap)
    if validity!=FecV2Valid{
        t.Fatalf("valid full k distribution incorrectly censored: %s %q",validity,reason)
    }
    // False zero loss from no genuine positive feedback is prohibited.
    snap.ActualK[15]=386
    snap.Validity=FecV2Unknown
    validity,_,_=fecV2Quality(2*time.Second,snap)
    if validity!=FecV2Unknown{t.Fatal("no M2 feedback forged VALID")}
    snap.Validity=FecV2Valid
    snap.HostDrops=1
    validity,_,_=fecV2Quality(2*time.Second,snap)
    if validity!=FecV2HostCapacity{t.Fatal("host drop not frozen")}
    snap.HostDrops=0
    snap.Fast.FirstSent=32
    snap.Fast.Observed=32
    snap.Slow.FirstSent=128
    snap.Slow.Observed=128
    snap.ActualK[15]=8
    validity,_,_=fecV2Quality(2*time.Second,snap)
    if validity!=FecV2Unknown{t.Fatal("sparse/idle window forged VALID")}
    _=cfg
}

func TestF2ControlW56RealLowCanDownWithSmallKOverhang(t *testing.T) {
    cfg:=f2Config("k-skew",FecV2C2S,FecV2Auto,FecV2Conservative)
    state,_,err:=FecV2Step(cfg,FecV2State{},FecV2Snapshot{},0)
    if err!=nil{t.Fatal(err)}
    for _,sec:=range []int{2,4}{
        at:=time.Duration(sec)*time.Second
        state,_,err=FecV2Step(cfg,state,f2Snapshot("k-skew",FecV2C2S,at,310,1800),at)
        if err!=nil{t.Fatal(err)}
    }
    if state.Desired!=FecV2Maximum{t.Fatal("genuine high loss failed UP")}
    downs:=0
    for sec:=6;sec<=38;sec+=2{
        at:=time.Duration(sec)*time.Second
        snap:=f2Snapshot("k-skew",FecV2C2S,at,10,60)
        snap.ActualK[15]=386 // original native close-vs-M2 skew, within bound
        previous:=state
        next,intent,e:=FecV2Step(cfg,state,snap,at)
        if e!=nil||intent.Validity!=FecV2Valid{
            t.Fatalf("bounded authentic k window rejected at %ds: %+v %v",sec,intent,e)
        }
        if intent.Send{
            if previous.Desired!=FecV2Maximum||intent.Profile!=FecV2Strong||sec<36{
                t.Fatalf("too-fast/illegal DOWN: %+v",intent)
            }
            downs++
        }
        state=next
    }
    if downs!=1 ||state.Desired!=FecV2Strong {
        t.Fatalf("no legitimate gradual W56 DOWN: downs=%d state=%+v",downs,state)
    }
}
