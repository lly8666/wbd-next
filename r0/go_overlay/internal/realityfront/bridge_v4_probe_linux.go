//go:build linux && cgo && wbd_v4_native_probe

// TEST-ONLY Linux in-process Go→Rust bridge. Never built for production.
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_test_probe_prepare(const unsigned char *, size_t, uint32_t, uint64_t *);
extern int32_t wbd_m0_test_probe_commit(uint64_t, uint32_t, uint32_t);
extern int32_t wbd_m0_test_probe_abort(uint64_t);
extern int32_t wbd_m0_test_probe_stop(uint64_t);
extern int32_t wbd_m0_test_probe_release(uint64_t);
extern int32_t wbd_m0_test_probe_state(uint64_t, uint32_t *);
*/
import "C"
import (
    "errors"
    "fmt"
    "runtime"
    "unsafe"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
var errV4NativeProbe=errors.New("V4 test-only native probe refused")
type v4NativeRustProbe struct {handle uint64; prepared,committed bool}
func (b *v4NativeRustProbe) prepare(s V4ColdSessionSnapshot,boundary uint32)(v4PreparedOwner,error){
    // Only genuine credential-verified EstablishServerV4 can invoke this
    // private backend slot. This FFI alone NEVER authenticates raw C bytes.
    raw,err:=s.MarshalColdBundle()
    if err!=nil{return nil,err}
    var handle C.uint64_t
    code:=C.wbd_m0_test_probe_prepare((*C.uchar)(unsafe.Pointer(&raw[0])),
        C.size_t(len(raw)),C.uint32_t(boundary),&handle)
    runtime.KeepAlive(raw)
    if code!=0||handle==0{return nil,fmt.Errorf("%w: prepare=%d",errV4NativeProbe,int(code))}
    b.handle=uint64(handle);b.prepared=true
    return &v4NativeRustPending{handle:b.handle,owner:b},nil
}
type v4NativeRustPending struct {
    handle uint64
    owner *v4NativeRustProbe
    committed,aborted bool
}
func (p *v4NativeRustPending) commit(early []faketcp.TransitionPacket)error{
    if p.committed||p.aborted{return errV4NativeProbe}
    if len(early)>faketcp.MaxTransitionRecords{return errV4NativeProbe}
    total:=0
    for _,packet:=range early{total+=len(packet.Payload)}
    if total>int(^uint32(0)){return errV4NativeProbe}
    code:=C.wbd_m0_test_probe_commit(C.uint64_t(p.handle),
        C.uint32_t(len(early)),C.uint32_t(total))
    if code!=0{return fmt.Errorf("%w: commit=%d",errV4NativeProbe,int(code))}
    p.committed=true;p.owner.committed=true;return nil
}
func (p *v4NativeRustPending) abort(){
    if p.committed||p.aborted{return}
    p.aborted=true;_=C.wbd_m0_test_probe_abort(C.uint64_t(p.handle))
}
func (b *v4NativeRustProbe) state()(uint32,error){
    if b.handle==0{return 0,errV4NativeProbe}
    var phase C.uint32_t
    code:=C.wbd_m0_test_probe_state(C.uint64_t(b.handle),&phase)
    if code!=0{return 0,fmt.Errorf("%w: state=%d",errV4NativeProbe,int(code))}
    return uint32(phase),nil
}
func (b *v4NativeRustProbe) stopAndRelease()error{
    if !b.committed||b.handle==0{return errV4NativeProbe}
    if c:=C.wbd_m0_test_probe_stop(C.uint64_t(b.handle));c!=0{
        return fmt.Errorf("%w: stop=%d",errV4NativeProbe,int(c))
    }
    if c:=C.wbd_m0_test_probe_release(C.uint64_t(b.handle));c!=0{
        return fmt.Errorf("%w: release=%d",errV4NativeProbe,int(c))
    }
    return nil
}
