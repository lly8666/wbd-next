//go:build windows && wbd_v4_embedded_go
package realityfront

// One original signed Windows Wintun and 2/4 independent original-Go TLS
// Npcap captures; the same two Rust Game workers own all steady packets.
import(
 "context"
 "runtime"
 "unsafe"
)
type V4WindowsGameExtraLaneV3 struct{
 Owner uint64
 InitialTXSeq,InitialRXSeq uint32
 LocalPort,PeerPort uint16
 RXCapture,TXCapture uintptr
 Npcap V4WindowsNpcapNativeFnsV1
}
type V4WindowsGameNativeIOV3 struct{
 Version,Size uint32
 Group uint64
 Lanes,FEC uint32
 First V4WindowsNativeIOV1
 Extra [3]V4WindowsGameExtraLaneV3
}
// Only the protected 2/4 independent Go TLS owners can authorize a native
// group handoff; this C layout does not mint a fresh TLS epoch.
func(g *V4WindowsAuthenticatedGameGroup) StartNativeGameIO(
 ctx context.Context,cfg V4WindowsGameNativeIOV3,
)error{
 if g==nil||ctx==nil{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 g.mu.Lock();defer g.mu.Unlock()
 n:=len(g.members)
 if g.closed||g.joined==0||(n!=2&&n!=4)||
   cfg.First.WintunSession==0||cfg.First.WintunReadEvent==0||
   cfg.First.RXCapture==0||cfg.First.TXCapture==0{
  return errV4WindowsOwner
 }
 first:=g.members[0]
 if first==nil||first.device==nil||first.bridge==nil{
  return errV4WindowsOwner
 }
 cfg.Version=3
 cfg.Size=uint32(unsafe.Sizeof(cfg))
 cfg.Group=g.joined
 cfg.Lanes=uint32(n)
 cfg.FEC=0
 if g.gameFec>0{cfg.FEC=1}
 cfg.First.Version=1
 cfg.First.Size=uint32(unsafe.Sizeof(cfg.First))
 cfg.First.Owner=first.bridge.handle
 cfg.First.Epoch=g.epoch
 cfg.First.LUID=first.device.identity.LUID
 cfg.First.IfIndex=first.device.identity.InterfaceIndex
 for i:=1;i<n;i++{
  owner:=g.members[i]
  if owner==nil||owner.bridge==nil||owner.device==nil||
    owner.bridge.epoch!=g.epoch||owner.device.identity!=first.device.identity{
   return errV4WindowsOwner
  }
  cfg.Extra[i-1].Owner=owner.bridge.handle
 }
 p,err:=first.bridge.fixedProc("wbd_m0_win_game_native_v3_start")
 if err!=nil{return err}
 err=winOwnerCall(p,uintptr(unsafe.Pointer(&cfg)))
 runtime.KeepAlive(cfg)
 return err
}
func(g *V4WindowsAuthenticatedGameGroup) NativeGameIOStats(
 ctx context.Context,
)(V4WindowsNativeWorkerStatsV1,error){
 var v V4WindowsNativeWorkerStatsV1
 if g==nil||ctx==nil{return v,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return v,err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||len(g.members)==0{
  return v,errV4WindowsOwner
 }
 owner:=g.members[0]
 proc,err:=owner.bridge.fixedProc("wbd_m0_win_game_native_v3_stats")
 if err!=nil{return v,err}
 err=winOwnerCall(proc,uintptr(g.joined),uintptr(unsafe.Pointer(&v)))
 runtime.KeepAlive(&v)
 if err!=nil||v.Version!=1||v.Size!=uint32(unsafe.Sizeof(v))||v.Workers!=2{
  return v,errV4WindowsOwner
 }
 return v,nil
}
func(g *V4WindowsAuthenticatedGameGroup) OfferNativeGameEarly(
 ctx context.Context,lane uint32,seq uint32,wire []byte,
)error{
 if g==nil||ctx==nil||len(wire)<32||len(wire)>1536{
  return errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||lane==0||int(lane)>len(g.members){
  return errV4WindowsOwner
 }
 proc,err:=g.members[0].bridge.fixedProc("wbd_m0_win_game_native_v3_early")
 if err!=nil{return err}
 err=winOwnerCall(proc,uintptr(g.joined),uintptr(lane),uintptr(seq),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)))
 runtime.KeepAlive(wire)
 return err
}
// Join native Npcap/Wintun borrows before Go closes ANY of their handles;
// group.StopCryptoAfterDriverDrain must be called only after this returns.
func(g *V4WindowsAuthenticatedGameGroup) JoinNativeGameIO(
 ctx context.Context,
)error{
 if g==nil||ctx==nil{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||len(g.members)==0{return errV4WindowsOwner}
 proc,err:=g.members[0].bridge.fixedProc("wbd_m0_win_game_native_v3_stop")
 if err!=nil{return err}
 return winOwnerCall(proc,uintptr(g.joined))
}
