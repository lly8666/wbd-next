//go:build windows && wbd_v4_embedded_go
package realityfront

// PLAN024 original Go TLS credential-verified Windows Fixed/Auto feature7
// owner -> the SAME M1/M3 Rust AEAD/PN and RS16 first-delivery C ABI.
// These calls do NOT assert Go authenticated M2 applied-revision, kernel
// packet copy, native WFP or a public WinForms Applied/Disconnected state.
import (
 "context"
 "encoding/binary"
 "errors"
 "fmt"
 "runtime"
 "syscall"
 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4WindowsFEC2Delivery struct{
 BlockID uint64
 SourceIndex uint32
 Recovered bool
 IPv4 []byte
}
type winFec2RawDelivery struct{
 BlockID uint64
 Index,Length,Recovered uint32
 Frame [512]byte
}
func V4WindowsEstablishOriginalFEC2ClientOwner(
 ctx context.Context,library string,assoc *faketcp.ClientAssociation,
 cfg ClientAdmissionConfig,
)(*V4WindowsAuthenticatedClientOwner,*V4ClientSession,error){
 if ctx==nil||assoc==nil||assoc.BootstrapConn()==nil||
  cfg.Policy.Transport!=TransportNormal||
  cfg.Policy.FECMode==FECOff||
  cfg.Policy.DesiredLanes!=1||cfg.DesiredLanes!=1{
  return nil,nil,ErrAdmissionUnsupported
 }
 native,err:=newV4WindowsPrivateOwnerBridge(library)
 if err!=nil{return nil,nil,err}
 session,err:=EstablishClientV4(ctx,assoc.BootstrapConn(),cfg,
  V4ClientOptions{DataPlaneReady:true,fec2Product:true})
 if err!=nil{return nil,nil,err}
 handoff,err:=assoc.Detach()
 if err!=nil{return nil,nil,err}
 if err=native.prepareAuthenticatedClient(session,handoff,assoc.Flow());err!=nil{
  return nil,nil,errors.Join(errV4WindowsOwner,err)
 }
 state,err:=native.state()
 if err!=nil||state.phase!=2||state.applied!=0||state.generation==0||
  state.server!=0{return nil,nil,errV4WindowsOwner}
 return &V4WindowsAuthenticatedClientOwner{bridge:native},session,nil
}
func V4WindowsEstablishOriginalFEC2ServerOwner(
 ctx context.Context,library string,assoc *faketcp.ServerAssociation,
 cfg ServerAdmissionConfig,opts V4ServerOptions,
)(*V4WindowsAuthenticatedServerOwner,*V4ServerSession,error){
 if ctx==nil||assoc==nil||opts.ownerBridge!=nil{return nil,nil,ErrAdmissionParams}
 b,err:=newV4WindowsPrivateOwnerBridge(library)
 if err!=nil{return nil,nil,err}
 opts.DataPlaneReady=true
 opts.ownerBridge=b
 opts.fec2Product=true
 session,err:=EstablishServerV4(ctx,assoc,cfg,opts)
 if err!=nil{return nil,nil,err}
 state,err:=b.state()
 if err!=nil||state.phase!=2||state.server!=1||state.applied!=0||
  state.generation==0||!b.committed{return nil,nil,errV4WindowsOwner}
 return &V4WindowsAuthenticatedServerOwner{bridge:b},session,nil
}
func winFec2Source(blockID uint64,index uint8,ipv4 []byte)([]byte,error){
 if blockID==0||index>=16||len(ipv4)<20||len(ipv4)>450||
  ipv4[0]>>4!=4||ipv4[0]&15<5{return nil,errV4WindowsOwner}
 out:=make([]byte,10+len(ipv4))
 binary.BigEndian.PutUint64(out[:8],blockID)
 out[8]=index
 copy(out[10:],ipv4)
 return out,nil
}
func winFec2Sealer(ctx context.Context,bridge *v4WindowsNativeOwnerBridge,
 device *v4WindowsRealDeviceLease,kind uint32,symbol []byte,
)([]byte,uint32,uint64,error){
 if ctx==nil||bridge==nil||device==nil||bridge.handle==0||
  kind!=2&&kind!=3||len(symbol)<10||len(symbol)>512{
  return nil,0,0,errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return nil,0,0,err}
 if err:=device.device.VerifyCurrentNative(ctx,device.identity);err!=nil{
  return nil,0,0,errors.Join(errV4WindowsOwner,err)
 }
 proc,err:=bridge.dll.FindProc("wbd_m0_win_owner_v4_fec2_seal")
 if err!=nil{return nil,0,0,err}
 wire:=make([]byte,len(symbol)+31)
 var used uintptr
 var seq uint32
 var pn uint64
 err=winOwnerCall(proc,uintptr(bridge.handle),
  uintptr(unsafe.Pointer(&bridge.epoch[0])),16,
  uintptr(device.identity.LUID),uintptr(device.identity.InterfaceIndex),
  uintptr(kind),uintptr(unsafe.Pointer(&symbol[0])),uintptr(len(symbol)),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&used)),
  uintptr(unsafe.Pointer(&seq)),uintptr(unsafe.Pointer(&pn)))
 runtime.KeepAlive(bridge.epoch);runtime.KeepAlive(symbol);runtime.KeepAlive(wire)
 if err!=nil||used!=uintptr(len(wire)){return nil,0,0,errors.Join(errV4WindowsOwner,err)}
 return wire,seq,pn,nil
}
func winFec2Opener(ctx context.Context,bridge *v4WindowsNativeOwnerBridge,
 device *v4WindowsRealDeviceLease,seq uint32,wire []byte,
)([]V4WindowsFEC2Delivery,error){
 if ctx==nil||bridge==nil||device==nil||bridge.handle==0||
  len(wire)<=31||len(wire)>543{return nil,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return nil,err}
 if err:=device.device.VerifyCurrentNative(ctx,device.identity);err!=nil{
  return nil,errors.Join(errV4WindowsOwner,err)
 }
 proc,err:=bridge.dll.FindProc("wbd_m0_win_owner_v4_fec2_open")
 if err!=nil{return nil,fmt.Errorf("original Rust FEC2 open ABI missing: %w",err)}
 raw:=make([]winFec2RawDelivery,16)
 var count uint32
 err=winOwnerCall(proc,uintptr(bridge.handle),
  uintptr(unsafe.Pointer(&bridge.epoch[0])),16,
  uintptr(device.identity.LUID),uintptr(device.identity.InterfaceIndex),
  uintptr(seq),uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&raw[0])),uintptr(len(raw)),
  uintptr(unsafe.Pointer(&count)))
 runtime.KeepAlive(bridge.epoch);runtime.KeepAlive(wire);runtime.KeepAlive(raw)
 if err!=nil||count>16{return nil,errors.Join(errV4WindowsOwner,err)}
 out:=make([]V4WindowsFEC2Delivery,0,count)
 for i:=uint32(0);i<count;i++{
  v:=raw[i]
  if v.BlockID==0||v.Index>=16||v.Length<20||v.Length>512||
   v.Frame[0]>>4!=4||v.Frame[0]&15<5{return nil,errV4WindowsOwner}
  out=append(out,V4WindowsFEC2Delivery{
   BlockID:v.BlockID,SourceIndex:v.Index,Recovered:v.Recovered==1,
   IPv4:append([]byte(nil),v.Frame[:v.Length]...),
  })
 }
 return out,nil
}
func(s *V4WindowsAuthenticatedClientOwner) SealBoundOriginalFEC2Source(
 ctx context.Context,blockID uint64,index uint8,ipv4 []byte,
)([]byte,uint32,uint64,error){
 if s==nil||s.bridge==nil||s.device==nil{return nil,0,0,errV4WindowsOwner}
 scope,err:=s.OriginalOwnerReadback()
 if err!=nil||!scope.OwnerActive||!scope.DeviceBound||
  scope.DeviceQuiesced||scope.ServerSide{return nil,0,0,errV4WindowsOwner}
 symbol,err:=winFec2Source(blockID,index,ipv4)
 if err!=nil{return nil,0,0,err}
 return winFec2Sealer(ctx,s.bridge,s.device,2,symbol)
}
func(s *V4WindowsAuthenticatedClientOwner) OpenBoundOriginalFEC2(
 ctx context.Context,seq uint32,wire []byte,
)([]V4WindowsFEC2Delivery,error){
 if s==nil||s.bridge==nil||s.device==nil{return nil,errV4WindowsOwner}
 scope,err:=s.OriginalOwnerReadback()
 if err!=nil||!scope.OwnerActive||!scope.DeviceBound||
  scope.DeviceQuiesced||scope.ServerSide{return nil,errV4WindowsOwner}
 return winFec2Opener(ctx,s.bridge,s.device,seq,wire)
}
func(s *V4WindowsAuthenticatedServerOwner) SealBoundOriginalFEC2Source(
 ctx context.Context,blockID uint64,index uint8,ipv4 []byte,
)([]byte,uint32,uint64,error){
 if s==nil||s.bridge==nil||s.device==nil{return nil,0,0,errV4WindowsOwner}
 if err:=s.checkedBound(ctx);err!=nil{return nil,0,0,err}
 symbol,err:=winFec2Source(blockID,index,ipv4)
 if err!=nil{return nil,0,0,err}
 return winFec2Sealer(ctx,s.bridge,s.device,2,symbol)
}
func(s *V4WindowsAuthenticatedServerOwner) OpenBoundOriginalFEC2(
 ctx context.Context,seq uint32,wire []byte,
)([]V4WindowsFEC2Delivery,error){
 if s==nil||s.bridge==nil||s.device==nil{return nil,errV4WindowsOwner}
 if err:=s.checkedBound(ctx);err!=nil{return nil,err}
 return winFec2Opener(ctx,s.bridge,s.device,seq,wire)
}
