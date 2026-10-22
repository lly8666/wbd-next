//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

// Original-Go protected V4 CLIENT -> actual Rust role-bound generation with
// real M4 raw/TUN and joined continuous worker. The published legacy V3
// DialTunnelClient is deliberately untouched: it must never process V4
// ciphertext under a V3 owner. New FEC2/Game capability promotion requires
// separate actual native client parity/independent-lane owner integrations.
import (
    "context"
    "errors"
    "fmt"
    "net"
    "os"
    "sync"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4LinuxClientProductConfig struct {
    NetworkInterface string
    NetworkIfIndex uint32
    Tun *os.File
    TunName string
    CleanupOwnedNetwork func()error
    FECMode FecV2Mode
    FECProfile FecV2Profile
}
type V4LinuxClientProduct struct {
    mu sync.Mutex
    cfg V4LinuxClientProductConfig
    owner *v4EmbeddedNativeBridge
    session *V4ClientSession
    association *faketcp.ClientAssociation
    fec *v4ProductFecMonitor
    stopped bool
}
func NewV4LinuxClientProduct(cfg V4LinuxClientProductConfig)(*V4LinuxClientProduct,error){
    if cfg.Tun==nil||cfg.CleanupOwnedNetwork==nil||cfg.NetworkIfIndex==0||
       cfg.NetworkInterface==""||len(cfg.TunName)==0||len(cfg.TunName)>15{
        return nil,ErrAdmissionParams
    }
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||iface==nil||uint32(iface.Index)!=cfg.NetworkIfIndex{
        return nil,ErrAdmissionParams
    }
    if _,err:=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    if cfg.FECMode!=""&&cfg.FECMode!=FecV2Off&&
        !v4ProductFecEnabled(cfg.FECMode){return nil,ErrAdmissionUnsupported}
    if cfg.FECMode==FecV2Fixed&&!cfg.FECProfile.Valid(){return nil,ErrAdmissionParams}
    return &V4LinuxClientProduct{cfg:cfg},nil
}
// ConnectAuthenticatedPeer is the real TLS client public product half:
// original Go FakeTCP SYN/SYNACK must be established and receive handling
// active; only the verified V4 protected reply can install native keys.
// Exact original Go Detach, not a guessed TCP seq, grants the Rust generation.
// No test-only sender, cold fixture, or legacy V3 data plane is involved.
func (p *V4LinuxClientProduct) ConnectAuthenticatedPeer(
    ctx context.Context,assoc *faketcp.ClientAssociation,cfg ClientAdmissionConfig,
)(*V4ClientSession,error){
    if p==nil||assoc==nil{return nil,ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner!=nil||p.session!=nil||p.stopped{return nil,ErrAdmissionUnsupported}
    conn:=assoc.BootstrapConn()
    if conn==nil{return nil,ErrAdmissionParams}
    // One TLS exporter binds the requested FEC mode to the same
    // original-Go V4 Rust owner, never a legacy V3 separate FEC stream.
    mode:=p.cfg.FECMode
    if mode==""{mode=FecV2Off}
    wireMode:=FECOff
    if mode==FecV2Fixed{wireMode=FECFixed}
    if mode==FecV2Auto{wireMode=FECAuto}
    if cfg.Policy.Transport!=TransportNormal||
       cfg.Policy.FECMode!=wireMode||cfg.DesiredLanes!=1{
        return nil,ErrAdmissionUnsupported
    }
    session,err:=EstablishClientV4(ctx,conn,cfg,V4ClientOptions{
        DataPlaneReady:true,fec2Product:v4ProductFecEnabled(mode),
    })
    if err!=nil{return nil,err}
    cold,err:=session.ColdSnapshot()
    if err!=nil{return nil,err}
    if cold.ServerSide(){return nil,ErrAdmissionParams}
    handoff,err:=assoc.Detach()
    if err!=nil{return nil,err}
    bridge:=&v4EmbeddedNativeBridge{}
    if err=bridge.prepareAuthenticatedClient(session,handoff,assoc.Flow());err!=nil{
        return nil,fmt.Errorf("V4 genuine Go client TLS/native owner: %w",err)
    }
    p.owner=bridge
    p.session=session
    p.association=assoc
    if err=bridge.attachRawRxOnInterface(p.cfg.NetworkInterface,p.cfg.NetworkIfIndex);err==nil{
        err=bridge.attachKernelTun(p.cfg.Tun.Fd(),p.cfg.TunName)
    }
    if err==nil{
        p.fec,err=v4ConfigureProductFec(bridge,mode,p.cfg.FECProfile,cold)
    }
    if err==nil{err=bridge.armOriginalPublicM2Feedback()}
    if err==nil{err=bridge.startRustOwnerLoop(p.cfg.NetworkIfIndex)}
    if err!=nil{
        shutdown:=p.closeLocked()
        return nil,errors.Join(
            fmt.Errorf("V4 original Go client M4 raw/TUN worker start: %w",err),
            shutdown,
        )
    }
    if p.fec!=nil{p.fec.start(bridge)}
    return session,nil
}
func (p *V4LinuxClientProduct) OriginalFECReadback()(V4PublicFecReadback,error){
    if p==nil{return V4PublicFecReadback{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecReadback{},ErrAdmissionUnsupported}
    return p.fec.readback(p.owner)
}
// Real original Go TLS owner M2 wire counters before Stop. No GUI/CLI
// operator can forge these numbers; every metric comes from original Rust.
func (p *V4LinuxClientProduct) OriginalFecRxCounters()(V4PublicFecRxCounters,error){
    if p==nil{return V4PublicFecRxCounters{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecRxCounters{},ErrAdmissionUnsupported}
    return p.owner.originalPublicFecRxCounters()
}
func (p *V4LinuxClientProduct) OriginalOuterCounters()(V4PublicOuterCounters,error){
    if p==nil{return V4PublicOuterCounters{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicOuterCounters{},ErrAdmissionUnsupported}
    return p.owner.originalPublicOuterCounters()
}
func (p *V4LinuxClientProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    worker:=p.fec
    p.mu.Unlock()
    if worker!=nil{worker.stop()}
    p.mu.Lock()
    defer p.mu.Unlock()
    return p.closeLocked()
}
func (p *V4LinuxClientProduct) closeLocked()error{
    if p.stopped{return nil}
    if p.owner==nil||p.session==nil{return ErrAdmissionUnsupported}
    _,err:=V4StopThenCleanupNetwork(p.owner,p.cfg.CleanupOwnedNetwork)
    if err!=nil{return err}
    if p.association!=nil{p.association.Close()}
    p.stopped=true
    return nil
}
