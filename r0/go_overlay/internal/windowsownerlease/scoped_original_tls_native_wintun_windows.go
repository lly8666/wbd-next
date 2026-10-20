//go:build windows && wbd_v4_embedded_go
package windowsownerlease

import (
 "context"
 "errors"
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
 id,err:=out.native.identity(ctx,installation,epoch)
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
