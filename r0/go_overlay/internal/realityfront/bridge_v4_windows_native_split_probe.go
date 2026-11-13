//go:build windows && wbd_v4_embedded_go
package realityfront

// PLAN029 private V3: one original credential/Win32 Wintun generation,
// one synchronous COLD Go→Rust copy. No product V2 selector uses this.
import ("context";"runtime";"unsafe")
type V4WindowsColdCIDR struct{
 Network [4]byte
 Bits uint8
 Reserved [3]byte
}
type V4WindowsColdSplitConfig struct{
 RouteMode,PhysicalIfIndex uint32
 PhysicalSource,Lease4,DirectDNS,TunnelDNS,FakeStart,FakeEnd [4]byte
 InnerMTU,DirectHard uint32
 CN,LAN,Direct []V4WindowsColdCIDR
 Domains []byte
 FakeJournalPath []byte
 // Cold deferred kernel TCP plan. This never implies OS Applied or grants
 // the listener any ingress permission before exact Defender receipt.
 TCPSynthetic4 [4]byte
 TCPOwned bool
}
type v4WindowsColdSplitWireV1 struct{
 Version,Size uint32
 RouteMode,PhysicalIfIndex uint32
 PhysicalSource,Lease4,DirectDNS,TunnelDNS,FakeStart,FakeEnd [4]byte
 InnerMTU,DirectHard uint32
 CNCount,LANCount,DirectCount uint32
 CN,LAN,Direct uintptr
 DomainsLength uint32
 Domains uintptr
 JournalLength uint32
 JournalPath uintptr
 TCPSynthetic4 [4]byte
 TCPOwned uint32
}
type v4WindowsNativeIOV3Probe struct{
 Version,Size uint32
 V2 V4WindowsNativeIOV2
 Split v4WindowsColdSplitWireV1
}
// Fixed Rust repr(C) 48-byte single-generation cold command. The same
// original Go authenticated Rust worker chooses the kernel port AFTER
// four-stage OS Apply. A prepared listener cannot admit Direct TCP until
// an independently exact-owned Defender Allow is installed/read back.
type v4WindowsNativeTCPControlV1 struct{
 Version,Size uint32
 Owner uint64
 Epoch [16]byte
 LUID uint64
 IfIndex uint32
 Port,Operation uint16 // prepare=1; runtime enable not exposed here
}
func(c *V4WindowsColdSplitConfig)wire()(v4WindowsColdSplitWireV1,error){
 var w v4WindowsColdSplitWireV1
 if c==nil||c.RouteMode>2||c.PhysicalIfIndex==0||
  c.InnerMTU<576||c.InnerMTU>1500||c.DirectHard==0||
  c.DirectHard>16384||len(c.CN)>32768||len(c.LAN)>32768||
  len(c.Direct)>32768||len(c.Domains)>1<<20||
  len(c.FakeJournalPath)>4096||
  c.TCPOwned{ // NEVER arm before OS Apply and exact Defender proof.
  return w,errV4WindowsOwner
 }
 w=v4WindowsColdSplitWireV1{
  Version:1,Size:uint32(unsafe.Sizeof(w)),
  RouteMode:c.RouteMode,PhysicalIfIndex:c.PhysicalIfIndex,
  PhysicalSource:c.PhysicalSource,Lease4:c.Lease4,
  DirectDNS:c.DirectDNS,TunnelDNS:c.TunnelDNS,
  FakeStart:c.FakeStart,FakeEnd:c.FakeEnd,
  InnerMTU:c.InnerMTU,DirectHard:c.DirectHard,
  CNCount:uint32(len(c.CN)),LANCount:uint32(len(c.LAN)),
  DirectCount:uint32(len(c.Direct)),DomainsLength:uint32(len(c.Domains)),
  JournalLength:uint32(len(c.FakeJournalPath)),
  TCPSynthetic4:c.TCPSynthetic4,
 }
 if c.TCPOwned{w.TCPOwned=1}
 if len(c.CN)>0{w.CN=uintptr(unsafe.Pointer(&c.CN[0]))}
 if len(c.LAN)>0{w.LAN=uintptr(unsafe.Pointer(&c.LAN[0]))}
 if len(c.Direct)>0{w.Direct=uintptr(unsafe.Pointer(&c.Direct[0]))}
 if len(c.Domains)>0{w.Domains=uintptr(unsafe.Pointer(&c.Domains[0]))}
 if len(c.FakeJournalPath)>0{w.JournalPath=uintptr(unsafe.Pointer(&c.FakeJournalPath[0]))}
 return w,nil
}
// ProductApplied in OriginalOwnerReadback is a legacy device field that
// always reads false. Actual N4 OS Applied is verified by the caller's
// product.Apply() and product.LiveReceipt() BEFORE these cold methods.
// Do not fabricate legacy Applied=true to overcome this false prerequisite.
// This check proves only current original authenticated device liveness;
// Rust still checks generation/epoch/LUID/index, and exact Defender owned
// Allow is required separately before enabling TCP.
func plan029PostApplyOriginalOwnerReady(state V4WindowsScopedOwnerReadback) bool {
 return state.OwnerActive && state.DeviceBound &&
  !state.DeviceQuiesced && !state.ServerSide
}
// The first part of the post-Apply, two-phase Direct kernel TCP handshake.
// It does not make the listener reachable: the V3 Rust owner remains
// fail-closed until a separate exact Defender receipt authorizes a
// later control command. This bridge intentionally exposes PREPARE only.
func(s *V4WindowsAuthenticatedClientOwner) Plan029PrepareNativeTCPAfterOSApply(
 ctx context.Context,
)(uint16,error){
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil{
  return 0,errV4WindowsOwner
 }
 if e:=ctx.Err();e!=nil{return 0,e}
 state,e:=s.OriginalOwnerReadback()
 if e!=nil{return 0,e}
 if !plan029PostApplyOriginalOwnerReady(state){return 0,errV4WindowsOwner}
 req:=v4WindowsNativeTCPControlV1{Version:1,
  Owner:s.bridge.handle,Epoch:s.bridge.epoch,
  LUID:s.device.identity.LUID,IfIndex:s.device.identity.InterfaceIndex,
  Operation:1}
 req.Size=uint32(unsafe.Sizeof(req))
 proc,e:=s.bridge.fixedProc("wbd_m0_win_native_tcp_control_v1")
 if e!=nil{return 0,e}
 if e=winOwnerCall(proc,uintptr(unsafe.Pointer(&req)));e!=nil{return 0,e}
 if req.Port==0{return 0,errV4WindowsOwner}
 runtime.KeepAlive(req)
 return req.Port,nil
}
// The caller must hold exact owned Defender Add/readback for this
// port before ENABLE. This cold FFI cannot create firewall permissions.
func(s *V4WindowsAuthenticatedClientOwner) Plan029EnableNativeTCPAfterDefender(
 ctx context.Context,port uint16,
)error{
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil||port==0{return errV4WindowsOwner}
 if e:=ctx.Err();e!=nil{return e}
 state,e:=s.OriginalOwnerReadback()
 if e!=nil{return e}
 if !plan029PostApplyOriginalOwnerReady(state){return errV4WindowsOwner}
 req:=v4WindowsNativeTCPControlV1{Version:1,
  Owner:s.bridge.handle,Epoch:s.bridge.epoch,
  LUID:s.device.identity.LUID,IfIndex:s.device.identity.InterfaceIndex,
  Port:port,Operation:2}
 req.Size=uint32(unsafe.Sizeof(req))
 proc,e:=s.bridge.fixedProc("wbd_m0_win_native_tcp_control_v1")
 if e!=nil{return e}
 if e=winOwnerCall(proc,uintptr(unsafe.Pointer(&req)));e!=nil{return e}
 runtime.KeepAlive(req)
 if req.Port!=port{return errV4WindowsOwner}
 return nil
}
func(s *V4WindowsAuthenticatedClientOwner) StartNativeIOWithColdSplitProbe(
 ctx context.Context,cfg V4WindowsNativeIOV1,mode uint32,aggressive bool,
 cold V4WindowsColdSplitConfig,
)error{
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil||mode>2{
  return errV4WindowsOwner
 }
 if e:=ctx.Err();e!=nil{return e}
 state,e:=s.OriginalOwnerReadback()
 if e!=nil{return e}
 if !state.OwnerActive||!state.DeviceBound||state.DeviceQuiesced||
  state.ServerSide||state.ProductApplied{return errV4WindowsOwner}
 cfg.Version=1;cfg.Size=uint32(unsafe.Sizeof(cfg))
 cfg.Owner=s.bridge.handle;cfg.Epoch=s.bridge.epoch
 cfg.LUID=s.device.identity.LUID;cfg.IfIndex=s.device.identity.InterfaceIndex
 if cfg.PathMTU==0||cfg.RXCapture==0||cfg.TXCapture==0||
  cfg.WintunSession==0||cfg.WintunReadEvent==0{return errV4WindowsOwner}
 split,e:=cold.wire();if e!=nil{return e}
 v2:=V4WindowsNativeIOV2{Version:2,Mode:mode,Normal:cfg}
 if mode==2&&aggressive{v2.Reserved=1}
 if s.bridge.sackPermitted{v2.Reserved|=2}
 v2.Size=uint32(unsafe.Sizeof(v2))
 v3:=v4WindowsNativeIOV3Probe{Version:3,V2:v2,Split:split}
 v3.Size=uint32(unsafe.Sizeof(v3))
 proc,e:=s.bridge.fixedProc("wbd_m0_win_native_v3_start")
 if e!=nil{return e}
 e=winOwnerCall(proc,uintptr(unsafe.Pointer(&v3)))
 runtime.KeepAlive(cold)
 runtime.KeepAlive(v3)
 return e
}
