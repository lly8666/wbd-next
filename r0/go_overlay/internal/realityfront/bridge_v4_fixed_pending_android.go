//go:build android && cgo && wbd_v4_embedded_go

// Original-Go protected Fixed/Auto Android bridge to real Rust M4.
// REQUESTED and PENDING are not APPLIED without same-revision source,
// repair and authentic mature PLAN027 Quality from the original M3.
package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_fixed_stage_pending(
    uint64_t,const unsigned char *,size_t,uint8_t,uint64_t);
extern int32_t wbd_m0_embedded_go_fixed_pending_readback(
    uint64_t,const unsigned char *,size_t,uint8_t *,uint64_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_fixed_m4_counters(
    uint64_t,uint64_t *,size_t);
*/
import "C"
import (
    "fmt"
    "runtime"
    "unsafe"
)

// One original verified Go TLS generation, never a peer-supplied readiness
// Boolean or public cold data: stage an operator Fixed policy; success is
// REQUESTED/PENDING only. The normal feature3 original client must reject.
func (b *v4EmbeddedNativeBridge) stageOriginalFixedPending(
    cfg FecV2Config, prev FecV2State, epoch [16]byte,
)(FecV2State,FecV2Ack,error){
    ack:=FecV2Ack{Client:cfg.Client,Direction:cfg.Direction,
        Revision:cfg.ConfigRevision}
    if b==nil||!b.committed||b.stopped||b.handle==0||
        epoch==[16]byte{}||epoch!=b.protectedEpoch||
        b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2)||
        cfg.Client!=b.authenticatedPrincipal||
        cfg.Direction!=func()FecV2Direction{
            if b.serverSide{return FecV2S2C}
            return FecV2C2S
        }()||cfg.Transport!=FecV2Normal{
        ack.Rejected=true
        return prev,ack,ErrFecV2Scope
    }
    if err:=cfg.validate();err!=nil{
        ack.Rejected=true;return prev,ack,err
    }
    // Auto's first selected, bounded profile uses this SAME original
    // authenticated native FixedStream owner. Future Auto changes still
    // require a separately accepted revision and real feedback; UNKNOWN
    // first-send coverage is never a zero-loss selection.
    if cfg.Mode!=FecV2Fixed&&cfg.Mode!=FecV2Auto{
        ack.Rejected=true;return prev,ack,errFecV2Policy
    }
    if prev.Initialized&&cfg.ConfigRevision<=prev.ConfigRevision{
        ack.Rejected=true;return prev,ack,ErrFecV2Revision
    }
    pending,intent,err:=FecV2Step(cfg,prev,FecV2Snapshot{},0)
    if err!=nil{
        ack.Rejected=true;return prev,ack,err
    }
    if !intent.Send||intent.Revision==0||intent.Profile!=cfg.Profile||
        pending.DesiredOff||pending.AppliedRevision>0{
        ack.Rejected=true;return prev,ack,errFecV2Policy
    }
    rc:=C.wbd_m0_embedded_go_fixed_stage_pending(C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(16),
        C.uint8_t(intent.Profile),C.uint64_t(intent.Revision))
    runtime.KeepAlive(epoch)
    if rc!=0{
        ack.Rejected=true
        return prev,ack,fmt.Errorf("%w: Fixed pending owner denied=%d",
            errV4Embedded,int(rc))
    }
    ack.Revision=intent.Revision
    return pending,ack,nil
}

// Cold Auto requires the original native feature7 Fixed/Auto PENDING.
func (b *v4EmbeddedNativeBridge) verifyOriginalAndroidAutoPending()error{
    if b==nil||!b.committed||b.stopped||b.handle==0||
        b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2)||
        b.protectedEpoch==[16]byte{}{return ErrAdmissionUnsupported}
    var profile C.uint8_t
    var revision C.uint64_t
    var applied C.uint32_t
    rc:=C.wbd_m0_embedded_go_fixed_pending_readback(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),C.size_t(16),
        &profile,&revision,&applied)
    runtime.KeepAlive(b)
    if rc!=0||uint64(revision)!=1||uint8(profile)>6||applied!=0{
        return fmt.Errorf("%w: Android original Auto pending not ready=%d",
            errV4Embedded,int(rc))
    }
    return nil
}

// Auto profile is a newer policy on the original authenticated TLS owner,
// not a second FEC sender. A pending old revision is never coalesced by Go.
// Rust keeps old source+parity immutable until M1 quiescent cutover, and
// requires new kernel source+parity plus true M2 before applied readback.
func (b *v4EmbeddedNativeBridge) stageOriginalAutoRevision(
    epoch [16]byte,prev FecV2State,intent FecV2Intent,
)error{
    if b==nil||!b.committed||b.stopped||b.handle==0||
        epoch==[16]byte{}||epoch!=b.protectedEpoch||
        b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2)||
        !prev.Initialized||prev.Mode!=FecV2Auto||
        prev.Client!=b.authenticatedPrincipal||
        prev.Direction!=func()FecV2Direction{
            if b.serverSide{return FecV2S2C}
            return FecV2C2S
        }()||prev.AppliedRevision!=prev.RequestedRevision||
        !intent.Send||intent.Mode!=FecV2Auto||
        intent.Client!=prev.Client||intent.Direction!=prev.Direction||
        intent.Revision<=prev.RequestedRevision||!intent.Profile.Valid(){
        return ErrFecV2Scope
    }
    rc:=C.wbd_m0_embedded_go_fixed_stage_pending(C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(16),
        C.uint8_t(intent.Profile),C.uint64_t(intent.Revision))
    runtime.KeepAlive(epoch)
    if rc!=0{return fmt.Errorf("%w: native Auto revision pending denied=%d",
        errV4Embedded,int(rc))}
    return nil
}

// Reads the SAME generation/epoch owner, which intentionally returns
// applied=0 until real native parity send/repair-to-app is demonstrated.
// Do not map this pending receipt to FecV2Apply or product enabled.
func (b *v4EmbeddedNativeBridge) readbackOriginalFixedPending(
    pending FecV2State,epoch [16]byte,
)(FecV2State,FecV2Ack,error){
    ack:=FecV2Ack{Client:pending.Client,Direction:pending.Direction,
        Revision:pending.RequestedRevision,Profile:pending.Desired}
    if b==nil||!b.committed||b.stopped||b.handle==0||
        epoch==[16]byte{}||epoch!=b.protectedEpoch||
        !pending.Initialized||pending.Client!=b.authenticatedPrincipal||
        b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2)||
        pending.Direction!=func()FecV2Direction{
            if b.serverSide{return FecV2S2C}
            return FecV2C2S
        }()||
        (pending.Mode!=FecV2Fixed&&pending.Mode!=FecV2Auto){
        return pending,ack,ErrFecV2Scope
    }
    var profile C.uint8_t
    var revision C.uint64_t
    var applied C.uint32_t
    rc:=C.wbd_m0_embedded_go_fixed_pending_readback(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&epoch[0])),
        C.size_t(16),&profile,&revision,&applied)
    runtime.KeepAlive(epoch)
    if rc!=0{return pending,ack,fmt.Errorf("%w: native Fixed pending readback=%d",
        errV4Embedded,int(rc))}
    if uint8(profile)!=uint8(pending.Desired)||
        uint64(revision)!=pending.RequestedRevision||uint32(applied)>1{
        return pending,ack,errFecV2Policy
    }
    if applied==0{return pending,ack,nil}
    // Only a successful ORIGINAL native kernel source+repair transition
    // can return applied=1, in an explicitly opt-in FEC sender. The default
    // engine has no such path; Go never promotes accepted intent by itself.
    ack.Applied=true
    actual,changed,err:=FecV2Apply(pending,ack)
    if err!=nil||!changed{return pending,ack,errFecV2Policy}
    return actual,ack,nil
}

// B13: read-only exact original M4 + PLAN027 mature quality evidence.
// 0..6 are B12d real send/receive/auth counters, 7 is a locally
// history-matched 3s-mature source Quality report, 8 is native APPLIED
// after real same-revision source+parity and matching positive report.
func (b *v4EmbeddedNativeBridge) originalAndroidFixedM4Counters()([9]uint64,error){
    var result [9]uint64
    if b==nil||!b.committed||b.stopped||b.handle==0||
       b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2){
        return result,errV4Embedded
    }
    var counters [9]C.uint64_t
    rc:=C.wbd_m0_embedded_go_fixed_m4_counters(
        C.uint64_t(b.handle),&counters[0],C.size_t(len(counters)))
    if rc!=0{
        return result,fmt.Errorf("%w: original Android Fixed M4 copy counters=%d",
            errV4Embedded,int(rc))
    }
    for i:=range result{result[i]=uint64(counters[i])}
    return result,nil
}
