//go:build android && cgo && wbd_v4_embedded_go

package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_game_group_join(const uint64_t *,size_t,uint32_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_game_group_state(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_android_game_group_raw_bind(uint64_t);
extern int32_t wbd_m0_embedded_go_android_game_group_raw_state(uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_android_game_group_m4_start(uint64_t,int32_t,const unsigned char *,size_t,uint32_t,uint32_t,uint32_t,const unsigned char *,const unsigned char *,size_t,uint32_t,const unsigned char *);
extern int32_t wbd_m0_embedded_go_android_game_group_m4_counters(uint64_t,uint64_t *,size_t);
extern int32_t wbd_fec_network_game_group_counters(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_game_group_stop(uint64_t);
extern int32_t wbd_m0_embedded_go_game_group_release(uint64_t);
*/
import "C"
import (
    "context"
    "errors"
    "fmt"
    "net"
    "net/netip"
    "os"
    "runtime"
    "sync"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// The same original Go TLS and private Rust GameAdapter power
// Android Game2/4 off or authenticated fixed Game FEC. No Go DATA worker.
type V4AndroidGameConfig struct{
    Lanes uint8
    GameFecEnabled bool
    GameFecProfile uint8
    NetworkInterface string
    NetworkIfIndex uint32
    AndroidPhysicalNetworkHandle uint64
    AndroidPhysicalMTU uint32
    Tun *os.File
    TunName string
    ConfigureTunnelMTU func(peerMSS,clientLimit,serverLimit uint16)error
    ConfigureLeaseIPv4 func(string)error
    TunnelDNS bool
    TunnelDNSUpstream netip.Addr
    HealthSeconds uint32
    PhysicalDNS bool
    PhysicalDNSUpstream netip.Addr
    CN8503Raw []byte
}
type V4AndroidGameProduct struct{
    mu sync.Mutex
    cfg V4AndroidGameConfig
    native uint64
    owners []*v4EmbeddedNativeBridge
    verified *V4LinuxGameVerifiedGroup
    sessions []*V4ClientSession
    authenticatedLease string
    stopped bool
    connected bool
}
func NewV4AndroidGameProduct(cfg V4AndroidGameConfig)(*V4AndroidGameProduct,error){
    if (cfg.Lanes!=2&&cfg.Lanes!=4)||
        (cfg.GameFecEnabled&&cfg.GameFecProfile>6)||
        cfg.Tun==nil||cfg.ConfigureLeaseIPv4==nil||
        cfg.NetworkInterface==""||len(cfg.NetworkInterface)>15||
        cfg.NetworkIfIndex==0||cfg.AndroidPhysicalNetworkHandle==0||
        cfg.AndroidPhysicalMTU<576||cfg.AndroidPhysicalMTU>65535||
        cfg.TunName==""||len(cfg.TunName)>15||
        (cfg.HealthSeconds!=15&&cfg.HealthSeconds!=30)||
        !cfg.PhysicalDNSUpstream.Is4()||
        (cfg.TunnelDNS&&(cfg.PhysicalDNS||len(cfg.CN8503Raw)>0))||
        (cfg.PhysicalDNS&&len(cfg.CN8503Raw)>0){
        return nil,ErrAdmissionParams
    }
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||iface==nil||uint32(iface.Index)!=cfg.NetworkIfIndex||
        uint32(iface.MTU)!=cfg.AndroidPhysicalMTU{
        return nil,ErrAdmissionUnsupported
    }
    if _,err=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    return &V4AndroidGameProduct{cfg:cfg},nil
}
// ConnectAuthenticatedGame consumes genuine original-Go SYN/TLS session
// state, never caller-supplied cold-bundle bytes or mutable private crypto.
// The provided associations must already be real established FakeTCP peers.
func (p *V4AndroidGameProduct) ConnectAuthenticatedGame(
    ctx context.Context,assocs []*faketcp.ClientAssociation,base ClientAdmissionConfig,
)(lease string,err error){
    if p==nil{return "",ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if p.connected||p.stopped||p.native!=0||len(p.owners)!=0||
       len(assocs)!=int(p.cfg.Lanes)||!base.AutoLease||
       base.DesiredLanes!=p.cfg.Lanes||base.Policy.Transport!=TransportGame||
       base.Policy.DesiredLanes!=p.cfg.Lanes||base.Policy.SupportedNow()!=nil{
        return "",ErrAdmissionUnsupported
    }
    defer func(){
        if err!=nil{
            err=errors.Join(err,p.stopLocked())
        }
    }()
    var epoch [16]byte
    var negotiatedFec uint8
    if p.cfg.GameFecEnabled{negotiatedFec=p.cfg.GameFecProfile+1}
    for i,assoc:=range assocs{
        if assoc==nil||assoc.BootstrapConn()==nil{
            return "",ErrAdmissionParams
        }
        laneCfg:=base
        laneCfg.LaneID=uint8(i+1)
        // Same real Go TLS policy and exporter as Linux Game2/off.
        session,e:=EstablishClientV4(ctx,assoc.BootstrapConn(),laneCfg,V4ClientOptions{
            DataPlaneReady:true,Epoch:epoch,fec2Product:true,
            GameFec:negotiatedFec,StartupPadding:0,
        })
        if e!=nil{return "",e}
        // EstablishClientV4 already compares the protected reply's
        // extension.GameFec to GameFec:negotiatedFec before returning
        // this authenticated session. Do not invent a client struct
        // field or re-check a mutable post-TLS snapshot here.
        if i==0{epoch=session.Epoch}
        handoff,e:=assoc.Detach()
        if e!=nil{return "",e}
        owner:=&v4EmbeddedNativeBridge{}
        if e=owner.prepareAuthenticatedClient(session,handoff,assoc.Flow());e!=nil{
            return "",e
        }
        p.owners=append(p.owners,owner)
        p.sessions=append(p.sessions,session)
        current,e:=session.AuthenticatedLeaseIPv4()
        if e!=nil||current==""{return "",ErrAdmissionUnsupported}
        if i==0{
            lease=current
            if e=p.cfg.ConfigureLeaseIPv4(lease);e!=nil{return "",e}
            p.authenticatedLease=lease
        }else if current!=lease{
            return "",ErrAdmissionUnsupported
        }
        if e=owner.bindAuthenticatedClientIPv4(current);e!=nil{return "",e}
        if p.cfg.ConfigureTunnelMTU!=nil{
            cold,e:=session.ColdSnapshot()
            if e!=nil{return "",e}
            cl,sl:=cold.RecordLimits()
            if e=p.cfg.ConfigureTunnelMTU(handoff.Peer.MSS,cl,sl);e!=nil{return "",e}
        }
        // One selected ConnectivityManager Network, exact client source
        // interface/ifindex/MTU, applied BEFORE any Game RAW fd is opened.
        e=v4BindPlatformUnderlay(owner,V4LinuxClientProductConfig{
            NetworkInterface:p.cfg.NetworkInterface,
            NetworkIfIndex:p.cfg.NetworkIfIndex,
            AndroidPhysicalNetworkHandle:p.cfg.AndroidPhysicalNetworkHandle,
            AndroidPhysicalMTU:p.cfg.AndroidPhysicalMTU,
        })
        if e!=nil{return "",e}
    }
    verified,e:=V4LinuxGameClientVerifiedGroup(p.sessions...)
    if e!=nil{return "",e}
    p.verified=verified
    e=verified.withPrivateOriginalTLS(func(cold []V4ColdSessionSnapshot)error{
        if len(cold)!=int(p.cfg.Lanes){return ErrAdmissionUnsupported}
        ids:=make([]C.uint64_t,len(cold))
        for i,owner:=range p.owners{
            if owner==nil||owner.handle==0||!owner.committed||
                owner.stopped||owner.protectedLane!=uint8(i+1)||
                owner.protectedEpoch!=cold[i].Epoch()||
                owner.protectedFeatures!=cold[i].features||
                owner.authenticatedPrincipal!=cold[i].principal||
                owner.serverSide||cold[i].server{
                return ErrAdmissionUnsupported
            }
            phase,stateErr:=owner.state()
            if stateErr!=nil||phase!=2{return ErrAdmissionUnsupported}
            ids[i]=C.uint64_t(owner.handle)
        }
        var group C.uint64_t
        rc:=C.wbd_m0_embedded_go_game_group_join(
            &ids[0],C.size_t(len(ids)),0,&group)
        runtime.KeepAlive(ids)
        if rc!=0||group==0{
            return fmt.Errorf("%w: original authenticated Android Game2 group join=%d",
                errV4Embedded,int(rc))
        }
        p.native=uint64(group)
        return nil
    })
    if e!=nil{return "",e}
    if e=p.bindAndStartOriginalM4();e!=nil{return "",e}
    p.connected=true
    return lease,nil
}
func (p *V4AndroidGameProduct) bindAndStartOriginalM4()error{
    if p.native==0||p.verified==nil{return ErrAdmissionUnsupported}
    if rc:=C.wbd_m0_embedded_go_android_game_group_raw_bind(
        C.uint64_t(p.native));rc!=0{
        return fmt.Errorf("%w: selected-Network per-lane RAW bind=%d",errV4Embedded,int(rc))
    }
    var bound C.uint32_t
    rc:=C.wbd_m0_embedded_go_android_game_group_raw_state(
        C.uint64_t(p.native),&bound)
    if rc!=0||bound!=C.uint32_t(p.cfg.Lanes){
        return fmt.Errorf("%w: real Game2 two RAW lane readback=%d/%d",
            errV4Embedded,int(rc),uint32(bound))
    }
    name:=[]byte(p.cfg.TunName)
    dns:=C.uint32_t(0)
    if p.cfg.TunnelDNS{dns=1}
    physical:=C.uint32_t(0)
    if p.cfg.PhysicalDNS||len(p.cfg.CN8503Raw)>0{physical=1}
    upstream:=p.cfg.PhysicalDNSUpstream.As4()
    tunnelUpstream:=p.cfg.TunnelDNSUpstream
    if !tunnelUpstream.IsValid(){tunnelUpstream=netip.MustParseAddr("1.1.1.1")}
    if !tunnelUpstream.Is4(){return ErrAdmissionParams}
    tunnelRaw:=tunnelUpstream.As4()
    var cn *C.uchar
    if len(p.cfg.CN8503Raw)>0{
        cn=(*C.uchar)(unsafe.Pointer(&p.cfg.CN8503Raw[0]))
    }
    fec:=C.uint32_t(255) // off; 0..6 = original fixed Game FEC
    if p.cfg.GameFecEnabled{fec=C.uint32_t(p.cfg.GameFecProfile)}
    rc=C.wbd_m0_embedded_go_android_game_group_m4_start(
        C.uint64_t(p.native),C.int32_t(p.cfg.Tun.Fd()),
        (*C.uchar)(unsafe.Pointer(&name[0])),C.size_t(len(name)),
        dns,C.uint32_t(p.cfg.HealthSeconds),physical,
        (*C.uchar)(unsafe.Pointer(&upstream[0])),cn,
        C.size_t(len(p.cfg.CN8503Raw)),fec,(*C.uchar)(unsafe.Pointer(&tunnelRaw[0])))
    runtime.KeepAlive(tunnelRaw)
    runtime.KeepAlive(name)
    runtime.KeepAlive(upstream)
    runtime.KeepAlive(p.cfg.CN8503Raw)
    if rc!=0{
        return fmt.Errorf("%w: original Game2 Rust single-TUN/two-RAW M4=%d",
            errV4Embedded,int(rc))
    }
    lanes,ready,e:=p.OriginalNativeState()
    if e!=nil{return e}
    if lanes!=uint32(p.cfg.Lanes)||!ready{return ErrAdmissionUnsupported}
    return nil
}
// Readback reflects the ACTUAL Rust group worker state; TLS cold READY
// is never promoted into M4 success by this Go wrapper.
func (p *V4AndroidGameProduct) OriginalNativeState()(lanes uint32,ready bool,err error){
    if p==nil||p.native==0||p.stopped{return 0,false,ErrAdmissionUnsupported}
    var count,installed C.uint32_t
    rc:=C.wbd_m0_embedded_go_game_group_state(
        C.uint64_t(p.native),&count,&installed)
    if rc!=0{
        return 0,false,fmt.Errorf("%w: original Android Game2 M4 state=%d",errV4Embedded,int(rc))
    }
    return uint32(count),installed==1,nil
}
type V4AndroidGameCounters struct{
    RawCopied,RawReceived,TunDelivered,Rejected uint64
    TunnelDnsQueries,TunnelDnsReplies uint64
    PhysicalDnsQueries,PhysicalDnsReplies,PhysicalDnsErrors uint64
}
func (p *V4AndroidGameProduct) OriginalM4Counters()(V4AndroidGameCounters,error){
    if p==nil||p.native==0||p.stopped||!p.connected{
        return V4AndroidGameCounters{},ErrAdmissionUnsupported
    }
    var values [9]C.uint64_t
    rc:=C.wbd_m0_embedded_go_android_game_group_m4_counters(
        C.uint64_t(p.native),&values[0],9)
    if rc!=0{
        return V4AndroidGameCounters{},fmt.Errorf(
            "%w: original Android Game2 M4 counts=%d",errV4Embedded,int(rc))
    }
    return V4AndroidGameCounters{
        RawCopied:uint64(values[0]),RawReceived:uint64(values[1]),
        TunDelivered:uint64(values[2]),Rejected:uint64(values[3]),
        TunnelDnsQueries:uint64(values[4]),TunnelDnsReplies:uint64(values[5]),
        PhysicalDnsQueries:uint64(values[6]),PhysicalDnsReplies:uint64(values[7]),
        PhysicalDnsErrors:uint64(values[8]),
    },nil
}
// The existing Linux original FEC group readback ABI yields actual
// source/parity/kernel-copied/recovered candidate counters. Recovered
// candidate is NOT a verified App TUN delivery; M4 TunDelivered is separate.
type V4AndroidGameFecCounters struct{
    SourceOffered,ParityOffered,ParityKernelCopied uint64
    SourceCandidate,RecoveredCandidate,Expired,Failed uint64
    ParityPlanned,ParitySent,RetainedBytes uint64
}
func (p *V4AndroidGameProduct) OriginalGameFecCounters()(V4AndroidGameFecCounters,error){
    if p==nil||!p.cfg.GameFecEnabled||p.native==0||p.stopped||
        !p.connected{return V4AndroidGameFecCounters{},ErrAdmissionUnsupported}
    var values [16]C.uint64_t
    rc:=C.wbd_fec_network_game_group_counters(
        C.uint64_t(p.native),&values[0],C.size_t(len(values)))
    if rc!=0{return V4AndroidGameFecCounters{},
        fmt.Errorf("%w: original Android fixed Game FEC counters=%d",
            errV4Embedded,int(rc))}
    return V4AndroidGameFecCounters{
        SourceOffered:uint64(values[0]),ParityOffered:uint64(values[1]),
        ParityKernelCopied:uint64(values[2]),
        SourceCandidate:uint64(values[3]),RecoveredCandidate:uint64(values[4]),
        Expired:uint64(values[5]),Failed:uint64(values[6]),
        ParityPlanned:uint64(values[7]),ParitySent:uint64(values[8]),
        RetainedBytes:uint64(values[9]),
    },nil
}
func (p *V4AndroidGameProduct) AuthenticatedLeaseIPv4()(string,error){
    if p==nil||!p.connected||p.authenticatedLease==""||p.stopped{
        return "",ErrAdmissionUnsupported
    }
    return p.authenticatedLease,nil
}
// Group Stop joins the actual single-TUN/two-RAW M4 and all native
// driver borrows BEFORE original-Go per-lane M1 owner Release. A failed
// joined Stop never reports disconnect or revokes the owner prematurely.
func (p *V4AndroidGameProduct) stopLocked()error{
    if p.stopped{return nil}
    if p.native!=0{
        rc:=C.wbd_m0_embedded_go_game_group_stop(C.uint64_t(p.native))
        if rc!=0{
            return fmt.Errorf("%w: original Game2 group joined Stop=%d",
                errV4Embedded,int(rc))
        }
    }
    var failures error
    for _,owner:=range p.owners{
        if owner==nil||owner.handle==0{continue}
        _,e:=owner.StopAndReleaseOriginalOwner()
        failures=errors.Join(failures,e)
    }
    if failures!=nil{return failures}
    if p.native!=0{
        rc:=C.wbd_m0_embedded_go_game_group_release(C.uint64_t(p.native))
        if rc!=0{return fmt.Errorf("%w: original Game2 group Release=%d",
            errV4Embedded,int(rc))}
        p.native=0
    }
    if p.verified!=nil{
        if e:=p.verified.revoke();e!=nil{return e}
    }
    p.owners=nil
    p.connected=false
    p.stopped=true
    return nil
}
func (p *V4AndroidGameProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    return p.stopLocked()
}

// Stable low-rate NativeState monitoring can use this period; the Go
// product has no independent DATA/PTO/health loop at any point.
const V4AndroidGameStatusInterval=time.Second
