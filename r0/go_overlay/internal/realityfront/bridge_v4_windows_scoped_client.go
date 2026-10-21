//go:build windows && wbd_v4_embedded_go
package realityfront

// M0-facing typed Windows client credential TLS -> authentic M1/M3 Rust
// ProtectedScopedOwner -> SAME-process M4-created Wintun Hold lifetime API.
// It intentionally has NO product Connected/WFP/route/DNS grant. The M4
// product owns its separate native OS transaction and all network cleanup.
import (
    "context"
    "errors"
    "runtime"
    "unsafe"

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

// SealBoundOriginalNormalOff is callable only AFTER original-Go verified
// credential TLS, successful Rust commit and the same live M4-created native
// Wintun Hold. It asks the SAME Rust M1 owner for a single immutable M3 AEAD
// record. This makes NO assertion that any OS UDP packet was sent yet.
func (s *V4WindowsAuthenticatedClientOwner) SealBoundOriginalNormalOff(
    ctx context.Context,ipv4 []byte,
)([]byte,uint32,uint64,error){
    if ctx==nil||s==nil||s.bridge==nil||s.device==nil||
        s.bridge.sealNormalProc==nil||len(ipv4)<20||len(ipv4)>512||
        ipv4[0]>>4!=4{
        return nil,0,0,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,0,0,err}
    if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    owner,err:=s.OriginalOwnerReadback()
    if err!=nil||!owner.OwnerActive||!owner.DeviceBound||
        owner.DeviceQuiesced||owner.ProductApplied{
        return nil,0,0,errV4WindowsOwner
    }
    // 31 is the original M3 fixed on-wire record overhead. The v3 Rust
    // authority also computes its own conservative 576B budget and rejects
    // oversize data before consuming a PN.
    wire:=make([]byte,len(ipv4)+31)
    var used uintptr
    var seq uint32
    var pn uint64
    err=winOwnerCall(s.bridge.sealNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&used)),
        uintptr(unsafe.Pointer(&seq)),uintptr(unsafe.Pointer(&pn)),
    )
    runtime.KeepAlive(ipv4)
    runtime.KeepAlive(wire)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used!=uintptr(len(wire)){
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    return wire,seq,pn,nil
}

// OpenBoundOriginalNormalOff authenticates a peer's M3 record using the
// ORIGINAL Go credential-TLS-derived Rust owner AND the very same live
// process-created Wintun generation. It neither accepts unauthenticated
// IPv4 from a kernel socket nor itself grants WFP/route OS Applied.
// A failed Rust AEAD / PN / replay result NEVER yields any plaintext.
func(s *V4WindowsAuthenticatedClientOwner) OpenBoundOriginalNormalOff(
    ctx context.Context,seq uint32,wire []byte,
)([]byte,error){
    if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
        s.bridge.openNormalProc==nil||len(wire)<51||len(wire)>543{
        return nil,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,err}
    if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
        return nil,errors.Join(errV4WindowsOwner,err)
    }
    state,err:=s.OriginalOwnerReadback()
    if err!=nil||!state.OwnerActive||!state.DeviceBound||
        state.DeviceQuiesced||state.ProductApplied||state.ServerSide{
        return nil,errV4WindowsOwner
    }
    plain:=make([]byte,len(wire))
    var used uintptr
    err=winOwnerCall(s.bridge.openNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&plain[0])),uintptr(len(plain)),
        uintptr(unsafe.Pointer(&used)),
    )
    runtime.KeepAlive(wire)
    runtime.KeepAlive(plain)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used<20||used>uintptr(len(plain)){
        // Return NO data on any Rust error, including incomplete or
        // non-single IPv4 records. Rust owns replay and authentication.
        return nil,errors.Join(errV4WindowsOwner,err)
    }
    if plain[0]>>4!=4 || plain[0]&0xf<5 ||
        int(plain[0]&0xf)*4>int(used){
        return nil,errV4WindowsOwner
    }
    return plain[:used],nil
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


// Authenticated SERVER half of the same original-Go FakeTCP credential TLS
// callback and native Windows Rust M1/M3 owner; used for real peer receive.
// It cannot be fabricated with caller-supplied cold material or exported
// command-line parameters and does not authorize the host WFP product.
type V4WindowsAuthenticatedServerOwner struct{
    bridge *v4WindowsNativeOwnerBridge
    device *v4WindowsRealDeviceLease
}
func V4WindowsEstablishOriginalServerOwner(
    ctx context.Context,library string,assoc *faketcp.ServerAssociation,
    cfg ServerAdmissionConfig,options V4ServerOptions,
)(*V4WindowsAuthenticatedServerOwner,*V4ServerSession,error){
    if ctx==nil||assoc==nil{return nil,nil,errV4WindowsOwner}
    owner,err:=newV4WindowsPrivateOwnerBridge(library)
    if err!=nil{return nil,nil,err}
    if options.ownerBridge!=nil{return nil,nil,errV4WindowsOwner}
    options.ownerBridge=owner
    session,err:=EstablishServerV4(ctx,assoc,cfg,options)
    if err!=nil{return nil,nil,err}
    st,err:=owner.state()
    if err!=nil||st.phase!=2||st.server!=1||st.applied!=0||
        st.generation==0||!owner.committed{return nil,nil,errV4WindowsOwner}
    return &V4WindowsAuthenticatedServerOwner{bridge:owner},session,nil
}
func(s *V4WindowsAuthenticatedServerOwner) BindOriginalM4NativeDevice(
    ctx context.Context,device V4WindowsCurrentNativeDevice,
    id V4WindowsNativeDeviceIdentity,
)error{
    if s==nil||s.bridge==nil||s.device!=nil{return errV4WindowsOwner}
    hold,err:=s.bridge.holdOriginalCreatedWintun(ctx,device,id)
    if hold!=nil{s.device=hold}
    return err
}
func(s *V4WindowsAuthenticatedServerOwner) checkedBound(
    ctx context.Context,
)error{
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.handle==0{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
        return errors.Join(errV4WindowsOwner,err)
    }
    st,err:=s.bridge.state()
    if err!=nil||st.phase!=2||st.server!=1||st.applied!=0||
        st.generation==0{return errV4WindowsOwner}
    dev,err:=s.bridge.realNativeDeviceState()
    if err!=nil||dev.Bound!=1||dev.Quiesced!=0||dev.Applied!=0||
        dev.IfIndex!=s.device.identity.InterfaceIndex||
        dev.LUID!=s.device.identity.LUID{
        return errV4WindowsOwner
    }
    return nil
}
// Actual original TLS-derived SERVER M3 authenticated decrypt, receiving
// only the exact native kernel UDP application's wire record. The C ABI
// consumes replay/PN and never returns failed AEAD plaintext.
func(s *V4WindowsAuthenticatedServerOwner) OpenBoundOriginalNormalOff(
    ctx context.Context,seq uint32,wire []byte,
)([]byte,error){
    if len(wire)<51||len(wire)>543{return nil,errV4WindowsOwner}
    if err:=s.checkedBound(ctx);err!=nil{return nil,err}
    plain:=make([]byte,len(wire))
    var used uintptr
    err:=winOwnerCall(s.bridge.openNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&plain[0])),uintptr(len(plain)),
        uintptr(unsafe.Pointer(&used)))
    runtime.KeepAlive(wire)
    runtime.KeepAlive(plain)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used<20||used>uintptr(len(plain)){
        return nil,errors.Join(errV4WindowsOwner,err)
    }
    if plain[0]>>4!=4||plain[0]&15<5||
        int(plain[0]&15)*4>int(used){
        return nil,errV4WindowsOwner
    }
    return plain[:used],nil
}
// True original TLS-derived SERVER M1 immutable outbound AEAD record,
// using the same bounded 576-byte native normal/off Rust budget as client.
func(s *V4WindowsAuthenticatedServerOwner) SealBoundOriginalNormalOff(
    ctx context.Context,ipv4 []byte,
)([]byte,uint32,uint64,error){
    if len(ipv4)<20||len(ipv4)>512||ipv4[0]>>4!=4{
        return nil,0,0,errV4WindowsOwner
    }
    if err:=s.checkedBound(ctx);err!=nil{return nil,0,0,err}
    wire:=make([]byte,len(ipv4)+31)
    var used uintptr
    var seq uint32
    var pn uint64
    err:=winOwnerCall(s.bridge.sealNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&used)),
        uintptr(unsafe.Pointer(&seq)),uintptr(unsafe.Pointer(&pn)))
    runtime.KeepAlive(ipv4);runtime.KeepAlive(wire)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used!=uintptr(len(wire)){
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    return wire,seq,pn,nil
}
func(s *V4WindowsAuthenticatedServerOwner) StopScopedOwner(ctx context.Context)error{
    if s==nil||ctx==nil||s.bridge==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if s.device!=nil{return s.device.quiesceAndStopRustOnly(ctx)}
    return s.bridge.stopRustOwnerOnly()
}

// OriginalVerifiedTCPBoundaries exposes ONLY original FakeTCP Detach's
// authenticated TCP seq/ACK starting fence for the packet transport.
// It is not a cold key, a Rust handle or an OS network authorization.
func(s *V4WindowsAuthenticatedClientOwner) OriginalVerifiedTCPBoundaries()(
 sendNext,receiveNext uint32,err error,
){
 if s==nil||s.bridge==nil||s.device==nil||!s.bridge.committed||
  s.bridge.stopped||s.bridge.tcpSendNext==0||
  s.bridge.tcpRecvNext==0{
  return 0,0,errV4WindowsOwner
 }
 state,e:=s.OriginalOwnerReadback()
 if e!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied{
  return 0,0,errV4WindowsOwner
 }
 return s.bridge.tcpSendNext,s.bridge.tcpRecvNext,nil
}
