//go:build linux && cgo && wbd_v4_embedded_go
package realityfront

// One FEC2 product policy owner per ORIGINAL credential-protected Go V4
// TLS client/direction/epoch. Normal/off never creates this object.
// This is not a second M2 controller, alternate data sender, or test-only
// APPLIED: only original Rust M1/M3/M4 actual kernel source+parity and mature
// authenticated opposite-direction kind1 can publish fixed/auto startup ACK.
import (
    "log"
    "sync"
    "time"
)

type V4PublicFecReadback struct {
    Mode FecV2Mode
    RequestedRevision uint64
    AppliedRevision uint64
    Profile FecV2Profile
    Pending bool
}
// Read-only snapshot of the ORIGINAL rust owner's post-kernel firstsend and
// authenticated reverse M2 coverage; no local Go receipt or guessed APPLIED.
type V4PublicFecM2Proof struct {
    Accepted,NotSent,Uncertain,Unknown2s,Unknown8s uint64
    Covered2s,Covered8s,ReverseReports uint64
    FirstCensored,CoverageCensored bool
    // Actual original M4 FIRST DATA + same-generation authenticated
    // reverse M2 positive receipt age, accumulated by the native 8s
    // mature window. Not an outer-repair shadow RTT or one-way delay.
    PositiveConfirmationLagNs,PositiveConfirmationSamples uint64
    PositiveConfirmationMeanUs uint64
    PositiveConfirmationMeanKnown bool
}
// Exactly the same raw native 30-field snapshot already used by FEC Auto.
// Avoid a second M2 state, new feedback packet, per-packet callback, or
// guessed default RTT when there are no real unambiguous positives.
func v4Fec2PositiveConfirmation(raw [30]uint64)(uint64,uint64,uint64,bool){
    lag,samples:=raw[12],raw[13]
    if samples==0{return lag,0,0,false}
    return lag,samples,lag/samples/1000,true
}
func v4ReadOriginalFecM2Proof(b *v4EmbeddedNativeBridge)(V4PublicFecM2Proof,error){
    var zero V4PublicFecM2Proof
    first,err:=b.rustOwnerNormalM2Firstsend()
    if err!=nil{return zero,err}
    coverage,err:=b.rustOwnerNormalM2Coverage()
    if err!=nil{return zero,err}
    // This native ABI only exists for an authenticated feature7 FEC
    // owner; failure must remain unavailable, never a fake 0ms mean.
    quality,err:=b.rustOwnerFec2MatureQuality()
    if err!=nil{return zero,err}
    lag,samples,mean,known:=v4Fec2PositiveConfirmation(quality)
    return V4PublicFecM2Proof{
        Accepted:first.Accepted,NotSent:first.DefinitelyNotSent,
        Uncertain:first.Uncertain,Unknown2s:first.Unknown2s,
        Unknown8s:first.Unknown8s,Covered2s:coverage.Covered2s,
        Covered8s:coverage.Covered8s,
        ReverseReports:coverage.AuthenticatedReverseReports,
        FirstCensored:first.Censored,CoverageCensored:coverage.Censored,
        PositiveConfirmationLagNs:lag,PositiveConfirmationSamples:samples,
        PositiveConfirmationMeanUs:mean,PositiveConfirmationMeanKnown:known,
    },nil
}

type V4PublicFecRxProof struct {
    SourceSeen,SourceAccepted,ParitySeen,ParityAccepted uint64
    SystematicCandidate,RecoveredCandidate,SystematicTun,RecoveredTun uint64
    TunFailed,DecoderRejected,AdmissionDisabled uint64
}
// Original authenticated M3 FEC first-delivery bytes classified ONLY after
// real TUN copied; does not include application receipt or raw packet data.
// Real original M1 TUN read before product FEC source staging. Five bounded
// event counts; cumulative and sampled without packet contents or addresses.
// Distinguishes already-loaned original feature7 TUN packets admitted into
// FEC source TX vs rejected before it can enter ClassStats.accepted.
type V4PublicFecM1Stage struct {
    Attempted,Queued,NotReady,Error,OversizePrecheck,ModeSkipped uint64
}

type V4PublicFecM1Ingress struct {
    ReadIPv4,SmallLoaned,SmallArenaFail,Jumbo,Rejected uint64
}

type V4PublicFecRxIpClass struct {
    SystematicUDP,RecoveredUDP,SystematicTCP,RecoveredTCP uint64
    OtherIP,TCPAckOnly,TCPData,TCPOther uint64
}

type v4ProductFecMonitor struct {
    epoch [16]byte
    state FecV2State
    cfg FecV2Config
    mu sync.Mutex
    // Real 2s/8s M4 FIRST source maturity and exact closed-k are all
    // monotonically increasing; no per-packet Go callbacks or trace buffers.
    history []v4AutoQualitySample
    startedAt time.Time
    lastAutoAt time.Duration
    stopCh chan struct{}
    doneCh chan struct{}
    once sync.Once
    started bool
}
func v4ProductFecEnabled(mode FecV2Mode)bool{
    return mode==FecV2Fixed||mode==FecV2Auto
}
func v4ConfigureProductFec(
    bridge *v4EmbeddedNativeBridge,mode FecV2Mode,
    profile FecV2Profile,authenticated V4ColdSessionSnapshot,
)(*v4ProductFecMonitor,error){
    if !v4ProductFecEnabled(mode){return nil,nil}
    if mode==FecV2Auto{profile=FecV2Strong}
    if !profile.Valid()||authenticated.Epoch()==[16]byte{}{
        return nil,ErrAdmissionParams
    }
    direction:=FecV2C2S
    if authenticated.ServerSide(){direction=FecV2S2C}
    cfg:=FecV2Config{
        Client:authenticated.Principal(),Direction:direction,
        Transport:FecV2Normal,Mode:mode,Profile:profile,
        AutoPolicy:FecV2Conservative,ConfigRevision:1,
    }
    state,ack,err:=bridge.stageOriginalFixedPending(
        cfg,FecV2State{},authenticated.Epoch(),
    )
    if err!=nil{return nil,err}
    if ack.Rejected||ack.Applied||ack.Revision!=1||!state.Initialized{
        return nil,ErrAdmissionUnsupported
    }
    return &v4ProductFecMonitor{
        epoch:authenticated.Epoch(),state:state,cfg:cfg,
        history:make([]v4AutoQualitySample,0,12),
        stopCh:make(chan struct{}),doneCh:make(chan struct{}),
    },nil
}
// Native facts are cumulative. Delaying the k histogram by 8s aligns it
// with M2's 8s-mature FIRST source window (source first-sent 8..16s ago).
// Unknown, ambiguous, missing hist or capacity censorship never become
// a manufactured zero-loss sample.
type v4AutoQualitySample struct {
    at time.Duration
    counters [30]uint64
}
func v4FecAutoDiff(a,b uint64)(uint64,bool){
    if b<a{return 0,false}
    return b-a,true
}
func v4FecAutoWindow(now,then [30]uint64,offset int)(FecV2Window,bool){
    var v [5]uint64
    for i:=range v {
        x,ok:=v4FecAutoDiff(then[offset+i],now[offset+i])
        if !ok{return FecV2Window{},false}
        v[i]=x
    }
    return FecV2Window{
        FirstSent:v[0],Observed:v[1]+v[2],Missing:v[2],
        Unknown:v[3]+v[4],
    },v[0]==v[1]+v[2]+v[3]+v[4]
}
func (m *v4ProductFecMonitor)autoObserve(bridge *v4EmbeddedNativeBridge,
    now time.Duration)(FecV2Snapshot,error){
    snap:=FecV2Snapshot{
        Client:m.cfg.Client,Direction:m.cfg.Direction,
        At:now,Validity:FecV2Unknown,
    }
    raw,err:=bridge.rustOwnerFec2MatureQuality()
    if err!=nil{return snap,err}
    m.history=append(m.history,v4AutoQualitySample{at:now,counters:raw})
    // Retain 20s plus one floor point, never an unbounded history table.
    for len(m.history)>12{m.history=m.history[1:]}
    find:=func(age time.Duration)([30]uint64,bool){
        for i:=len(m.history)-1;i>=0;i--{
            if m.history[i].at<=now-age {
                return m.history[i].counters,true
            }
        }
        return [30]uint64{},false
    }
    fast,haveFast:=find(2*time.Second)
    slow,haveSlow:=find(8*time.Second)
    histOld,haveHist:=find(16*time.Second)
    if !haveFast||!haveSlow||!haveHist{return snap,nil}
    var ok bool
    snap.Fast,ok=v4FecAutoWindow(raw,fast,0)
    if !ok{return snap,nil}
    snap.Slow,ok=v4FecAutoWindow(raw,slow,5)
    if !ok{return snap,nil}
    for k:=0;k<16;k++{
        n,valid:=v4FecAutoDiff(histOld[14+k],slow[14+k])
        if !valid{return snap,nil}
        snap.ActualK[k]=n
    }
    if raw[11]!=0 {
        snap.Validity=FecV2HostCapacity
        snap.HostDrops=raw[11]
        return snap,nil
    }
    reports,ok:=v4FecAutoDiff(slow[10],raw[10])
    if !ok||reports==0{return snap,nil}
    lag,ok:=v4FecAutoDiff(slow[12],raw[12])
    if !ok{return snap,nil}
    samples,ok:=v4FecAutoDiff(slow[13],raw[13])
    if !ok||samples==0{return snap,nil}
    // Authentic DATA positive confirmation age, not the OFF outer shadow's
    // synthetic 600ms value; includes feedback cadence, conservative RTT.
    mean:=lag/samples
    if mean>uint64((1<<63)-1){return snap,nil}
    snap.SRTT=time.Duration(mean)
    snap.Validity=FecV2Valid
    return snap,nil
}
func (m *v4ProductFecMonitor)tick(
    bridge *v4EmbeddedNativeBridge,now time.Duration,
){
    m.mu.Lock()
    defer m.mu.Unlock()
    if m.state.AppliedRevision!=m.state.RequestedRevision{
        // Native M4 definitely copied source+parity plus authenticated
        // reverse M2 are the ONLY authority to mark this revision applied.
        if v4PublicMatureFixedNative(bridge,m.epoch,m.state.RequestedRevision)!=nil {
            return
        }
        applied,_,err:=bridge.readbackOriginalFixedPending(m.state,m.epoch)
        if err!=nil{return}
        m.state=applied
        m.history=m.history[:0] // policy now has a new actual-k epoch
    }
    if m.cfg.Mode!=FecV2Auto||now-m.lastAutoAt<2*time.Second{return}
    m.lastAutoAt=now
    snap,err:=m.autoObserve(bridge,now)
    if err!=nil{return}
    if m.state.AppliedRevision!=m.state.RequestedRevision{return}
    next,intent,err:=FecV2Step(m.cfg,m.state,snap,now)
    if err!=nil{return}
    var kSources uint64
    for i,n:=range snap.ActualK{kSources+=uint64(i+1)*n}
    log.Printf("V4_PUBLIC_FEC2_AUTO_QUALITY direction=%s revision=%d profile=%d validity=%s reason=%q fast_first=%d fast_observed=%d fast_missing=%d fast_unknown=%d slow_first=%d slow_observed=%d slow_missing=%d slow_unknown=%d actual_k_sources=%d reverse_confirm_lag_us=%d target_profile=%d request=%t",
        m.cfg.Direction,m.state.RequestedRevision,m.state.Desired,
        intent.Validity,intent.Reason,snap.Fast.FirstSent,snap.Fast.Observed,
        snap.Fast.Missing,snap.Fast.Unknown,snap.Slow.FirstSent,
        snap.Slow.Observed,snap.Slow.Missing,snap.Slow.Unknown,
        kSources,snap.SRTT.Microseconds(),intent.Profile,intent.Send)
    if intent.Send{
        if err=bridge.stageOriginalAutoRevision(m.epoch,m.state,intent);err!=nil{
            // Native still owns the older profile until a real quiescent
            // cutover; no early Go requested/applied revision advancement.
            return
        }
        log.Printf("V4_PUBLIC_FEC2_AUTO_STAGE mode=auto direction=%s requested=%d profile=%d validity=%s reason=%s",
            m.cfg.Direction,intent.Revision,intent.Profile,intent.Validity,intent.Reason)
    }
    m.state=next
}
func (m *v4ProductFecMonitor)start(bridge *v4EmbeddedNativeBridge){
    if m==nil{return}
    m.started=true
    m.startedAt=time.Now()
    go func(){
        defer close(m.doneCh)
        ticker:=time.NewTicker(200*time.Millisecond)
        defer ticker.Stop()
        for{
            select{
            case <-m.stopCh:return
            case <-ticker.C:m.tick(bridge,time.Since(m.startedAt))
            }
        }
    }()
}
func (m *v4ProductFecMonitor)stop(){
    if m==nil{return}
    m.once.Do(func(){close(m.stopCh)})
    if m.started{<-m.doneCh}
}
func (m *v4ProductFecMonitor)readback(
    bridge *v4EmbeddedNativeBridge,
)(V4PublicFecReadback,error){
    var out V4PublicFecReadback
    if m==nil{return out,ErrAdmissionUnsupported}
    m.mu.Lock()
    defer m.mu.Unlock()
    next,_,err:=bridge.readbackOriginalFixedPending(m.state,m.epoch)
    if err!=nil{return out,err}
    m.state=next
    return V4PublicFecReadback{
        Mode:next.Mode,RequestedRevision:next.RequestedRevision,
        AppliedRevision:next.AppliedRevision,Profile:next.Desired,
        Pending:next.AppliedRevision!=next.RequestedRevision,
    },nil
}
