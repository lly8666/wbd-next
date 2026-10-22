//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

// V4 Linux original-Go server's NON-TEST protected-TLS -> Rust owner -> real
// M4 raw/TUN lifecycle. No caller may install a raw cold bundle or forge
// DataPlaneReady: ownerBridge is filled only INSIDE the verified admission.
// This is a server-side integration component. A public Go CLI and symmetric
// V4 client runtime are still required before declaring a released product.
import (
    "context"
    "errors"
    "fmt"
    "net"
    "os"
    "sync"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// V4LinuxServerProductConfig must be constructed from the running server's
// actual original Go FakeTCP association and its owned OS network resources.
// The original Go caller retains the TUN fd; Rust duplicates it under the
// credential-bound generation. Cleanup is called ONLY after Rust Stop drains
// both M4 drivers, pending slab loans and owner worker threads.
type V4LinuxServerProductConfig struct {
    Epochs *V4EpochStore
    NetworkInterface string
    NetworkIfIndex uint32
    Tun *os.File
    TunName string
    CleanupOwnedNetwork func()error
    FECMode FecV2Mode
    FECProfile FecV2Profile
}
type V4LinuxServerProduct struct {
    mu sync.Mutex
    cfg V4LinuxServerProductConfig
    owner *v4EmbeddedNativeBridge
    session *V4ServerSession
    fec *v4ProductFecMonitor
    // Immutable TLS identity survives caller mutation of the result view.
    principal string
    tunnel [16]byte
    lane uint8
    epoch [16]byte
    stopped bool
}
// NewV4LinuxServerProduct requires the real kernel device, rather than a
// loopback hardcoded developer test path. It does not grant any session before
// credential-protected EstablishServerV4 succeeds on a real association.
func NewV4LinuxServerProduct(cfg V4LinuxServerProductConfig)(*V4LinuxServerProduct,error){
    if cfg.Epochs==nil||cfg.Tun==nil||cfg.CleanupOwnedNetwork==nil||
       cfg.NetworkIfIndex==0||cfg.NetworkInterface==""||len(cfg.TunName)==0||
       len(cfg.TunName)>15 {
        return nil,ErrAdmissionParams
    }
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||uint32(iface.Index)!=cfg.NetworkIfIndex{
        return nil,ErrAdmissionParams
    }
    if _,err:=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    if cfg.FECMode!=""&&cfg.FECMode!=FecV2Off&&
        !v4ProductFecEnabled(cfg.FECMode){return nil,ErrAdmissionUnsupported}
    if cfg.FECMode==FecV2Fixed&&!cfg.FECProfile.Valid(){return nil,ErrAdmissionParams}
    return &V4LinuxServerProduct{cfg:cfg},nil
}

// AcceptAuthenticatedPeer is the REAL original Go TLS admission, detach,
// exact FakeTCP transition, Rust M1/M3 owner Commit, actual M4 raw/TUN attach
// and continuous native worker start. Never call on a candidate that has not
// passed the original Go FakeTCP recognized/credential authentication.
func (p *V4LinuxServerProduct) AcceptAuthenticatedPeer(
    ctx context.Context,assoc *faketcp.ServerAssociation,cfg ServerAdmissionConfig,
)(*V4ServerSession,error){
    if p==nil||assoc==nil{return nil,ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner!=nil||p.session!=nil||p.stopped{return nil,ErrAdmissionUnsupported}
    mode:=p.cfg.FECMode
    if mode==""{mode=FecV2Off}
    expectedWireMode:=FECOff
    if mode==FecV2Fixed{expectedWireMode=FECFixed}
    if mode==FecV2Auto{expectedWireMode=FECAuto}
    priorPolicyAllow:=cfg.PolicyAllow
    cfg.PolicyAllow=func(policy AdmissionPolicy)error{
        if policy.Transport!=TransportNormal||policy.FECMode!=expectedWireMode||
            policy.DesiredLanes!=1 {
            return ErrAdmissionUnsupported
        }
        if priorPolicyAllow!=nil{return priorPolicyAllow(policy)}
        return nil
    }
    bridge:=&v4EmbeddedNativeBridge{}
    session,err:=EstablishServerV4(ctx,assoc,cfg,V4ServerOptions{
        DataPlaneReady:true,Epochs:p.cfg.Epochs,ownerBridge:bridge,
        fec2Product:v4ProductFecEnabled(mode),
    })
    if err!=nil{return nil,err}
    // From this point the original Go server has detached the authenticated
    // association and committed the Rust owner. Any driver/start error must
    // first Stop/release Rust; no system route/TUN cleanup can race that Stop.
    p.owner=bridge
    p.session=session
    // Freeze original authenticated source *before* returning any exported
    // mutable AdmissionResult or allowing Stop concurrently.
    verified,verifyErr:=session.ColdSnapshot()
    if verifyErr!=nil{
        shutdown:=p.closeLocked()
        return nil,errors.Join(verifyErr,shutdown)
    }
    p.principal=verified.Principal()
    p.tunnel=verified.TunnelID()
    p.lane=verified.LaneID()
    p.epoch=verified.Epoch()
    if err=bridge.attachRawRxOnInterface(
        p.cfg.NetworkInterface,p.cfg.NetworkIfIndex,
    );err==nil{
        err=bridge.attachKernelTun(p.cfg.Tun.Fd(),p.cfg.TunName)
    }
    if err==nil{
        p.fec,err=v4ConfigureProductFec(bridge,mode,p.cfg.FECProfile,verified)
    }
    if err==nil{err=bridge.armOriginalPublicM2Feedback()}
    if err==nil{err=bridge.startRustOwnerLoop(p.cfg.NetworkIfIndex)}
    if err!=nil{
        shutdown:=p.closeLocked()
        return nil,errors.Join(
            fmt.Errorf("V4 genuine Go TLS/Rust M4 driver start: %w",err),
            shutdown,
        )
    }
    if p.fec!=nil{p.fec.start(bridge)}
    return session,nil
}
func (p *V4LinuxServerProduct) OriginalFECReadback()(V4PublicFecReadback,error){
    if p==nil{return V4PublicFecReadback{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecReadback{},ErrAdmissionUnsupported}
    return p.fec.readback(p.owner)
}

// Close returns ONLY after original Rust has stopped its packet workers,
// drained M1/M4 outstanding borrows and released the generation; THEN the
// externally owned Go kernel/WAL/route/TUN cleanup runs, THEN the protected
// Go logical lane epoch may be reused. Errors remain retryable.
// Real original Go TLS owner M2 wire counters before Stop. No GUI/CLI
// operator can forge these numbers; every metric comes from original Rust.
func (p *V4LinuxServerProduct) OriginalFecRxCounters()(V4PublicFecRxCounters,error){
    if p==nil{return V4PublicFecRxCounters{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecRxCounters{},ErrAdmissionUnsupported}
    return p.owner.originalPublicFecRxCounters()
}
func (p *V4LinuxServerProduct) OriginalOuterCounters()(V4PublicOuterCounters,error){
    if p==nil{return V4PublicOuterCounters{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicOuterCounters{},ErrAdmissionUnsupported}
    return p.owner.originalPublicOuterCounters()
}
func (p *V4LinuxServerProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    worker:=p.fec
    p.mu.Unlock()
    if worker!=nil{worker.stop()}
    p.mu.Lock()
    defer p.mu.Unlock()
    return p.closeLocked()
}
func (p *V4LinuxServerProduct) closeLocked()error{
    if p.stopped{return nil}
    if p.owner==nil||p.session==nil{return ErrAdmissionUnsupported}
    _,err:=V4StopThenCleanupNetwork(p.owner,p.cfg.CleanupOwnedNetwork)
    if err!=nil{return err}
    if p.principal==""||p.epoch==[16]byte{}||p.lane==0 {
        return ErrAdmissionParams
    }
    if err=p.cfg.Epochs.ReleaseLane(
        p.principal,p.tunnel[:],p.lane,p.epoch,
    );err!=nil{return err}
    p.stopped=true
    return nil
}
