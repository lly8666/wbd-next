//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront

// Real original-Go V4 Game2/4 grouped product. TLS credentials and FakeTCP
// Detach are performed by the original Go implementations on EACH transport
// lane; one native GameAdapter owns shared first-delivery, independent PN,
// actual M4 kernel packet workers and all Stop borrows. Never route to V3.
import (
    "context"
    "errors"
    "fmt"
    "net"
    "os"
    "sync"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

type V4LinuxGameProductConfig struct {
    NetworkInterface string
    NetworkIfIndex uint32
    Tun *os.File
    TunName string
    CleanupOwnedNetwork func()error
    ConfigureTunnelMTU func(peerMSS,clientLimit,serverLimit uint16)error
    Epochs *V4EpochStore // mandatory only for actual server group
    GameFecEnabled bool // explicit BOTH-endpoint fixed FEC, never Auto
    GameFecProfile uint8 // 0..6; only used when GameFecEnabled
    DisableOuterRepair bool // Game M4 first copy only, no Normal M2 DATA repair
    Game4CopyStagger bool // explicit opt-in only FEC OFF
}
type V4LinuxGameProduct struct{
    mu sync.Mutex
    cfg V4LinuxGameProductConfig
    server bool
    native *v4NativeGameJoined
    bridges []*v4EmbeddedNativeBridge
    clientSessions []*V4ClientSession
    serverSessions []*V4ServerSession
    game *V4LinuxGameVerifiedGroup
    stopped bool
    connected bool
}
func newV4LinuxGameProduct(cfg V4LinuxGameProductConfig,server bool)(*V4LinuxGameProduct,error){
    if cfg.GameFecEnabled&&cfg.GameFecProfile>6{return nil,ErrAdmissionParams}
    if cfg.Game4CopyStagger&&cfg.GameFecEnabled{return nil,ErrAdmissionUnsupported}
    if cfg.NetworkInterface==""||cfg.NetworkIfIndex==0||cfg.Tun==nil||
       cfg.TunName==""||len(cfg.TunName)>15||cfg.CleanupOwnedNetwork==nil||
       (server&&cfg.Epochs==nil){return nil,ErrAdmissionParams}
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||iface==nil||uint32(iface.Index)!=cfg.NetworkIfIndex{
        return nil,ErrAdmissionParams
    }
    if _,err:=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    return &V4LinuxGameProduct{cfg:cfg,server:server},nil
}
func NewV4LinuxGameClientProduct(cfg V4LinuxGameProductConfig)(*V4LinuxGameProduct,error){
    return newV4LinuxGameProduct(cfg,false)
}
func NewV4LinuxGameServerProduct(cfg V4LinuxGameProductConfig)(*V4LinuxGameProduct,error){
    return newV4LinuxGameProduct(cfg,true)
}
func validGameGroupPolicy(p AdmissionPolicy,n int)bool{
    return (n==2||n==4)&&p.Schema==PolicySchemaV3&&
        p.Transport==TransportGame&&p.DesiredLanes==uint8(n)&&
        p.SupportedNow()==nil
}
func (p *V4LinuxGameProduct) commitGroupedOwnerLocked()error{
    var err error
    if p.server{
        p.game,err=V4LinuxGameServerVerifiedGroup(p.serverSessions...)
    }else{
        p.game,err=V4LinuxGameClientVerifiedGroup(p.clientSessions...)
    }
    if err!=nil{return err}
    p.native,err=p.game.joinAuthenticatedOriginalRust(p.bridges...)
    if err!=nil{return err}
    if p.cfg.GameFecEnabled{
        if err=p.native.configureFixedFEC(p.cfg.GameFecProfile);err!=nil{return err}
    }
    if p.cfg.Game4CopyStagger{
        if len(p.bridges)!=4{return ErrAdmissionUnsupported}
        if err=p.native.configureGame4CopyStagger();err!=nil{return err}
    }
    if err=p.native.configureOuterRepair(!p.cfg.DisableOuterRepair);err!=nil{return err}
    if err=p.native.startNativeM4(
        p.cfg.NetworkInterface,p.cfg.NetworkIfIndex,p.cfg.Tun,p.cfg.TunName,
    );err!=nil{return err}
    count,installed,err:=p.native.originalCryptoState()
    if err!=nil{return err}
    if !installed||int(count)!=len(p.bridges){return ErrAdmissionUnsupported}
    p.connected=true
    return nil
}
// ConnectClientGame authenticates 2/4 REAL original Go TLS/FakeTCP peers
// with one unchanged logical epoch and 2/4 independent local wire ports.
func (p *V4LinuxGameProduct) ConnectClientGame(
    ctx context.Context,associations []*faketcp.ClientAssociation,
    base ClientAdmissionConfig,
)error{
    if p==nil||p.server{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    n:=len(associations)
    if p.stopped||p.connected||len(p.bridges)!=0||
       !validGameGroupPolicy(base.Policy,n)||int(base.DesiredLanes)!=n{
        return ErrAdmissionUnsupported
    }
    var epoch [16]byte
    for i,a:=range associations{
        if a==nil||a.BootstrapConn()==nil{
            return errors.Join(ErrAdmissionParams,p.abortLocked())
        }
        cfg:=base;cfg.LaneID=uint8(i+1)
        gameFec:=uint8(0)
        if p.cfg.GameFecEnabled{gameFec=p.cfg.GameFecProfile+1}
        session,e:=EstablishClientV4(ctx,a.BootstrapConn(),cfg,V4ClientOptions{
            DataPlaneReady:true,Epoch:epoch,fec2Product:true,GameFec:gameFec,
        })
        if e!=nil{return errors.Join(e,p.abortLocked())}
        if i==0{epoch=session.Epoch}
        handoff,e:=a.Detach()
        if e!=nil{return errors.Join(e,p.abortLocked())}
        bridge:=&v4EmbeddedNativeBridge{}
        if e=bridge.prepareAuthenticatedClient(session,handoff,a.Flow());e!=nil{
            return errors.Join(fmt.Errorf("Game lane%d client Rust=%w",i+1,e),p.abortLocked())
        }
        p.clientSessions=append(p.clientSessions,session)
        p.bridges=append(p.bridges,bridge)
        if p.cfg.ConfigureTunnelMTU!=nil {
            cold,err:=session.ColdSnapshot()
            if err!=nil{return errors.Join(err,p.abortLocked())}
            cl,sl:=cold.RecordLimits()
            if err=p.cfg.ConfigureTunnelMTU(handoff.Peer.MSS,cl,sl);err!=nil{return errors.Join(err,p.abortLocked())}
        }
    }
    if err:=p.commitGroupedOwnerLocked();err!=nil{
        return errors.Join(err,p.abortLocked())
    }
    return nil
}
// AcceptServerGame consumes already established real Go FakeTCP associations.
// The only accepted original TLS request matches the same exact group lane
// policy; a rogue independently authenticated V4 Normal lane cannot join.
func (p *V4LinuxGameProduct) AcceptServerGame(
    ctx context.Context,associations []*faketcp.ServerAssociation,
    base ServerAdmissionConfig,
)error{
    if p==nil||!p.server{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    n:=len(associations)
    if p.stopped||p.connected||len(p.bridges)!=0||(n!=2&&n!=4){
        return ErrAdmissionUnsupported
    }
    for i,a:=range associations{
        if a==nil{return errors.Join(ErrAdmissionParams,p.abortLocked())}
        id:=uint8(i+1)
        cfg:=base
        allow:=base.PolicyAllow
        validate:=base.ValidateRequest
        cfg.PolicyAllow=func(policy AdmissionPolicy)error{
            if !validGameGroupPolicy(policy,n){return ErrAdmissionUnsupported}
            if allow!=nil{return allow(policy)}
            return nil
        }
        cfg.ValidateRequest=func(req AdmissionRequest)error{
            if req.LaneID!=id||req.DesiredLanes!=uint8(n){
                return ErrAdmissionUnsupported
            }
            if validate!=nil{return validate(req)}
            return nil
        }
        bridge:=&v4EmbeddedNativeBridge{}
        gameFec:=uint8(0)
        if p.cfg.GameFecEnabled{gameFec=p.cfg.GameFecProfile+1}
        session,e:=EstablishServerV4(ctx,a,cfg,V4ServerOptions{
            DataPlaneReady:true,Epochs:p.cfg.Epochs,
            ownerBridge:bridge,fec2Product:true,GameFec:gameFec,
        })
        if e!=nil{return errors.Join(e,p.abortLocked())}
        p.serverSessions=append(p.serverSessions,session)
        p.bridges=append(p.bridges,bridge)
        if p.cfg.ConfigureTunnelMTU!=nil {
            cold,err:=session.ColdSnapshot()
            if err!=nil{return errors.Join(err,p.abortLocked())}
            cl,sl:=cold.RecordLimits()
            if err=p.cfg.ConfigureTunnelMTU(a.PeerTCPProfile().MSS,cl,sl);err!=nil{return errors.Join(err,p.abortLocked())}
        }
    }
    if err:=p.commitGroupedOwnerLocked();err!=nil{
        return errors.Join(err,p.abortLocked())
    }
    return nil
}
func (p *V4LinuxGameProduct) CopyScheduleRead()([21]uint64,error){
    var empty [21]uint64
    if p==nil{return empty,ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil||len(p.bridges)!=4{
        return empty,ErrAdmissionUnsupported
    }
    return p.native.copyScheduleRead()
}
func (p *V4LinuxGameProduct) OuterPolicy()(V4GameOuterPolicy,error){
    if p==nil{return V4GameOuterPolicy{},ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil{
        return V4GameOuterPolicy{},ErrAdmissionUnsupported
    }
    policy,err:=p.native.originalGameOuterPolicy()
    if err!=nil{return policy,err}
    if policy.RepairEnabled==p.cfg.DisableOuterRepair{
        return V4GameOuterPolicy{},ErrAdmissionUnsupported
    }
    if p.cfg.DisableOuterRepair&&policy.DataRetransmitted!=0{
        return V4GameOuterPolicy{},ErrAdmissionUnsupported
    }
    return policy,nil
}
func (p *V4LinuxGameProduct) KernelCounters()(V4GameKernelCounters,error){
    if p==nil{return V4GameKernelCounters{},ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil{
        return V4GameKernelCounters{},ErrAdmissionUnsupported
    }
    return p.native.originalM4Counters()
}
// Genuine M3/M4 post-driver counters, only valid for explicit Game fixed FEC.
func (p *V4LinuxGameProduct) FecCounters()(V4GameFecCounters,error){
    if p==nil{return V4GameFecCounters{},ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil||!p.cfg.GameFecEnabled{
        return V4GameFecCounters{},ErrAdmissionUnsupported
    }
    return p.native.originalGameFecCounters()
}
func (p *V4LinuxGameProduct) Connected()bool{
    if p==nil{return false}
    p.mu.Lock();defer p.mu.Unlock()
    return p.connected&&!p.stopped&&p.native!=nil
}
func (p *V4LinuxGameProduct) abortLocked()error{
    // This is also the normal joined native Stop. Original native drivers
    // must join BEFORE TUN Go FD or epoch cleanup. A failed Stop preserves
    // caller's owned network and refuses a false Disconnect.
    if p.native!=nil{
        if err:=p.native.stopOriginalOwners();err!=nil{return err}
    }else{
        for _,bridge:=range p.bridges{
            if bridge==nil||bridge.handle==0||bridge.stopped{continue}
            if _,err:=bridge.StopAndReleaseOriginalOwner();err!=nil{return err}
        }
        if p.game!=nil{if err:=p.game.revoke();err!=nil{return err}}
    }
    if err:=p.cfg.CleanupOwnedNetwork();err!=nil{return err}
    if p.server{
        for _,session:=range p.serverSessions{
            cold,e:=session.ColdSnapshot()
            if e!=nil{return e}
            if err:=p.cfg.Epochs.ReleaseLane(
                cold.principal,cold.tunnelID[:],cold.laneID,cold.epoch,
            );err!=nil{return err}
        }
    }
    p.connected=false;p.stopped=true
    return nil
}
func (p *V4LinuxGameProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if p.stopped{return nil}
    return p.abortLocked()
}
