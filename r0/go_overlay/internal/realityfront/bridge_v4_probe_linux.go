//go:build linux && cgo && wbd_v4_native_probe

// TEST-ONLY Linux in-process Go→Rust bridge. Never built for production.
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_test_probe_prepare(const unsigned char *, size_t, const unsigned char *, size_t, uint64_t *);
extern int32_t wbd_m0_test_probe_commit(uint64_t, uint32_t, uint32_t, uint32_t);
extern int32_t wbd_m0_test_probe_open_unique(uint64_t, unsigned char *, size_t, uint64_t *, uint32_t *, uint64_t *);
extern int32_t wbd_m0_test_probe_seal_normal(uint64_t, const unsigned char *, size_t, uint16_t, uint16_t, unsigned char *, size_t, uint32_t *, uint64_t *, uint32_t *);
extern int32_t wbd_m0_test_probe_seal_linux_observed(uint64_t, const unsigned char *, size_t, uint32_t, unsigned char *, size_t, uint32_t *, uint64_t *, uint32_t *);
extern int32_t wbd_m0_test_probe_seal_linux_route(uint64_t, const unsigned char *, size_t, uint32_t, uint32_t, unsigned char *, size_t, uint32_t *, uint64_t *, uint32_t *);
extern int32_t wbd_m0_test_probe_send_kernel_udp(uint64_t, const unsigned char *, size_t, uint32_t, uint16_t, uint64_t *, uint32_t *, uint32_t *);
extern int32_t wbd_m0_test_probe_bind_kernel_rx(uint64_t,uint16_t *);
extern int32_t wbd_m0_test_probe_receive_kernel_rx(uint64_t,uint64_t *,uint64_t *);
extern int32_t wbd_m0_test_probe_attach_tun(uint64_t,int32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_test_probe_receive_kernel_to_tun(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_test_probe_tun_to_kernel_udp(uint64_t,uint32_t,uint16_t,uint64_t *,uint32_t *,uint32_t *,uint32_t *);
extern int32_t wbd_m0_test_probe_tun_to_kernel_raw(uint64_t,uint32_t,uint64_t *,uint32_t *,uint32_t *,uint32_t *);
extern int32_t wbd_m0_test_probe_bind_raw_rx(uint64_t,uint32_t);
extern int32_t wbd_m0_test_probe_receive_raw_to_tun(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_test_probe_stage(uint64_t, uint32_t, const unsigned char *, size_t);
extern int32_t wbd_m0_test_probe_drain(uint64_t, uint32_t *, uint32_t *, uint64_t *);
extern int32_t wbd_m0_test_probe_hold_rx(uint64_t, uint32_t *, uint32_t *, uint64_t *);
extern int32_t wbd_m0_test_probe_return_held_rx(uint64_t);
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
    "time"
    "unsafe"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
var errV4NativeProbe=errors.New("V4 test-only native probe refused")
var errV4NativeLinkPending=errors.New("authenticated LINK fragment is incomplete")
type v4NativeRustProbe struct {
    handle uint64
    txBoundary uint32
    rxBoundary uint32
    peerMSS uint16
    peerAdvertised bool
    observedFlow faketcp.ServerFlow // only frozen from protected Go Prepare
    prepared,committed bool
    testAssoc *faketcp.ServerAssociation // Go test-only hook, NOT a C pointer
    injectEarly [][]byte // tests exclusively, raw UNAUTHENTICATED wire
}
func (b *v4NativeRustProbe) bindTestAssociation(a *faketcp.ServerAssociation) {
    b.testAssoc=a
}
// The probe test injects actually routed FakeTCP bytes AFTER exact Prepare,
// BEFORE final protected reply. They pass through real DetachTransition.
func (b *v4NativeRustProbe) injectAfterPrepare(boundary uint32)error {
    if len(b.injectEarly)==0{return nil}
    if b.testAssoc==nil{return errV4NativeProbe}
    flow:=b.testAssoc.Flow()
    seq:=boundary
    for _,payload:=range b.injectEarly {
        seg:=faketcp.Segment{SrcIP:flow.ClientIP,DstIP:flow.ServerIP,
            SrcPort:flow.ClientPort,DstPort:flow.ServerPort,Seq:seq,
            Flags:faketcp.FlagPSH,Payload:append([]byte(nil),payload...)}
        out,err:=b.testAssoc.HandleSegment(seg,time.Now())
        if err!=nil||out.Disposition!=faketcp.RouteQueuedRecord{
            return fmt.Errorf("%w: FakeTCP early route=%v err=%v",errV4NativeProbe,out.Disposition,err)
        }
        seq+=uint32(len(payload))
    }
    return nil
}
func (b *v4NativeRustProbe) prepare(s V4ColdSessionSnapshot,boundary uint32,peer v4PeerTransport)(v4PreparedOwner,error){
    if peer.mss<64{return nil,errV4NativeProbe}
    // Only genuine credential-verified EstablishServerV4 can invoke this
    // private backend slot. This FFI alone NEVER authenticates raw C bytes.
    raw,err:=s.MarshalColdBundle()
    if err!=nil{return nil,err}
    // The same versioned command builder is production Go code. A native
    // buffer cannot authenticate anything; this callsite follows verified
    // credentials, private trusted snapshot, and actual PrepareTransition.
    command,err:=v4PrivateHandoffFromVerifiedSession(boundary,peer,s)
    if err!=nil{return nil,err}
    var handle C.uint64_t
    code:=C.wbd_m0_test_probe_prepare((*C.uchar)(unsafe.Pointer(&raw[0])),
        C.size_t(len(raw)),
        (*C.uchar)(unsafe.Pointer(&command[0])),C.size_t(len(command)),&handle)
    runtime.KeepAlive(raw)
    runtime.KeepAlive(command)
    if code!=0||handle==0{return nil,fmt.Errorf("%w: prepare=%d",errV4NativeProbe,int(code))}
    b.handle=uint64(handle);b.prepared=true
    b.rxBoundary=boundary
    b.peerMSS=peer.mss;b.peerAdvertised=peer.advertised
    b.observedFlow=peer.flow
    if err:=b.injectAfterPrepare(boundary);err!=nil{
        _=C.wbd_m0_test_probe_abort(handle)
        b.handle=0;b.prepared=false
        return nil,err
    }
    return &v4NativeRustPending{handle:b.handle,owner:b},nil
}
type v4NativeRustPending struct {
    handle uint64
    owner *v4NativeRustProbe
    committed,aborted bool
}
func (p *v4NativeRustPending) commit(early []faketcp.TransitionPacket, exactTXBoundary uint32)error{
    if p.committed||p.aborted{return errV4NativeProbe}
    if len(early)>faketcp.MaxTransitionRecords{return errV4NativeProbe}
    total:=0
    for _,packet:=range early{
        n:=len(packet.Payload)
        if n==0||n>2048||total>int(^uint32(0))-n{return errV4NativeProbe}
        total+=n
        code:=C.wbd_m0_test_probe_stage(C.uint64_t(p.handle),
            C.uint32_t(packet.Seq),(*C.uchar)(unsafe.Pointer(&packet.Payload[0])),C.size_t(n))
        runtime.KeepAlive(packet.Payload)
        if code!=0{return fmt.Errorf("%w: early stage seq=%d code=%d",
            errV4NativeProbe,packet.Seq,int(code))}
    }
    code:=C.wbd_m0_test_probe_commit(C.uint64_t(p.handle),
        C.uint32_t(len(early)),C.uint32_t(total),C.uint32_t(exactTXBoundary))
    if code!=0{return fmt.Errorf("%w: commit=%d",errV4NativeProbe,int(code))}
    p.committed=true;p.owner.committed=true;p.owner.txBoundary=exactTXBoundary;return nil
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
func (b *v4NativeRustProbe) drainEarly()(uint32,uint32,uint64,error){
    if !b.committed||b.handle==0{return 0,0,0,errV4NativeProbe}
    var count C.uint32_t
    var size C.uint32_t
    var digest C.uint64_t
    code:=C.wbd_m0_test_probe_drain(C.uint64_t(b.handle),&count,&size,&digest)
    if code!=0{return 0,0,0,fmt.Errorf("%w: drain=%d",errV4NativeProbe,int(code))}
    return uint32(count),uint32(size),uint64(digest),nil
}
// Retain real Rust-owned RX slabs while Stop is attempted; test feature only.
func (b *v4NativeRustProbe) holdEarly()(uint32,uint32,uint64,error){
    if !b.committed||b.handle==0{return 0,0,0,errV4NativeProbe}
    var count C.uint32_t
    var size C.uint32_t
    var digest C.uint64_t
    code:=C.wbd_m0_test_probe_hold_rx(C.uint64_t(b.handle),&count,&size,&digest)
    if code!=0{return 0,0,0,fmt.Errorf("%w: hold=%d",errV4NativeProbe,int(code))}
    return uint32(count),uint32(size),uint64(digest),nil
}
func (b *v4NativeRustProbe) stopPending()(bool,error){
    if !b.committed||b.handle==0{return false,errV4NativeProbe}
    code:=C.wbd_m0_test_probe_stop(C.uint64_t(b.handle))
    if code==5{return true,nil} // explicit Stop incomplete
    if code==0{return false,nil}
    return false,fmt.Errorf("%w: stop pending=%d",errV4NativeProbe,int(code))
}
func (b *v4NativeRustProbe) returnHeld()error{
    if b.handle==0{return errV4NativeProbe}
    code:=C.wbd_m0_test_probe_return_held_rx(C.uint64_t(b.handle))
    if code!=0{return fmt.Errorf("%w: return held=%d",errV4NativeProbe,int(code))}
    return nil
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

// Native observation only: invokes the exact normal-build scoped crypto
// AEAD/PN, LINK inspection/reassembly and first *complete* application
// candidate after verified Go's private Detach+Commit. This is observation,
// not a real platform product sink, nor a production capability.
func (b *v4NativeRustProbe) openAuthenticated(wire []byte)(uint64,uint32,uint64,error){
    if !b.committed||b.handle==0||len(wire)==0{return 0,0,0,errV4NativeProbe}
    copied:=append([]byte(nil),wire...)
    var pn C.uint64_t
    var kind C.uint32_t
    var digest C.uint64_t
    code:=C.wbd_m0_test_probe_open_unique(C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&copied[0])),C.size_t(len(copied)),
        &pn,&kind,&digest)
    runtime.KeepAlive(copied)
    if code==6{return 0,0,0,errV4NativeLinkPending}
    if code!=0{return 0,0,0,fmt.Errorf("%w: scoped Normal/off application candidate open=%d",errV4NativeProbe,int(code))}
    return uint64(pn),uint32(kind),uint64(digest),nil
}

// Test-only observation of the SAME normal-build Rust owner TX direction.
// The M4 path/peer MSS are EXPLICIT TEST INPUTS, not discovered live values;
// this does not send to real raw/TUN or publish an ABI capability.
func (b *v4NativeRustProbe) sealNativeNormal(payload []byte,outerMTU,peerMSS uint16)(
    []byte,uint64,uint32,error,
){
    if !b.committed||b.handle==0||len(payload)==0||peerMSS!=b.peerMSS{
        return nil,0,0,errV4NativeProbe
    }
    wire:=make([]byte,2048)
    var size C.uint32_t
    var pn C.uint64_t
    var seq C.uint32_t
    code:=C.wbd_m0_test_probe_seal_normal(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&payload[0])),
        C.size_t(len(payload)),C.uint16_t(outerMTU),C.uint16_t(peerMSS),
        (*C.uchar)(unsafe.Pointer(&wire[0])),C.size_t(len(wire)),
        &size,&pn,&seq,
    )
    runtime.KeepAlive(payload)
    if code!=0{return nil,0,0,fmt.Errorf("%w: normal scoped TX=%d",errV4NativeProbe,int(code))}
    if size==0||int(size)>len(wire){return nil,0,0,errV4NativeProbe}
    return wire[:int(size)],uint64(pn),uint32(seq),nil
}

// TEST-ONLY C observer. The Rust normal-build ProtectedScopedOwner asks M4's
// kernel-backed interface index/MTU source and combines it with the original
// protected SYN peer MSS. No caller-supplied MTU or MSS, no AF_PACKET socket,
// and no production ABI or application output are created by this method.
func (b *v4NativeRustProbe) sealNativeNormalObservedLinux(
    payload []byte,expectedIfindex uint32,
)([]byte,uint64,uint32,error){
    if !b.committed||b.handle==0||len(payload)==0 {
        return nil,0,0,errV4NativeProbe
    }
    out:=make([]byte,2048)
    var used C.uint32_t
    var pn C.uint64_t
    var seq C.uint32_t
    code:=C.wbd_m0_test_probe_seal_linux_observed(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&payload[0])),C.size_t(len(payload)),
        C.uint32_t(expectedIfindex),(*C.uchar)(unsafe.Pointer(&out[0])),
        C.size_t(len(out)),&used,&pn,&seq,
    )
    runtime.KeepAlive(payload)
    if code!=0 {
        return nil,0,0,fmt.Errorf("%w: kernel observed scoped TX=%d",
            errV4NativeProbe,int(code))
    }
    if used==0||int(used)>len(out){return nil,0,0,errV4NativeProbe}
    return out[:int(used)],uint64(pn),uint32(seq),nil
}

func (b *v4NativeRustProbe) sealNativeNormalKernelRoute(
    payload []byte,expectedIfindex uint32,destination [4]byte,
)([]byte,uint64,uint32,error){
    if !b.committed||b.handle==0||len(payload)==0 {return nil,0,0,errV4NativeProbe}
    output:=make([]byte,2048)
    var used C.uint32_t
    var pn C.uint64_t
    var seq C.uint32_t
    destinationBE:=uint32(destination[0])<<24|uint32(destination[1])<<16|
        uint32(destination[2])<<8|uint32(destination[3])
    code:=C.wbd_m0_test_probe_seal_linux_route(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&payload[0])),
        C.size_t(len(payload)),C.uint32_t(expectedIfindex),
        C.uint32_t(destinationBE),(*C.uchar)(unsafe.Pointer(&output[0])),
        C.size_t(len(output)),&used,&pn,&seq,
    )
    runtime.KeepAlive(payload)
    if code!=0{return nil,0,0,fmt.Errorf("%w: scoped kernel IPv4 route=%d",errV4NativeProbe,int(code))}
    if used==0||int(used)>len(output){return nil,0,0,errV4NativeProbe}
    return output[:int(used)],uint64(pn),uint32(seq),nil
}

// Genuine M4 Linux kernel sendmmsg of the SAME ordinary Rust owner FrozenRecord.
// Go receives on its own UDP socket and opens the original TLS-derived AEAD.
// This test-only wrapper never substitutes a local copy for kernel delivery,
// never treats UDP copy-complete as peer receipt, and is NOT TUN/raw.
func (b *v4NativeRustProbe) sendKernelUDP(payload []byte,ifindex uint32,remotePort uint16)(
    uint64,uint32,uint32,error,
){
    if !b.committed||b.handle==0||len(payload)==0||remotePort==0{
        return 0,0,0,errV4NativeProbe
    }
    var pn C.uint64_t
    var seq C.uint32_t
    var wireSize C.uint32_t
    code:=C.wbd_m0_test_probe_send_kernel_udp(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&payload[0])),
        C.size_t(len(payload)),C.uint32_t(ifindex),C.uint16_t(remotePort),
        &pn,&seq,&wireSize,
    )
    runtime.KeepAlive(payload)
    if code!=0{return 0,0,0,fmt.Errorf("%w: real kernel M4 UDP scoped TX=%d",errV4NativeProbe,int(code))}
    return uint64(pn),uint32(seq),uint32(wireSize),nil
}

// Test-tagged glue only. The native Rust M4 receiver remains allocated by
// original ScopedOwner generation; the test's Go UDP sender supplies the
// encrypted C2S record via an ACTUAL Linux kernel UDP datagram.
func (b *v4NativeRustProbe) bindKernelRx()(uint16,error){
    if !b.committed||b.handle==0{return 0,errV4NativeProbe}
    var port C.uint16_t
    code:=C.wbd_m0_test_probe_bind_kernel_rx(C.uint64_t(b.handle),&port)
    if code!=0||port==0{return 0,fmt.Errorf("%w: kernel RX binding code=%d",errV4NativeProbe,int(code))}
    return uint16(port),nil
}
func (b *v4NativeRustProbe) receiveKernelRx()(uint64,uint64,error){
    if !b.committed||b.handle==0{return 0,0,errV4NativeProbe}
    var pn C.uint64_t
    var digest C.uint64_t
    code:=C.wbd_m0_test_probe_receive_kernel_rx(
        C.uint64_t(b.handle),&pn,&digest,
    )
    if code!=0{return 0,0,fmt.Errorf("%w: kernel RX in owner=%d",errV4NativeProbe,int(code))}
    return uint64(pn),uint64(digest),nil
}

// Test-only glue. The ordinary Rust ScopedTunSink owns a dup of this
// already-configured Linux TUN FD and publishes only AEAD-verified M3
// complete IPV4 packets. No test-only unverified business delivery.
func (b *v4NativeRustProbe) attachKernelTun(fd uintptr,ifname string)error{
    if !b.committed||b.handle==0||len(ifname)==0||len(ifname)>15{return errV4NativeProbe}
    raw:=[]byte(ifname)
    code:=C.wbd_m0_test_probe_attach_tun(
        C.uint64_t(b.handle),C.int32_t(fd),
        (*C.uchar)(unsafe.Pointer(&raw[0])),C.size_t(len(raw)),
    )
    runtime.KeepAlive(raw)
    if code!=0{return fmt.Errorf("%w: attach real TUN=%d",errV4NativeProbe,int(code))}
    return nil
}
func (b *v4NativeRustProbe) receiveKernelToTun()(uint32,uint32,error){
    if !b.committed||b.handle==0{return 0,0,errV4NativeProbe}
    var delivered C.uint32_t
    var rejected C.uint32_t
    code:=C.wbd_m0_test_probe_receive_kernel_to_tun(
        C.uint64_t(b.handle),&delivered,&rejected,
    )
    if code!=0{return 0,0,fmt.Errorf("%w: real TUN app delivery=%d",errV4NativeProbe,int(code))}
    return uint32(delivered),uint32(rejected),nil
}

// Same owner, real TUN kernel-read app ingress directly into M1 slab, AEAD
// S2C, and M4 sendmmsg to an independent Go kernel socket. Test-only ABI.
func (b *v4NativeRustProbe) tunToKernelUDP(ifindex uint32,port uint16)(
    uint64,uint32,uint32,uint32,error,
){
    if !b.committed||b.handle==0||port==0{return 0,0,0,0,errV4NativeProbe}
    var pn C.uint64_t
    var seq,wireSize,appSize C.uint32_t
    code:=C.wbd_m0_test_probe_tun_to_kernel_udp(
        C.uint64_t(b.handle),C.uint32_t(ifindex),C.uint16_t(port),
        &pn,&seq,&wireSize,&appSize,
    )
    if code!=0{return 0,0,0,0,fmt.Errorf("%w: real TUN kernel app->Rust S2C->M4 sendmmsg code=%d",errV4NativeProbe,int(code))}
    return uint64(pn),uint32(seq),uint32(wireSize),uint32(appSize),nil
}

// Test observer only; normal Rust M4 sends an actual raw IPv4/TCP FakeTCP
// envelope containing the original protected AEAD S2C frozen record.
func (b *v4NativeRustProbe) tunToKernelRaw(ifindex uint32)(
    uint64,uint32,uint32,uint32,error,
){
    if !b.committed||b.handle==0{return 0,0,0,0,errV4NativeProbe}
    var pn C.uint64_t
    var seq,ipSize,appSize C.uint32_t
    code:=C.wbd_m0_test_probe_tun_to_kernel_raw(
        C.uint64_t(b.handle),C.uint32_t(ifindex),
        &pn,&seq,&ipSize,&appSize,
    )
    if code!=0{return 0,0,0,0,fmt.Errorf("%w: actual Linux IPv4/TCP raw carrier=%d",errV4NativeProbe,int(code))}
    return uint64(pn),uint32(seq),uint32(ipSize),uint32(appSize),nil
}

// Test-tag only. Receiver is opened after authentic Go protected V4 Detach,
// before Go sends a real TCP raw ciphertext packet on the same Linux netns.
func (b *v4NativeRustProbe) bindRawRx(ifindex uint32)error{
    if !b.committed||b.handle==0||ifindex==0{return errV4NativeProbe}
    code:=C.wbd_m0_test_probe_bind_raw_rx(C.uint64_t(b.handle),C.uint32_t(ifindex))
    if code!=0{return fmt.Errorf("%w: real raw RX binding=%d",errV4NativeProbe,int(code))}
    return nil
}
func (b *v4NativeRustProbe) receiveRawToTun()(uint32,uint32,error){
    if !b.committed||b.handle==0{return 0,0,errV4NativeProbe}
    var d,f C.uint32_t
    code:=C.wbd_m0_test_probe_receive_raw_to_tun(C.uint64_t(b.handle),&d,&f)
    if code!=0{return 0,0,fmt.Errorf("%w: original Rust raw RX->AEAD/TUN=%d",errV4NativeProbe,int(code))}
    return uint32(d),uint32(f),nil
}
