//go:build windows

package windowsclient

// M0 additive original-Go native MTU proof. All frozen M4 source and
// its exact legacy SHA pins stay byte-for-byte unchanged. Same package
// grants no authority; only original M4 txn owner/gate/guard does.
import "context"

// LiveConfiguredMTU is a READ-ONLY, same-gen, machine-gated OS proof.
// It does not rewrite NlMtu while an active five-stage WAL persists: such
// an edit would make a crash unrecoverable under the original CAS receipt.
// A foreign change is a hard error, never new Rust FrameBudget authority.
func(n *N4NativeUnifiedTxn) LiveConfiguredMTU(ctx context.Context)(uint32,error){
 if n==nil||ctx==nil||n.assemblyOnly{return 0,ErrN4NativeGuard}
 n.mu.Lock();defer n.mu.Unlock()
 release,err:=n.withGate(ctx);if err!=nil{return 0,err}
 defer release()
 j,err:=n4UnifiedRead(n.Path);if err!=nil{return 0,err}
 if j.Identity!=n.Identity||j.Phase!="active"||len(j.Records)!=5{
  return 0,ErrN4JournalConflict
 }
 for _,item:=range j.Records{
  if item.State!="owned"{return 0,ErrN4JournalConflict}
 }
 stage,ok:=n.Stages[2].(n4WindowsMTUStage)
 if !ok{return 0,ErrN4NativeGuard}
 if j.Records[2].Name!="mtu"{return 0,ErrN4JournalConflict}
 state,err:=stage.Inspect(ctx,n.Identity,j.Records[2].Before)
 if err!=nil{return 0,err}
 if state!=N4UnifiedOwned{return 0,ErrN4ForeignRoute}
 // Inspect CAS matches every captured OS interface field, not only NlMtu.
 return stage.Target,nil
}
