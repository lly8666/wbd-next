//go:build windows && wbd_v4_embedded_go
package windowsownerlease

import (
 "context"
 "errors"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
type ScopedOriginalTLSNativeWintun struct {
 Owner *realityfront.V4WindowsAuthenticatedClientOwner
 Native CreatedWintun
 Identity realityfront.V4WindowsNativeDeviceIdentity
 Bound bool
}
func ConnectScopedOriginalTLSWintun(ctx context.Context,
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,installation,epoch [16]byte,
)(*ScopedOriginalTLSNativeWintun,error){
 if ctx==nil||owner==nil||tun==nil||installation==[16]byte{}||
 epoch==[16]byte{}{return nil,ErrNativeDeviceNotOwned}
 out:=&ScopedOriginalTLSNativeWintun{Owner:owner,Native:CreatedWintun{TUN:tun}}
 id,err:=out.Native.Identity(ctx,installation,epoch)
 if err!=nil{return nil,err}
 out.Identity=id
 if err=owner.BindOriginalM4NativeDevice(ctx,out.Native,id);err!=nil{
  return out,errors.Join(ErrNativeDeviceNotOwned,err)
 }
 state,err:=owner.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
 state.DeviceQuiesced||state.ProductApplied{return out,ErrNativeDeviceNotOwned}
 out.Bound=true
 return out,nil
}
func(s *ScopedOriginalTLSNativeWintun) StopRustScoped(ctx context.Context)error{
 if s==nil||s.Owner==nil||ctx==nil{return ErrNativeDeviceNotOwned}
 err:=s.Owner.StopScopedOwner(ctx)
 if err==nil{s.Bound=false}
 return err
}
