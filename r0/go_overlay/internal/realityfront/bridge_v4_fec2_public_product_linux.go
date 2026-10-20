//go:build linux && cgo && wbd_v4_embedded_go
package realityfront

// One FEC2 product policy owner per ORIGINAL credential-protected Go V4
// TLS client/direction/epoch. Normal/off never creates this object.
// This is not a second M2 controller, alternate data sender, or test-only
// APPLIED: only original Rust M1/M3/M4 actual kernel source+parity and mature
// authenticated opposite-direction kind1 can publish fixed/auto startup ACK.
import (
    "sync"
    "time"
)

type V4PublicFecReadback struct {
    Mode FecV2Mode
    RequestedRevision uint64
    AppliedRevision uint64
    Profile FecV2Profile
    Pending bool
}
type v4ProductFecMonitor struct {
    epoch [16]byte
    state FecV2State
    stopCh chan struct{}
    doneCh chan struct{}
    once sync.Once
    started bool
}
func v4ProductFecEnabled(mode FecV2Mode)bool{
    return mode==FecV2Fixed||mode==FecV2Auto
}
func v4ConfigureProductFec(
    bridge *v4EmbeddedNativeBridge,mode FecV2Mode,
    profile FecV2Profile,authenticated V4ColdSessionSnapshot,
)(*v4ProductFecMonitor,error){
    if !v4ProductFecEnabled(mode){return nil,nil}
    if mode==FecV2Auto{profile=FecV2Strong}
    if !profile.Valid()||authenticated.Epoch()==[16]byte{}{
        return nil,ErrAdmissionParams
    }
    direction:=FecV2C2S
    if authenticated.ServerSide(){direction=FecV2S2C}
    cfg:=FecV2Config{
        Client:authenticated.Principal(),Direction:direction,
        Transport:FecV2Normal,Mode:mode,Profile:profile,
        AutoPolicy:FecV2Conservative,ConfigRevision:1,
    }
    state,ack,err:=bridge.stageOriginalFixedPending(
        cfg,FecV2State{},authenticated.Epoch(),
    )
    if err!=nil{return nil,err}
    if ack.Rejected||ack.Applied||ack.Revision!=1||!state.Initialized{
        return nil,ErrAdmissionUnsupported
    }
    return &v4ProductFecMonitor{
        epoch:authenticated.Epoch(),state:state,
        stopCh:make(chan struct{}),doneCh:make(chan struct{}),
    },nil
}
func (m *v4ProductFecMonitor)start(bridge *v4EmbeddedNativeBridge){
    if m==nil{return}
    m.started=true
    go func(){
        defer close(m.doneCh)
        ticker:=time.NewTicker(200*time.Millisecond)
        defer ticker.Stop()
        for{
            select{
            case <-m.stopCh:return
            case <-ticker.C:
                // NO positive transition until mature 2s observed first
                // sends, real source and parity copied by M4, original
                // M3 opposite-direction verified kind1, same epoch/revision.
                if v4PublicMatureFixedNative(
                    bridge,m.epoch,m.state.RequestedRevision,
                )==nil{return}
            }
        }
    }()
}
func (m *v4ProductFecMonitor)stop(){
    if m==nil{return}
    m.once.Do(func(){close(m.stopCh)})
    if m.started{<-m.doneCh}
}
func (m *v4ProductFecMonitor)readback(
    bridge *v4EmbeddedNativeBridge,
)(V4PublicFecReadback,error){
    var out V4PublicFecReadback
    if m==nil{return out,ErrAdmissionUnsupported}
    next,_,err:=bridge.readbackOriginalFixedPending(m.state,m.epoch)
    if err!=nil{return out,err}
    return V4PublicFecReadback{
        Mode:next.Mode,RequestedRevision:next.RequestedRevision,
        AppliedRevision:next.AppliedRevision,Profile:next.Desired,
        Pending:next.AppliedRevision!=next.RequestedRevision,
    },nil
}
