//go:build linux && cgo && wbd_v4_embedded_go

// Developer-opt-in non-_test package-private Go→Rust control adapter.
// Caller is only the credential-verified EstablishServerV4 ownerBridge path.
// NOT public cold248 install; do not ship feature-enabled C library yet.
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
typedef struct {
 uint32_t version,struct_size,configured_outer_ip_mtu,physical_outer_ip_mtu;
 uint32_t peer_advertised_mss,agreed_record_wire_cap,ipv4_header_bytes;
 uint32_t tcp_data_header_bytes,mode;
} WbdV4MTUBudgetInputV1;
typedef struct {
 uint32_t version,struct_size,effective_outer_ip_ceiling,local_syn_advertised_mss;
 uint32_t record_wire_cap,record_payload_cap,single_inner_ip_cap;
 uint32_t link_fragment_payload_cap;
} WbdV4MTUBudgetOutputV1;
extern int32_t wbd_m0_v4_mtu_budget_v1(
 const WbdV4MTUBudgetInputV1 *,uint32_t,WbdV4MTUBudgetOutputV1 *,uint32_t);
extern int32_t wbd_m0_embedded_go_prepare(const unsigned char *,size_t,
    const unsigned char *,size_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_prepare_client(const unsigned char *,size_t,
    const unsigned char *,size_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_stage(uint64_t,uint32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_commit(uint64_t,uint32_t,uint32_t,uint32_t);
extern int32_t wbd_m0_embedded_go_bind_authenticated_client_ipv4(uint64_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_shared_tun_open(int32_t,const unsigned char *,size_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_shared_tun_bind(uint64_t,uint64_t);
extern int32_t wbd_m0_embedded_go_shared_tun_close(uint64_t);
extern int32_t wbd_m0_embedded_go_abort(uint64_t);
extern int32_t wbd_m0_embedded_go_stop(uint64_t);
extern int32_t wbd_m0_embedded_go_release(uint64_t);
extern int32_t wbd_m0_embedded_go_state(uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_attach_raw_rx(uint64_t,uint32_t);
extern int32_t wbd_m0_embedded_go_attach_raw_rx_on_interface(uint64_t,uint32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_attach_tun(uint64_t,int32_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_raw_to_tun(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_tun_to_raw(uint64_t,uint32_t,
    uint64_t *,uint32_t *,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_start(uint64_t,uint32_t);
extern int32_t wbd_m0_embedded_go_arm_public_original_m2_feedback(uint64_t,const unsigned char *,size_t,uint32_t);
extern int32_t wbd_m0_embedded_go_public_auto_low_rate_config(uint64_t,const unsigned char *,size_t,uint32_t);
extern int32_t wbd_m0_embedded_go_public_auto_low_rate_effective(uint64_t,const unsigned char *,size_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_public_native_health_config(uint64_t,const unsigned char *,size_t,uint32_t,uint32_t,uint32_t);
extern int32_t wbd_m0_embedded_go_public_native_health_effective(uint64_t,const unsigned char *,size_t,uint32_t *,size_t);
extern int32_t wbd_m0_embedded_go_set_public_outer_repair(uint64_t,uint32_t);
extern int32_t wbd_m0_embedded_go_read_public_outer_repair(uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_public_outer_counters(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_public_outer_diagnostics(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_public_fec2_tx_snapshot(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_public_fec2_mature_quality(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_public_fec2_tx_failures(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_loop_stats(uint64_t,uint64_t *,uint64_t *,uint64_t *,uint64_t *);
extern int32_t wbd_m0_embedded_go_loop_authenticated_dead(uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_firstsend_m2(uint64_t,uint64_t *,uint64_t *,uint64_t *,uint64_t *,uint64_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_loop_firstsend_m2_coverage(uint64_t,uint64_t *,uint64_t *,uint64_t *,uint32_t *);
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
    "net/netip"
    "os"
    "runtime"
    "sync"
    "unsafe"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
var errV4Embedded=errors.New("embedded V4 Rust control refused")
// Numeric Rust refusal is kept behind a typed, credential-free boundary.
// The parent remains errV4Embedded so old errors.Is semantics are intact.
type v4EmbeddedNativeStatus struct{
    Operation string
    Code int
}
func (e *v4EmbeddedNativeStatus) Error()string{return errV4Embedded.Error()}
func (e *v4EmbeddedNativeStatus) Unwrap()error{return errV4Embedded}

type v4EmbeddedNativeBridge struct {
    handle uint64
    committed bool
    stopped bool // terminal release receipt; not a Rust owner token
    originalFlow faketcp.ServerFlow
    serverSide bool // original Go protected TLS cold snapshot, not caller data
    rxBoundary uint32
    txBoundary uint32
    protectedEpoch [16]byte
    authenticatedPrincipal string
    protectedFeatures uint16
    protectedLane uint8 // original immutable Go TLS negotiated 1..4 lane
    sackPermitted bool // original Go FakeTCP SYN/SYN-ACK result, not a packet claim
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
    b.serverSide=true
    b.rxBoundary=boundary
    b.protectedEpoch=s.epoch
    b.authenticatedPrincipal=s.principal
    b.protectedFeatures=s.features
    b.protectedLane=s.laneID
    return &v4EmbeddedPending{b:b},nil
}
// Actual original Go client TLS reply is checked before this private
// wrapper can construct original C2S/S2C exporter material. The client
// FakeTCP Detach supplies the exact transport RX/TX boundaries; no arbitrary
// operator cold bytes can enable the Rust owner.
func (b *v4EmbeddedNativeBridge) prepareAuthenticatedClient(
    session *V4ClientSession,handoff faketcp.ClientHandoff,
    flow faketcp.ClientFlow,
)error{
    if b==nil||b.handle!=0||b.committed||session==nil{return errV4Embedded}
    cold,err:=session.ColdSnapshot()
    if err!=nil||cold.ServerSide() {return errV4Embedded}
    snapshot,err:=cold.MarshalColdBundle()
    if err!=nil{return err}
    peer:=v4PeerTransport{
        mss:handoff.Peer.MSS,advertised:handoff.Peer.AdvertisedMSS,
        flow:faketcp.ServerFlow{
            ClientIP:flow.LocalIP,ServerIP:flow.PeerIP,
            ClientPort:flow.LocalPort,ServerPort:flow.PeerPort,
        },
    }
    cmd,err:=v4PrivateHandoffFromVerifiedClientSession(handoff.ReceiveNext,peer,cold)
    if err!=nil{return err}
    var h C.uint64_t
    rc:=C.wbd_m0_embedded_go_prepare_client(
        (*C.uchar)(unsafe.Pointer(&snapshot[0])),C.size_t(len(snapshot)),
        (*C.uchar)(unsafe.Pointer(&cmd[0])),C.size_t(len(cmd)),&h)
    runtime.KeepAlive(snapshot);runtime.KeepAlive(cmd)
    if rc!=0||h==0{return fmt.Errorf("%w: client prepare=%d",errV4Embedded,int(rc))}
    b.handle=uint64(h)
    // The original Go association has already detached; there can be no
    // live Rust TUN/driver before exact commit of protected TLS seq limits.
    rc=C.wbd_m0_embedded_go_commit(C.uint64_t(b.handle),0,0,C.uint32_t(handoff.SendNext))
    if rc!=0{
        _=C.wbd_m0_embedded_go_abort(C.uint64_t(b.handle))
        b.handle=0
        return fmt.Errorf("%w: client commit=%d",errV4Embedded,int(rc))
    }
    b.originalFlow=peer.flow
    b.serverSide=false
    b.rxBoundary=handoff.ReceiveNext
    b.txBoundary=handoff.SendNext
    b.protectedEpoch=cold.Epoch()
    b.authenticatedPrincipal=cold.Principal()
    b.protectedFeatures=session.negotiatedFeatures
    b.protectedLane=cold.laneID
    b.sackPermitted=handoff.Peer.SACKPermitted
    b.committed=true
    return nil
}
// Private original-Go verified client /32 lease, checked after real
// protected TLS and before Rust raw/TUN worker. Server uses the verified
// lease to reject forged *incoming* inner IPv4 sources; client authorizes
// its OS-installed /32 and one shared default M1 TUN reader. An untrusted
// outer tuple, manual IP, feature token or mutable result cannot bind it.
func (b *v4EmbeddedNativeBridge) bindAuthenticatedClientIPv4(lease string)error{
    if b==nil||b.handle==0||!b.committed||lease==""{
        return errV4Embedded
    }
    prefix,err:=netip.ParsePrefix(lease)
    if err!=nil||!prefix.Addr().Is4()||prefix.Bits()!=32||
       prefix.Addr().IsUnspecified()||prefix.Addr().IsMulticast(){
        return errV4Embedded
    }
    addr:=prefix.Addr().As4()
    rc:=C.wbd_m0_embedded_go_bind_authenticated_client_ipv4(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&addr[0])),C.size_t(len(addr)))
    runtime.KeepAlive(addr)
    if rc!=0{return fmt.Errorf("%w: authenticated client IPv4 bind=%d",errV4Embedded,int(rc))}
    return nil
}
// V4LinuxSharedTun owns ONE process-wide real Linux TUN kernel reader,
// whether that Go process is a server with per-/32 peers or a client with
// a protected default. Go retains the OS fd; Rust clones it and joins every
// registered original-TLS Rust M1 sender before Close succeeds.
// Per-session Stop never closes this independent reader.
type V4LinuxSharedTun struct{
    mu sync.Mutex
    handle uint64
}
func NewV4LinuxSharedTun(f *os.File,name string)(*V4LinuxSharedTun,error){
    if f==nil||name==""||len(name)>15{return nil,errV4Embedded}
    var h C.uint64_t
    rc:=C.wbd_m0_embedded_go_shared_tun_open(C.int32_t(f.Fd()),
        (*C.uchar)(unsafe.Pointer(unsafe.StringData(name))),
        C.size_t(len(name)),&h)
    runtime.KeepAlive(f)
    if rc!=0||h==0{return nil,fmt.Errorf("%w: shared native TUN open=%d",errV4Embedded,int(rc))}
    return &V4LinuxSharedTun{handle:uint64(h)},nil
}
func (r *V4LinuxSharedTun) Close()error{
    if r==nil{return nil}
    r.mu.Lock()
    defer r.mu.Unlock()
    if r.handle==0{return nil}
    rc:=C.wbd_m0_embedded_go_shared_tun_close(C.uint64_t(r.handle))
    if rc!=0{return fmt.Errorf("%w: shared native TUN Close=%d (owned sessions must Stop first)",
        errV4Embedded,int(rc))}
    r.handle=0
    return nil
}
func (b *v4EmbeddedNativeBridge) bindAuthenticatedSharedTun(r *V4LinuxSharedTun)error{
    if b==nil||b.handle==0||!b.committed||r==nil{
        return errV4Embedded
    }
    r.mu.Lock()
    defer r.mu.Unlock()
    if r.handle==0{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_shared_tun_bind(C.uint64_t(b.handle),C.uint64_t(r.handle))
    if rc!=0{return fmt.Errorf("%w: authenticated shared TUN bind=%d",&v4EmbeddedNativeStatus{Operation:"shared_tun_bind",Code:int(rc)},int(rc))}
    return nil
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
// The shipping original-Go V4 Linux admission owner MUST bind actual
// operator-selected underlay, never the old opt-in loopback-only ABI.
// Rust checks actual kernel ifname/ifindex under the authenticated generation.
func (b *v4EmbeddedNativeBridge) attachRawRxOnInterface(ifname string,ifindex uint32)error{
    if !b.committed||b.handle==0||ifindex==0||len(ifname)==0||len(ifname)>15{
        return errV4Embedded
    }
    for _,ch:=range []byte(ifname){
        if !(ch>='a'&&ch<='z'||ch>='A'&&ch<='Z'||ch>='0'&&ch<='9'||ch=='_'||ch=='-'){
            return errV4Embedded
        }
    }
    bytes:=[]byte(ifname)
    rc:=C.wbd_m0_embedded_go_attach_raw_rx_on_interface(
        C.uint64_t(b.handle),C.uint32_t(ifindex),
        (*C.uchar)(unsafe.Pointer(&bytes[0])),C.size_t(len(bytes)))
    runtime.KeepAlive(bytes)
    if rc!=0{return fmt.Errorf("%w: authenticated raw underlay %q/%d bind=%d",&v4EmbeddedNativeStatus{Operation:"raw_rx_attach",Code:int(rc)},ifname,ifindex,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) attachKernelTun(fd uintptr,name string)error{
    if !b.committed||b.handle==0||len(name)==0||len(name)>15{return errV4Embedded}
    raw:=[]byte(name)
    rc:=C.wbd_m0_embedded_go_attach_tun(C.uint64_t(b.handle),C.int32_t(fd),
        (*C.uchar)(unsafe.Pointer(&raw[0])),C.size_t(len(raw)))
    runtime.KeepAlive(raw)
    if rc!=0{return fmt.Errorf("%w: bind real TUN=%d",&v4EmbeddedNativeStatus{Operation:"tun_attach",Code:int(rc)},int(rc))}
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
// Only the actual shipping original Go V4 client/server after credential
// authentication, FakeTCP Detach and real native M4 driver binding may
// arm original M2 feedback on this same Rust owner. Scoped old-Go fixture
// has its own authenticated receipt sender; it must not race a second one.
// Original public CLI exposes only Rust's post-kernel, post-AEAD M2
// counters. These are facts, NOT a synthetic readiness or APPLIED grant.
type V4PublicOuterCounters struct{
    OuterRepairEnabled bool
    FirstKernelCopied uint64
    AuthenticatedAckRetired uint64
    OriginalFrozenRepaired uint64
    DriverUncertain uint64
    BudgetOrCapacityBlocked uint64
    RetiredTotal uint64
    CandidateFirst,CandidateRetry uint64
    AckedAttempt0,AckedAttempt1,AckedAttempt2 uint64
    ExpiredAttempt0,ExpiredAttempt1,ExpiredAttempt2 uint64
    LatePositiveExpired uint64
    TimingSamples,SRTTus,RTTVarus,RecentRTTus,Reorderus,PTOus,Cacheus uint64
    ShadowOutstanding uint64
    BlockedFreshGlobal,BlockedFreshShadow,BlockedGrant uint64
    BlockedBurst,BlockedQuota,BlockedCapacity,BlockedStale uint64
    BlockedLocalOther,BlockedGlobalOther,BlockedInvariant uint64
    RepairAcceptedRetired,RepairUncertainRetired,RepairAbandonedRetired uint64
    MaxQueueAgeus,RepairAttemptLimit,ShadowLimit,RetainCapus uint64
    FirstWireBytes,RepairAcceptedWireBytes,RepairUncertainWireBytes uint64
}
func (b *v4EmbeddedNativeBridge) originalPublicOuterCounters()(V4PublicOuterCounters,error){
    var zero V4PublicOuterCounters
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,errV4Embedded}
    var values [9]C.uint64_t
    rc:=C.wbd_m0_embedded_go_public_outer_counters(
        C.uint64_t(b.handle),&values[0],9)
    if rc!=0{return zero,fmt.Errorf("%w: native original M2 stats=%d",errV4Embedded,int(rc))}
    var d [34]C.uint64_t
    rc=C.wbd_m0_embedded_go_public_outer_diagnostics(
        C.uint64_t(b.handle),&d[0],34)
    if rc!=0{return zero,fmt.Errorf("%w: native original M2 diagnostics=%d",errV4Embedded,int(rc))}
    var enabled C.uint32_t
    rc=C.wbd_m0_embedded_go_read_public_outer_repair(C.uint64_t(b.handle),&enabled)
    if rc!=0||enabled>1{return zero,fmt.Errorf("%w: outer repair readback=%d",errV4Embedded,int(rc))}
    return V4PublicOuterCounters{
        OuterRepairEnabled:enabled==1,
        FirstKernelCopied:uint64(values[0]),
        AuthenticatedAckRetired:uint64(values[1]),
        OriginalFrozenRepaired:uint64(values[2]),
        DriverUncertain:uint64(values[3]),
        BudgetOrCapacityBlocked:uint64(values[4]),
        RetiredTotal:uint64(values[5]),
        FirstWireBytes:uint64(values[6]),
        RepairAcceptedWireBytes:uint64(values[7]),
        RepairUncertainWireBytes:uint64(values[8]),
        CandidateFirst:uint64(d[0]),CandidateRetry:uint64(d[1]),
        AckedAttempt0:uint64(d[2]),AckedAttempt1:uint64(d[3]),AckedAttempt2:uint64(d[4]),
        ExpiredAttempt0:uint64(d[5]),ExpiredAttempt1:uint64(d[6]),ExpiredAttempt2:uint64(d[7]),
        LatePositiveExpired:uint64(d[8]),TimingSamples:uint64(d[9]),
        SRTTus:uint64(d[10]),RTTVarus:uint64(d[11]),RecentRTTus:uint64(d[12]),
        Reorderus:uint64(d[13]),PTOus:uint64(d[14]),Cacheus:uint64(d[15]),
        ShadowOutstanding:uint64(d[16]),
        BlockedFreshGlobal:uint64(d[17]),BlockedFreshShadow:uint64(d[18]),
        BlockedGrant:uint64(d[19]),BlockedBurst:uint64(d[20]),
        BlockedQuota:uint64(d[21]),BlockedCapacity:uint64(d[22]),
        BlockedStale:uint64(d[23]),BlockedLocalOther:uint64(d[24]),
        BlockedGlobalOther:uint64(d[25]),BlockedInvariant:uint64(d[26]),
        RepairAcceptedRetired:uint64(d[27]),RepairUncertainRetired:uint64(d[28]),
        RepairAbandonedRetired:uint64(d[29]),MaxQueueAgeus:uint64(d[30]),
        RepairAttemptLimit:uint64(d[31]),ShadowLimit:uint64(d[32]),
        RetainCapus:uint64(d[33]),
    },nil
}
// Read-only original Rust worker stats under the authenticated owner scope.
type V4PublicFecTxSnapshot struct{
    Accepted,SourceNotReady,Full,Partial uint64
    K1,K2To4,K5To12,K13To16 uint64
    RPlanned,RSent,ExpiredJobs,PressureJobs,PressureSources,UnknownCapacity uint64
}
func (b *v4EmbeddedNativeBridge) originalPublicFecTxSnapshot()(V4PublicFecTxSnapshot,error){
    var zero V4PublicFecTxSnapshot
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,errV4Embedded}
    var v [14]C.uint64_t
    rc:=C.wbd_m0_embedded_go_public_fec2_tx_snapshot(C.uint64_t(b.handle),&v[0],14)
    if rc!=0{return zero,fmt.Errorf("%w: FEC TX snapshot=%d",errV4Embedded,int(rc))}
    return V4PublicFecTxSnapshot{
        Accepted:uint64(v[0]),SourceNotReady:uint64(v[1]),
        Full:uint64(v[2]),Partial:uint64(v[3]),
        K1:uint64(v[4]),K2To4:uint64(v[5]),K5To12:uint64(v[6]),
        K13To16:uint64(v[7]),RPlanned:uint64(v[8]),RSent:uint64(v[9]),
        ExpiredJobs:uint64(v[10]),PressureJobs:uint64(v[11]),
        PressureSources:uint64(v[12]),UnknownCapacity:uint64(v[13]),
    },nil
}
// Real generation-local failure reasons, never a guessed cause from aggregate M2.
type V4PublicFecTxFailures struct{
    SourcePayload,SourceArena,SourceSeal uint64
    ParityPolicy,ParityArena,ParitySeal,ParityM4Noncopy,SourceM4Noncopy uint64
}
func (b *v4EmbeddedNativeBridge) originalPublicFecTxFailures()(V4PublicFecTxFailures,error){
    var zero V4PublicFecTxFailures
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,errV4Embedded}
    var v [8]C.uint64_t
    rc:=C.wbd_m0_embedded_go_public_fec2_tx_failures(C.uint64_t(b.handle),&v[0],8)
    if rc!=0{return zero,fmt.Errorf("%w: FEC TX failure reasons=%d",errV4Embedded,int(rc))}
    return V4PublicFecTxFailures{SourcePayload:uint64(v[0]),SourceArena:uint64(v[1]),
        SourceSeal:uint64(v[2]),ParityPolicy:uint64(v[3]),ParityArena:uint64(v[4]),
        ParitySeal:uint64(v[5]),ParityM4Noncopy:uint64(v[6]),SourceM4Noncopy:uint64(v[7])},nil
}
// Strict post-auth, pre-worker native policy; a Go-only toggle is invalid.
func (b *v4EmbeddedNativeBridge) configureOriginalOuterRepair(enabled bool)error{
    if b==nil||!b.committed||b.stopped||b.handle==0{return errV4Embedded}
    value:=C.uint32_t(0)
    if enabled{value=1}
    rc:=C.wbd_m0_embedded_go_set_public_outer_repair(C.uint64_t(b.handle),value)
    if rc!=0{return fmt.Errorf("%w: set native outer repair=%d",errV4Embedded,int(rc))}
    var applied C.uint32_t
    rc=C.wbd_m0_embedded_go_read_public_outer_repair(C.uint64_t(b.handle),&applied)
    if rc!=0||applied!=value{
        return fmt.Errorf("%w: native outer repair mismatch requested=%d actual=%d code=%d",
            errV4Embedded,uint32(value),uint32(applied),int(rc))
    }
    return nil
}
// 3x-dead redundancy and the actual owner-only Rust effective readback.
// This is a cold post-TLS/pre-worker call shared by Linux client and server.
func (b *v4EmbeddedNativeBridge) configureOriginalNativeHealth(
 interval,dead,dormant uint32,
)error{
 if b==nil||!b.committed||b.stopped||b.handle==0||
  b.protectedEpoch==[16]byte{}||
  interval<1||interval>3600||dead>86400||
  uint64(dead)<3*uint64(interval)||dormant>86400{return errV4Embedded}
 rc:=C.wbd_m0_embedded_go_public_native_health_config(
  C.uint64_t(b.handle),
  (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),C.size_t(16),
  C.uint32_t(interval),C.uint32_t(dead),C.uint32_t(dormant))
 if rc!=0{return fmt.Errorf("%w: original native Rust Health config rc=%d",errV4Embedded,int(rc))}
 effective,err:=b.readOriginalNativeHealth()
 if err!=nil||effective!=[3]uint32{interval,dead,dormant}{
  return fmt.Errorf("%w: original native Rust Health effective requested=%v readback=%v: %v",
   errV4Embedded,[3]uint32{interval,dead,dormant},effective,err)
 }
 return nil
}
func (b *v4EmbeddedNativeBridge) readOriginalNativeHealth()([3]uint32,error){
 var result [3]uint32
 if b==nil||!b.committed||b.stopped||b.handle==0||
  b.protectedEpoch==[16]byte{}{return result,errV4Embedded}
 var data [3]C.uint32_t
 rc:=C.wbd_m0_embedded_go_public_native_health_effective(
  C.uint64_t(b.handle),
  (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),C.size_t(16),
  &data[0],C.size_t(len(data)))
 if rc!=0{return result,fmt.Errorf("%w: original native Rust Health readback rc=%d",errV4Embedded,int(rc))}
 for i:=range result{result[i]=uint32(data[i])}
 return result,nil
}
// Auto mode is selected once by the credential-verified Go product,
 // read back from the same Rust native owner before any M4 worker starts.
func (b *v4EmbeddedNativeBridge) enableOriginalLowRateAuto()error{
    if b==nil||!b.committed||b.stopped||b.handle==0||
        b.protectedEpoch==[16]byte{}{return errV4Embedded}
    ep:=(*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0]))
    rc:=C.wbd_m0_embedded_go_public_auto_low_rate_config(
        C.uint64_t(b.handle),ep,C.size_t(16),C.uint32_t(1))
    if rc!=0{return fmt.Errorf("%w: Linux original Auto low-rate config rc=%d",errV4Embedded,int(rc))}
    var applied C.uint32_t
    rc=C.wbd_m0_embedded_go_public_auto_low_rate_effective(
        C.uint64_t(b.handle),ep,C.size_t(16),&applied)
    if rc!=0||applied!=1{
        return fmt.Errorf("%w: Linux original Auto low-rate readback rc=%d applied=%d",errV4Embedded,int(rc),uint32(applied))
    }
    return nil
}
func (b *v4EmbeddedNativeBridge) armOriginalPublicM2Feedback(peerPersona uint32)error{
    if b==nil||!b.committed||b.stopped||b.handle==0||
        b.protectedEpoch==[16]byte{} {return errV4Embedded}
    // One cold capability bit on the original scoped bind: the native
    // receiver may use SACK only when the protected FakeTCP peer agreed.
    if b.sackPermitted { peerPersona|=4 }
    rc:=C.wbd_m0_embedded_go_arm_public_original_m2_feedback(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),C.size_t(16),C.uint32_t(peerPersona))
    if rc!=0{return fmt.Errorf("%w: original public M2 feedback bind=%d",errV4Embedded,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) startRustOwnerLoop(ifindex uint32)error{
    if !b.committed||b.handle==0{return errV4Embedded}
    rc:=C.wbd_m0_embedded_go_loop_start(C.uint64_t(b.handle),C.uint32_t(ifindex))
    if rc!=0{return fmt.Errorf("%w: Rust original owner loop=%d",&v4EmbeddedNativeStatus{Operation:"rust_loop_start",Code:int(rc)},int(rc))}
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
// Read actual post-AEAD C2S kind1 receiver/first-send M2 coverage.
 // With no authentic reverse report all these counters MUST be zero.
 type v4NormalM2Coverage struct {
     Covered2s,Covered8s,AuthenticatedReverseReports uint64
     Censored bool
 }
 func (b *v4EmbeddedNativeBridge) rustOwnerNormalM2Coverage()(v4NormalM2Coverage,error){
     var z v4NormalM2Coverage
     if !b.committed||b.handle==0{return z,errV4Embedded}
     var a,b8,reports C.uint64_t
     var c C.uint32_t
     rc:=C.wbd_m0_embedded_go_loop_firstsend_m2_coverage(
         C.uint64_t(b.handle),&a,&b8,&reports,&c)
     if rc!=0{return z,fmt.Errorf("%w: normal M2 authentic reverse coverage=%d",errV4Embedded,int(rc))}
     return v4NormalM2Coverage{uint64(a),uint64(b8),uint64(reports),c!=0},nil
 }
// Full original native source-only quality readback. No copied parity,
// repair-shadow RTT or inferred netem loss enters these 30 monotone counts.
func (b *v4EmbeddedNativeBridge) rustOwnerFec2MatureQuality()([30]uint64,error){
    var out [30]uint64
    if b==nil||!b.committed||b.handle==0||b.stopped{return out,errV4Embedded}
    var native [30]C.uint64_t
    rc:=C.wbd_m0_embedded_go_public_fec2_mature_quality(
        C.uint64_t(b.handle),&native[0],C.size_t(len(native)))
    if rc!=0{return out,fmt.Errorf("%w: native FEC M2 quality=%d",errV4Embedded,int(rc))}
    for i,v:=range native {out[i]=uint64(v)}
    return out,nil
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

// One readback on stop/diagnostic only: native Linux per-thread CPU time,
// kept separate from total Go+Rust process CPU in the Actions monitor.
type V4PublicWorkerCPU struct{RxNs,TxNs uint64}
// Low-frequency terminal or explicitly enabled diagnostic only. This method
// queries real native worker completion counters and CPU; no packet or
// authentication path is redirected to Go.
type V4PublicLoopPulse struct{
    RxRecords,TxRecords,RxErrors,TxErrors uint64
    RxThreadCPUns,TxThreadCPUns uint64
    AuthenticatedPeerDead bool
}
func (b *v4EmbeddedNativeBridge) originalPublicLoopPulse()(V4PublicLoopPulse,error){
    if b==nil||!b.committed||b.stopped||b.handle==0 {
        return V4PublicLoopPulse{},errV4Embedded
    }
    stats,err:=b.rustOwnerLoopStats()
    if err!=nil{return V4PublicLoopPulse{},err}
    rx,tx,err:=b.rustOwnerWorkerCPU()
    if err!=nil{return V4PublicLoopPulse{},err}
    var nativeDead C.uint32_t
    rc:=C.wbd_m0_embedded_go_loop_authenticated_dead(
        C.uint64_t(b.handle),&nativeDead)
    if rc!=0{return V4PublicLoopPulse{},fmt.Errorf(
        "%w: native authenticated Health terminal readback=%d",
        errV4Embedded,int(rc))}
    return V4PublicLoopPulse{
        RxRecords:stats.RxOK,TxRecords:stats.TxOK,
        RxErrors:stats.RxErr,TxErrors:stats.TxErr,
        RxThreadCPUns:rx,TxThreadCPUns:tx,
        AuthenticatedPeerDead:nativeDead!=0,
    },nil
}
func (b *v4EmbeddedNativeBridge) originalPublicWorkerCPU()(V4PublicWorkerCPU,error){
    rx,tx,err:=b.rustOwnerWorkerCPU()
    return V4PublicWorkerCPU{RxNs:rx,TxNs:tx},err
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

// V4ColdMTUBudgetInput is pure, usable before TLS. MSS is raw SYN MSS.
// OS installed/applied is a separate receipt, never inferred from this output.
type V4ColdMTUBudgetInput struct {
 ConfiguredOuterIPMTU,PhysicalOuterIPMTU uint32
 PeerAdvertisedMSS,AgreedRecordWireCap uint32
 IPv4HeaderBytes,TCPDataHeaderBytes,Mode uint32
}
type V4ColdMTUBudgetOutput struct {
 EffectiveOuterIPCeiling,LocalSYNAdvertisedMSS uint32
 RecordWireCap,RecordPayloadCap,SingleInnerIPCap uint32
 LinkFragmentPayloadCap uint32
}
func V4DeriveColdMTUBudget(i V4ColdMTUBudgetInput)(V4ColdMTUBudgetOutput,error){
 req:=C.WbdV4MTUBudgetInputV1{
  version:1,struct_size:C.uint32_t(unsafe.Sizeof(C.WbdV4MTUBudgetInputV1{})),
  configured_outer_ip_mtu:C.uint32_t(i.ConfiguredOuterIPMTU),
  physical_outer_ip_mtu:C.uint32_t(i.PhysicalOuterIPMTU),
  peer_advertised_mss:C.uint32_t(i.PeerAdvertisedMSS),
  agreed_record_wire_cap:C.uint32_t(i.AgreedRecordWireCap),
  ipv4_header_bytes:C.uint32_t(i.IPv4HeaderBytes),
  tcp_data_header_bytes:C.uint32_t(i.TCPDataHeaderBytes),
  mode:C.uint32_t(i.Mode),
 }
 var out C.WbdV4MTUBudgetOutputV1
 rc:=C.wbd_m0_v4_mtu_budget_v1(&req,C.uint32_t(unsafe.Sizeof(req)),
  &out,C.uint32_t(unsafe.Sizeof(out)))
 if rc!=0 {return V4ColdMTUBudgetOutput{},fmt.Errorf("V4 Rust MTU ABI v1 rejected: %d",int(rc))}
 if out.version!=1||out.struct_size!=C.uint32_t(unsafe.Sizeof(out)){
  return V4ColdMTUBudgetOutput{},fmt.Errorf("V4 Rust MTU ABI readback layout mismatch")
 }
 return V4ColdMTUBudgetOutput{
  EffectiveOuterIPCeiling:uint32(out.effective_outer_ip_ceiling),
  LocalSYNAdvertisedMSS:uint32(out.local_syn_advertised_mss),
  RecordWireCap:uint32(out.record_wire_cap),
  RecordPayloadCap:uint32(out.record_payload_cap),
  SingleInnerIPCap:uint32(out.single_inner_ip_cap),
  LinkFragmentPayloadCap:uint32(out.link_fragment_payload_cap),
 },nil
}
