//go:build windows && wbd_v4_embedded_go
package windowsownerlease

// The M0 ownership bridge between REAL original Go credential verified
// TLS, Rust M1/M3 normal/off, this original signed Wintun and the durable
// Windows WFP/default-route/MTU/DNS/native five-stage WAL product.
// No process-ready status, test-only Rust identity, disk-only receipt or
// caller-supplied IP packet may authorize an OS Applied grant.
import (
 "context"
 "errors"

 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)

// N4NativeAuthenticatedPeerTraffic is the original live TCP transport
// counterpart. It MUST complete real credential-derived Rust M3 AEAD
// peer first+reverse packets via signed Wintun+native OS application, not
// synthetic success, and drain all asynchronous outbound/receive loans
// without releasing Rust/Wintun while native host WAL is still armed.
type N4NativeAuthenticatedPeerTraffic interface {
 VerifyPeerFirstAndReverse(context.Context,
  *realityfront.V4WindowsAuthenticatedClientOwner,
  *windowsclient.TUN,windowsclient.N4UnifiedIdentity)error
 DrainPeerAndKernelLoans(context.Context,
  *realityfront.V4WindowsAuthenticatedClientOwner,
  *windowsclient.TUN,windowsclient.N4UnifiedIdentity)error
}

type originalTLSLiveProductProof struct{
 scoped *ScopedOriginalTLSNativeWintun
 tun *windowsclient.TUN
 client *realityfront.V4WindowsAuthenticatedClientOwner
 packet N4NativeAuthenticatedPeerTraffic
 id windowsclient.N4UnifiedIdentity
}
func(p *originalTLSLiveProductProof) VerifyOriginalNativeHold(
 ctx context.Context,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.scoped==nil||p.tun==nil||p.client==nil||
  p.packet==nil||ctx==nil||id!=p.id||!p.scoped.bound{
  return ErrNativeDeviceNotOwned
 }
 actual:=p.scoped.identity
 if actual.Installation!=id.Installation||
  actual.Generation!=id.Generation||
  actual.LUID!=id.WintunLUID||
  actual.InterfaceIndex!=id.WintunIndex||
  actual.GUID!=id.WintunGUID||
  actual.Alias!=id.AdapterAlias{
  return ErrNativeDeviceNotOwned
 }
 if err:=p.scoped.native.VerifyCurrentNative(ctx,actual);err!=nil{
  return errors.Join(ErrNativeDeviceNotOwned,err)
 }
 state,err:=p.client.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied||state.ServerSide||
  state.Generation==0{
  return errors.Join(ErrNativeDeviceNotOwned,err)
 }
 return nil
}
func(p *originalTLSLiveProductProof) VerifyOriginalCredentialAndKernelOwner(
 ctx context.Context,id windowsclient.N4UnifiedIdentity,
)error{return p.VerifyOriginalNativeHold(ctx,id)}
func(p *originalTLSLiveProductProof) VerifyBidirectionalAuthenticatedFirstDelivery(
 ctx context.Context,id windowsclient.N4UnifiedIdentity,
)error{
 if err:=p.VerifyOriginalNativeHold(ctx,id);err!=nil{return err}
 return p.packet.VerifyPeerFirstAndReverse(ctx,p.client,p.tun,id)
}
func(p *originalTLSLiveProductProof) DrainCryptoAndKernelLoans(
 ctx context.Context,id windowsclient.N4UnifiedIdentity,
)error{
 if err:=p.VerifyOriginalNativeHold(ctx,id);err!=nil{return err}
 return p.packet.DrainPeerAndKernelLoans(ctx,p.client,p.tun,id)
}
func(p *originalTLSLiveProductProof) FinishOriginalNativeStop(
 ctx context.Context,id windowsclient.N4UnifiedIdentity,
)error{
 if err:=p.VerifyOriginalNativeHold(ctx,id);err!=nil{return err}
 return p.scoped.StopRustScoped(ctx)
}

// OriginalTLSNativeProductSession is the OWNED public core session behind
// the Windows CLI/WinForms. Its liveOS receipt is created only inside the
// original native five-stage WAL and authenticated first/reverse network
// path. Actual CLI must hold this session, never invoke legacy PowerShell
// network Apply in parallel.
type OriginalTLSNativeProductSession struct{
 product *windowsclient.N4RealWindowsProduct
 scoped *ScopedOriginalTLSNativeWintun
}
func PrepareOriginalTLSNativeProduct(
 ctx context.Context,
 client *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,plan windowsclient.NetworkPlan,
 install,epoch [16]byte,packet N4NativeAuthenticatedPeerTraffic,
)(*OriginalTLSNativeProductSession,error){
 if ctx==nil||client==nil||tun==nil||packet==nil{
  return nil,ErrNativeDeviceNotOwned
 }
 // REAL original TLS Rust owner+Win32 PnP Hold first, before OS mutation.
 scoped,err:=ConnectScopedOriginalTLSWintun(ctx,client,tun,install,epoch)
 if err!=nil{return nil,err}
 id,err:=windowsclient.N4OriginalCurrentPinnedWintunIdentity(
  ctx,tun,install,epoch)
 if err!=nil{
  return nil,errors.Join(err,scoped.StopRustScoped(context.Background()))
 }
 proof:=&originalTLSLiveProductProof{
  scoped:scoped,tun:tun,client:client,packet:packet,id:id,
 }
 product,err:=windowsclient.N4PrepareRealWindowsProduct(
  ctx,tun,plan,id,proof)
 if err!=nil{
  return nil,errors.Join(err,scoped.StopRustScoped(context.Background()))
 }
 return &OriginalTLSNativeProductSession{product:product,scoped:scoped},nil
}
func(s *OriginalTLSNativeProductSession) Apply(
 ctx context.Context,
)(windowsclient.N4NativeLiveOSReceipt,error){
 if s==nil||s.product==nil{
  return windowsclient.N4NativeLiveOSReceipt{},ErrNativeDeviceNotOwned
 }
 return s.product.Apply(ctx)
}
func(s *OriginalTLSNativeProductSession) LiveReceipt(
 ctx context.Context,
)(windowsclient.N4NativeLiveOSReceipt,error){
 if s==nil||s.product==nil{
  return windowsclient.N4NativeLiveOSReceipt{},ErrNativeDeviceNotOwned
 }
 return s.product.LiveReceipt(ctx)
}
func(s *OriginalTLSNativeProductSession) Stop(ctx context.Context)error{
 if s==nil||s.product==nil{return ErrNativeDeviceNotOwned}
 return s.product.Stop(ctx)
}
