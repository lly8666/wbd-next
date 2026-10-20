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
}
type V4LinuxClientProduct struct {
    mu sync.Mutex
    cfg V4LinuxClientProductConfig
    owner *v4EmbeddedNativeBridge
    session *V4ClientSession
    association *faketcp.ClientAssociation
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
    // Strict runtime feature3 Normal/off until the separate Rust FEC2
    // source/repair and Game2/4 lane groups are bound to the native client.
    if cfg.Policy.Transport!=TransportNormal||cfg.Policy.FECMode!=FECOff||
       cfg.DesiredLanes!=1{
        return nil,ErrAdmissionUnsupported
    }
    session,err:=EstablishClientV4(ctx,conn,cfg,V4ClientOptions{DataPlaneReady:true})
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
    if err==nil{err=bridge.startRustOwnerLoop(p.cfg.NetworkIfIndex)}
    if err!=nil{
        shutdown:=p.closeLocked()
        return nil,errors.Join(
            fmt.Errorf("V4 original Go client M4 raw/TUN worker start: %w",err),
            shutdown,
        )
    }
    return session,nil
}
func (p *V4LinuxClientProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
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
