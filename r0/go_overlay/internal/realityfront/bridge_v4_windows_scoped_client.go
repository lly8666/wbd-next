//go:build windows && wbd_v4_embedded_go
package realityfront

// M0-facing typed Windows client credential TLS -> authentic M1/M3 Rust
// ProtectedScopedOwner -> SAME-process M4-created Wintun Hold lifetime API.
// It intentionally has NO product Connected/WFP/route/DNS grant. The M4
// product owns its separate native OS transaction and all network cleanup.
import (
    "context"
    "errors"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4WindowsScopedOwnerReadback struct {
    Generation uint32
    ServerSide bool
    OwnerActive bool
    DeviceBound bool
    DeviceQuiesced bool
    ProductApplied bool
}
type V4WindowsAuthenticatedClientOwner struct{
    bridge *v4WindowsNativeOwnerBridge
    device *v4WindowsRealDeviceLease
}
// Only the original FakeTCP + credential protected TLS handshake can create
// the private bridge token: no struct with caller supplied cold/WBGH fields.
func V4WindowsEstablishOriginalClientOwner(
    ctx context.Context,library string,assoc *faketcp.ClientAssociation,
    cfg ClientAdmissionConfig,
)(*V4WindowsAuthenticatedClientOwner,*V4ClientSession,error){
    if ctx==nil||assoc==nil{return nil,nil,ErrAdmissionParams}
    native,err:=newV4WindowsPrivateOwnerBridge(library)
    if err!=nil{return nil,nil,err}
    result,err:=native.connectVerifiedClient(ctx,assoc,cfg)
    if err!=nil{return nil,nil,err}
    state,err:=native.state()
    if err!=nil||state.phase!=2||state.applied!=0||
        state.generation==0||state.server!=0{return nil,nil,errV4WindowsOwner}
    return &V4WindowsAuthenticatedClientOwner{bridge:native},result,nil
}
// BindOriginalM4NativeDevice requires the actual external native M4 holder;
// a token may never be rebound to another OS adapter or newer TLS epoch.
// A successful device binding remains scoped, not a product Apply signal.
func(s *V4WindowsAuthenticatedClientOwner) BindOriginalM4NativeDevice(
    ctx context.Context,device V4WindowsCurrentNativeDevice,
    id V4WindowsNativeDeviceIdentity,
)error{
    if s==nil||s.bridge==nil||s.device!=nil{return errV4WindowsOwner}
    held,err:=s.bridge.holdOriginalCreatedWintun(ctx,device,id)
    if held!=nil{s.device=held}
    return err
}
func(s *V4WindowsAuthenticatedClientOwner) OriginalOwnerReadback()(V4WindowsScopedOwnerReadback,error){
    var out V4WindowsScopedOwnerReadback
    if s==nil||s.bridge==nil{return out,errV4WindowsOwner}
    state,err:=s.bridge.state()
    if err!=nil{return out,err}
    dev,err:=s.bridge.realNativeDeviceState()
    if err!=nil{return out,err}
    if dev.Applied!=0{return out,errV4WindowsOwner}
    return V4WindowsScopedOwnerReadback{
        Generation:state.generation,ServerSide:false,OwnerActive:state.phase==2,
        DeviceBound:dev.Bound==1,DeviceQuiesced:dev.Quiesced==1,
        ProductApplied:false,
    },nil
}
// This only stops Rust M1/M3 after an M4-held CURRENT created Wintun has
// separately quiesced (or without any device binding at all). It cannot be
// promoted to V4OriginalOwnerStopper's "OwnerAndDriversDrained" product
// completion, because real WFP/routes and their WAL are M4's responsibility.
func(s *V4WindowsAuthenticatedClientOwner) StopScopedOwner(ctx context.Context)error{
    if s==nil||s.bridge==nil||ctx==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if s.device!=nil{
        if err:=s.device.quiesceAndStopRustOnly(ctx);err!=nil{return err}
        return nil
    }
    return s.bridge.stopRustOwnerOnly()
}
func(s *V4WindowsAuthenticatedClientOwner) StopAndReleaseOriginalOwner()(
    V4OwnerStopCompletion,error,
){
    // Explicit rejection prevents M4 network cleanup being ordered after
    // merely an M0 Rust crypto owner without real native M4 kernel drivers
    // and CAS-proven OS WFP/route ownership.
    return V4OwnerStopCompletion{},errors.Join(errV4WindowsOwner,ErrAdmissionUnsupported)
}
