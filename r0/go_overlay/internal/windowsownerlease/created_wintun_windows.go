//go:build windows && wbd_v4_embedded_go
package windowsownerlease

// The only M0 Windows OS adapter that imports BOTH M4 windowsclient and
// M0 realityfront. Imports are ONE WAY. M4's original same-process Wintun
// lease is the sole proof; an alias, saved configuration or forged raw Rust
// token cannot create one. This package does not install WFP/routing/DNS.
import (
    "context"
    "errors"
    "fmt"
    "syscall"
    "unsafe"

    "golang.org/x/sys/windows"
    "github.com/lly8666/wobuzhidao/internal/windowsclient"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)
var ErrNativeDeviceNotOwned=errors.New("original-Go authenticated Windows created Wintun not owned")
// IP Helper's native DLL/Proc binding is immutable process-wide; only the
// actual OS identity and M4 reservation remain dynamic and verified.
var convertLuidToGuid=syscall.NewLazyDLL("iphlpapi.dll").NewProc("ConvertInterfaceLuidToGuid")
type CreatedWintun struct{
    TUN *windowsclient.TUN
}
// Identity always consults the current LIVE original M4-created adapter
// handle and Windows IP Helper. It never trusts the interface alias alone.
func(d CreatedWintun) Identity(
    ctx context.Context,installation,epoch [16]byte,
)(realityfront.V4WindowsNativeDeviceIdentity,error){
    var zero realityfront.V4WindowsNativeDeviceIdentity
    if ctx==nil||d.TUN==nil||installation==[16]byte{}||
        epoch==[16]byte{}{return zero,ErrNativeDeviceNotOwned}
    actual,err:=d.TUN.NativeIdentity(ctx)
    if err!=nil{return zero,errors.Join(ErrNativeDeviceNotOwned,err)}
    if !actual.CreatedByProcess||actual.Index==0||actual.LUID==0||
        d.TUN.Name()==""{return zero,ErrNativeDeviceNotOwned}
    if err:=convertLuidToGuid.Find();err!=nil{return zero,errors.Join(ErrNativeDeviceNotOwned,err)}
    var guid windows.GUID
    rc,_,_:=convertLuidToGuid.Call(uintptr(unsafe.Pointer(&actual.LUID)),
        uintptr(unsafe.Pointer(&guid)))
    if rc!=0{return zero,fmt.Errorf("%w: IP Helper GUID errno=%d",ErrNativeDeviceNotOwned,rc)}
    return realityfront.V4WindowsNativeDeviceIdentity{
        Installation:installation,Generation:epoch,
        LUID:actual.LUID,InterfaceIndex:actual.Index,
        GUID:guid.String(),Alias:d.TUN.Name(),
    },nil
}
func(d CreatedWintun) currentHolder(id realityfront.V4WindowsNativeDeviceIdentity)(
    windowsclient.N4WindowsCreatedWintunReservation,windowsclient.N4UnifiedIdentity,
){
    nativeID:=windowsclient.N4UnifiedIdentity{
        Installation:id.Installation,Generation:id.Generation,
        WintunLUID:id.LUID,WintunIndex:id.InterfaceIndex,
        WintunGUID:id.GUID,AdapterAlias:id.Alias,
    }
    return windowsclient.N4WindowsCreatedWintunReservation{
        Tunnel:d.TUN,Installation:id.Installation,Generation:id.Generation,
    },nativeID
}
func(d CreatedWintun) VerifyCurrentNative(
    ctx context.Context,id realityfront.V4WindowsNativeDeviceIdentity,
)error{
    if ctx==nil||d.TUN==nil{return ErrNativeDeviceNotOwned}
    now,err:=d.Identity(ctx,id.Installation,id.Generation)
    if err!=nil{return err}
    if now!=id{return ErrNativeDeviceNotOwned}
    holder,nativeID:=d.currentHolder(id)
    if err:=holder.Verify(ctx,nativeID);err!=nil{
        return errors.Join(ErrNativeDeviceNotOwned,err)
    }
    return nil
}
func(d CreatedWintun) HoldCurrentNative(
    ctx context.Context,id realityfront.V4WindowsNativeDeviceIdentity,
)(func(),error){
    if err:=d.VerifyCurrentNative(ctx,id);err!=nil{return nil,err}
    holder,nativeID:=d.currentHolder(id)
    // Real M4's reservation includes beginCall()/endCall() active wait,
    // so Wintun.Close cannot retire/reuse the native handle until release.
    release,err:=holder.Hold(ctx,nativeID)
    if err!=nil{return nil,errors.Join(ErrNativeDeviceNotOwned,err)}
    if release==nil{return nil,ErrNativeDeviceNotOwned}
    return release,nil
}
