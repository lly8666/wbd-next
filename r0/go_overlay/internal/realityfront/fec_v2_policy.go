// FEC v2 cold-only policy. This file is inert until M0 installs it in the
// actual Go control clone, binds authenticated per-client/direction snapshots,
// and wires SetTxFec acknowledgements. No timers, network IO or idle writes.
package realityfront

import (
    "errors"
    "math"
    "time"
)

type FecV2Profile uint8

const (
    FecV2Light FecV2Profile = iota
    FecV2Mild
    FecV2Medium
    FecV2Balanced
    FecV2High
    FecV2Strong
    FecV2Maximum
)
const FecV2ProfileCount = 7

var fecV2ProfileNames = [FecV2ProfileCount]string{
    "light", "mild", "medium", "balanced", "high", "strong", "maximum",
}
var fecV2RhoNum = [FecV2ProfileCount]uint8{1, 1, 3, 1, 3, 1, 5}
var fecV2RhoDen = [FecV2ProfileCount]uint8{8, 4, 8, 2, 4, 1, 4}

func (p FecV2Profile) Valid() bool { return p < FecV2ProfileCount }
func (p FecV2Profile) String() string {
    if !p.Valid() { return "invalid" }
    return fecV2ProfileNames[p]
}

// FecV2Parity is a fixed-policy calculation on actual closed-block k,
// not a target based on an assumed full group or legacy 20-source tables.
func FecV2Parity(p FecV2Profile, k uint8) (uint8, error) {
    if !p.Valid() || k == 0 || k > 16 { return 0, errFecV2Policy }
    n, d := uint16(fecV2RhoNum[p]), uint16(fecV2RhoDen[p])
    return uint8((uint16(k)*n + d-1)/d), nil
}

type FecV2Mode string
const (
    FecV2Off FecV2Mode = "off"
    FecV2Fixed FecV2Mode = "fixed"
    FecV2Auto FecV2Mode = "auto"
)
type FecV2Transport string
const (
    FecV2Normal FecV2Transport = "normal"
    FecV2Game FecV2Transport = "game"
)
type FecV2Direction string
const (
    FecV2C2S FecV2Direction = "c2s"
    FecV2S2C FecV2Direction = "s2c"
)
type FecV2AutoPolicy string
const (
    FecV2Conservative FecV2AutoPolicy = "normal"
    FecV2Aggressive FecV2AutoPolicy = "aggressive"
)

var errFecV2Policy = errors.New("fec v2: invalid policy or observation")
var ErrFecV2GameAuto = errors.New("fec v2: Game does not support auto")
var ErrFecV2Revision = errors.New("fec v2: stale or exhausted revision")
var ErrFecV2Scope = errors.New("fec v2: client/direction mismatch")

// ConfigRevision belongs to the existing Go parameter/controller owner.
// StartProfile=nil means strong; aggressive starts one profile above it.
// The caller must keep a distinct State per authenticated client/direction.
type FecV2Config struct {
    Client string
    Direction FecV2Direction
    Transport FecV2Transport
    Mode FecV2Mode
    Profile FecV2Profile
    AutoPolicy FecV2AutoPolicy
    StartProfile *FecV2Profile
    ConfigRevision uint64
}
func (c FecV2Config) validate() error {
    if c.Client == "" || (c.Direction != FecV2C2S && c.Direction != FecV2S2C) ||
        (c.Transport != FecV2Normal && c.Transport != FecV2Game) ||
        (c.Mode != FecV2Off && c.Mode != FecV2Fixed && c.Mode != FecV2Auto) {
        return errFecV2Policy
    }
    if c.Mode == FecV2Auto && c.Transport == FecV2Game { return ErrFecV2GameAuto }
    if c.Mode == FecV2Fixed && !c.Profile.Valid() { return errFecV2Policy }
    if c.Mode == FecV2Auto && c.AutoPolicy != FecV2Conservative && c.AutoPolicy != FecV2Aggressive {
        return errFecV2Policy
    }
    if c.StartProfile != nil && !c.StartProfile.Valid() { return errFecV2Policy }
    return nil
}

// All counters describe successfully first-submitted mature SOURCE symbols,
// never final-receipt success, retransmit attempts, parity or an inferred
// physical wire loss rate. Windows contain disjoint fast 2s/slow 8s horizons.
// Observed has definite first-send outcome; other statuses are not zeros.
type FecV2Window struct {
    FirstSent uint64
    Observed uint64
    Missing uint64
    Unknown uint64
    Censored uint64
}
func (w FecV2Window) sane() bool {
    return w.Observed <= w.FirstSent && w.Missing <= w.Observed &&
        w.Unknown <= w.FirstSent-w.Observed &&
        w.Censored <= w.FirstSent-w.Observed-w.Unknown
}
type FecV2Validity string
const (
    FecV2Valid FecV2Validity = "VALID"
    FecV2Unknown FecV2Validity = "UNKNOWN"
    FecV2Censored FecV2Validity = "CENSORED"
    FecV2HostCapacity FecV2Validity = "HOST_CAPACITY"
)
type FecV2Snapshot struct {
    Client string
    Direction FecV2Direction
    At time.Duration             // monotonic caller-provided measurement timestamp
    SRTT time.Duration           // trusted lane RTT, or zero if unknown
    Validity FecV2Validity
    Fast FecV2Window
    Slow FecV2Window
    ActualK [16]uint64           // slow-window mature closed block counts, k=1..16
    UnexplainedDenominatorJump bool
    HostDrops uint64
    QueueGrowing bool
    TrustedMissingOrLate uint64   // monotonic cumulative confirmed business misses/late events
    ConsecutiveMatureGaps uint8   // burst hint, not IID wire loss
}

type FecV2State struct {
    Initialized bool
    Client string
    Direction FecV2Direction
    ConfigRevision uint64
    Mode FecV2Mode
    Policy FecV2AutoPolicy
    Desired FecV2Profile
    DesiredOff bool
    RequestedRevision uint64
    AppliedRevision uint64
    AppliedProfile FecV2Profile
    AppliedOff bool
    LastEvaluate time.Duration
    LastSnapshot time.Duration
    HaveSnapshot bool
    HighFastWindows uint8
    DownSince time.Duration
    DownSources uint64
    // Only genuinely VALID low-loss evaluations add evidence. A short
    // actual-k cohort alignment miss may pause (not advance) the hold.
    DownValidWindows uint8
    DownLastValid time.Duration
    LastDown time.Duration
    LastSparseUp time.Duration
    LastSparseEvents uint64 // last consumed cumulative trustworthy events
    BurstUntil time.Duration
}
type FecV2Intent struct {
    Send bool                  // send SetTxFec only if true
    Client string
    Direction FecV2Direction
    Mode FecV2Mode
    Profile FecV2Profile
    Revision uint64
    Validity FecV2Validity
    Reason string
    PredictedResidual float64 // 0..1, model estimate, not an observed loss
    TargetUnattainable bool
}

func fecV2NextRevision(c FecV2Config, s FecV2State) (uint64, error) {
    if s.RequestedRevision == ^uint64(0) { return 0, ErrFecV2Revision }
    n := s.RequestedRevision + 1
    if c.ConfigRevision > n { n = c.ConfigRevision }
    if n == 0 { return 0, ErrFecV2Revision }
    return n, nil
}
func fecV2Raise(p FecV2Profile) FecV2Profile {
    if p < FecV2Maximum { return p+1 }
    return p
}
func fecV2Start(c FecV2Config) FecV2Profile {
    p := FecV2Strong
    if c.StartProfile != nil { p = *c.StartProfile }
    if c.AutoPolicy == FecV2Aggressive { p = fecV2Raise(p) }
    return p
}
func fecV2Issue(c FecV2Config, s FecV2State, out FecV2Intent, p FecV2Profile, off bool) (FecV2State,FecV2Intent,error) {
    n,e := fecV2NextRevision(c,s)
    if e != nil { return s,out,e }
    s.Desired = p
    s.DesiredOff = off
    s.RequestedRevision = n
    out.Send,out.Profile,out.Revision = true,p,n
    return s,out,nil
}

// Exact binomial tail for bounded k<=16, r<=20. Evaluated at most once
// per caller's 2s cold tick; the result is NOT a measured line-loss rate.
func fecV2Residual(k, r uint8, p float64) float64 {
    if p <= 0 { return 0 }
    if p >= 1 { return 1 }
    n := int(k)+int(r)-1
    tail := 0.0
    xprob := math.Pow(1-p,float64(n))
    for x:=0; x<=n; x++ {
        if x>=int(r) { tail += xprob }
        if x<n { xprob *= float64(n-x)/float64(x+1)*p/(1-p) }
    }
    return math.Min(1,p*tail)
}
func fecV2Mix(hist [16]uint64, profile FecV2Profile, p float64) float64 {
    total,weighted := 0.0,0.0
    for i,n := range hist {
        if n==0 {continue}
        k:=uint8(i+1)
        r,_:=FecV2Parity(profile,k)
        w:=float64(n)*float64(k)
        total+=w
        weighted+=w*fecV2Residual(k,r,p)
    }
    if total==0 {return 1}
    return weighted/total
}
func fecV2Base(hist [16]uint64,p float64) (FecV2Profile,bool,float64) {
    for i:=FecV2Light; i<=FecV2Maximum; i++ {
        q:=fecV2Mix(hist,i,p)
        if q<=0.001 {return i,false,q}
    }
    return FecV2Maximum,true,fecV2Mix(hist,FecV2Maximum,p)
}

// Native 8s-M2 first-send maturity and the actual block-close k counters
// both describe genuine first-transmitted sources, but their fixed windows
// have different closure boundary timing. W55 retained original cohorts:
// 38 C2S actual-k UNKNOWN ticks, usually just 0.03..4.9% *above* 8s
// mature source count, never missing ACKs. The non-sparse product traffic
// runs ~7k sources/window. Allow at most a 5% upper boundary skew, with a
// conservative residual penalty for every uncertain source, not a clipped
// histogram, forged receipt, zero-loss inference, or lenient under-coverage.
const fecV2MaxActualKWindowOverhang=0.05

func fecV2KCount(h [16]uint64) float64 {
    total:=0.0
    for i,n:=range h { total+=float64(n)*float64(i+1) }
    return total
}

// q(known mix)+fraction-of-cohort-uncertainty*worst(any legal k) never
// treats unmatched block-close symbols as clean, and is evaluated only in
// the existing 2s cold quality control. This is a conservative uncertainty
// envelope, not a claim of a mathematically exact same-time histogram.
func fecV2GuardedMix(s FecV2Snapshot,profile FecV2Profile,p float64) float64 {
    if s.Slow.FirstSent==0{return 1}
    observed:=fecV2Mix(s.ActualK,profile,p)
    ratio:=fecV2KCount(s.ActualK)/float64(s.Slow.FirstSent)
    skew:=math.Abs(ratio-1)
    if skew==0{return observed}
    worst:=0.0
    for k:=uint8(1);k<=16;k++{
        repair,_:=FecV2Parity(profile,k)
        q:=fecV2Residual(k,repair,p)
        if q>worst{worst=q}
    }
    return math.Min(1,observed+skew*worst)
}
func fecV2GuardedBase(s FecV2Snapshot,p float64)(FecV2Profile,bool){
    for profile:=FecV2Light;profile<=FecV2Maximum;profile++{
        if fecV2GuardedMix(s,profile,p)<=0.001{return profile,false}
    }
    return FecV2Maximum,true
}
func fecV2Quality(now time.Duration,s FecV2Snapshot) (FecV2Validity, string, float64) {
    if s.Validity==FecV2HostCapacity || s.HostDrops>0 || s.QueueGrowing {
        return FecV2HostCapacity,"local drop / queue growth",0
    }
    if s.At<0 || now<s.At || s.SRTT<0 {return FecV2Unknown,"invalid observation time",0}
    maxAge:=6*time.Second
    if 3*s.SRTT>maxAge {maxAge=3*s.SRTT}
    if now-s.At>maxAge {return FecV2Unknown,"stale feedback",0}
    if s.Validity!=FecV2Valid {
        if s.Validity==FecV2Censored {return FecV2Censored,"censored first-send evidence",0}
        return FecV2Unknown,"missing feedback",0
    }
    if !s.Fast.sane() || !s.Slow.sane() || s.UnexplainedDenominatorJump {
        return FecV2Unknown,"window denominator invalid",0
    }
    if s.Fast.FirstSent==0 || s.Slow.FirstSent==0 || s.Fast.Observed==0 || s.Slow.Observed==0 {
        return FecV2Unknown,"zero first-send sample",0
    }
    for _,w:=range []FecV2Window{s.Fast,s.Slow} {
        if float64(w.Observed)/float64(w.FirstSent)<0.90 {
            return FecV2Unknown,"first-send coverage below 90%",0
        }
        if float64(w.Unknown+w.Censored)/float64(w.FirstSent)>0.20 {
            return FecV2Censored,"uncertain / censored fraction above 20%",0
        }
    }
    kSources:=fecV2KCount(s.ActualK)
    kRatio:=kSources/float64(s.Slow.FirstSent)
    if kSources==0 || kRatio<0.90 ||
        kRatio>1+fecV2MaxActualKWindowOverhang {
        return FecV2Unknown,"actual-k observation incomplete",0
    }
    if s.Fast.Observed<512 || s.Slow.Observed<512 {
        return FecV2Unknown,"fewer than 512 valid sources",0
    }
    pf:=float64(s.Fast.Missing)/float64(s.Fast.Observed)
    ps:=float64(s.Slow.Missing)/float64(s.Slow.Observed)
    n:=float64(s.Slow.Observed)
    margin:=math.Min(0.005,1.64*math.Sqrt(ps*(1-ps)/n))
    if kRatio>1 {
        return FecV2Valid,"mature first-send; bounded authentic k-window overhang",
            math.Min(1,math.Max(pf,ps)+margin)
    }
    return FecV2Valid,"mature first-send evidence",math.Min(1,math.Max(pf,ps)+margin)
}

// Reset all of the downshift proof together; it is never inferred from
// a skipped, unknown, censored, or capacity-limited quality observation.
func fecV2ClearDown(s *FecV2State) {
    s.DownSince,s.DownSources=0,0
    s.DownValidWindows,s.DownLastValid=0,0
}

// FecV2Step is deterministic, side-effect-free and has no timers or idle
// activity writes. The controlling Go goroutine must provide distinct state
// per authenticated client/direction and send its returned intent itself.
// A requested revision is NOT an applied revision (see FecV2Apply).
func FecV2Step(c FecV2Config, previous FecV2State, snap FecV2Snapshot, now time.Duration) (FecV2State,FecV2Intent,error) {
    var out FecV2Intent
    out.Client,out.Direction,out.Mode=c.Client,c.Direction,c.Mode
    if err:=c.validate();err!=nil{return previous,out,err}
    if now<0 {return previous,out,errFecV2Policy}
    s:=previous
    if s.Initialized && (s.Client!=c.Client || s.Direction!=c.Direction) {
        return previous,out,ErrFecV2Scope
    }
    if s.Initialized && c.ConfigRevision<s.ConfigRevision {
        return previous,out,ErrFecV2Revision
    }
    if !s.Initialized || c.ConfigRevision>s.ConfigRevision || c.Mode!=s.Mode ||
        (c.Mode==FecV2Auto && c.AutoPolicy!=s.Policy) {
        s.Initialized=true
        s.Client,s.Direction,s.ConfigRevision=c.Client,c.Direction,c.ConfigRevision
        s.Mode,s.Policy=c.Mode,c.AutoPolicy
        s.HighFastWindows=0
        fecV2ClearDown(&s)
        s.BurstUntil=0
        s.LastEvaluate=0
        p,off:=FecV2Light,false
        switch c.Mode {
        case FecV2Off: off=true
        case FecV2Fixed: p=c.Profile
        case FecV2Auto: p=fecV2Start(c)
        }
        out.Validity,out.Reason=FecV2Unknown,"new configuration"
        return fecV2Issue(c,s,out,p,off)
    }
    out.Profile,out.Revision=s.Desired,s.RequestedRevision
    if c.Mode!=FecV2Auto {out.Reason="fixed/off has no auto sampler";return s,out,nil}
    if s.LastEvaluate!=0 && now-s.LastEvaluate<2*time.Second {
        out.Reason="evaluation rate limited";return s,out,nil
    }
    s.LastEvaluate=now
    if snap.Client!=c.Client || snap.Direction!=c.Direction {return previous,out,ErrFecV2Scope}
    if s.HaveSnapshot && snap.At<=s.LastSnapshot {
        out.Validity,out.Reason=FecV2Unknown,"feedback not advanced";return s,out,nil
    }
    s.LastSnapshot,s.HaveSnapshot=snap.At,true
    validity,reason,p:=fecV2Quality(now,snap)
    out.Validity,out.Reason=validity,reason
    if validity!=FecV2Valid {
        s.HighFastWindows=0
        // In real M2 windows, independently matured original FIRST-source
        // receipts and k-histogram cohorts can straddle a two-second tick.
        // Preserve *previous* VALID evidence across at most a 6s alignment
        // gap, but NEVER count this UNKNOWN tick or issue a downgrade from it.
        // Missing feedback, censorship, host drops and longer unknowns reset.
        transientK := validity==FecV2Unknown &&
            reason=="actual-k observation incomplete" &&
            s.DownSince!=0 && s.DownLastValid!=0 &&
            now>=s.DownLastValid && now-s.DownLastValid<=6*time.Second
        if !transientK {fecV2ClearDown(&s)}
        // Host-limited misses cannot be banked for a later network-loss
        // escalation. Consume them while freezing the known good profile.
        if validity==FecV2HostCapacity && snap.TrustedMissingOrLate>s.LastSparseEvents {
            s.LastSparseEvents=snap.TrustedMissingOrLate
        }
        freshSparse:=snap.TrustedMissingOrLate>s.LastSparseEvents &&
            snap.TrustedMissingOrLate-s.LastSparseEvents>=2
        if validity!=FecV2HostCapacity && freshSparse &&
            (s.LastSparseUp==0 || now-s.LastSparseUp>=10*time.Second) &&
            s.Desired<FecV2Maximum {
            s.LastSparseEvents=snap.TrustedMissingOrLate
            s.LastSparseUp=now
            out.Reason="bounded sparse credible misses"
            return fecV2Issue(c,s,out,fecV2Raise(s.Desired),false)
        }
        return s,out,nil
    }
    baseline,unattainable:=fecV2GuardedBase(snap,p)
    target:=baseline
    if c.AutoPolicy==FecV2Aggressive {target=fecV2Raise(target)}
    if snap.ConsecutiveMatureGaps>=3 && snap.Fast.Observed>=512 {
        s.BurstUntil=now+10*time.Second
    }
    if s.BurstUntil>now {
        extra:=fecV2Raise(baseline)
        if extra>target {target=extra}
    }
    out.TargetUnattainable=unattainable
    out.PredictedResidual=fecV2GuardedMix(snap,s.Desired,p)
    if target>s.Desired {
        if s.HighFastWindows<2 {s.HighFastWindows++}
        fecV2ClearDown(&s)
        if s.HighFastWindows>=2 {
            s.HighFastWindows=0
            out.Reason="two valid rising fast windows"
            return fecV2Issue(c,s,out,target,false)
        }
        return s,out,nil
    }
    s.HighFastWindows=0
    if target<s.Desired && s.Desired>FecV2Light && s.BurstUntil<=now &&
        fecV2GuardedMix(snap,s.Desired-1,p)<=0.0005 {
        // A ticker stall is not an implicit VALID observation.
        if s.DownSince==0 || (s.DownLastValid!=0 &&
            (now<s.DownLastValid || now-s.DownLastValid>6*time.Second)) {
            fecV2ClearDown(&s)
            s.DownSince=now
        }
        if s.DownSources>^uint64(0)-snap.Fast.Observed {s.DownSources=^uint64(0)
        } else {s.DownSources+=snap.Fast.Observed}
        if s.DownValidWindows<5 {s.DownValidWindows++}
        s.DownLastValid=now
        // Require both elapsed hold and >=5 authentic valid 2s windows.
        // Interleaved UNKNOWN adds neither an outcome nor maturity.
        if now-s.DownSince>=10*time.Second && s.DownValidWindows>=5 &&
            s.DownSources>=4096 &&
            (s.LastDown==0 || now-s.LastDown>=10*time.Second) {
            s.LastDown=now
            fecV2ClearDown(&s)
            out.Reason="10s and 4096 valid sources; one-step down"
            return fecV2Issue(c,s,out,s.Desired-1,false)
        }
    } else {fecV2ClearDown(&s)}
    return s,out,nil
}

// Applied receipt is scoped to the exact client, direction, desired profile
// and current revision. Older late receipts never repaint the current GUI.
// Rejected/pending acknowledgement leaves Applied* unchanged.
type FecV2Ack struct {
    Client string
    Direction FecV2Direction
    Revision uint64
    Profile FecV2Profile
    Off bool
    Applied bool
    Rejected bool
}
func FecV2Apply(s FecV2State,a FecV2Ack) (FecV2State,bool,error) {
    if !s.Initialized || a.Client!=s.Client || a.Direction!=s.Direction {
        return s,false,ErrFecV2Scope
    }
    if a.Revision<s.RequestedRevision {return s,false,nil}
    if a.Revision>s.RequestedRevision || (a.Applied && a.Rejected) {
        return s,false,ErrFecV2Revision
    }
    if !a.Applied || a.Rejected {return s,false,nil}
    if a.Profile!=s.Desired || a.Off!=s.DesiredOff {
        return s,false,errFecV2Policy
    }
    s.AppliedRevision,s.AppliedProfile,s.AppliedOff=a.Revision,a.Profile,a.Off
    return s,true,nil
}
