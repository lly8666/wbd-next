//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe

package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_bind_fec2_probe_after_verified_tls(
    uint64_t,const unsigned char *,size_t,uint16_t,uint8_t,uint64_t);
extern int32_t wbd_m0_embedded_go_fec2_probe_scope_status(
    uint64_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_fec2_probe_applied_policy(
    uint64_t,uint8_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_stage_policy(
    uint64_t,const unsigned char *,size_t,uint8_t,uint64_t);
extern int32_t wbd_m0_embedded_go_fec2_probe_verified_peer_counts(
    uint64_t,const unsigned char *,size_t,uint64_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_mature_firstsend(
    uint64_t,const unsigned char *,size_t,uint64_t,uint64_t *,uint64_t *,uint8_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_real_raw_tx(
    uint64_t,uint32_t,uint64_t *,uint64_t *,
    uint32_t *,uint32_t *,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_live_peer_consume(
    uint64_t,const unsigned char *,size_t,uint32_t *,uint64_t *,
    uint8_t *,uint32_t *,unsigned char *,size_t,size_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_actual_peer_consume(
    uint64_t,const unsigned char *,size_t,unsigned char *,size_t,
    uint64_t *,uint8_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_actual_m2_rx_feedback(
    uint64_t,uint64_t,uint8_t,uint32_t *,uint64_t *,uint64_t *,uint8_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_reverse_raw_receipt(
    uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_sender_shadow_status(
    uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_real_frozen_repair(
    uint64_t,uint64_t *,uint32_t *,uint32_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_real_frozen_prefix_two(
    uint64_t,uint64_t *,uint32_t *,uint32_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_real_kernel_multimsg_two(
    uint64_t,uint64_t *,uint32_t *,uint32_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_process_quota_snapshot(
    uint64_t,uint32_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_process_quota_hold(
    uint64_t,uint64_t);
*/
import "C"
import (
    "fmt"
    "runtime"
    "time"
    "unsafe"
)

// Only this EXTRA opt-in test build may call this private owner binding
// after EstablishServerV4 has checked actual TLS credentials and Detach.
// The default remains Strong/revision1 in opt-in tests. A protected Go
// policy intent can replace these exact values before TLS prepare; the
// downstream original Rust owner proves what was actually applied. No
// product GUI/CLI auto ticker or production feature flag is enabled.
func v4Fec2ProbeAfterProtectedCommit(b *v4EmbeddedNativeBridge) error {
    if b.protectedFeatures==v4RequiredFeatures {
        return nil
    }
    if b.protectedFeatures!=v4RequiredFeatures|v4FeatureFEC2 ||
        b.protectedEpoch==[16]byte{} || b.handle==0 {
        return errV4Embedded
    }
    profile,revision:=uint8(5),uint64(1)
    if b.fec2ProbePolicySet{
        profile,revision=b.fec2ProbeProfile,b.fec2ProbeRevision
    }
    rc:=C.wbd_m0_embedded_go_bind_fec2_probe_after_verified_tls(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),
        C.size_t(16),C.uint16_t(b.protectedFeatures),
        C.uint8_t(profile),C.uint64_t(revision))
    runtime.KeepAlive(b.protectedEpoch)
    if rc!=0{return fmt.Errorf("%w: private FEC2 owner grant %d",errV4Embedded,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) fec2ProbeScope(epoch [16]byte) bool {
    if b.handle==0{return false}
    rc:=C.wbd_m0_embedded_go_fec2_probe_scope_status(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(16))
    runtime.KeepAlive(epoch)
    return rc==0
}

// Explicit EXTRA-test-only bound Go TLS owner M4 raw kernel FEC2 send.
// Not the real automatic M1 scheduler or RX repair, never a product API.
func (b *v4EmbeddedNativeBridge) fec2ProbeKernelRawTx(
    ifindex uint32,
)([2]uint64,[2]uint32,[2]uint32,error){
    var pn [2]uint64
    var seq [2]uint32
    var length [2]uint32
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return pn,seq,length,errV4Embedded
    }
    rc:=C.wbd_m0_embedded_go_fec2_probe_real_raw_tx(
        C.uint64_t(b.handle),C.uint32_t(ifindex),
        (*C.uint64_t)(unsafe.Pointer(&pn[0])),
        (*C.uint64_t)(unsafe.Pointer(&pn[1])),
        (*C.uint32_t)(unsafe.Pointer(&seq[0])),
        (*C.uint32_t)(unsafe.Pointer(&seq[1])),
        (*C.uint32_t)(unsafe.Pointer(&length[0])),
        (*C.uint32_t)(unsafe.Pointer(&length[1])))
    if rc!=0 {return pn,seq,length,fmt.Errorf("%w: native M4 FEC2 raw probe %d",errV4Embedded,int(rc))}
    return pn,seq,length,nil
}

// Validated independent original Rust client receive-side AEAD/PN bitmap,
// using the immutable ORIGINAL Go TLS S2C direction keys. It is accessible
// only with the private feature+epoch bound sender owner still ACTIVE.
// Developer-only actual M4 packet -> independent original Go TLS key
// receive. Same Rust FEC2LiveRx code, not a product client or synthetic ACK.
func (b *v4EmbeddedNativeBridge) fec2ProbeLivePeerConsume(
    ciphertext []byte,
)(block uint64,index uint8,recovered bool,frame []byte,err error){
    if b==nil||!b.committed||b.stopped||b.handle==0||
        len(ciphertext)<31||len(ciphertext)>2048{
        err=errV4Embedded;return
    }
    output:=make([]byte,2048)
    var n C.uint32_t
    var id C.uint64_t
    var idx C.uint8_t
    var recover C.uint32_t
    var used C.size_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_live_peer_consume(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&ciphertext[0])),
        C.size_t(len(ciphertext)),&n,&id,&idx,&recover,
        (*C.uchar)(unsafe.Pointer(&output[0])),C.size_t(len(output)),&used)
    runtime.KeepAlive(ciphertext)
    if rc!=0||n>1||int(used)>len(output) {
        err=fmt.Errorf("%w: live independent peer=%d",errV4Embedded,int(rc));return
    }
    if n==0{return 0,0,false,nil,nil}
    return uint64(id),uint8(idx),recover!=0,output[:int(used)],nil
}
func (b *v4EmbeddedNativeBridge) fec2ProbeActualPeerConsume(
    cipherRecord []byte,
)(uint64,uint8,[]byte,error){
    if b.handle==0 || !b.committed || b.protectedFeatures!=7 ||
        len(cipherRecord)==0 {return 0,0,nil,errV4Embedded}
    decoded:=make([]byte,2048)
    var pn C.uint64_t
    var kind C.uint8_t
    var actual C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_actual_peer_consume(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&cipherRecord[0])),C.size_t(len(cipherRecord)),
        (*C.uchar)(unsafe.Pointer(&decoded[0])),C.size_t(len(decoded)),
        &pn,&kind,&actual)
    runtime.KeepAlive(cipherRecord)
    if rc!=0||int(actual)>len(decoded){
        return 0,0,nil,fmt.Errorf("%w: independent authenticated FEC2 peer %d",
            errV4Embedded,int(rc))
    }
    return uint64(pn),uint8(kind),decoded[:int(actual)],nil
}

// Actual M2 RX feedback draft only, NOT a cryptographically opened reverse
// receipt or a real on-wire send. Sent outcome is one of NotSent, Accepted,
// Uncertain, bound to the very same authenticated session/owner.
func (b *v4EmbeddedNativeBridge) fec2ProbeActualM2RxFeedback(
    nowNS uint64, outcome uint8,
)(uint32,uint64,uint64,uint8,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,0,errV4Embedded
    }
    var seq C.uint32_t
    var max,base C.uint64_t
    var bits C.uint8_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_actual_m2_rx_feedback(
        C.uint64_t(b.handle),C.uint64_t(nowNS),C.uint8_t(outcome),
        &seq,&max,&base,&bits)
    if rc!=0{return 0,0,0,0,
        fmt.Errorf("%w: authenticated M2 RX draft rc=%d",errV4Embedded,int(rc))}
    return uint32(seq),uint64(max),uint64(base),uint8(bits),nil
}

// Private Linux FEC2 probe only: ORIGINAL raw C2S M4 capture -> original
// scoped Rust M3 reverse AEAD/unique PN -> M2 authenticated typed receipt.
// Driver copy alone never releases the original frozen owner shadow.
func (b *v4EmbeddedNativeBridge) fec2ProbeReverseRawReceipt()(uint32,uint32,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7 {
        return 0,0,errV4Embedded
    }
    var released,remaining C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_reverse_raw_receipt(
        C.uint64_t(b.handle),&released,&remaining)
    if rc!=0{return 0,0,fmt.Errorf("%w: reverse raw authenticated receipt rc=%d",
        errV4Embedded,int(rc))}
    return uint32(released),uint32(remaining),nil
}
func (b *v4EmbeddedNativeBridge) fec2ProbeShadowOutstanding()(uint32,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,errV4Embedded
    }
    var outstanding C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_sender_shadow_status(
        C.uint64_t(b.handle),&outstanding)
    if rc!=0{return 0,fmt.Errorf("%w: frozen shadow status rc=%d",
        errV4Embedded,int(rc))}
    return uint32(outstanding),nil
}

 
// M0 opt-in only. Original M2 scoped PTO reserve + process grant -> SAME
// original M1 frozen ciphertext through ORIGINAL M4 raw send_one; the
// returned PN and seq are not allocated here and cannot be resealed by Go.
func (b *v4EmbeddedNativeBridge) fec2ProbeRealFrozenRepair()(
    uint64,uint32,uint32,uint64,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,0,errV4Embedded
    }
    var pn,charged C.uint64_t
    var seq,wire C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_real_frozen_repair(
        C.uint64_t(b.handle),&pn,&seq,&wire,&charged)
    if rc!=0{
        return 0,0,0,0,fmt.Errorf("%w: scoped same frozen repair rc=%d",
            errV4Embedded,int(rc))
    }
    return uint64(pn),uint32(seq),uint32(wire),uint64(charged),nil
}

// Test-only real protected TLS owner process-shared M2 admission.
// Does not prove real kernel send prefix or concurrent production deployment.
func (b *v4EmbeddedNativeBridge) fec2ProbeProcessQuotaSnapshot()(
    uint32,uint64,uint64,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,errV4Embedded
    }
    var count C.uint32_t
    var held,cap C.uint64_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_process_quota_snapshot(
        C.uint64_t(b.handle),&count,&held,&cap)
    if rc!=0{return 0,0,0,fmt.Errorf("%w: process quota snapshot rc=%d",
        errV4Embedded,int(rc))}
    return uint32(count),uint64(held),uint64(cap),nil
}
func (b *v4EmbeddedNativeBridge) fec2ProbeProcessQuotaHold(bytes uint64) error{
    if b.handle==0||!b.committed||b.protectedFeatures!=7 {
        return errV4Embedded
    }
    rc:=C.wbd_m0_embedded_go_fec2_probe_process_quota_hold(
        C.uint64_t(b.handle),C.uint64_t(bytes))
    if rc!=0{return fmt.Errorf("%w: process quota claim rc=%d",errV4Embedded,int(rc))}
    return nil
}

// Test-only 2-slot M2 typed settlement with original M4 kernel copy for
// slot0, positive never-syscalled slot1. This is NOT a native sendmmsg
// uncertain completion classifier and never promotes product FEC2.
func (b *v4EmbeddedNativeBridge) fec2ProbeRealFrozenPrefixTwo()(
    uint64,uint32,uint32,uint64,uint64,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,0,0,errV4Embedded
    }
    var pn,accepted,notAttempted C.uint64_t
    var seq,wire C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_real_frozen_prefix_two(
        C.uint64_t(b.handle),&pn,&seq,&wire,&accepted,&notAttempted)
    if rc!=0{return 0,0,0,0,0,fmt.Errorf("%w: original mixed frozen prefix rc=%d",
        errV4Embedded,int(rc))}
    return uint64(pn),uint32(seq),uint32(wire),
        uint64(accepted),uint64(notAttempted),nil
}

// Actual original M4 ONE Linux sendmmsg syscall with two original M1
// FrozenRecord immutable buffers and one original M2 global scoped broker.
// Test-only, not peer ACK or production interface.
func (b *v4EmbeddedNativeBridge) fec2ProbeRealKernelMultimsgTwo()(
    uint64,uint32,uint32,uint64,uint64,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,0,0,errV4Embedded
    }
    var pn,charged,secondOuter C.uint64_t
    var seq,wire C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_real_kernel_multimsg_two(
        C.uint64_t(b.handle),&pn,&seq,&wire,&charged,&secondOuter)
    if rc!=0{return 0,0,0,0,0,fmt.Errorf("%w: original native 2-slot M4 sendmmsg rc=%d",
        errV4Embedded,int(rc))}
    return uint64(pn),uint32(seq),uint32(wire),
        uint64(charged),uint64(secondOuter),nil
}

// Bind a real ORIGINAL Go FecV2Step decision to the future authenticated
// owner; NO Rust access before credential-checked TLS and Detach.
func (b *v4EmbeddedNativeBridge) fec2ProbeChoosePolicy(
    c FecV2Config,
)(FecV2State,error){
    var zero FecV2State
    if b.handle!=0||b.committed||b.fec2ProbePolicySet ||
        c.Client!="protected-owner"||c.Direction!=FecV2S2C ||
        c.Transport!=FecV2Normal ||c.Mode==FecV2Off {
        return zero,errV4Embedded
    }
    state,intent,err:=FecV2Step(c,zero,FecV2Snapshot{},time.Second)
    if err!=nil{return zero,err}
    if !intent.Send||intent.Revision==0||!intent.Profile.Valid()||
        state.DesiredOff||intent.Profile!=state.Desired||
        intent.Revision!=state.RequestedRevision{
        return zero,errV4Embedded
    }
    b.fec2ProbeProfile=uint8(intent.Profile)
    b.fec2ProbeRevision=intent.Revision
    b.fec2ProbePolicySet=true
    return state,nil
}
// Original Rust readback is the only valid applied-ack provenance; Go's
// FecV2Apply independently validates intended client/direction/revision.
func (b *v4EmbeddedNativeBridge) fec2ProbeAppliedPolicy(
    state FecV2State,
)(FecV2State,error){
    if !b.committed||b.stopped||b.handle==0||!b.fec2ProbePolicySet||
       state.Client!="protected-owner"||state.Direction!=FecV2S2C ||
       !b.fec2ProbeScope(b.protectedEpoch){
        return state,errV4Embedded
    }
    var profile C.uint8_t
    var revision C.uint64_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_applied_policy(
        C.uint64_t(b.handle),&profile,&revision)
    if rc!=0{return state,fmt.Errorf("%w: Rust applied policy rc=%d",
        errV4Embedded,int(rc))}
    if uint8(profile)!=uint8(state.Desired)||
       uint64(revision)!=state.RequestedRevision {
        return state,errV4Embedded
    }
    applied,ok,err:=FecV2Apply(state,FecV2Ack{
        Client:state.Client,Direction:state.Direction,
        Revision:uint64(revision),Profile:FecV2Profile(profile),
        Applied:true,
    })
    if err!=nil||!ok{return state,errV4Embedded}
    b.fec2ProbeProfile=uint8(profile)
    b.fec2ProbeRevision=uint64(revision)
    return applied,nil
}

// Actual authenticated Go AUTO quality tick -> original Rust pending
// revision. No client-supplied FEC2 hot config, bypass of TLS or product
// timer. Applied readback remains old until original M1 starts the next
// block and original M4 kernel positively copies its source and repair.
func (b *v4EmbeddedNativeBridge) fec2ProbeStageAutoTick(
    cfg FecV2Config,state FecV2State,snapshot FecV2Snapshot,now time.Duration,
)(FecV2State,FecV2Intent,error){
    var invalid FecV2Intent
    if !b.committed||b.stopped||b.handle==0||!b.fec2ProbePolicySet||
        !b.fec2ProbeScope(b.protectedEpoch)||
        cfg.Client!="protected-owner"||cfg.Direction!=FecV2S2C||
        cfg.Transport!=FecV2Normal||cfg.Mode!=FecV2Auto {
        return state,invalid,errV4Embedded
    }
    next,intent,e:=FecV2Step(cfg,state,snapshot,now)
    if e!=nil||!intent.Send{return next,intent,e}
    if !intent.Profile.Valid()||intent.Revision<=state.RequestedRevision{
        return state,intent,errV4Embedded
    }
    rc:=C.wbd_m0_embedded_go_fec2_probe_stage_policy(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),
        C.size_t(16),C.uint8_t(intent.Profile),C.uint64_t(intent.Revision))
    runtime.KeepAlive(b.protectedEpoch)
    if rc!=0{return state,intent,fmt.Errorf("%w: authenticated Go auto stage rc=%d",
        errV4Embedded,int(rc))}
    return next,intent,nil
}

// M0 test-only source of original M3 AEAD-first RX observability.
// Only authenticated first DATA/repair/recovered counts exist here: no
// defensible mature loss denominator, host drop or one-way RTT. Consequently
// feed the ORIGINAL Go FecV2Step as UNKNOWN and never convert silence into
// zero packet loss or an auto down/up decision.
func (b *v4EmbeddedNativeBridge) fec2ProbeObservedQuality(
    exactEpoch [16]byte,at time.Duration,
)(FecV2Snapshot,uint64,uint64,uint64,error){
    var empty FecV2Snapshot
    if !b.committed||b.stopped||b.handle==0||at<0{
        return empty,0,0,0,errV4Embedded
    }
    var source,repair,recovered C.uint64_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_verified_peer_counts(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&exactEpoch[0])),C.size_t(16),
        &source,&repair,&recovered)
    runtime.KeepAlive(exactEpoch)
    if rc!=0{
        return empty,0,0,0,fmt.Errorf("%w: verified first-RX scope rc=%d",
            errV4Embedded,int(rc))
    }
    snapshot:=FecV2Snapshot{
        Client:"protected-owner",Direction:FecV2S2C,
        At:at,Validity:FecV2Unknown,
    }
    // Receiver alone cannot attest the sender's FirstSent denominator.
    // No Fast/Slow FirstSent/Observed samples are invented even if source
    // AEAD succeeds; deliver those three separate identity-scoped counters
    // to diagnostics, NEVER to the sender-loss estimator.
    return snapshot,uint64(source),uint64(repair),uint64(recovered),nil
}

// Mature 2s/8s readback from the original Rust sender's FINAL kernel
// copied-firstsend plus AEAD/replay verified C2S receipts. An ambiguous
// repair is CENSORED, uncovered UNKNOWN; no RX-only fake denominator.
func (b *v4EmbeddedNativeBridge) fec2ProbeMatureQuality(
    exactEpoch [16]byte,at time.Duration,
)(FecV2Snapshot,error){
    snap:=FecV2Snapshot{Client:"protected-owner",Direction:FecV2S2C,
        At:at,Validity:FecV2Unknown}
    if !b.committed||b.stopped||b.handle==0||at<0||
        !b.fec2ProbeScope(exactEpoch){return snap,ErrFecV2Scope}
    var fast,slow [5]C.uint64_t
    var status C.uint8_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_mature_firstsend(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&exactEpoch[0])),C.size_t(16),
        C.uint64_t(uint64(at)),&fast[0],&slow[0],&status)
    runtime.KeepAlive(exactEpoch)
    if rc!=0{return snap,fmt.Errorf("%w: M2 genuine maturity rc=%d",
        errV4Embedded,int(rc))}
    converted:=func(values [5]C.uint64_t)FecV2Window{
        return FecV2Window{FirstSent:uint64(values[0]),
            Observed:uint64(values[1]),Missing:uint64(values[2]),
            Unknown:uint64(values[3]),Censored:uint64(values[4])}
    }
    snap.Fast=converted(fast)
    snap.Slow=converted(slow)
    switch status {
    case 0:snap.Validity=FecV2Valid
    case 1:snap.Validity=FecV2Unknown
    case 2:snap.Validity=FecV2Censored
    case 3:snap.Validity=FecV2HostCapacity
    default:return FecV2Snapshot{},ErrFecV2Scope
    }
    return snap,nil
}

// Live original Go 2s scheduler backend: ONLY the credential-verified
// test-owner may stage/read back its native Rust applied revision.
type fecV2OriginalRustBackend struct{ b *v4EmbeddedNativeBridge }
func (p fecV2OriginalRustBackend) valid(epoch [16]byte,client string,d FecV2Direction)bool{
    b:=p.b
    return b!=nil&&b.committed&&!b.stopped&&b.handle!=0&&
        b.protectedFeatures==7&&epoch==b.protectedEpoch&&
        client=="protected-owner"&&d==FecV2S2C&&b.fec2ProbeScope(epoch)
}
func (p fecV2OriginalRustBackend) Observe(
    epoch [16]byte,client string,d FecV2Direction,now time.Duration,
)(FecV2Snapshot,error){
    if !p.valid(epoch,client,d){return FecV2Snapshot{},ErrFecV2Scope}
    // Genuine 2s/8s M2 sender window, never the peer-side RX counters.
    return p.b.fec2ProbeMatureQuality(epoch,now)
}
func (p fecV2OriginalRustBackend) Readback(
    epoch [16]byte,client string,d FecV2Direction,
)(FecV2Ack,error){
    if !p.valid(epoch,client,d){return FecV2Ack{},ErrFecV2Scope}
    var profile C.uint8_t
    var revision C.uint64_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_applied_policy(
        C.uint64_t(p.b.handle),&profile,&revision)
    if rc!=0{return FecV2Ack{},fmt.Errorf("%w: Rust applied rc=%d",errV4Embedded,int(rc))}
    // Rust profile 7 is a private "quiescent OFF" flag, not a grade.
    // Keep the existing Go FecV2Ack.Off and its exact revision guard.
    off:=profile==7
    if profile>7{return FecV2Ack{},ErrFecV2Scope}
    grade:=FecV2Profile(profile)
    if off{grade=FecV2Light}
    return FecV2Ack{Client:client,Direction:d,Revision:uint64(revision),
        Profile:grade,Off:off,Applied:true},nil
}
func (p fecV2OriginalRustBackend) Stage(epoch [16]byte,v FecV2Intent)error{
    if !p.valid(epoch,v.Client,v.Direction)||
        (v.Mode!=FecV2Auto && v.Mode!=FecV2Fixed && v.Mode!=FecV2Off)||
        v.Revision==0||!v.Profile.Valid(){return ErrFecV2Scope}
    ack,err:=p.Readback(epoch,v.Client,v.Direction)
    if err!=nil{return err}
    off:=v.Mode==FecV2Off
    if ack.Revision==v.Revision && ack.Profile==v.Profile && ack.Off==off{return nil}
    if ack.Revision>=v.Revision{return ErrFecV2Revision}
    if off{
        // Only the Rust owner may assert a quiescent OFF and return ACK.
        // A rejected unsettled shadow leaves the old Go config unchanged.
        return p.b.fec2ProbeTryStageExact(epoch,7,v.Revision)
    }
    return p.b.fec2ProbeTryStageExact(epoch,uint8(v.Profile),v.Revision)
}
// Feature-opt-in only; product FEC2 remains OFF. The goroutine runs only
// after real Go TLS credential verification. Original Stop joins it before
// destroying the Rust owner, so no late SetTxFec can race generation reuse.
func (b *v4EmbeddedNativeBridge) fec2ProbeStartAutoRuntime(
    cfg FecV2Config,
)(*fecV2ControlRuntime,error){
    if !b.committed||b.stopped||b.handle==0||b.fec2AutoStop!=nil||
        b.protectedFeatures!=7||cfg.Client!="protected-owner"||
        cfg.Direction!=FecV2S2C||!b.fec2ProbeScope(b.protectedEpoch){
        return nil,ErrFecV2Scope
    }
    r,err:=newFecV2ControlRuntime(
        cfg,b.protectedEpoch,fecV2OriginalRustBackend{b:b})
    if err!=nil{return nil,err}
    if err:=r.Start();err!=nil{return nil,err}
    b.fec2AutoStop=r.Stop
    return r,nil
}

// M0-only fault-injection entry for exact epoch/revision lifecycle checks.
// No public Go or product API; wrong epochs must be rejected by ORIGINAL
// protected Rust owner even when a different Go session has a valid token.
func (b *v4EmbeddedNativeBridge) fec2ProbeTryStageExact(
    epoch [16]byte,profile uint8,revision uint64,
)error{
    if !b.committed||b.stopped||b.handle==0{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_fec2_probe_stage_policy(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(16),
        C.uint8_t(profile),C.uint64_t(revision))
    runtime.KeepAlive(epoch)
    if rc!=0{return fmt.Errorf("%w: scoped stage rejected rc=%d",errV4Embedded,int(rc))}
    return nil
}
