//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

// Immutable original-Go protected TLS Game2/4 *admission group*.
// This proves only an authenticated grouped input for one native owner.
// It does NOT create another Rust crypto path or claim M4 is installed.
import (
    "errors"
    "sync"
)

type V4GamePublicGroupIdentity struct {
    Lanes uint8
    Epoch [16]byte
    TunnelID [16]byte
    Principal string
    Features uint16
}

// V4LinuxGameVerifiedGroup can be made only from live original TLS sessions
// whose cold snapshots survive post-TLS mutable-view tampering checks.
// There is deliberately no cold-byte constructor nor DataPlaneReady switch.
type V4LinuxGameVerifiedGroup struct {
    mu sync.Mutex
    id V4GamePublicGroupIdentity
    cold []V4ColdSessionSnapshot
    stopped bool
}

func newV4LinuxGameVerifiedGroup(
    snapshots []V4ColdSessionSnapshot, policies []AdmissionPolicy, server bool,
)(*V4LinuxGameVerifiedGroup,error){
    ordered,err:=v4CheckAuthenticatedGameLanes(snapshots,policies,server)
    if err!=nil{return nil,err}
    if len(ordered)!=2&&len(ordered)!=4{return nil,ErrAdmissionUnsupported}
    if ordered[0].features!=(v4RequiredFeatures|v4FeatureFEC2){
        // Private native FEC record support is required in currently frozen
        // GameAdapter. This checks same-session feature only; not native ON.
        return nil,ErrAdmissionUnsupported
    }
    id:=V4GamePublicGroupIdentity{
        Lanes:uint8(len(ordered)),Epoch:ordered[0].epoch,
        TunnelID:ordered[0].tunnelID,Principal:ordered[0].principal,
        Features:ordered[0].features,
    }
    return &V4LinuxGameVerifiedGroup{id:id,cold:ordered},nil
}
func V4LinuxGameClientVerifiedGroup(sessions ...*V4ClientSession)(
    *V4LinuxGameVerifiedGroup,error,
){
    if len(sessions)!=2&&len(sessions)!=4{return nil,ErrAdmissionParams}
    snapshots:=make([]V4ColdSessionSnapshot,0,len(sessions))
    policies:=make([]AdmissionPolicy,0,len(sessions))
    for _,s:=range sessions{
        if s==nil{return nil,ErrAdmissionUnsupported}
        cold,err:=s.ColdSnapshot()
        if err!=nil{return nil,err}
        snapshots=append(snapshots,cold)
        policies=append(policies,s.verifiedPolicy)
    }
    return newV4LinuxGameVerifiedGroup(snapshots,policies,false)
}
func V4LinuxGameServerVerifiedGroup(sessions ...*V4ServerSession)(
    *V4LinuxGameVerifiedGroup,error,
){
    if len(sessions)!=2&&len(sessions)!=4{return nil,ErrAdmissionParams}
    snapshots:=make([]V4ColdSessionSnapshot,0,len(sessions))
    policies:=make([]AdmissionPolicy,0,len(sessions))
    for _,s:=range sessions{
        if s==nil{return nil,ErrAdmissionUnsupported}
        cold,err:=s.ColdSnapshot()
        if err!=nil{return nil,err}
        snapshots=append(snapshots,cold)
        policies=append(policies,s.verifiedPolicy)
    }
    return newV4LinuxGameVerifiedGroup(snapshots,policies,true)
}
func (g *V4LinuxGameVerifiedGroup) OriginalTLSIdentity()(
    V4GamePublicGroupIdentity,error,
){
    if g==nil{return V4GamePublicGroupIdentity{},ErrAdmissionParams}
    g.mu.Lock();defer g.mu.Unlock()
    if g.stopped{return V4GamePublicGroupIdentity{},ErrAdmissionUnsupported}
    return g.id,nil
}
// Package-private one-shot callback is where M0 connects a *real* native M4
// group. This routine never publishes raw keys to CLI/UI or arbitrary cold.
// Copies are only valid for this synchronous trusted original-Go callback.
func (g *V4LinuxGameVerifiedGroup) withPrivateOriginalTLS(
    fn func([]V4ColdSessionSnapshot)error,
)error{
    if g==nil||fn==nil{return ErrAdmissionParams}
    g.mu.Lock();defer g.mu.Unlock()
    if g.stopped||len(g.cold)!=int(g.id.Lanes){return ErrAdmissionUnsupported}
    snapshot:=append([]V4ColdSessionSnapshot(nil),g.cold...)
    // Fail-closed callback until the actual M0 C owner reports installed.
    return fn(snapshot)
}
// Revoke the group input after partial admission failure or actual native
// Stop; this does not report native Stop success by itself.
func (g *V4LinuxGameVerifiedGroup) revoke()error{
    if g==nil{return ErrAdmissionParams}
    g.mu.Lock();defer g.mu.Unlock()
    if g.stopped{return nil}
    if len(g.cold)==0{return errors.New("empty Game owner grant")}
    for i:=range g.cold{g.cold[i]=V4ColdSessionSnapshot{}}
    g.cold=nil
    g.stopped=true
    return nil
}
