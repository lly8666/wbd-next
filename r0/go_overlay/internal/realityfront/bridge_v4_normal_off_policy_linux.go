//go:build linux && cgo && wbd_v4_embedded_go
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_normal_off_stage(uint64_t,const unsigned char *,size_t,uint64_t);
extern int32_t wbd_m0_embedded_go_normal_off_readback(uint64_t,const unsigned char *,size_t,uint64_t *);
*/
import "C"
import (
    "fmt"
    "runtime"
    "unsafe"
)
// Normal/off request remains PENDING until the SAME TLS-scoped Rust owner
// confirms its actual applied revision. This is neither a probe-only
// fabricated ACK nor authorization to enable fixed/auto FEC2.
func (b *v4EmbeddedNativeBridge) stageOriginalNormalOff(
    cfg FecV2Config,prev FecV2State,epoch [16]byte,
)(FecV2State,FecV2Ack,error){
    ack:=FecV2Ack{Client:cfg.Client,Direction:cfg.Direction,Revision:cfg.ConfigRevision}
    if b==nil||!b.committed||b.stopped||b.handle==0||
       epoch==[16]byte{}||epoch!=b.protectedEpoch||
       cfg.Client!=b.authenticatedPrincipal||cfg.Direction!=FecV2S2C||
       cfg.Transport!=FecV2Normal{return prev,ack,ErrFecV2Scope}
    if err:=cfg.validate();err!=nil{return prev,ack,err}
    if cfg.Mode!=FecV2Off{
        ack.Rejected=true
        return prev,ack,errFecV2Policy
    }
    if prev.Initialized && cfg.ConfigRevision<=prev.ConfigRevision {
        return prev,ack,ErrFecV2Revision
    }
    pending,intent,err:=FecV2Step(cfg,prev,FecV2Snapshot{},0)
    if err!=nil{return prev,ack,err}
    if !intent.Send||!pending.DesiredOff||intent.Profile!=FecV2Light||
       intent.Revision==0{return prev,ack,errFecV2Policy}
    rc:=C.wbd_m0_embedded_go_normal_off_stage(C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(len(epoch)),
        C.uint64_t(intent.Revision))
    runtime.KeepAlive(epoch)
    if rc!=0{return prev,ack,fmt.Errorf("%w: normal OFF native stage=%d",errV4Embedded,int(rc))}
    ack.Revision=intent.Revision
    return pending,ack,nil
}
func (b *v4EmbeddedNativeBridge) readbackOriginalNormalOff(
    requested FecV2State,epoch [16]byte,
)(FecV2State,FecV2Ack,error){
    ack:=FecV2Ack{Client:requested.Client,Direction:requested.Direction,
        Revision:requested.RequestedRevision,Profile:requested.Desired,Off:true}
    if b==nil||!b.committed||b.stopped||b.handle==0||
       epoch==[16]byte{}||epoch!=b.protectedEpoch||
       !requested.Initialized||requested.Client!=b.authenticatedPrincipal||
       requested.Direction!=FecV2S2C||requested.Mode!=FecV2Off{
        return requested,ack,ErrFecV2Scope
    }
    var actual C.uint64_t
    rc:=C.wbd_m0_embedded_go_normal_off_readback(C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(len(epoch)),&actual)
    runtime.KeepAlive(epoch)
    if rc!=0{return requested,ack,fmt.Errorf("%w: normal OFF native readback=%d",errV4Embedded,int(rc))}
    if uint64(actual)<requested.RequestedRevision{
        return requested,ack,nil // no native ACK yet, never invent applied
    }
    if uint64(actual)>requested.RequestedRevision{
        return requested,ack,ErrFecV2Revision
    }
    ack.Applied=true
    accepted,changed,err:=FecV2Apply(requested,ack)
    if err!=nil||!changed{return requested,ack,errFecV2Policy}
    return accepted,ack,nil
}
