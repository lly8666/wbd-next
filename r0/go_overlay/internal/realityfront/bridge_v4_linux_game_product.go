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
    SharedTun *V4LinuxSharedTun // verified server /32 or client default, one TUN reader across Game generations
    CleanupOwnedNetwork func()error
    ConfigureTunnelMTU func(peerMSS,clientLimit,serverLimit uint16)error
    ConfigureLeaseIPv4 func(lease string)error // apply once before Game group Rust M4 start
    Authenticate func(username,password string)bool // server account roster
    ServerManualLease4 string // trusted server /32; original cold TLS only
    Epochs *V4EpochStore // mandatory only for actual server group
    GameFecEnabled bool // explicit BOTH-endpoint fixed FEC, never Auto
    GameFecProfile uint8 // 0..6; only used when GameFecEnabled
    DisableOuterRepair bool // Game M4 first copy only, no Normal M2 DATA repair
    Game4CopyStagger bool // pre-start 4-lane delayed physical copies
    Game4CopyWideStagger bool // longer opt-in T0+50ms/+140ms tail
    PeerPersona V4PublicNativePeerPersona // original-Go server only
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
    if cfg.Game4CopyWideStagger&&!cfg.Game4CopyStagger{return nil,ErrAdmissionParams}
    // Game4 fixed FEC is explicitly allowed with the default stagger;
    // native per-group profile and copy schedule are both installed before M4.
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
func (p *V4LinuxGameProduct) MatchesProtectedGameFec(fec uint8)bool{
    if p==nil{return false}
    p.mu.Lock();defer p.mu.Unlock()
    expected:=uint8(0)
    if p.cfg.GameFecEnabled{expected=p.cfg.GameFecProfile+1}
    return !p.stopped&&p.connected&&fec==expected
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
        mode:=uint32(1)
        if p.cfg.Game4CopyWideStagger{mode=2}
        if err=p.native.configureGame4CopyStagger(mode);err!=nil{return err}
    }
    if err=p.native.configureOuterRepair(!p.cfg.DisableOuterRepair);err!=nil{return err}
    if p.server{
        if err=p.native.configurePeerPersona(p.cfg.PeerPersona);err!=nil{return err}
    }
    // The same original Rust single-reader demux is valid for client Game:
    // client default route changes by generation only AFTER new M4 Ready.
    // Server retains exact authenticated destination-/32 dispatch.
    if p.cfg.SharedTun!=nil{
        if err=p.native.bindAuthenticatedSharedTun(p.cfg.SharedTun);err!=nil{return err}
    }
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
    var effectiveLease string
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
        if base.AutoLease{
            lease,leaseErr:=session.AuthenticatedLeaseIPv4()
            if leaseErr!=nil||lease==""||p.cfg.ConfigureLeaseIPv4==nil{
                return errors.Join(ErrAdmissionParams,leaseErr,p.abortLocked())
            }
            if i==0{
                effectiveLease=lease
                if err:=p.cfg.ConfigureLeaseIPv4(lease);err!=nil{
                    return errors.Join(err,p.abortLocked())
                }
            }else if lease!=effectiveLease{
                return errors.Join(ErrAdmissionParams,p.abortLocked())
            }
            // Client Game shared-TUN default route is authenticated only
            // after the original TLS-assigned /32 has been OS-applied and
            // read back. The Rust M4 group join then sees identical verified
            // source lease on every lane; no mutable client IP can select it.
            if err:=bridge.bindAuthenticatedClientIPv4(lease);err!=nil{
                return errors.Join(err,p.abortLocked())
            }
        }
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
// The same principal/tunnel/epoch/record protection remains authoritative
// while just ONE physical TLS/AEAD lane changes. Neither an untrusted SYN
// tuple nor a new Go-side cohort can change which Rust M4 slot is updated.
func sameOriginalGameLaneHotIdentity(old,next V4ColdSessionSnapshot,lane uint8)bool{
    return lane>=1&&lane<=4&&old.server==next.server&&
        old.laneID==lane&&next.laneID==lane&&
        old.principal==next.principal&&old.tunnelID==next.tunnelID&&
        old.epoch==next.epoch&&old.features==next.features&&
        old.cipher==next.cipher&&old.clientLimit==next.clientLimit&&
        old.serverLimit==next.serverLimit&&
        old.incarnation!=next.incarnation&&
        old.keys.C2S!=next.keys.C2S&&old.keys.S2C!=next.keys.S2C
}

// A failed candidate original TLS handshake has not taken the current
// GameAdapter, kernel socket, or the selected old lane's owner. It is
// correct to keep all four live and try another cold association later.
// NEVER tag native-M4-commit/old-Stop uncertainty with this sentinel.
var ErrV4GameLaneUncommittedCold=errors.New("Game4 new TLS lane failed before native M4 commit")

// Fresh original TLS for lane N occurs on a new genuine FakeTCP association.
// Its authenticated epoch MUST equal the one still owned by the other three
// Game4 lanes. Rust swaps the selected M4 RX/AEAD/PN worker on success.
func (p *V4LinuxGameProduct) ReplaceClientGameLane(
    ctx context.Context,a *faketcp.ClientAssociation,
    base ClientAdmissionConfig,lane uint8,
)error{
    if p==nil||p.server||ctx==nil||a==nil||lane<1||lane>4{
        return ErrAdmissionParams
    }
    p.mu.Lock();defer p.mu.Unlock()
    if p.stopped||!p.connected||p.native==nil||
        len(p.clientSessions)!=4||len(p.bridges)!=4||
        !validGameGroupPolicy(base.Policy,4)||base.DesiredLanes!=4{
        return ErrAdmissionUnsupported
    }
    i:=int(lane)-1
    previous:=p.clientSessions[i]
    old,e:=previous.ColdSnapshot()
    if e!=nil{return e}
    base.LaneID=lane
    fec:=uint8(0)
    if p.cfg.GameFecEnabled{fec=p.cfg.GameFecProfile+1}
    next,e:=EstablishClientV4(ctx,a.BootstrapConn(),base,V4ClientOptions{
        DataPlaneReady:true,Epoch:previous.Epoch,fec2Product:true,GameFec:fec,
    })
    if e!=nil{return fmt.Errorf("%w: %w",ErrV4GameLaneUncommittedCold,e)}
    cold,e:=next.ColdSnapshot()
    if e!=nil||!sameOriginalGameLaneHotIdentity(old,cold,lane){
        return errors.Join(ErrAdmissionParams,e)
    }
    handoff,e:=a.Detach()
    if e!=nil{return e}
    bridge:=&v4EmbeddedNativeBridge{}
    if e=bridge.prepareAuthenticatedClient(next,handoff,a.Flow());e!=nil{
        return e
    }
    abort:=func(err error)error{
        if _,stopErr:=bridge.StopAndReleaseOriginalOwner();stopErr!=nil{
            return errors.Join(err,stopErr)
        }
        return err
    }
    if base.AutoLease{
        lease,e:=next.AuthenticatedLeaseIPv4()
        previousLease,pErr:=previous.AuthenticatedLeaseIPv4()
        if e!=nil||pErr!=nil||lease==""||lease!=previousLease{
            return abort(errors.Join(ErrAdmissionParams,e,pErr))
        }
        if e=bridge.bindAuthenticatedClientIPv4(lease);e!=nil{return abort(e)}
    }
    oldBridge,e:=p.native.replaceAuthenticatedOriginalLane(lane,bridge)
    if e!=nil{return abort(e)}
    // New Rust M4 has acknowledged its original selected-slot driver
    // replacement. Publish Go pointer only now; other slots stay unchanged.
    p.clientSessions[i]=next
    p.bridges[i]=bridge
    if _,e=oldBridge.StopAndReleaseOriginalOwner();e!=nil{return e}
    return nil
}
// Authenticated Game cohort identity is available ONLY after original Go
// credential TLS and Rust private Prepare/Commit. This struct is never
// constructed from a SYN, source address, TCP port, or client-controlled
// plaintext. All fields are read-only outside realityfront.
type V4LinuxGameCohortID struct{
    Principal string
    TunnelID [16]byte
    Epoch [16]byte
    Lanes uint8
}

// One protected original TLS lane is temporarily held by the cold server
// dispatcher until n complete members of the SAME cohort are available.
// Ownership then moves exactly once into V4LinuxGameProduct (whose Close
// joins original Rust M4 before releasing the OS-backed epoch).
type V4LinuxGameAuthenticatedLane struct{
    session *V4ServerSession
    bridge *v4EmbeddedNativeBridge
    assoc *faketcp.ServerAssociation
    peerMSS uint16
    epochs *V4EpochStore
    transferred bool
}
func (l *V4LinuxGameAuthenticatedLane) Cohort()(
    V4LinuxGameCohortID,uint8,error,
){
    var zero V4LinuxGameCohortID
    if l==nil||l.session==nil||l.bridge==nil{return zero,0,ErrAdmissionParams}
    cold,err:=l.session.ColdSnapshot()
    if err!=nil{return zero,0,err}
    n:=int(l.session.verifiedPolicy.DesiredLanes)
    if !validGameGroupPolicy(l.session.verifiedPolicy,n)||
        cold.LaneID()==0||int(cold.LaneID())>n{
        return zero,0,ErrAdmissionUnsupported
    }
    return V4LinuxGameCohortID{
        Principal:cold.Principal(),TunnelID:cold.TunnelID(),
        Epoch:cold.Epoch(),Lanes:uint8(n),
    },cold.LaneID(),nil
}
// The client's ORIGINAL offered epoch is already inside credential-verified
// protected TLS. A ZERO request starts a full fresh Game group, including
// same-IP/MTU recovery after an old Game4 group dies. A nonzero request
// carries an explicit old group epoch for a one-lane hot reauth. This is
// only available after Rust M1 Commit + frozen cold snapshot validation;
// never trust the TCP port or a new unprotected flag as cohort authority.
func (l *V4LinuxGameAuthenticatedLane) ProtectedFreshGroupRequested()(bool,error){
    if l==nil||l.session==nil||l.bridge==nil{return false,ErrAdmissionParams}
    if _,err:=l.session.ColdSnapshot();err!=nil{return false,err}
    return l.session.verifiedRequestedFreshEpoch,nil
}

// Expose ONLY original authenticated Go record sizes to the one server
// cohort router. The TLS-derived AEAD keys, epoch randomizer and M1 owner
// remain private; an untrusted source-IP packet cannot mint this witness.
func (l *V4LinuxGameAuthenticatedLane) AuthenticatedRecordLimits()(uint16,uint16,error){
    if l==nil||l.session==nil||l.bridge==nil{return 0,0,ErrAdmissionParams}
    cold,e:=l.session.ColdSnapshot()
    if e!=nil{return 0,0,e}
    cl,sl:=cold.RecordLimits()
    if cl==0||sl==0{return 0,0,ErrAdmissionParams}
    return cl,sl,nil
}
// ProtectedMode is valid only after original TLS credential validation,
// epoch reservation and Rust M1 Prepare/Commit. It is NOT a plaintext
// discovery mechanism. Game profile is protected byte21 (+1), Normal fixed
// strength is protected byte22 and is read by its original product owner.
func (l *V4LinuxGameAuthenticatedLane) ProtectedMode()(normal bool,lanes uint8,gameFec uint8,err error){
    if l==nil||l.session==nil||l.bridge==nil{return false,0,0,ErrAdmissionParams}
    if _,err=l.session.ColdSnapshot();err!=nil{return false,0,0,err}
    policy:=l.session.verifiedPolicy
    if err=policy.SupportedNow();err!=nil{return false,0,0,err}
    switch policy.Transport{
    case TransportNormal:
        if policy.DesiredLanes!=1||l.session.verifiedGameFec!=0{
            return false,0,0,ErrAdmissionUnsupported
        }
        return true,1,0,nil
    case TransportGame:
        if (policy.DesiredLanes!=2&&policy.DesiredLanes!=4)||
            l.session.verifiedNormalFec!=0{
            return false,0,0,ErrAdmissionUnsupported
        }
        return false,policy.DesiredLanes,l.session.verifiedGameFec,nil
    default:
        return false,0,0,ErrAdmissionUnsupported
    }
}

// V4AuthenticateLinuxMixedServerLane is the sole original TLS entrypoint for
// a shared 443 listener. Credential-verified request policy chooses Normal
// versus Game2/Game4 AFTER TLS; no first-packet mode hint, second listener,
// untrusted SYN routing or new steady-state record format.
func V4AuthenticateLinuxMixedServerLane(
    ctx context.Context,assoc *faketcp.ServerAssociation,
    base ServerAdmissionConfig,cfg V4LinuxGameProductConfig,
)(*V4LinuxGameAuthenticatedLane,error){
    if assoc==nil||ctx==nil||cfg.Epochs==nil||cfg.SharedTun==nil{
        return nil,ErrAdmissionParams
    }
    priorAllow:=base.PolicyAllow
    priorValidate:=base.ValidateRequest
    base.PolicyAllow=func(policy AdmissionPolicy)error{
        if err:=policy.SupportedNow();err!=nil{return err}
        switch policy.Transport{
        case TransportNormal:
            if _,err:=v4ProtectedNormalFECFeatures(policy);err!=nil{return err}
        case TransportGame:
            if !validGameGroupPolicy(policy,int(policy.DesiredLanes)){
                return ErrAdmissionUnsupported
            }
        default:return ErrAdmissionUnsupported
        }
        if priorAllow!=nil{return priorAllow(policy)}
        return nil
    }
    base.ValidateRequest=func(req AdmissionRequest)error{
        if !req.AutoLease||len(req.TunnelID)!=16{return ErrAdmissionParams}
        if req.Policy.Transport==TransportGame{
            if err:=v4ServerGameProtectedLaneRequest(req,int(req.DesiredLanes));err!=nil{
                return err
            }
        }else if req.Policy.Transport!=TransportNormal||
            req.DesiredLanes!=1||req.LaneID!=1{
            return ErrAdmissionUnsupported
        }
        if priorValidate!=nil{return priorValidate(req)}
        return nil
    }
    bridge:=&v4EmbeddedNativeBridge{}
    session,err:=EstablishServerV4(ctx,assoc,base,V4ServerOptions{
        DataPlaneReady:true,Epochs:cfg.Epochs,ownerBridge:bridge,
        fec2Product:true,perClientMixedMode:true,
        Authenticate:cfg.Authenticate,AllowLaneReplacement:true,
    })
    if err!=nil{return nil,err}
    lane:=&V4LinuxGameAuthenticatedLane{
        session:session,bridge:bridge,assoc:assoc,
        peerMSS:assoc.PeerTCPProfile().MSS,epochs:cfg.Epochs,
    }
    normal,_,_,err:=lane.ProtectedMode()
    if err==nil&&!normal{_,_,err=lane.Cohort()}
    if err!=nil{return nil,errors.Join(err,lane.Close())}
    return lane,nil
}

// NormalOwnerKey excludes the epoch intentionally: a new authenticated
// generation replaces only this principal+tunnel's Normal owner. Exact
// incarnation and generation are still used by Rust/Go Stop internally.
func (l *V4LinuxGameAuthenticatedLane) NormalOwnerKey()(V4LinuxGameCohortID,error){
    var zero V4LinuxGameCohortID
    normal,_,_,err:=l.ProtectedMode()
    if err!=nil{return zero,err}
    if !normal{return zero,ErrAdmissionUnsupported}
    snap,err:=l.session.ColdSnapshot()
    if err!=nil{return zero,err}
    return V4LinuxGameCohortID{
        Principal:snap.Principal(),TunnelID:snap.TunnelID(),Lanes:1,
    },nil
}
func (l *V4LinuxGameAuthenticatedLane) DetachedPeer()(faketcp.DetachedPeer,error){
    if l==nil||l.assoc==nil{return faketcp.DetachedPeer{},ErrAdmissionParams}
    state,ok:=l.assoc.TransitionState()
    if !ok||state!=faketcp.TransitionDetached{return faketcp.DetachedPeer{},ErrAdmissionUnsupported}
    flow:=l.assoc.Flow()
    return faketcp.DetachedPeer{IP:flow.ClientIP,Port:flow.ClientPort},nil
}
func (l *V4LinuxGameAuthenticatedLane) Association()*faketcp.ServerAssociation{
    if l==nil{return nil}
    return l.assoc
}
func (l *V4LinuxGameAuthenticatedLane) Close()error{
    if l==nil||l.transferred{return nil}
    // Revoke the sole authenticated cold lane, not its sibling's Rust group.
    var err error
    if l.bridge!=nil&&l.bridge.handle!=0&&!l.bridge.stopped{
        _,err=l.bridge.StopAndReleaseOriginalOwner()
        if err!=nil{return err}
    }
    if l.epochs!=nil&&l.session!=nil{
        cold,e:=l.session.ColdSnapshot()
        if e!=nil{return errors.Join(err,e)}
        tunnel:=cold.TunnelID()
        if e=l.epochs.ReleaseLaneInstance(
            cold.Principal(),tunnel[:],cold.LaneID(),
            cold.Epoch(),cold.Incarnation(),
        );e!=nil{return errors.Join(err,e)}
    }
    l.transferred=true
    return err
}

// Cold one-association TLS may run concurrently for every 443 flow; TLS
// completions are grouped only by the authenticated immutable cohort key.
// This is a separate API from the original single-group legacy method.
func V4AuthenticateLinuxGameServerLane(
    ctx context.Context,assoc *faketcp.ServerAssociation,
    base ServerAdmissionConfig,cfg V4LinuxGameProductConfig,n int,
)(*V4LinuxGameAuthenticatedLane,error){
    if assoc==nil||ctx==nil||cfg.Epochs==nil||(n!=2&&n!=4){
        return nil,ErrAdmissionParams
    }
    allow:=base.PolicyAllow
    validate:=base.ValidateRequest
    base.PolicyAllow=func(policy AdmissionPolicy)error{
        if !validGameGroupPolicy(policy,n){return ErrAdmissionUnsupported}
        if allow!=nil{return allow(policy)}
        return nil
    }
    base.ValidateRequest=func(req AdmissionRequest)error{
        if err:=v4ServerGameProtectedLaneRequest(req,n);err!=nil{return err}
        if validate!=nil{return validate(req)}
        return nil
    }
    gameFec:=uint8(0)
    if cfg.GameFecEnabled{gameFec=cfg.GameFecProfile+1}
    bridge:=&v4EmbeddedNativeBridge{}
    session,err:=EstablishServerV4(ctx,assoc,base,V4ServerOptions{
        DataPlaneReady:true,Epochs:cfg.Epochs,
        ownerBridge:bridge,fec2Product:true,GameFec:gameFec,
        Authenticate:cfg.Authenticate,AllowLaneReplacement:cfg.SharedTun!=nil,
        ManualLease4:cfg.ServerManualLease4,
    })
    if err!=nil{return nil,err}
    lane:=&V4LinuxGameAuthenticatedLane{
        session:session,bridge:bridge,assoc:assoc,
        peerMSS:assoc.PeerTCPProfile().MSS,epochs:cfg.Epochs,
    }
    if _,_,err=lane.Cohort();err!=nil{
        return nil,errors.Join(err,lane.Close())
    }
    return lane,nil
}

// The complete cohort has already independently authenticated on each
// physical FakeTCP flow. Take ALL original lanes or none. Before sharing
// a TUN or publishing any Game Ready, enforce every original Go verified
// lane identity, policy, incarnation and independent exporter key.
func (p *V4LinuxGameProduct) AdoptServerGameLanes(
    members []*V4LinuxGameAuthenticatedLane,
)error{
    if p==nil||!p.server{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    n:=len(members)
    if p.stopped||p.connected||len(p.bridges)>0||(n!=2&&n!=4){
        return ErrAdmissionUnsupported
    }
    seen:=make(map[*V4LinuxGameAuthenticatedLane]bool,n)
    var cohort V4LinuxGameCohortID
    for i,l:=range members{
        if l==nil||l.transferred||seen[l]{return ErrAdmissionParams}
        seen[l]=true
        id,_,err:=l.Cohort()
        if err!=nil{return err}
        if i==0{cohort=id}else if id!=cohort{return ErrAdmissionParams}
    }
    for _,l:=range members{
        p.serverSessions=append(p.serverSessions,l.session)
        p.bridges=append(p.bridges,l.bridge)
        l.transferred=true
    }
    order,err:=v4GameServerTLSArrivalOrder(p.serverSessions)
    if err!=nil{return errors.Join(err,p.abortLocked())}
    sessions:=make([]*V4ServerSession,n)
    bridges:=make([]*v4EmbeddedNativeBridge,n)
    mss:=make([]uint16,n)
    for lane,arrival:=range order{
        sessions[lane]=p.serverSessions[arrival]
        bridges[lane]=p.bridges[arrival]
        mss[lane]=members[arrival].peerMSS
    }
    p.serverSessions=sessions
    p.bridges=bridges
    // No group can mutate a sibling's TUN: AUTO multi-group config has
    // no per-group ConfigureTunnelMTU and the shared device is Go-owned.
    for i,session:=range p.serverSessions{
        lease,e:=session.AuthenticatedLeaseIPv4()
        if e!=nil{return errors.Join(e,p.abortLocked())}
        if p.cfg.SharedTun!=nil&&lease==""{
            return errors.Join(ErrAdmissionParams,p.abortLocked())
        }
        if lease!=""{
            if e=p.bridges[i].bindAuthenticatedClientIPv4(lease);e!=nil{
                return errors.Join(e,p.abortLocked())
            }
        }
        if p.cfg.ConfigureTunnelMTU!=nil{
            cold,e:=session.ColdSnapshot()
            if e!=nil{return errors.Join(e,p.abortLocked())}
            cl,sl:=cold.RecordLimits()
            if e=p.cfg.ConfigureTunnelMTU(mss[i],cl,sl);e!=nil{
                return errors.Join(e,p.abortLocked())
            }
        }
    }
    if err=p.commitGroupedOwnerLocked();err!=nil{
        return errors.Join(err,p.abortLocked())
    }
    return nil
}

// A server may receive ONE authenticated successor lane with SAME cohort
// epoch while the other three original TLS lanes remain active. No complete
// cohort is re-admitted and no second Rust FEC/first-delivery owner exists.
func (p *V4LinuxGameProduct) ReplaceServerGameLane(
    member *V4LinuxGameAuthenticatedLane,lane uint8,
)error{
    if p==nil||!p.server||member==nil||member.transferred||
        lane<1||lane>4{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if p.stopped||!p.connected||p.native==nil||
        len(p.serverSessions)!=4||len(p.bridges)!=4{
        return ErrAdmissionUnsupported
    }
    idx:=int(lane)-1
    oldSession:=p.serverSessions[idx]
    old,e:=oldSession.ColdSnapshot()
    if e!=nil{return e}
    cold,e:=member.session.ColdSnapshot()
    if e!=nil||!sameOriginalGameLaneHotIdentity(old,cold,lane)||
        member.session.verifiedGameFec!=oldSession.verifiedGameFec||
        !validGameGroupPolicy(member.session.verifiedPolicy,4){
        return errors.Join(ErrAdmissionParams,e)
    }
    oldLease,e:=oldSession.AuthenticatedLeaseIPv4()
    newLease,leaseErr:=member.session.AuthenticatedLeaseIPv4()
    if e!=nil||leaseErr!=nil||oldLease!=newLease||
        (p.cfg.SharedTun!=nil&&newLease==""){
        return errors.Join(ErrAdmissionParams,e,leaseErr)
    }
    if newLease!=""{
        if e=member.bridge.bindAuthenticatedClientIPv4(newLease);e!=nil{return e}
    }
    oldBridge,e:=p.native.replaceAuthenticatedOriginalLane(lane,member.bridge)
    if e!=nil{return e}
    member.transferred=true
    p.serverSessions[idx]=member.session
    p.bridges[idx]=member.bridge
    if _,e=oldBridge.StopAndReleaseOriginalOwner();e!=nil{return e}
    // Release only exact former incarnation. The epoch store's matching
    // incarnation fence must preserve the just-installed successor.
    if p.cfg.Epochs!=nil{
        if e=p.cfg.Epochs.ReleaseLaneInstance(
            old.principal,old.tunnelID[:],old.laneID,old.epoch,
            old.incarnation,
        );e!=nil{return e}
    }
    return nil
}
// The n original Go FakeTCP associations can arrive in ANY SYN order. The
// client's protected TLS runs lane1..laneN sequentially, so processing the
// server TLS in SYN arrival order can deadlock and wrongly bind lane IDs.
// Admit all n finite cold flows concurrently, then sort by verified TLS lane.
// No Go steady-state packet reader, new transport or wire field is created.
func (p *V4LinuxGameProduct) AcceptServerGame(
    ctx context.Context,associations []*faketcp.ServerAssociation,
    base ServerAdmissionConfig,
)error{
    if p==nil||!p.server||ctx==nil{return ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    n:=len(associations)
    if p.stopped||p.connected||len(p.bridges)!=0||(n!=2&&n!=4){
        return ErrAdmissionUnsupported
    }
    seen:=make(map[*faketcp.ServerAssociation]struct{},n)
    for _,a:=range associations{
        if a==nil{return errors.Join(ErrAdmissionParams,p.abortLocked())}
        if _,ok:=seen[a];ok{return errors.Join(ErrAdmissionParams,p.abortLocked())}
        seen[a]=struct{}{}
    }
    allow:=base.PolicyAllow
    validate:=base.ValidateRequest
    protectedPolicy:=func(policy AdmissionPolicy)error{
        if !validGameGroupPolicy(policy,n){return ErrAdmissionUnsupported}
        if allow!=nil{return allow(policy)}
        return nil
    }
    protectedRequest:=func(req AdmissionRequest)error{
        // Invoked only AFTER credential-checked TLS inside EstablishServerV4.
        // TCP SYN arrival position is never an authentication authority.
        if err:=v4ServerGameProtectedLaneRequest(req,n);err!=nil{return err}
        if validate!=nil{return validate(req)}
        return nil
    }
    type admission struct{
        session *V4ServerSession
        bridge *v4EmbeddedNativeBridge
        peerMSS uint16
        err error
    }
    replies:=make(chan admission,n)
    coldCtx,cancel:=context.WithCancel(ctx)
    defer cancel()
    for _,assoc:=range associations{
        go func(a *faketcp.ServerAssociation){
            cfg:=base
            cfg.PolicyAllow=protectedPolicy
            cfg.ValidateRequest=protectedRequest
            bridge:=&v4EmbeddedNativeBridge{}
            gameFec:=uint8(0)
            if p.cfg.GameFecEnabled{gameFec=p.cfg.GameFecProfile+1}
            session,err:=EstablishServerV4(coldCtx,a,cfg,V4ServerOptions{
                DataPlaneReady:true,Epochs:p.cfg.Epochs,
                ownerBridge:bridge,fec2Product:true,GameFec:gameFec,
                Authenticate:p.cfg.Authenticate,
            })
            replies<-admission{session:session,bridge:bridge,
                peerMSS:a.PeerTCPProfile().MSS,err:err}
        }(assoc)
    }
    peerMSS:=make([]uint16,0,n)
    var tlsErr error
    // Wait for EVERY cold task before a failed group's native Stop.
    // An in-flight TLS must not publish a Rust owner after cleanup.
    for i:=0;i<n;i++{
        accepted:=<-replies
        if accepted.err!=nil&&tlsErr==nil{
            tlsErr=accepted.err
            cancel()
        }
        if accepted.session!=nil{
            p.serverSessions=append(p.serverSessions,accepted.session)
            p.bridges=append(p.bridges,accepted.bridge)
            peerMSS=append(peerMSS,accepted.peerMSS)
        }
    }
    if tlsErr!=nil{return errors.Join(tlsErr,p.abortLocked())}
    // Enforce account/tunnel/epoch/policy, distinct per-lane exporter keys,
    // and complete 1..n lane set BEFORE any shared-TUN MTU or lease writes.
    order,err:=v4GameServerTLSArrivalOrder(p.serverSessions)
    if err!=nil{return errors.Join(err,p.abortLocked())}
    sessions:=make([]*V4ServerSession,n)
    bridges:=make([]*v4EmbeddedNativeBridge,n)
    mss:=make([]uint16,n)
    for lane,arrival:=range order{
        sessions[lane]=p.serverSessions[arrival]
        bridges[lane]=p.bridges[arrival]
        mss[lane]=peerMSS[arrival]
    }
    p.serverSessions=sessions
    p.bridges=bridges
    for i,session:=range p.serverSessions{
        assigned,leaseErr:=session.AuthenticatedLeaseIPv4()
        if leaseErr!=nil{return errors.Join(leaseErr,p.abortLocked())}
        if assigned!=""{
            if leaseErr=p.bridges[i].bindAuthenticatedClientIPv4(assigned);leaseErr!=nil{
                return errors.Join(leaseErr,p.abortLocked())
            }
        }
        if p.cfg.ConfigureTunnelMTU!=nil{
            cold,e:=session.ColdSnapshot()
            if e!=nil{return errors.Join(e,p.abortLocked())}
            cl,sl:=cold.RecordLimits()
            if e=p.cfg.ConfigureTunnelMTU(mss[i],cl,sl);e!=nil{
                return errors.Join(e,p.abortLocked())
            }
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
// H1281 client-only: prove the candidate's remote grouped Game2/4 M4
// actually delivered an authenticated reverse IPv4 packet before replacing
// A's shared-TUN default route. Rust enforces the counter and publication.
func (p *V4LinuxGameProduct) PromoteGameAfterAuthenticatedPeerRx()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil||p.server{
        return ErrAdmissionUnsupported
    }
    return p.native.promoteSharedTunAfterAuthenticatedRx()
}
// A Game server's replacement B may not steal A's /32 on local M4
// START. The underlying Rust group must have authenticated client B's
// own post-M4-start Health; exact shared-TUN publication is server-only.
func (p *V4LinuxGameProduct) PromoteServerGameAfterAuthenticatedClientRx()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil||!p.server{
        return ErrAdmissionUnsupported
    }
    return p.native.promoteServerSharedTunAfterAuthenticatedClientHealth()
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
// An already authenticated group has ONE existing Rust Game M4 Health90
// verdict. Polling this cold readback cannot change the cryptographic
// owner or authorize any new packet; the caller must still perform exact
// group Stop and native drain before releasing its authenticated /32.
func (p *V4LinuxGameProduct) NativeM4Alive()(bool,error){
    if p==nil{return false,ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if !p.connected||p.stopped||p.native==nil{
        return false,ErrAdmissionUnsupported
    }
    return p.native.originalM4Alive()
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
            if err:=p.cfg.Epochs.ReleaseLaneInstance(
                cold.principal,cold.tunnelID[:],cold.laneID,cold.epoch,cold.incarnation,
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
