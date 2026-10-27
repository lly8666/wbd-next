//go:build windows

package windowsclient

// M0 PLAN020 actual product service wiring, not a unit-test assembly.
// The old Go public CLI must supply the ORIGINAL protected-TLS Rust
// generation via N4NativeProductLiveOwner. No option/boolean/READY line
// can fabricate an owner, a kernel first/reverse packet, or OS Applied.
import (
 "context"
 "errors"
 "sync"
)

// N4OriginalCurrentPinnedWintunIdentity obtains fresh OS PnP identity
// directly from the ORIGINAL process-created Wintun before building any
// host-wide WFP/route/DNS/MTU WAL. A saved GUID/alias cannot become owner.
func N4OriginalCurrentPinnedWintunIdentity(
 ctx context.Context,tun *TUN,installation,generation [16]byte,
)(N4UnifiedIdentity,error){
 var id N4UnifiedIdentity
 if ctx==nil||tun==nil||installation==[16]byte{}||
  generation==[16]byte{}{return id,ErrN4NativeGuard}
 now,err:=tun.NativeIdentity(ctx)
 if err!=nil||!now.CreatedByProcess||now.LUID==0||now.Index==0{
  return id,errors.Join(ErrN4NativeGuard,err)
 }
 guid,err:=n4NativeInterfaceGUID(now.Index)
 if err!=nil{return id,err}
 id=N4UnifiedIdentity{
  Installation:installation,Generation:generation,
  WintunLUID:now.LUID,WintunIndex:now.Index,
  WintunGUID:guid.String(),AdapterAlias:tun.Name(),
 }
 pin,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return N4UnifiedIdentity{},err}
 id.PnPInstanceSHA256=pin.InstanceSHA256
 if !n4ValidPinnedPnPHash(id.PnPInstanceSHA256){
  return N4UnifiedIdentity{},ErrN4NativeGuard
 }
 owner:=N4WindowsCreatedWintunReservation{
  Tunnel:tun,Installation:installation,Generation:generation,
 }
 if err=owner.Verify(ctx,id);err!=nil{return N4UnifiedIdentity{},err}
 return id,nil
}

// N4NativeProductLiveOwner bridges real original-Go credential TLS -> Rust
// M1/M3 peer -> same process-created signed Wintun. Unlike the lower-level
// transaction test interface, a production owner must independently verify
// that its Win32 device hold remains live AFTER kernel loans have drained
// and across all persistent WFP/default-route/DNS/IPv6/MTU undo operations.
// FinishOriginalNativeStop retires Rust + the original Wintun hold ONLY
// after native host OS cleanup has been positively read back.
type N4NativeProductLiveOwner interface {
 N4OriginalAuthenticatedPacketProof
 VerifyOriginalNativeHold(context.Context,N4UnifiedIdentity) error
 BindOriginalNativePacketRing(context.Context,N4UnifiedIdentity,*N4OriginalKernelPacketLease)error
 FinishOriginalNativeStop(context.Context,N4UnifiedIdentity) error
}

// N4RealWindowsProduct wires one authenticated Rust owner, one original
// Wintun-native kernel ring lease and one fully durable five-stage OS WAL.
// All public state transitions originate in this object, NOT the mere
// existence of a child process, a Wintun alias or a disk WAL file.
type N4RealWindowsProduct struct {
 mu sync.Mutex
 controller *N4WindowsNativeProductController
 kernel *N4OriginalKernelPacketLease
 owner N4NativeProductLiveOwner
 identity N4UnifiedIdentity
 receipt N4NativeLiveOSReceipt
 applied bool
 stopped bool
}

// N4PrepareRealWindowsProduct performs the entire original owner -> signed
// native kernel -> persistent WFP/compact-route/DNS/MTU WAL assembly with
// zero network writes. It is a concrete entry into the 5 original OS stages,
// not an assemblyOnly shortcut, and requires a real original-TLS live owner.
// The caller MUST call Apply and Stop, including after a partial Apply.
func N4PrepareRealWindowsProduct(
 ctx context.Context,tun *TUN,plan NetworkPlan,
 id N4UnifiedIdentity,owner N4NativeProductLiveOwner,
)(*N4RealWindowsProduct,error){
 if ctx==nil||owner==nil||tun==nil||!id.valid(){
  return nil,ErrN4NativeGuard
 }
 if err:=owner.VerifyOriginalNativeHold(ctx,id);err!=nil{return nil,err}
 if err:=owner.VerifyOriginalCredentialAndKernelOwner(ctx,id);err!=nil{
  return nil,err
 }
 // Real signed-Wintun PnP, generation and exclusive native ring readback;
 // the created ring lease is held until ALL native host changes are gone.
 kernel,err:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
 if err!=nil{return nil,err}
 // Give only the precise live M0 original TLS peer transport access to
 // the one exclusive native ring; no dummy packet proof can bypass it.
 if err=owner.BindOriginalNativePacketRing(ctx,id,kernel);err!=nil{
  return nil,errors.Join(err,kernel.Stop(context.Background()))
 }
 guard:=&n4WindowsPersistentWFPGuard{
  InstallationID:id.Installation,WintunLUID:id.WintunLUID,
  ExclusiveSingleWintun:true,
 }
 controller,err:=n4AssembleWindowsQualifiedFullTxn(
  ctx,tun,plan,id,guard,owner,
 )
 if err!=nil{
  // No host network writes occurred; do not stop someone else's Rust
  // or network owner. Release only OUR new ring claim.
  releaseCtx:=context.Background()
  return nil,errors.Join(err,kernel.Stop(releaseCtx))
 }
 return &N4RealWindowsProduct{
  controller:controller,kernel:kernel,owner:owner,
  identity:id,
 },nil
}

// Apply publishes a live OS receipt only AFTER complete persistent
// WFP/lease/MTU/DNS/routes WAL activation, authenticated Rust first and
// reverse native kernel app delivery, and an independent OS readback.
// A partial failure is NEVER Converted to product Applied. The owner and
// ring remain held for recovery while WAL could still exist.
func(s *N4RealWindowsProduct) Apply(
 ctx context.Context,
)(N4NativeLiveOSReceipt,error){
 empty:=N4NativeLiveOSReceipt{Schema:N4NativeLiveOSSchema}
 if s==nil||ctx==nil{return empty,ErrN4NativeGuard}
 s.mu.Lock();defer s.mu.Unlock()
 if s.stopped||s.applied||s.controller==nil||s.owner==nil||
  s.kernel==nil{return empty,ErrN4JournalConflict}
 if err:=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{
  return empty,err
 }
 receipt,err:=s.controller.Connect(ctx)
 if err!=nil{return empty,err}
 if !receipt.AllNativeOSApplied{return empty,ErrN4NativeGuard}
 // If the original Rust/Wintun generation vanished while OS route/WFP
 // activation ran, NEVER return a positive receipt, and preserve WAL
 // for the caller's immediate owned Stop/Recover handling.
 if err=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{
  return empty,err
 }
 s.receipt=receipt
 s.applied=true
 return receipt,nil
}

// Stop drains first, restores every native OS stage via WAL reverse CAS,
// verifies no owned sidecar/host mutation remains, releases the kernel
// lease, and finally stops the original Rust TLS/Wintun generation.
// On any error state is retained for an operator retry. It never reports
// clean Disconnected solely from Go process exit.
func(s *N4RealWindowsProduct) Stop(ctx context.Context)error{
 if s==nil||ctx==nil{return ErrN4NativeGuard}
 s.mu.Lock();defer s.mu.Unlock()
 if s.stopped{return nil}
 if s.controller==nil||s.kernel==nil||s.owner==nil{
  return ErrN4NativeGuard
 }
 switch s.controller.state{
 case "applied","recovery_required":
  if err:=s.controller.Disconnect(ctx);err!=nil{return err}
 case "requested":
  // No stage is armed; still inspect actual OS/WAL absence before
  // retiring Rust, because a previous interrupted Connect may exist.
  if err:=s.controller.txn.VerifyLiveOSDisconnected(ctx);err!=nil{
   return err
  }
 case "disconnected":
  // Previous Stop may have finished OS cleanup then failed to stop
  // Rust; repeat the final phase only after another OS absence probe.
  if err:=s.controller.txn.VerifyLiveOSDisconnected(ctx);err!=nil{
   return err
  }
 default:
  return ErrN4JournalConflict
 }
 if err:=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{
  return err
 }
 if err:=s.kernel.Stop(ctx);err!=nil{return err}
 if err:=s.owner.FinishOriginalNativeStop(ctx,s.identity);err!=nil{
  return err
 }
 s.applied=false
 s.receipt=N4NativeLiveOSReceipt{}
 s.stopped=true
 return nil
}

// RuntimeMTU is at most a 1Hz call from the original client's existing
// telemetry timer. The entire original M4 WAL + live same-generation OS
// interface MTU must still match, or the product stops and retains its
// owned recovery state. This is NOT a dynamic reconfiguration write.
func(s *N4RealWindowsProduct) RuntimeMTU(ctx context.Context)(uint32,error){
 if s==nil||ctx==nil{return 0,ErrN4NativeGuard}
 s.mu.Lock();defer s.mu.Unlock()
 if !s.applied||s.stopped||s.controller==nil||s.owner==nil||
   s.controller.txn==nil{return 0,ErrN4NativeGuard}
 if err:=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{return 0,err}
 return s.controller.txn.LiveConfiguredMTU(ctx)
}
// LiveReceipt is the last actual complete OS readback, NOT a cached Go
// process-ready line. It cannot certify real current host state without
// checking under the transaction machine gate again.
func(s *N4RealWindowsProduct) LiveReceipt(
 ctx context.Context,
)(N4NativeLiveOSReceipt,error){
 empty:=N4NativeLiveOSReceipt{Schema:N4NativeLiveOSSchema}
 if s==nil||ctx==nil{return empty,ErrN4NativeGuard}
 s.mu.Lock();defer s.mu.Unlock()
 if !s.applied||s.stopped||s.owner==nil{
  return empty,ErrN4NativeGuard
 }
 if err:=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{
  return empty,err
 }
 return s.controller.txn.VerifyLiveOSApplied(ctx)
}
