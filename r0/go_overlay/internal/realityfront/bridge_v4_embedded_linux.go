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
extern int32_t wbd_m0_embedded_go_attach_raw_rx(uint64_t,uint32_t);
extern int32_t wbd_m0_embedded_go_attach_tun(uint64_t,int32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_raw_to_tun(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_tun_to_raw(uint64_t,uint32_t,
    uint64_t *,uint32_t *,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_start(uint64_t,uint32_t);
extern int32_t wbd_m0_embedded_go_loop_stats(uint64_t,uint64_t *,uint64_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_loop_firstsend_m2(uint64_t,uint64_t *,uint64_t *,uint64_t *,uint64_t *,uint64_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_debug_pause_jumbo(uint64_t,uint32_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_thread_cpu(uint64_t,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_loop_route_refresh(uint64_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_loop_route_events(uint64_t,uint64_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_observed_tx_ipv4_mtu(uint64_t,uint32_t,uint32_t *);
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
    stopped bool // terminal release receipt; not a Rust owner token
    originalFlow faketcp.ServerFlow
    rxBoundary uint32
    txBoundary uint32
    protectedEpoch [16]byte
    protectedFeatures uint16
    // M0-only opt-in settings. Actual production config/state still lives
    // in the Go parameter owner and remains FEC2-OFF until product wiring.
    fec2ProbePolicySet bool
    fec2ProbeProfile uint8
    fec2ProbeRevision uint64
    // Optional authenticated control-loop shutdown. Ordinary FEC2-OFF
    // sessions keep nil; Stop always joins the loop before Rust release.
    fec2AutoStop func()
}
func (b *v4EmbeddedNativeBridge) prepare(
    s V4ColdSessionSnapshot,boundary uint32,peer v4PeerTransport,
)(v4PreparedOwner,error){
    if b.handle!=0{return nil,errV4Embedded}
    b.stopped=false
    cold,err:=s.MarshalColdBundle()
    if err!=nil{return nil,err}
    cmd,err:=v4PrivateHandoffFromVerifiedSession(boundary,peer,s)
    if err!=nil{return nil,err}
    var h C.uint64_t
    rc:=C.wbd_m0_embedded_go_prepare(
        (*C.uchar)(unsafe.Pointer(&cold[0])),C.size_t(len(cold)),
        (*C.uchar)(unsafe.Pointer(&cmd[0])),C.size_t(len(cmd)),&h)
    runtime.KeepAlive(cold);runtime.KeepAlive(cmd)
    if rc!=0||h==0{return nil,fmt.Errorf("%w: prepare=%d",errV4Embedded,int(rc))}
    b.handle=uint64(h)
    b.originalFlow=peer.flow
    b.rxBoundary=boundary
    b.protectedEpoch=s.epoch
    b.protectedFeatures=s.features
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
    // The normal build uses an inert hook. Only the separate explicit
    // wbd_v4_fec2_owner_probe build can bind after this true Go TLS/Detach
    // callback; a forged WBGH version2 is NOT permission by itself.
    if err:=v4Fec2ProbeAfterProtectedCommit(p.b);err!=nil{
        // A failed post-reply probe grant cannot leave a live detached
        // Rust generation after Go rolls back its epoch transaction.
        _=C.wbd_m0_embedded_go_stop(C.uint64_t(p.b.handle))
        _=C.wbd_m0_embedded_go_release(C.uint64_t(p.b.handle))
        p.b.handle=0;p.done=true
        return err
    }
    p.done=true;p.b.committed=true
    p.b.txBoundary=tx
    return nil
}
func (p *v4EmbeddedPending) abort(){
    if p.done||p.b.handle==0{return}
    p.done=true
    _=C.wbd_m0_embedded_go_abort(C.uint64_t(p.b.handle))
    p.b.handle=0
}
// An old numeric generation may be inspected after retirement solely to
// assert Rust's actual registry no longer exposes it to a new generation.
func v4EmbeddedNativeState(handle uint64)(uint32,error){
    if handle==0{return 0,errV4Embedded}
    var phase C.uint32_t
    rc:=C.wbd_m0_embedded_go_state(C.uint64_t(handle),&phase)
    if rc!=0{return 0,fmt.Errorf("%w: state=%d",errV4Embedded,int(rc))}
    return uint32(phase),nil
}
func (b *v4EmbeddedNativeBridge) state()(uint32,error){
    return v4EmbeddedNativeState(b.handle)
}
// Private original Go credential-bound Rust backend implements the M0/M4
// shared shutdown boundary. A positive receipt is returned ONLY after the
// true C Stop has joined its workers/drained device borrows and C Release
// removed the generation. The same verified Go epoch is preserved.
func (b *v4EmbeddedNativeBridge) StopAndReleaseOriginalOwner()(V4OwnerStopCompletion,error){
    var zero V4OwnerStopCompletion
    if b==nil || b.protectedEpoch==[16]byte{} {return zero,errV4Embedded}
    epoch:=b.protectedEpoch
    if err:=b.stopRelease();err!=nil{return zero,err}
    if !b.stopped || b.handle!=0 || b.committed{return zero,errV4Embedded}
    return V4OwnerStopCompletion{
        Epoch:epoch,OwnerAndDriversDrained:true,GenerationReleased:true,
    },nil
}
func (b *v4EmbeddedNativeBridge) stopRelease()error{
    if b.stopped && b.handle==0 && !b.committed{return nil} // repeated Stop
    if b.handle==0||!b.committed{return errV4Embedded}
    if b.fec2AutoStop!=nil{
        stop:=b.fec2AutoStop
        b.fec2AutoStop=nil
        stop()
    }
    rc:=C.wbd_m0_embedded_go_stop(C.uint64_t(b.handle))
    if rc!=0{return fmt.Errorf("%w: STOP_INCOMPLETE_OR_FAILED=%d",errV4Embedded,int(rc))}
    rc=C.wbd_m0_embedded_go_release(C.uint64_t(b.handle))
    if rc!=0{return fmt.Errorf("%w: release=%d",errV4Embedded,int(rc))}
    b.handle=0;b.committed=false;b.stopped=true;return nil
}


func (b *v4EmbeddedNativeBridge) attachRawRx(ifindex uint32)error{
    if !b.committed||b.handle==0{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_attach_raw_rx(C.uint64_t(b.handle),C.uint32_t(ifindex))
    if rc!=0{return fmt.Errorf("%w: bind real raw=%d",errV4Embedded,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) attachKernelTun(fd uintptr,name string)error{
    if !b.committed||b.handle==0||len(name)==0||len(name)>15{return errV4Embedded}
    raw:=[]byte(name)
    rc:=C.wbd_m0_embedded_go_attach_tun(C.uint64_t(b.handle),C.int32_t(fd),
        (*C.uchar)(unsafe.Pointer(&raw[0])),C.size_t(len(raw)))
    runtime.KeepAlive(raw)
    if rc!=0{return fmt.Errorf("%w: bind real TUN=%d",errV4Embedded,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) receiveRawToTun()(uint32,uint32,error){
    if !b.committed||b.handle==0{return 0,0,errV4Embedded}
    var delivered C.uint32_t
    var failed C.uint32_t
    rc:=C.wbd_m0_embedded_go_raw_to_tun(C.uint64_t(b.handle),&delivered,&failed)
    if rc!=0{return 0,0,fmt.Errorf("%w: M4 raw to TUN=%d",errV4Embedded,int(rc))}
    return uint32(delivered),uint32(failed),nil
}

func (b *v4EmbeddedNativeBridge) tunToKernelRaw(ifindex uint32)(uint64,uint32,uint32,uint32,error){
    if !b.committed||b.handle==0{return 0,0,0,0,errV4Embedded}
    var pn C.uint64_t
    var seq,full,app C.uint32_t
    rc:=C.wbd_m0_embedded_go_tun_to_raw(
        C.uint64_t(b.handle),C.uint32_t(ifindex),&pn,&seq,&full,&app)
    if rc!=0{return 0,0,0,0,fmt.Errorf("%w: real TUN to raw=%d",errV4Embedded,int(rc))}
    return uint64(pn),uint32(seq),uint32(full),uint32(app),nil
}

// Development-only original Rust owner continuous worker controls. No Go
// per-packet RX/TX invocation while the loop owns both drivers.
func (b *v4EmbeddedNativeBridge) startRustOwnerLoop(ifindex uint32)error{
    if !b.committed||b.handle==0{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_loop_start(C.uint64_t(b.handle),C.uint32_t(ifindex))
    if rc!=0{return fmt.Errorf("%w: Rust original owner loop=%d",errV4Embedded,int(rc))}
    return nil
}
type v4EmbeddedLoopStats struct{RxOK,TxOK,RxErr,TxErr uint64}
func (b *v4EmbeddedNativeBridge) rustOwnerLoopStats()(v4EmbeddedLoopStats,error){
    if !b.committed||b.handle==0{return v4EmbeddedLoopStats{},errV4Embedded}
    var rx,tx,re,te C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_stats(C.uint64_t(b.handle),&rx,&tx,&re,&te)
    if rc!=0{return v4EmbeddedLoopStats{},fmt.Errorf("%w: Rust loop stats=%d",errV4Embedded,int(rc))}
    return v4EmbeddedLoopStats{uint64(rx),uint64(tx),uint64(re),uint64(te)},nil
}

// Actual original M4 copied/uncertain/unsent records observed by frozen
// M2; an absent authenticated peer receipt must never show zero loss.
type v4NormalM2Firstsend struct {
    Accepted,DefinitelyNotSent,Uncertain,Unknown2s,Unknown8s uint64
    Censored bool
}
func (b *v4EmbeddedNativeBridge) rustOwnerNormalM2Firstsend()(v4NormalM2Firstsend,error){
    var z v4NormalM2Firstsend
    if !b.committed||b.handle==0{return z,errV4Embedded}
    var a,n,u,s,l C.uint64_t
    var c C.uint32_t
    rc:=C.wbd_m0_embedded_go_loop_firstsend_m2(
        C.uint64_t(b.handle),&a,&n,&u,&s,&l,&c)
    if rc!=0{return z,fmt.Errorf("%w: normal M2 actual firstsend=%d",errV4Embedded,int(rc))}
    return v4NormalM2Firstsend{uint64(a),uint64(n),uint64(u),uint64(s),uint64(l),c!=0},nil
}
// Developer-only feature-gated barrier. This is not a product scheduler,
// data-plane syscall, or authorization to enable FEC2.
func (b *v4EmbeddedNativeBridge) rustOwnerDebugJumboPause(enabled bool)(bool,uint32,error){
    if !b.committed||b.handle==0{return false,0,errV4Embedded}
    var on C.uint32_t
    if enabled {on=1}
    var paused,loaned C.uint32_t
    rc:=C.wbd_m0_embedded_go_loop_debug_pause_jumbo(
        C.uint64_t(b.handle),on,&paused,&loaned)
    if rc!=0{return false,0,fmt.Errorf("%w: jumbo turn barrier=%d",errV4Embedded,int(rc))}
    return paused!=0,uint32(loaned),nil
}

func (b *v4EmbeddedNativeBridge) rustOwnerWorkerCPU()(uint64,uint64,error){
    if !b.committed||b.handle==0{return 0,0,errV4Embedded}
    var rx,tx C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_thread_cpu(C.uint64_t(b.handle),&rx,&tx)
    if rc!=0{return 0,0,fmt.Errorf("%w: kernel worker thread CPU=%d",errV4Embedded,int(rc))}
    return uint64(rx),uint64(tx),nil
}

func (b *v4EmbeddedNativeBridge) observedRealRustTxIPv4MTU(ifindex uint32)(uint32,error){
    if !b.committed||b.handle==0{return 0,errV4Embedded}
    var limit C.uint32_t
    rc:=C.wbd_m0_embedded_go_observed_tx_ipv4_mtu(
        C.uint64_t(b.handle),C.uint32_t(ifindex),&limit)
    if rc!=0||limit<28{return 0,fmt.Errorf("%w: observed genuine kernel TX budget=%d",errV4Embedded,int(rc))}
    return uint32(limit),nil
}

func (b *v4EmbeddedNativeBridge) rustOwnerRouteRefreshCount()(uint64,error){
    if !b.committed||b.handle==0{return 0,errV4Embedded}
    var out C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_route_refresh(C.uint64_t(b.handle),&out)
    if rc!=0{return 0,fmt.Errorf("%w: original Rust route refresh count=%d",errV4Embedded,int(rc))}
    return uint64(out),nil
}

// Event witness is a diagnostic-only query; never authorizes a new route.
func (b *v4EmbeddedNativeBridge) rustOwnerRouteEventState()(uint64,bool,error){
    if !b.committed||b.handle==0{return 0,false,errV4Embedded}
    var revision C.uint64_t
    var healthy C.uint32_t
    rc:=C.wbd_m0_embedded_go_loop_route_events(C.uint64_t(b.handle),&revision,&healthy)
    if rc!=0{return 0,false,fmt.Errorf("%w: route event observer=%d",errV4Embedded,int(rc))}
    return uint64(revision),healthy==1,nil
}
