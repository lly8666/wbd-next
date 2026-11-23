//go:build android && cgo && wbd_v4_embedded_go

package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_game_group_join(const uint64_t *,size_t,uint32_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_game_group_state(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_android_game_group_raw_bind(uint64_t);
extern int32_t wbd_m0_embedded_go_android_game_group_raw_state(uint64_t,uint32_t *);
extern int32_t wbd_m0_embedded_go_android_game_group_m4_start(uint64_t,int32_t,const unsigned char *,size_t,uint32_t,uint32_t);
extern int32_t wbd_m0_embedded_go_android_game_group_m4_counters(uint64_t,uint64_t *,size_t);
extern int32_t wbd_m0_embedded_go_game_group_stop(uint64_t);
extern int32_t wbd_m0_embedded_go_game_group_release(uint64_t);
*/
import "C"
import (
    "context"
    "errors"
    "fmt"
    "net"
    "os"
    "runtime"
    "sync"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// This is a real Android Go→Bionic Rust product boundary, not a second
// Linux Game kernel driver. Only Game2/off can be admitted at B41;
// Game4 and fixed Game FEC are deliberately unconnected.
type V4AndroidGame2Config struct{
    NetworkInterface string
    NetworkIfIndex uint32
    AndroidPhysicalNetworkHandle uint64
    AndroidPhysicalMTU uint32
    Tun *os.File
    TunName string
    ConfigureTunnelMTU func(peerMSS,clientLimit,serverLimit uint16)error
    ConfigureLeaseIPv4 func(string)error
    TunnelDNS bool
    HealthSeconds uint32
}
type V4AndroidGame2Product struct{
    mu sync.Mutex
    cfg V4AndroidGame2Config
    native uint64
    owners []*v4EmbeddedNativeBridge
    verified *V4LinuxGameVerifiedGroup
    sessions []*V4ClientSession
    authenticatedLease string
    stopped bool
    connected bool
}
func NewV4AndroidGame2Product(cfg V4AndroidGame2Config)(*V4AndroidGame2Product,error){
    if cfg.Tun==nil||cfg.ConfigureLeaseIPv4==nil||
        cfg.NetworkInterface==""||len(cfg.NetworkInterface)>15||
        cfg.NetworkIfIndex==0||cfg.AndroidPhysicalNetworkHandle==0||
        cfg.AndroidPhysicalMTU<576||cfg.AndroidPhysicalMTU>65535||
        cfg.TunName==""||len(cfg.TunName)>15||
        (cfg.HealthSeconds!=15&&cfg.HealthSeconds!=30){
        return nil,ErrAdmissionParams
    }
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||iface==nil||uint32(iface.Index)!=cfg.NetworkIfIndex||
        uint32(iface.MTU)!=cfg.AndroidPhysicalMTU{
        return nil,ErrAdmissionUnsupported
    }
    if _,err=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    return &V4AndroidGame2Product{cfg:cfg},nil
}
// ConnectAuthenticatedGame2 consumes genuine original-Go SYN/TLS session
// state, never caller-supplied cold-bundle bytes or mutable private crypto.
// The provided associations must already be real established FakeTCP peers.
func (p *V4AndroidGame2Product) ConnectAuthenticatedGame2(
    ctx context.Context,assocs []*faketcp.ClientAssociation,base ClientAdmissionConfig,
)(lease string,err error){
    if p==nil{return "",ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if p.connected||p.stopped||p.native!=0||len(p.owners)!=0||
       len(assocs)!=2||!base.AutoLease||
       base.DesiredLanes!=2||base.Policy.Transport!=TransportGame||
       base.Policy.DesiredLanes!=2||base.Policy.SupportedNow()!=nil{
        return "",ErrAdmissionUnsupported
    }
    defer func(){
        if err!=nil{
            err=errors.Join(err,p.stopLocked())
        }
    }()
    var epoch [16]byte
    for i,assoc:=range assocs{
        if assoc==nil||assoc.BootstrapConn()==nil{
            return "",ErrAdmissionParams
        }
        laneCfg:=base
        laneCfg.LaneID=uint8(i+1)
        // Same real Go TLS policy and exporter as Linux Game2/off.
        session,e:=EstablishClientV4(ctx,assoc.BootstrapConn(),laneCfg,V4ClientOptions{
            DataPlaneReady:true,Epoch:epoch,fec2Product:true,GameFec:0,
            StartupPadding:0,
        })
        if e!=nil{return "",e}
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
        if len(cold)!=2{return ErrAdmissionUnsupported}
        ids:=[2]C.uint64_t{}
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
func (p *V4AndroidGame2Product) bindAndStartOriginalM4()error{
    if p.native==0||p.verified==nil{return ErrAdmissionUnsupported}
    if rc:=C.wbd_m0_embedded_go_android_game_group_raw_bind(
        C.uint64_t(p.native));rc!=0{
        return fmt.Errorf("%w: selected-Network per-lane RAW bind=%d",errV4Embedded,int(rc))
    }
    var bound C.uint32_t
    rc:=C.wbd_m0_embedded_go_android_game_group_raw_state(
        C.uint64_t(p.native),&bound)
    if rc!=0||bound!=2{
        return fmt.Errorf("%w: real Game2 two RAW lane readback=%d/%d",
            errV4Embedded,int(rc),uint32(bound))
    }
    name:=[]byte(p.cfg.TunName)
    dns:=C.uint32_t(0)
    if p.cfg.TunnelDNS{dns=1}
    rc=C.wbd_m0_embedded_go_android_game_group_m4_start(
        C.uint64_t(p.native),C.int32_t(p.cfg.Tun.Fd()),
        (*C.uchar)(unsafe.Pointer(&name[0])),C.size_t(len(name)),
        dns,C.uint32_t(p.cfg.HealthSeconds))
    runtime.KeepAlive(name)
    if rc!=0{
        return fmt.Errorf("%w: original Game2 Rust single-TUN/two-RAW M4=%d",
            errV4Embedded,int(rc))
    }
    lanes,ready,e:=p.OriginalNativeState()
    if e!=nil{return e}
    if lanes!=2||!ready{return ErrAdmissionUnsupported}
    return nil
}
// Readback reflects the ACTUAL Rust group worker state; TLS cold READY
// is never promoted into M4 success by this Go wrapper.
func (p *V4AndroidGame2Product) OriginalNativeState()(lanes uint32,ready bool,err error){
    if p==nil||p.native==0||p.stopped{return 0,false,ErrAdmissionUnsupported}
    var count,installed C.uint32_t
    rc:=C.wbd_m0_embedded_go_game_group_state(
        C.uint64_t(p.native),&count,&installed)
    if rc!=0{
        return 0,false,fmt.Errorf("%w: original Android Game2 M4 state=%d",errV4Embedded,int(rc))
    }
    return uint32(count),installed==1,nil
}
type V4AndroidGame2Counters struct{
    RawCopied,RawReceived,TunDelivered,Rejected uint64
    TunnelDnsQueries,TunnelDnsReplies uint64
}
func (p *V4AndroidGame2Product) OriginalM4Counters()(V4AndroidGame2Counters,error){
    if p==nil||p.native==0||p.stopped||!p.connected{
        return V4AndroidGame2Counters{},ErrAdmissionUnsupported
    }
    var values [6]C.uint64_t
    rc:=C.wbd_m0_embedded_go_android_game_group_m4_counters(
        C.uint64_t(p.native),&values[0],6)
    if rc!=0{
        return V4AndroidGame2Counters{},fmt.Errorf(
            "%w: original Android Game2 M4 counts=%d",errV4Embedded,int(rc))
    }
    return V4AndroidGame2Counters{
        RawCopied:uint64(values[0]),RawReceived:uint64(values[1]),
        TunDelivered:uint64(values[2]),Rejected:uint64(values[3]),
        TunnelDnsQueries:uint64(values[4]),TunnelDnsReplies:uint64(values[5]),
    },nil
}
func (p *V4AndroidGame2Product) AuthenticatedLeaseIPv4()(string,error){
    if p==nil||!p.connected||p.authenticatedLease==""||p.stopped{
        return "",ErrAdmissionUnsupported
    }
    return p.authenticatedLease,nil
}
// Group Stop joins the actual single-TUN/two-RAW M4 and all native
// driver borrows BEFORE original-Go per-lane M1 owner Release. A failed
// joined Stop never reports disconnect or revokes the owner prematurely.
func (p *V4AndroidGame2Product) stopLocked()error{
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
func (p *V4AndroidGame2Product) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    return p.stopLocked()
}

// Stable low-rate NativeState monitoring can use this period; the Go
// product has no independent DATA/PTO/health loop at any point.
const V4AndroidGame2StatusInterval=time.Second
