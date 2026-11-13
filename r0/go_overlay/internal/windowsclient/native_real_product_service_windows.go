//go:build windows

package windowsclient

// M0 PLAN020 actual product service wiring, not a unit-test assembly.
// The old Go public CLI must supply the ORIGINAL protected-TLS Rust
// generation via N4NativeProductLiveOwner. No option/boolean/READY line
// can fabricate an owner, a kernel first/reverse packet, or OS Applied.
import (
 "context"
 "errors"
 "fmt"
 "net/netip"
 "sync"
 "time"
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
 tcpDefender *n4Plan029DefenderKey
 applied bool
 stopped bool
}

// N4PrepareRealWindowsProduct performs the entire original owner -> signed
// native kernel -> no-WFP lease/MTU/DNS/routes WAL assembly with
// zero network writes. This entry requires four genuine v2 stages,
// not an assemblyOnly shortcut, and requires a real original-TLS live owner.
// The caller MUST call Apply and Stop, including after a partial Apply.
func N4PrepareRealWindowsProduct(
 ctx context.Context,tun *TUN,plan NetworkPlan,
 id N4UnifiedIdentity,owner N4NativeProductLiveOwner,
 tcpSynthetic4 ...netip.Addr,
)(*N4RealWindowsProduct,error){
 if ctx==nil||owner==nil||tun==nil||!id.valid(){
  return nil,ErrN4NativeGuard
 }
 if err:=owner.VerifyOriginalNativeHold(ctx,id);err!=nil{return nil,err}
 if err:=owner.VerifyOriginalCredentialAndKernelOwner(ctx,id);err!=nil{
  return nil,err
 }
 // PLAN029: only the four actual Win32 writers, never a five-stage
 // legacy WFP guard or any non-WFP no-op adapter. Assembly alone grants
 // NOTHING: the current authenticated Rust packet owner must first bind
 // the original generation's exclusive kernel ring.
 txn,err:=n4AssembleWindowsNoWFPNativeTxn(ctx,tun,plan,id,tcpSynthetic4...)
 if err!=nil{return nil,err}
 // Real signed-Wintun PnP, generation and exclusive native ring readback;
 // the created ring lease is held until ALL native host changes are gone.
 kernel,err:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
 if err!=nil{return nil,err}
 // Give only the precise live M0 original TLS peer transport access to
 // the one exclusive native ring; no dummy packet proof can bypass it.
 if err=owner.BindOriginalNativePacketRing(ctx,id,kernel);err!=nil{
  return nil,errors.Join(err,kernel.Stop(context.Background()))
 }
 // Qualification is a ONE-WAY cold transition AFTER exclusive
 // real Wintun binding and verified original credential/Rust generation.
 // The four stages will still have to APPLY to Win32, verify the actual
 // OS rows, prove app-first+reverse and STOP cleanly in this SAME session
 // before any positive Applied or Ready receipt can exist.
 if err=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,owner);err!=nil{
  releaseCtx,cancel:=context.WithTimeout(context.Background(),30*time.Second)
  defer cancel()
  drained:=owner.DrainCryptoAndKernelLoans(releaseCtx,id)
  if drained!=nil{return nil,errors.Join(err,drained)}
  return nil,errors.Join(err,kernel.Stop(releaseCtx))
 }
 controller,err:=n4NewWindowsNativeProductController(txn,owner)
 if err!=nil{
  releaseCtx,cancel:=context.WithTimeout(context.Background(),30*time.Second)
  defer cancel()
  drained:=owner.DrainCryptoAndKernelLoans(releaseCtx,id)
  if drained!=nil{return nil,errors.Join(err,drained)}
  return nil,errors.Join(err,kernel.Stop(releaseCtx))
 }
 return &N4RealWindowsProduct{
  controller:controller,kernel:kernel,owner:owner,
  identity:id,
 },nil
}

// This is intentionally NOT a public Apply/Ready shortcut. The assembler
// returned assemblyOnly=true to prevent arbitrary callers from writing to
// Win32; ONLY the original-credential service, after a real current-owner
// Wintun loan has been bound, calls this once. In particular no v1 guard,
// fifth stage, mock or name-only adapter may be upgraded.
func n4AdmitAuthenticatedNoWFPProduct(
 ctx context.Context,txn *N4NativeUnifiedTxn,
 proof N4OriginalAuthenticatedPacketProof,
)error{
 if ctx==nil||txn==nil||proof==nil||!txn.noLegacyWFP||
  !txn.assemblyOnly||len(txn.stages())!=4||txn.Stages[4]!=nil{
  return ErrN4NativeGuard
 }
 if err:=ctx.Err();err!=nil{return err}
 if err:=txn.preflight();err!=nil{return err}
 l,ok:=txn.Stages[0].(n4WindowsNoWFPLeaseStage)
 if !ok||l.WALPath!=txn.Path||
  n4ValidateLeaseIntent(l.Lease)!=nil||
  l.Lease.InterfaceIndex!=txn.Identity.WintunIndex{
  return ErrN4NativeGuard
 }
 m,ok:=txn.Stages[1].(n4WindowsNoWFPMTUStage)
 if !ok||m.WALPath!=txn.Path||m.Target<576||m.Target>1500{
  return ErrN4NativeGuard
 }
 d,ok:=txn.Stages[2].(n4WindowsNoWFPDNSStage)
 if !ok||d.WALPath!=txn.Path||len(d.Servers)!=1{
  return ErrN4NativeGuard
 }
 r,ok:=txn.Stages[3].(n4WindowsNoWFPRouteStage)
 if !ok||r.WALPath!=txn.Path||r.Backend==nil{
  return ErrN4NativeGuard
 }
 if err:=proof.VerifyOriginalCredentialAndKernelOwner(ctx,txn.Identity);err!=nil{
  return err
 }
 txn.assemblyOnly=false
 return nil
}

// Apply publishes a live OS receipt only AFTER complete persistent
// no-WFP lease/MTU/DNS/routes WAL activation, authenticated Rust first and
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
 // If the original Rust/Wintun generation vanished while OS route
 // activation ran, NEVER return a positive receipt, and preserve WAL
 // for the caller's immediate owned Stop/Recover handling.
 if err=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{
  return empty,err
 }
 s.receipt=receipt
 s.applied=true
 return receipt,nil
}

// PLAN029 one kernel Direct TCP backend: only after actual complete
// four-stage OS Applied and Rust PREPARE returned its kernel listener port,
// persist one generation-bound intent/owned Defender Allow for synthetic /32.
func(s *N4RealWindowsProduct) Plan029ArmOwnedDirectTCP(
 ctx context.Context,port uint16,
)error{
 if s==nil||ctx==nil||port==0{return ErrN4NativeGuard}
 s.mu.Lock();defer s.mu.Unlock()
 if !s.applied||s.stopped||s.tcpDefender!=nil||
  s.owner==nil||s.controller==nil||s.controller.txn==nil{return ErrN4NativeGuard}
 txn:=s.controller.txn
 if !txn.noLegacyWFP||txn.assemblyOnly||len(txn.stages())!=4{return ErrN4NativeGuard}
 route,ok:=txn.Stages[3].(n4WindowsNoWFPRouteStage)
 if !ok||!route.SyntheticTCP4.IsValid()||route.Plan.StatePath==""{return ErrN4NativeGuard}
 if err:=s.owner.VerifyOriginalNativeHold(ctx,s.identity);err!=nil{return err}
 live,err:=txn.VerifyLiveOSApplied(ctx)
 if err!=nil{return err}
 if !live.AllNativeOSApplied{return ErrN4NativeGuard}
 key,err:=n4Plan029DefenderKeyFor(s.identity,route.Plan.Lease4.Addr(),route.SyntheticTCP4,port)
 if err!=nil{return err}
 // A later partial Add must remain recoverable by this same identity.
 s.tcpDefender=&key
 return n4Plan029DefenderInstall(ctx,n4Plan029DefenderSidecarPath(route.Plan.StatePath),
  s.identity,key,n4Plan029DefenderCOM{})
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
 // Exact own grant must be removed before its /32 route and original
 // Rust/Wintun loan. An ambiguous/foreign rule retains all WALs and
 // refuses false Disconnected. Stop can retry the same generation.
 if s.tcpDefender!=nil{
  if s.controller.txn==nil{return ErrN4NativeGuard}
  route,ok:=s.controller.txn.Stages[3].(n4WindowsNoWFPRouteStage)
  if !ok||route.Plan.StatePath==""{return ErrN4NativeGuard}
  err:=n4Plan029DefenderRecover(ctx,
   n4Plan029DefenderSidecarPath(route.Plan.StatePath),
   s.identity,*s.tcpDefender,n4Plan029DefenderCOM{})
  if err!=nil{return fmt.Errorf("PLAN029 owned Defender Stop: %w",err)}
  s.tcpDefender=nil
 }
 switch s.controller.state{
 case "applied","recovery_required":
  if err:=s.controller.Disconnect(ctx);err!=nil{
   fmt.Printf("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_disconnect result=FAIL error=%v\n",err)
   return err
  }
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
 if err:=s.kernel.Stop(ctx);err!=nil{
  fmt.Printf("M0_PLAN027_NATIVE_STOP_RESULT stage=kernel_lease result=FAIL error=%v\n",err)
  return err
 }
 if err:=s.owner.FinishOriginalNativeStop(ctx,s.identity);err!=nil{
  fmt.Printf("M0_PLAN027_NATIVE_STOP_RESULT stage=crypto_after_wal result=FAIL error=%v\n",err)
  return err
 }
 fmt.Println("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS")
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
