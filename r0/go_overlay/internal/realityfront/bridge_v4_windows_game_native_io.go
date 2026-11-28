//go:build windows && wbd_v4_embedded_go
package realityfront

// One original signed Windows Wintun and 2/4 independent original-Go TLS
// Npcap captures; the same two Rust Game workers own all steady packets.
import(
 "context"
 "runtime"
 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
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
 DisableOuterRepair uint32 // 0=ON default, 1=OFF cold native owner
 First V4WindowsNativeIOV1
 Extra [3]V4WindowsGameExtraLaneV3
}
// Extension: SAME Game TLS group and SAME Wintun/Npcap loan, one
// synchronously copied cold CN split source. V3 native users unchanged.
type v4WindowsGameNativeIOV4 struct{
 Version,Size uint32
 Game V4WindowsGameNativeIOV3
 Split v4WindowsColdSplitWireV1
}
// No modification to the V3/V4 ABI: V5 carries the explicit canonical
// Game startup-padding selector through the one authenticated cold handoff.
type v4WindowsGameNativeIOV5 struct{
 Version,Size uint32
 Game V4WindowsGameNativeIOV3
 Split v4WindowsColdSplitWireV1
 StartupPaddingMode uint32 // off=0, tls=1, flows=2
}
// Only the protected 2/4 independent Go TLS owners can authorize a native
// group handoff; this C layout does not mint a fresh TLS epoch.
func(g *V4WindowsAuthenticatedGameGroup) StartNativeGameIO(
 ctx context.Context,cfg V4WindowsGameNativeIOV3,
)error{
 return g.startNativeGameIO(ctx,cfg,nil)
}
func(g *V4WindowsAuthenticatedGameGroup) StartNativeGameIOWithColdSplit(
 ctx context.Context,cfg V4WindowsGameNativeIOV3,cold V4WindowsColdSplitConfig,
)error{
 return g.startNativeGameIO(ctx,cfg,&cold)
}
func(g *V4WindowsAuthenticatedGameGroup) startNativeGameIO(
 ctx context.Context,cfg V4WindowsGameNativeIOV3,cold *V4WindowsColdSplitConfig,
)error{
 if g==nil||ctx==nil{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 g.mu.Lock();defer g.mu.Unlock()
 n:=len(g.members)
 if g.closed||g.joined==0||(n!=2&&n!=4)||cfg.DisableOuterRepair>1||
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
 if cold!=nil{
  split,err:=cold.wire();if err!=nil{return err}
  var padding uint32
  switch cold.StartupPaddingMode{
  case "","off":padding=0
  case "tls":padding=1
  case "flows":padding=2
  default:return errV4WindowsOwner
  }
  v5:=v4WindowsGameNativeIOV5{Version:5,Game:cfg,
   Split:split,StartupPaddingMode:padding}
  v5.Size=uint32(unsafe.Sizeof(v5))
  p,err:=first.bridge.fixedProc("wbd_m0_win_game_native_v5_start")
  if err!=nil{return err}
  err=winOwnerCall(p,uintptr(unsafe.Pointer(&v5)))
  runtime.KeepAlive(cold)
  runtime.KeepAlive(v5)
  return err
 }
 p,err:=first.bridge.fixedProc("wbd_m0_win_game_native_v3_start")
 if err!=nil{return err}
 err=winOwnerCall(p,uintptr(unsafe.Pointer(&cfg)))
 runtime.KeepAlive(cfg)
 return err
}
func(g *V4WindowsAuthenticatedGameGroup) NativeGameStaleLanes(ctx context.Context)(uint32,error){
 if g==nil||ctx==nil{return 0,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return 0,err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||len(g.members)==0{return 0,errV4WindowsOwner}
 proc,err:=g.members[0].bridge.fixedProc("wbd_m0_win_game_native_stale_lanes")
 if err!=nil{return 0,err}
 var mask uint32
 err=winOwnerCall(proc,uintptr(g.joined),uintptr(unsafe.Pointer(&mask)))
 runtime.KeepAlive(&mask)
 return mask,err
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

// Source-authoritative frozen GameOuter, exact authenticated live joined
// generation; this is never a Go flag echo or an Applied/Stop grant.
func(g *V4WindowsAuthenticatedGameGroup) NativeGameOuterRepairEffective(
 ctx context.Context,
)(uint32,error){
 if g==nil||ctx==nil{return 0,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return 0,err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||len(g.members)==0{return 0,errV4WindowsOwner}
 proc,err:=g.members[0].bridge.fixedProc("wbd_m0_win_game_native_v4_outer_repair_effective")
 if err!=nil{return 0,err}
 var enabled uint32
 if err=winOwnerCall(proc,uintptr(g.joined),uintptr(unsafe.Pointer(&enabled)));err!=nil||enabled>1{
  return 0,errV4WindowsOwner
 }
 return enabled,nil
}

// After four-stage OS Apply and actual original owner liveness, ask
// the SAME Game2/4 Rust TX to prepare a kernel TCP listener.
 // Both independent TLS group sizes share ONE original TCP controller; Caller MUST
// install an exact owned Defender rule before enabling it.
func(g *V4WindowsAuthenticatedGameGroup) plan029GameTCPControl(
 ctx context.Context,operation,port uint16,
)(uint16,error){
 if g==nil||ctx==nil||operation!=1&&operation!=2||
  operation==1&&port!=0||operation==2&&port==0{
  return 0,errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return 0,err}
 g.mu.Lock()
 if g.closed||g.joined==0||(len(g.members)!=2&&len(g.members)!=4)||g.members[0]==nil{
  g.mu.Unlock();return 0,errV4WindowsOwner
 }
 first:=g.members[0];g.mu.Unlock()
 if first.bridge==nil||first.device==nil{return 0,errV4WindowsOwner}
 state,err:=first.OriginalOwnerReadback()
 if err!=nil{return 0,err}
 if !plan029PostApplyOriginalOwnerReady(state){return 0,errV4WindowsOwner}
 req:=v4WindowsNativeTCPControlV1{Version:1,
  Owner:first.bridge.handle,Epoch:first.bridge.epoch,
  LUID:first.device.identity.LUID,IfIndex:first.device.identity.InterfaceIndex,
  Operation:operation,Port:port}
 req.Size=uint32(unsafe.Sizeof(req))
 proc,err:=first.bridge.fixedProc("wbd_m0_win_game_native_v4_tcp_control")
 if err!=nil{return 0,err}
 err=winOwnerCall(proc,uintptr(unsafe.Pointer(&req)))
 runtime.KeepAlive(req)
 if err!=nil||req.Port==0{return 0,errV4WindowsOwner}
 if operation==2&&req.Port!=port{return 0,errV4WindowsOwner}
 return req.Port,nil
}
func(g *V4WindowsAuthenticatedGameGroup) Plan029GamePrepareNativeTCPAfterOSApply(
 ctx context.Context,
)(uint16,error){return g.plan029GameTCPControl(ctx,1,0)}
func(g *V4WindowsAuthenticatedGameGroup) Plan029GameEnableNativeTCPAfterDefender(
 ctx context.Context,port uint16,
)error{
 _,err:=g.plan029GameTCPControl(ctx,2,port);return err
}

// Begin only the selected new port's cold FakeTCP transport. The group
// remains active and no existing lane is stopped or reconfigured.
// No caller may publish this as a new M4 lane before native commit.
func(g *V4WindowsAuthenticatedGameGroup) BeginNativeGameLaneCandidate(
 ctx context.Context,cfg faketcp.NpcapConfig,
)(*faketcp.XdpGameCandidate,error){
 if g==nil||ctx==nil{return nil,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return nil,err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||(len(g.members)!=2&&len(g.members)!=4)||g.staged!=nil||g.retiring!=nil{return nil,ErrAdmissionUnsupported}
 b:=g.members[0].bridge
 port,err:=b.fixedProc("wbd_m0_win_game_candidate_port");if err!=nil{return nil,err}
 read,err:=b.fixedProc("wbd_m0_win_game_candidate_read");if err!=nil{return nil,err}
 write,err:=b.fixedProc("wbd_m0_win_game_candidate_write");if err!=nil{return nil,err}
 return faketcp.BeginXdpGameCandidate(g.joined,cfg,port,read,write)
}
