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
}
type v4WindowsNativeIOV3Probe struct{
 Version,Size uint32
 V2 V4WindowsNativeIOV2
 Split v4WindowsColdSplitWireV1
}
func(c *V4WindowsColdSplitConfig)wire()(v4WindowsColdSplitWireV1,error){
 var w v4WindowsColdSplitWireV1
 if c==nil||c.RouteMode>2||c.PhysicalIfIndex==0||
  c.InnerMTU<576||c.InnerMTU>1500||c.DirectHard==0||
  c.DirectHard>16384||len(c.CN)>32768||len(c.LAN)>32768||
  len(c.Direct)>32768||len(c.Domains)>1<<20{return w,errV4WindowsOwner}
 w=v4WindowsColdSplitWireV1{
  Version:1,Size:uint32(unsafe.Sizeof(w)),
  RouteMode:c.RouteMode,PhysicalIfIndex:c.PhysicalIfIndex,
  PhysicalSource:c.PhysicalSource,Lease4:c.Lease4,
  DirectDNS:c.DirectDNS,TunnelDNS:c.TunnelDNS,
  FakeStart:c.FakeStart,FakeEnd:c.FakeEnd,
  InnerMTU:c.InnerMTU,DirectHard:c.DirectHard,
  CNCount:uint32(len(c.CN)),LANCount:uint32(len(c.LAN)),
  DirectCount:uint32(len(c.Direct)),DomainsLength:uint32(len(c.Domains)),
 }
 if len(c.CN)>0{w.CN=uintptr(unsafe.Pointer(&c.CN[0]))}
 if len(c.LAN)>0{w.LAN=uintptr(unsafe.Pointer(&c.LAN[0]))}
 if len(c.Direct)>0{w.Direct=uintptr(unsafe.Pointer(&c.Direct[0]))}
 if len(c.Domains)>0{w.Domains=uintptr(unsafe.Pointer(&c.Domains[0]))}
 return w,nil
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
