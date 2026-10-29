//go:build windows && wbd_v4_embedded_go

package realityfront

// PLAN026: cold-only NativeOwner ABI on the SAME authenticated original-Go
// TLS-derived Rust handle. No business packet crosses Go/Rust after start.
import (
    "context"
    "runtime"
    "unsafe"
)

type V4WindowsNpcapNativeFnsV1 struct {
    NextEx,SendPacket,GetEvent uintptr
    QueueAlloc,QueueTransmit,QueueDestroy uintptr
}
type V4WindowsWintunNativeFnsV1 struct {
    Receive,Release,Allocate,Send uintptr
}
// Same #[repr(C)] layout as wbd-engine/v4_windows_native_runtime.rs.
type V4WindowsNativeIOV1 struct {
    Version,Size uint32
    Owner uint64
    Epoch [16]byte
    LUID uint64
    IfIndex,PathMTU uint32
    InitialTXSeq,InitialRXSeq uint32
    LocalIP,PeerIP [4]byte
    LocalPort,PeerPort uint16
    SourceMAC,NextHopMAC [6]byte
    RXCapture,TXCapture,WintunSession,WintunReadEvent uintptr
    Npcap V4WindowsNpcapNativeFnsV1
    Wintun V4WindowsWintunNativeFnsV1
}
type V4WindowsNativeWorkerStatsV1 struct {
    Version,Size uint32
    TXCopied,RXDelivered,TXAfterRX,Rejected uint64
    WorkerError int32
    Workers uint32
}
// The native V2 wrapper changes the operating mode without touching the
// proven 192-byte V1 device/identity handoff. Exactly one of Fixed or Auto
// may use the same two Rust workers; Game needs multi-lane attachment.
type V4WindowsNativeIOV2 struct {
    Version,Size uint32
    Mode,Reserved uint32
    Normal V4WindowsNativeIOV1
}
func(s *V4WindowsAuthenticatedClientOwner) StartNativeIO(
    ctx context.Context,cfg V4WindowsNativeIOV1,
) error {
    return s.StartNativeIOForMode(ctx,cfg,0)
}
func(s *V4WindowsAuthenticatedClientOwner) StartNativeIOForMode(
    ctx context.Context,cfg V4WindowsNativeIOV1,mode uint32,
) error {
    return s.StartNativeIOForModePolicy(ctx,cfg,mode,false)
}
// AutoPolicy is one cold native ABI bit, not a second hotpath controller.
func(s *V4WindowsAuthenticatedClientOwner) StartNativeIOForModePolicy(
    ctx context.Context,cfg V4WindowsNativeIOV1,mode uint32,aggressive bool,
) error {
    if mode>2{return errV4WindowsOwner}
    if s==nil||s.bridge==nil||s.device==nil||ctx==nil {
        return errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return err}
    state,err:=s.OriginalOwnerReadback()
    if err!=nil{return err}
    if !state.OwnerActive||!state.DeviceBound||state.DeviceQuiesced||
       state.ServerSide||state.ProductApplied{return errV4WindowsOwner}
    cfg.Version=1
    cfg.Size=uint32(unsafe.Sizeof(cfg))
    cfg.Owner=s.bridge.handle
    cfg.Epoch=s.bridge.epoch
    cfg.LUID=s.device.identity.LUID
    cfg.IfIndex=s.device.identity.InterfaceIndex
    if cfg.PathMTU==0||cfg.RXCapture==0||cfg.TXCapture==0||
       cfg.WintunSession==0||cfg.WintunReadEvent==0{return errV4WindowsOwner}
    if mode==0{
        proc,err:=s.bridge.fixedProc("wbd_m0_win_native_v1_start")
        if err!=nil{return err}
        err=winOwnerCall(proc,uintptr(unsafe.Pointer(&cfg)))
        runtime.KeepAlive(cfg)
        return err
    }
    v2:=V4WindowsNativeIOV2{Version:2,Mode:mode,Normal:cfg}
    if mode==2&&aggressive{v2.Reserved=1}
    v2.Size=uint32(unsafe.Sizeof(v2))
    proc,err:=s.bridge.fixedProc("wbd_m0_win_native_v2_start")
    if err!=nil{return err}
    err=winOwnerCall(proc,uintptr(unsafe.Pointer(&v2)))
    runtime.KeepAlive(v2)
    return err
}
// An early segment was read by the cold Go capture reader during the TLS
// handoff. It is copied into the Rust RX worker's bounded EARLY queue and
// undergoes the normal M3 AEAD/PN proof, never direct Wintun delivery.
func(s *V4WindowsAuthenticatedClientOwner) OfferNativeEarly(
    ctx context.Context,seq uint32,wire []byte,
)error{
    if s==nil||s.bridge==nil||ctx==nil||len(wire)<51||len(wire)>2048{
        return errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return err}
    proc,err:=s.bridge.fixedProc("wbd_m0_win_native_v1_early")
    if err!=nil{return err}
    err=winOwnerCall(proc,uintptr(s.bridge.handle),uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)))
    runtime.KeepAlive(wire)
    return err
}
func(s *V4WindowsAuthenticatedClientOwner) NativeIOStats(
    ctx context.Context,
)(V4WindowsNativeWorkerStatsV1,error){
    var state V4WindowsNativeWorkerStatsV1
    if s==nil||s.bridge==nil||ctx==nil{return state,errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return state,err}
    proc,err:=s.bridge.fixedProc("wbd_m0_win_native_v1_stats")
    if err!=nil{return state,err}
    err=winOwnerCall(proc,uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&state)))
    runtime.KeepAlive(&state)
    if err!=nil{return state,err}
    if state.Version!=1||state.Size!=uint32(unsafe.Sizeof(state))||
       state.Workers!=2{return state,errV4WindowsOwner}
    return state,nil
}
// The active original M1/Rust Auto actor is the sole grade authority.
// This read-only C ABI returns requested and truly source/M2 Applied values.
type V4WindowsRustAutoStateV1 struct {
    Version,Size uint32
    RequestedRevision,AppliedRevision uint64
    Profile,Applied uint32
}
func(s *V4WindowsAuthenticatedClientOwner) ReadBoundRustAutoState(
    ctx context.Context,
)(V4WindowsRustAutoStateV1,error){
    var value V4WindowsRustAutoStateV1
    if ctx==nil||s==nil||s.bridge==nil||s.device==nil{
        return value,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return value,err}
    proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v9_rust_auto_state")
    if err!=nil{return value,err}
    value.Size=uint32(unsafe.Sizeof(value))
    err=winOwnerCall(proc,uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&value)),uintptr(unsafe.Sizeof(value)))
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||value.Version!=1||value.Size!=uint32(unsafe.Sizeof(value))||
        value.Profile>6||value.Applied>1{
        return value,errV4WindowsOwner
    }
    return value,nil
}
// Bound policy and effective are from the ORIGINAL Rust TX HealthClock.
// These do not claim OS WAL/GUI Applied and must precede native worker Start.
type V4WindowsNativeHealthPolicyV1 struct{
 Version,Size uint32
 IntervalSeconds,DeadSeconds,DormantSeconds uint32
 Configured uint32
}
func(s *V4WindowsAuthenticatedClientOwner) SetBoundNativeHealthPolicy(
 ctx context.Context,interval,dead,dormant uint32,
)(V4WindowsNativeHealthPolicyV1,error){
 var p V4WindowsNativeHealthPolicyV1
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
  interval<1||interval>3600||dead>86400||
  uint64(dead)<uint64(interval)*3{
  return p,errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return p,err}
 p=V4WindowsNativeHealthPolicyV1{Version:1,
  Size:uint32(unsafe.Sizeof(p)),IntervalSeconds:interval,
  DeadSeconds:dead,DormantSeconds:dormant}
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v9_native_health_config")
 if err!=nil{return p,err}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),
  uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&p)))
 runtime.KeepAlive(p)
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil{return p,err}
 effective,err:=s.ReadBoundNativeHealthPolicy(ctx)
 if err!=nil||effective.IntervalSeconds!=interval||
  effective.DeadSeconds!=dead||effective.DormantSeconds!=dormant{
  return effective,errV4WindowsOwner
 }
 return effective,nil
}
func(s *V4WindowsAuthenticatedClientOwner) ReadBoundNativeHealthPolicy(
 ctx context.Context,
)(V4WindowsNativeHealthPolicyV1,error){
 var p V4WindowsNativeHealthPolicyV1
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil{
  return p,errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return p,err}
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v9_native_health_effective")
 if err!=nil{return p,err}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),
  uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&p)))
 runtime.KeepAlive(&p)
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil||p.Version!=1||p.Size!=uint32(unsafe.Sizeof(p))||
  p.Configured!=1||p.IntervalSeconds==0||
  uint64(p.DeadSeconds)<3*uint64(p.IntervalSeconds){
  return p,errV4WindowsOwner
 }
 return p,nil
}
// Must be called BEFORE Go releases either Npcap capture loan, Wintun
// native loan, Wintun EndSession or original scoped Rust crypto owner.
func(s *V4WindowsAuthenticatedClientOwner) JoinNativeIO(
    ctx context.Context,
)error{
    if s==nil||s.bridge==nil||ctx==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    proc,err:=s.bridge.fixedProc("wbd_m0_win_native_v1_stop")
    if err!=nil{return err}
    return winOwnerCall(proc,uintptr(s.bridge.handle))
}
