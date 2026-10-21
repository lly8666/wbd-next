//go:build windows
package windowsclient

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "time"
)

// Implemented only by original credential Go TLS -> native signed Wintun ->
// Rust authenticated M1/M3, never from CLI flags or synthetic traffic.
type N4OriginalAuthenticatedPacketProof interface {
 VerifyOriginalCredentialAndKernelOwner(context.Context,N4UnifiedIdentity)error
 VerifyBidirectionalAuthenticatedFirstDelivery(context.Context,N4UnifiedIdentity)error
 DrainCryptoAndKernelLoans(context.Context,N4UnifiedIdentity)error
}

// This is the REAL persistent Windows WFP writer. It remains private to a
// fully authenticated native session, not an alternative shell or mock guard.
// The parent WAL durably writes intent BEFORE this stage mutates the host.
type n4QualifiedWindowsWFPStage struct{ n4WindowsGuardStage }
func(s n4QualifiedWindowsWFPStage)Apply(ctx context.Context,id N4UnifiedIdentity,b json.RawMessage)error{
 if err:=s.valid(id,b);err!=nil{return err}
 state,err:=s.Guard.ownedState(ctx);if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4JournalConflict}
 policy,err:=s.Guard.plan();if err!=nil{return err}
 if err:=n4ValidateExactWFPArmPlan(policy);err!=nil{return err}
 return n4WFPArmExactPlan(ctx,policy)
}

type N4WindowsNativeProductController struct{
 txn *N4NativeUnifiedTxn
 proof N4OriginalAuthenticatedPacketProof
 state string
}
func n4NewWindowsNativeProductController(txn *N4NativeUnifiedTxn,proof N4OriginalAuthenticatedPacketProof)(*N4WindowsNativeProductController,error){
 if txn==nil||proof==nil||txn.assemblyOnly{return nil,ErrN4NativeGuard}
 if err:=txn.preflight();err!=nil{return nil,err}
 return &N4WindowsNativeProductController{txn:txn,proof:proof,state:"requested"},nil
}

// The 5 original native OS stages are reused without editing the pinned M4
// donor. This only constructs an owner; it makes NO host changes until
// authenticated Connect. Original Wintun PnP, CAS and cross-process gate
// preflights are still performed by the existing assembler.
func n4AssembleWindowsQualifiedFullTxn(ctx context.Context,tun *TUN,plan NetworkPlan,id N4UnifiedIdentity,
 guard *n4WindowsPersistentWFPGuard,proof N4OriginalAuthenticatedPacketProof,
)(*N4WindowsNativeProductController,error){
 if ctx==nil||proof==nil||guard==nil||!guard.Durable(){return nil,ErrN4NativeGuard}
 if err:=proof.VerifyOriginalCredentialAndKernelOwner(ctx,id);err!=nil{return nil,err}
 txn,err:=n4AssembleWindowsNativeOwnedTxn(ctx,tun,plan,id,guard);if err!=nil{return nil,err}
 if !txn.assemblyOnly{return nil,ErrN4NativeGuard}
 txn.Stages[0]=n4QualifiedWindowsWFPStage{n4WindowsGuardStage{Guard:guard}}
 txn.assemblyOnly=false
 return n4NewWindowsNativeProductController(txn,proof)
}

// No public Applied is possible until original TLS/Rust proof, real first and
// reverse app packets and an independent five-stage native OS readback all
// succeed on the same live Wintun generation.
func(c *N4WindowsNativeProductController)Connect(ctx context.Context)(N4NativeLiveOSReceipt,error){
 empty:=N4NativeLiveOSReceipt{Schema:N4NativeLiveOSSchema}
 if c==nil||ctx==nil||c.txn==nil||c.proof==nil{return empty,ErrN4NativeGuard}
 if c.state!="requested"{return empty,ErrN4JournalConflict}
 if err:=ctx.Err();err!=nil{return empty,err}
 id:=c.txn.Identity
 if err:=c.proof.VerifyOriginalCredentialAndKernelOwner(ctx,id);err!=nil{return empty,err}
 c.state="pending"
 err:=c.txn.Apply(ctx)
 if err==nil{err=c.proof.VerifyBidirectionalAuthenticatedFirstDelivery(ctx,id)}
 if err==nil{err=c.proof.VerifyOriginalCredentialAndKernelOwner(ctx,id)}
 var applied N4NativeLiveOSReceipt
 if err==nil{applied,err=c.txn.VerifyLiveOSApplied(ctx)}
 if err==nil&&applied.AllNativeOSApplied{
  c.state="applied";return applied,nil
 }
 if err==nil{err=ErrN4NativeGuard}
 // Cancelled startup is not permission to skip durable WFP cleanup.
 rollbackCtx,cancel:=context.WithTimeout(context.Background(),45*time.Second);defer cancel()
 drainErr:=c.proof.DrainCryptoAndKernelLoans(rollbackCtx,id)
 if drainErr==nil{drainErr=c.txn.Recover(rollbackCtx)}
 if drainErr==nil{drainErr=c.txn.VerifyLiveOSDisconnected(rollbackCtx)}
 if drainErr!=nil{
  c.state="recovery_required"
  return empty,errors.Join(fmt.Errorf("native Connect rejected: %w",err),
   fmt.Errorf("WAL cleanup unverified: %w",drainErr))
 }
 c.state="requested";return empty,err
}

// Stop may not release the original Wintun reservation until native WFP,
// routes, lease, MTU and DNS are retired. Foreign/stale objects retain WAL.
func(c *N4WindowsNativeProductController)Disconnect(ctx context.Context)error{
 if c==nil||ctx==nil||c.txn==nil||c.proof==nil{return ErrN4NativeGuard}
 if c.state!="applied"&&c.state!="recovery_required"{return ErrN4JournalConflict}
 id:=c.txn.Identity
 if err:=c.proof.DrainCryptoAndKernelLoans(ctx,id);err!=nil{c.state="recovery_required";return err}
 if err:=c.txn.Recover(ctx);err!=nil{c.state="recovery_required";return err}
 if err:=c.txn.VerifyLiveOSDisconnected(ctx);err!=nil{c.state="recovery_required";return err}
 c.state="disconnected";return nil
}
