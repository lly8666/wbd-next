//go:build windows && wbd_v4_embedded_go
package windowsownerlease

import (
 "context"
 "errors"
 "path/filepath"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
type ScopedOriginalTLSNativeWintun struct {
 owner *realityfront.V4WindowsAuthenticatedClientOwner
 native CreatedWintun
 identity realityfront.V4WindowsNativeDeviceIdentity
 bound bool
}
func ConnectScopedOriginalTLSWintun(ctx context.Context,
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,installation,epoch [16]byte,
)(*ScopedOriginalTLSNativeWintun,error){
 if ctx==nil||owner==nil||tun==nil||installation==[16]byte{}||
 epoch==[16]byte{}{return nil,ErrNativeDeviceNotOwned}
 out:=&ScopedOriginalTLSNativeWintun{owner:owner,native:CreatedWintun{TUN:tun}}
 id,err:=out.native.Identity(ctx,installation,epoch)
 if err!=nil{return nil,err}
 out.identity=id
 if err=owner.BindOriginalM4NativeDevice(ctx,out.native,id);err!=nil{
  return out,errors.Join(ErrNativeDeviceNotOwned,err)
 }
 state,err:=owner.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
 state.DeviceQuiesced||state.ProductApplied{return out,ErrNativeDeviceNotOwned}
 out.bound=true
 return out,nil
}
func(s *ScopedOriginalTLSNativeWintun) StopRustScoped(ctx context.Context)error{
 if s==nil||s.owner==nil||ctx==nil{return ErrNativeDeviceNotOwned}
 err:=s.owner.StopScopedOwner(ctx)
 if err==nil{s.bound=false}
 return err
}

// NativeProductAdmission performs actual ORIGINAL GO TLS -> live M4 Wintun
// -> Rust owner -> Windows OS journal/guard READ-ONLY inspection. It cannot
// install/enable WFP, routes or DNS, and therefore cannot grant product
// Connected. M4 must implement independently qualified native transaction
// and live OS kernel/route readback before this is replaced by that gate.
type NativeProductAdmission struct {
    NativeIdentity realityfront.V4WindowsNativeDeviceIdentity
    OriginalTLSOwner realityfront.V4WindowsScopedOwnerReadback
    DiskState windowsclient.N4NativeStateSnapshot
    ProductApplied bool
}
func(s *ScopedOriginalTLSNativeWintun) NativeProductAdmission(
    ctx context.Context,statePath string,
)(NativeProductAdmission,error){
    var out NativeProductAdmission
    if s==nil||ctx==nil||s.owner==nil||!s.bound||
        s.identity.Generation==[16]byte{}||s.identity.Installation==[16]byte{}||
        !filepath.IsAbs(statePath) {return out,ErrNativeDeviceNotOwned}
    if err:=ctx.Err();err!=nil{return out,err}
    // Independently re-read actual Win32 adapter LUID, index and GUID at
    // admission time. A stale held pointer or alias is insufficient.
    if err:=s.native.VerifyCurrentNative(ctx,s.identity);err!=nil{
        return out,errors.Join(ErrNativeDeviceNotOwned,err)
    }
    state,err:=s.owner.OriginalOwnerReadback()
    if err!=nil{return out,errors.Join(ErrNativeDeviceNotOwned,err)}
    if !state.OwnerActive||!state.DeviceBound||state.DeviceQuiesced||
       state.ProductApplied||state.ServerSide||state.Generation==0{
        return out,ErrNativeDeviceNotOwned
    }
    out.NativeIdentity=s.identity
    out.OriginalTLSOwner=state
    disk,err:=windowsclient.N4NativeInspectState(ctx,statePath)
    if err!=nil{return out,errors.Join(ErrNativeDeviceNotOwned,err)}
    out.DiskState=disk
    // An intact WAL is only a DISK claim, not OS proof. In particular,
    // adopting preexisting, orphan, legacy or foreign state is forbidden.
    if disk.State!="absent"||disk.NativeWAL||disk.RouteIntent||
       disk.LegacyJournal||disk.GuardQualified{
        return out,ErrNativeDeviceNotOwned
    }
    // This M4-owned guard intentionally denies real WFP/native product
    // admission, even when the original-Go TLS Rust/Wintun Hold is valid.
    // Preserve ErrN4NativeGuard as the precise external blocker.
    if err:=windowsclient.N4NativeNetworkReady(ctx);err!=nil{
        return out,errors.Join(ErrNativeDeviceNotOwned,err)
    }
    // A future M4 pass of N4NativeNetworkReady still does not establish
    // OS applied+kernel UDP evidence by itself. M4 must add a separate
    // positive live OS readback/packet driver contract before promotion.
    return out,ErrNativeDeviceNotOwned
}
