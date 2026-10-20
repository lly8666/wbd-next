//go:build windows && wbd_v4_embedded_go
package realityfront

// Shared M0 original Go credential-TLS Rust-owner / M4 native OS Wintun
// boundary. The M4 Windows device implementation MUST live in a one-way
// adapter package to avoid realityfront -> windowsclient -> datapath ->
// realityfront's forbidden Go import cycle.
import (
    "context"
    "errors"
    "runtime"
    "unsafe"
)

// V4WindowsNativeDeviceIdentity is the precise same-process M4-created
// Wintun identity, NEVER operator config or a Rust-issued OS credential.
// Product Applied is always false until a separate OS/WFP/route transaction.
type V4WindowsNativeDeviceIdentity struct {
    Installation [16]byte
    Generation [16]byte
    LUID uint64
    InterfaceIndex uint32
    GUID string
    Alias string
}
type V4WindowsCurrentNativeDevice interface{
    // HoldCurrentNative must lock the original created-by-process Wintun
    // while independently reading its Win32 LUID/index/GUID and rejecting
    // mismatched identity before it returns the release closure.
    HoldCurrentNative(context.Context,V4WindowsNativeDeviceIdentity)(func(),error)
    VerifyCurrentNative(context.Context,V4WindowsNativeDeviceIdentity)error
}
// An M4-facing wrapper can only be instantiated through genuine original
// Go credential TLS; it does NOT implement a full Windows product owner.
type v4WindowsRealDeviceLease struct{
    bridge *v4WindowsNativeOwnerBridge
    device V4WindowsCurrentNativeDevice
    identity V4WindowsNativeDeviceIdentity
    release func()
    stopped bool
}
type v4WindowsDeviceFenceV2 struct{
    Version,StructSize,Generation,Bound,Quiesced,Applied,IfIndex,Reserved uint32
    LUID uint64
}
func (b *v4WindowsNativeOwnerBridge) realNativeDeviceState()(v4WindowsDeviceFenceV2,error){
    var v v4WindowsDeviceFenceV2
    if b==nil||b.handle==0||b.deviceStateProc==nil{return v,errV4WindowsOwner}
    if err:=winOwnerCall(b.deviceStateProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&v)),uintptr(unsafe.Sizeof(v)));err!=nil{return v,err}
    if v.Version!=2||v.StructSize!=uint32(unsafe.Sizeof(v))||
        v.Generation!=uint32(b.handle>>32)||v.Reserved!=0||v.Applied!=0{
        return v,errV4WindowsOwner
    }
    return v,nil
}
func (b *v4WindowsNativeOwnerBridge) holdOriginalCreatedWintun(
    ctx context.Context,device V4WindowsCurrentNativeDevice,
    id V4WindowsNativeDeviceIdentity,
)(*v4WindowsRealDeviceLease,error){
    if b==nil||device==nil||ctx==nil||b.dll==nil||b.handle==0||
        !b.committed||b.stopped||b.epoch==[16]byte{}||
        id.Generation!=b.epoch||id.Installation==[16]byte{}||
        id.InterfaceIndex==0||id.LUID==0||id.GUID==""||id.Alias==""||
        len(id.GUID)>64||len(id.Alias)>128{
        return nil,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,err}
    state,err:=b.state()
    if err!=nil||state.phase!=2||state.applied!=0{return nil,errV4WindowsOwner}
    bound,err:=b.realNativeDeviceState()
    if err!=nil||bound.Bound!=0{return nil,errV4WindowsOwner}
    release,err:=device.HoldCurrentNative(ctx,id)
    if err!=nil{return nil,errors.Join(errV4WindowsOwner,err)}
    if release==nil{return nil,errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{release();return nil,err}
    // A Go outer package MUST implement device using M4's exact original
    // real Wintun NativeIdentity/Reservation Hold. This inner call only
    // fences the Rust crypto generation; it cannot grant OS/WFP Apply.
    err=winOwnerCall(b.bindWintunProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&b.epoch[0])),16,
        uintptr(id.LUID),uintptr(id.InterfaceIndex))
    runtime.KeepAlive(b.epoch)
    if err!=nil{release();return nil,err}
    lease:=&v4WindowsRealDeviceLease{bridge:b,device:device,identity:id,release:release}
    bound,err=b.realNativeDeviceState()
    if err!=nil||bound.Bound!=1||bound.Quiesced!=0||
        bound.LUID!=id.LUID||bound.IfIndex!=id.InterfaceIndex{
        // Preserve original live device hold on ambiguous Rust state.
        return lease,errV4WindowsOwner
    }
    return lease,nil
}
func (lease *v4WindowsRealDeviceLease) quiesceAndStopRustOnly(ctx context.Context)error{
    if lease==nil||lease.bridge==nil||ctx==nil{return errV4WindowsOwner}
    if lease.stopped{return nil}
    if err:=ctx.Err();err!=nil{return err}
    b:=lease.bridge
    if b.handle==0||!b.committed||lease.release==nil{return errV4WindowsOwner}
    if err:=lease.device.VerifyCurrentNative(ctx,lease.identity);err!=nil{
        return errors.Join(errV4WindowsOwner,err)
    }
    if err:=winOwnerCall(b.quiesceWintunProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&b.epoch[0])),16,
        uintptr(lease.identity.LUID),uintptr(lease.identity.InterfaceIndex));err!=nil{return err}
    state,err:=b.realNativeDeviceState()
    if err!=nil||state.Bound!=1||state.Quiesced!=1||
        state.Applied!=0||state.LUID!=lease.identity.LUID||
        state.IfIndex!=lease.identity.InterfaceIndex{return errV4WindowsOwner}
    if err:=b.stopRustOwnerOnly();err!=nil{return err}
    lease.release()
    lease.release=nil
    lease.stopped=true
    return nil
}
