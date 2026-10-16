//go:build linux && cgo && wbd_v4_embedded_go

// Developer-opt-in non-_test package-private Go→Rust control adapter.
// Caller is only the credential-verified EstablishServerV4 ownerBridge path.
// NOT public cold248 install; do not ship feature-enabled C library yet.
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_prepare(const unsigned char *,size_t,
    const unsigned char *,size_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_stage(uint64_t,uint32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_commit(uint64_t,uint32_t,uint32_t,uint32_t);
extern int32_t wbd_m0_embedded_go_abort(uint64_t);
extern int32_t wbd_m0_embedded_go_stop(uint64_t);
extern int32_t wbd_m0_embedded_go_release(uint64_t);
extern int32_t wbd_m0_embedded_go_state(uint64_t,uint32_t *);
*/
import "C"
import (
    "errors"
    "fmt"
    "runtime"
    "unsafe"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
var errV4Embedded=errors.New("embedded V4 Rust control refused")
type v4EmbeddedNativeBridge struct {
    handle uint64
    committed bool
}
func (b *v4EmbeddedNativeBridge) prepare(
    s V4ColdSessionSnapshot,boundary uint32,peer v4PeerTransport,
)(v4PreparedOwner,error){
    if b.handle!=0{return nil,errV4Embedded}
    cold,err:=s.MarshalColdBundle()
    if err!=nil{return nil,err}
    cmd,err:=v4PrivateHandoffV1(boundary,peer)
    if err!=nil{return nil,err}
    var h C.uint64_t
    rc:=C.wbd_m0_embedded_go_prepare(
        (*C.uchar)(unsafe.Pointer(&cold[0])),C.size_t(len(cold)),
        (*C.uchar)(unsafe.Pointer(&cmd[0])),C.size_t(len(cmd)),&h)
    runtime.KeepAlive(cold);runtime.KeepAlive(cmd)
    if rc!=0||h==0{return nil,fmt.Errorf("%w: prepare=%d",errV4Embedded,int(rc))}
    b.handle=uint64(h)
    return &v4EmbeddedPending{b:b},nil
}
type v4EmbeddedPending struct{
    b *v4EmbeddedNativeBridge
    done bool
}
func (p *v4EmbeddedPending) commit(early []faketcp.TransitionPacket,tx uint32)error{
    if p.done||p.b.handle==0{return errV4Embedded}
    if len(early)>faketcp.MaxTransitionRecords{return errV4Embedded}
    total:=0
    for _,part:=range early{
        n:=len(part.Payload)
        if n==0||n>2048||total>int(^uint32(0))-n{return errV4Embedded}
        total+=n
        rc:=C.wbd_m0_embedded_go_stage(C.uint64_t(p.b.handle),C.uint32_t(part.Seq),
            (*C.uchar)(unsafe.Pointer(&part.Payload[0])),C.size_t(n))
        runtime.KeepAlive(part.Payload)
        if rc!=0{return fmt.Errorf("%w: stage=%d",errV4Embedded,int(rc))}
    }
    rc:=C.wbd_m0_embedded_go_commit(C.uint64_t(p.b.handle),
        C.uint32_t(len(early)),C.uint32_t(total),C.uint32_t(tx))
    if rc!=0{return fmt.Errorf("%w: commit=%d",errV4Embedded,int(rc))}
    p.done=true;p.b.committed=true
    return nil
}
func (p *v4EmbeddedPending) abort(){
    if p.done||p.b.handle==0{return}
    p.done=true
    _=C.wbd_m0_embedded_go_abort(C.uint64_t(p.b.handle))
    p.b.handle=0
}
func (b *v4EmbeddedNativeBridge) state()(uint32,error){
    if b.handle==0{return 0,errV4Embedded}
    var phase C.uint32_t
    rc:=C.wbd_m0_embedded_go_state(C.uint64_t(b.handle),&phase)
    if rc!=0{return 0,fmt.Errorf("%w: state=%d",errV4Embedded,int(rc))}
    return uint32(phase),nil
}
func (b *v4EmbeddedNativeBridge) stopRelease()error{
    if b.handle==0||!b.committed{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_stop(C.uint64_t(b.handle))
    if rc!=0{return fmt.Errorf("%w: STOP_INCOMPLETE_OR_FAILED=%d",errV4Embedded,int(rc))}
    rc=C.wbd_m0_embedded_go_release(C.uint64_t(b.handle))
    if rc!=0{return fmt.Errorf("%w: release=%d",errV4Embedded,int(rc))}
    b.handle=0;b.committed=false;return nil
}
