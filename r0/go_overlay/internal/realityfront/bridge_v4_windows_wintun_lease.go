//go:build windows && wbd_v4_embedded_go

package realityfront

// Real original-Go credential-checked Windows protected owner -> M4's
// process-created Wintun identity/hold. This is a native device lifetime
// contract, *not* the product's WFP route/DNS/IPv6 Apply or an OS Connected
// claim. Only the original Go TLS callback can obtain a bridge.handle.
import (
    "context"
    "errors"
    "fmt"
    "runtime"
    "syscall"
    "unsafe"

    "golang.org/x/sys/windows"

    "github.com/lly8666/wobuzhidao/internal/windowsclient"
)

// Pin the native GUID from IP Helper in the SAME process and CURRENT
// Wintun handle, without adopting an alias or trusting a JSON configuration.
// M4 independently repeats this OS GUID/LUID/index check in Hold and Verify.
func v4WindowsOriginalWintunIdentity(
    ctx context.Context,tun *windowsclient.TUN,
    installation,epoch [16]byte,
)(windowsclient.N4UnifiedIdentity,error){
    var zero windowsclient.N4UnifiedIdentity
    if ctx==nil||tun==nil||installation==[16]byte{}||epoch==[16]byte{}{
        return zero,errV4WindowsOwner
    }
    actual,err:=tun.NativeIdentity(ctx)
    if err!=nil{return zero,errors.Join(errV4WindowsOwner,err)}
    if !actual.CreatedByProcess||actual.Index==0||actual.LUID==0||
        tun.Name()==""{return zero,errV4WindowsOwner}
    proc:=syscall.NewLazyDLL("iphlpapi.dll").NewProc("ConvertInterfaceLuidToGuid")
    if err:=proc.Find();err!=nil{return zero,errors.Join(errV4WindowsOwner,err)}
    var guid windows.GUID
    status,_,_:=proc.Call(uintptr(unsafe.Pointer(&actual.LUID)),
        uintptr(unsafe.Pointer(&guid)))
    if status!=0{return zero,fmt.Errorf("%w: native interface GUID status=%d",errV4WindowsOwner,status)}
    id:=windowsclient.N4UnifiedIdentity{
        Installation:installation,Generation:epoch,
        WintunLUID:actual.LUID,WintunIndex:actual.Index,
        WintunGUID:guid.String(),AdapterAlias:tun.Name(),
    }
    // No product/full OS claim: the M4 protected five-stage owner must
    // separately bind its durable PnP instance pin, WFP guard and WAL.
    return id,nil
}

// v4WindowsRealWintunLease retains M4's ORIGINAL live Wintun adapter/session
// across the Rust owner, preventing a caller from swapping the adapter after
// native IP Helper LUID/index/GUID readback. No alias-only foreign adoption.
type v4WindowsRealWintunLease struct{
    bridge *v4WindowsNativeOwnerBridge
    native windowsclient.N4WindowsCreatedWintunReservation
    identity windowsclient.N4UnifiedIdentity
    release func()
    stopped bool
}
type v4WindowsDeviceFenceV2 struct{
    Version,StructSize,Generation,Bound,Quiesced,Applied,IfIndex,Reserved uint32
    LUID uint64
}
func (b *v4WindowsNativeOwnerBridge) realNativeDeviceState()(v4WindowsDeviceFenceV2,error){
    var state v4WindowsDeviceFenceV2
    if b==nil||b.handle==0||b.deviceStateProc==nil{return state,errV4WindowsOwner}
    if err:=winOwnerCall(b.deviceStateProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&state)),uintptr(unsafe.Sizeof(state)));err!=nil{
        return state,err
    }
    if state.Version!=2||state.StructSize!=uint32(unsafe.Sizeof(state))||
        state.Generation!=uint32(b.handle>>32)||state.Reserved!=0||state.Applied!=0{
        return state,errV4WindowsOwner
    }
    return state,nil
}
func (b *v4WindowsNativeOwnerBridge) holdOriginalCreatedWintun(
    ctx context.Context,tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)(*v4WindowsRealWintunLease,error){
    if b==nil||tun==nil||ctx==nil||b.dll==nil||b.handle==0||
        !b.committed||b.stopped||b.epoch==[16]byte{}||
        id.Generation!=b.epoch||id.Installation==[16]byte{}||
        id.WintunIndex==0||id.WintunLUID==0||id.WintunGUID==""||
        id.AdapterAlias==""||id.AdapterAlias!=tun.Name()||
        len(id.WintunGUID)>64||len(id.AdapterAlias)>128{
        return nil,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,err}
    state,err:=b.state()
    if err!=nil||state.phase!=2||state.applied!=0{return nil,errV4WindowsOwner}
    bound,err:=b.realNativeDeviceState()
    if err!=nil||bound.Bound!=0{return nil,errV4WindowsOwner}
    holder:=windowsclient.N4WindowsCreatedWintunReservation{
        Tunnel:tun,Installation:id.Installation,Generation:id.Generation,
    }
    release,err:=holder.Hold(ctx,id)
    if err!=nil{return nil,errors.Join(errV4WindowsOwner,err)}
    if release==nil{return nil,errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{release();return nil,err}
    // Caller never provides a raw device pointer/token or WFP readiness.
    // The M4 hold above confirmed the actual process-created native Wintun
    // handle, live IP Helper LUID/index and identical interface GUID.
    err=winOwnerCall(b.bindWintunProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&b.epoch[0])),16,
        uintptr(id.WintunLUID),uintptr(id.WintunIndex))
    runtime.KeepAlive(b.epoch)
    if err!=nil{release();return nil,err}
    bound,err=b.realNativeDeviceState()
    if err!=nil||bound.Bound!=1||bound.Quiesced!=0||
        bound.LUID!=id.WintunLUID||bound.IfIndex!=id.WintunIndex{
        // Do not release the live Wintun on ambiguous Rust state: the
        // owner still has a native lease. Let an explicit Stop recover.
        return &v4WindowsRealWintunLease{
            bridge:b,native:holder,identity:id,release:release,
        },errV4WindowsOwner
    }
    return &v4WindowsRealWintunLease{
        bridge:b,native:holder,identity:id,release:release,
    },nil
}
// Final Stop ordering is native real-device verification → quiescence
// after M4 has joined its own packet workers → protected Rust owner Stop /
// generation release → release original M4 Wintun hold. This routine does NOT
// close the M4 TUN, delete OS routes, remove WFP, or certify product Apply.
// No caller may invoke before its own actual M4 RX/TX workers are joined.
func (lease *v4WindowsRealWintunLease) quiesceAndStopRustOnly(ctx context.Context)error{
    if lease==nil||lease.bridge==nil||ctx==nil{return errV4WindowsOwner}
    if lease.stopped{return nil}
    if err:=ctx.Err();err!=nil{return err}
    b:=lease.bridge
    if b.handle==0||!b.committed||lease.release==nil{return errV4WindowsOwner}
    if err:=lease.native.Verify(ctx,lease.identity);err!=nil{
        // Preserve the real device hold and native token on OS ambiguity.
        return errors.Join(errV4WindowsOwner,err)
    }
    if err:=winOwnerCall(b.quiesceWintunProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&b.epoch[0])),16,
        uintptr(lease.identity.WintunLUID),
        uintptr(lease.identity.WintunIndex));err!=nil{return err}
    state,err:=b.realNativeDeviceState()
    if err!=nil||state.Bound!=1||state.Quiesced!=1||
        state.Applied!=0||state.LUID!=lease.identity.WintunLUID||
        state.IfIndex!=lease.identity.WintunIndex{return errV4WindowsOwner}
    if err:=b.stopRustOwnerOnly();err!=nil{return err}
    lease.release()
    lease.release=nil
    lease.stopped=true
    return nil
}
