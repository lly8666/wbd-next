//go:build windows

package windowsclient

// A single same-generation MTU CAS readback supports the original five
// WFP-owned v1 WAL and PLAN029's four-stage no-old-WFP v2 WAL. It MUST
// NOT infer MTU ownership from an alias, cached JSON, schema alone or
// the fact that another product stage was once marked Applied.
import (
 "context"
 "encoding/json"
)

// n4LiveMTUStageReceipt is PURE stage/WAL selection. The read-only native
// Inspect below is the separate actual Win32 owner + MTU proof. Keeping
// selection pure allows exercising both layouts without forged OS state.
func n4LiveMTUStageReceipt(
 n *N4NativeUnifiedTxn,j n4UnifiedJournal,
)(N4UnifiedStage,uint32,json.RawMessage,error){
 if n==nil||n.assemblyOnly||j.Identity!=n.Identity||
  j.Schema!=n.schema()||j.Phase!="active"{
  return nil,0,nil,ErrN4JournalConflict
 }
 stages:=n.stages()
 order,err:=n4UnifiedOrderForSchema(j.Schema)
 if err!=nil||len(stages)!=len(order)||len(j.Records)!=len(stages){
  return nil,0,nil,ErrN4JournalConflict
 }
 // This check never permits a spare v2 fifth "guard" stage, including
 // a no-op guard that might otherwise manufacture an Applied receipt.
 if n.noLegacyWFP && n.Stages[len(n4UnifiedOrderNoWFP)]!=nil{
  return nil,0,nil,ErrN4NativeGuard
 }
 for i,record:=range j.Records{
  if record.State!="owned"||record.Name!=order[i]||
   stages[i]==nil||stages[i].Name()!=order[i]{
   return nil,0,nil,ErrN4JournalConflict
  }
 }
 mtuIndex:=2 // v1: guard, lease, mtu, dns, routes
 if n.noLegacyWFP{mtuIndex=1} // v2: lease, mtu, dns, routes
 if j.Records[mtuIndex].Name!="mtu"{
  return nil,0,nil,ErrN4JournalConflict
 }
 stage:=stages[mtuIndex]
 var target uint32
 if n.noLegacyWFP{
  typed,ok:=stage.(n4WindowsNoWFPMTUStage)
  if !ok{return nil,0,nil,ErrN4NativeGuard}
  target=typed.Target
 }else{
  typed,ok:=stage.(n4WindowsMTUStage)
  if !ok{return nil,0,nil,ErrN4NativeGuard}
  target=typed.Target
 }
 if target<576||target>9000{return nil,0,nil,ErrNetworkPlan}
 return stage,target,j.Records[mtuIndex].Before,nil
}

// LiveConfiguredMTU is read-only, owns no permanent lease and never
// repairs a changed MTU. Its fresh original Wintun reservation/machine
// gate and exact stage Inspect are the authority. The single candidate
// native stage must still match every OS interface baseline field.
func(n *N4NativeUnifiedTxn) LiveConfiguredMTU(ctx context.Context)(uint32,error){
 if n==nil||ctx==nil||n.assemblyOnly{return 0,ErrN4NativeGuard}
 if err:=n.preflight();err!=nil{return 0,err}
 n.mu.Lock();defer n.mu.Unlock()
 release,err:=n.withGate(ctx);if err!=nil{return 0,err}
 defer release()
 j,err:=n4UnifiedRead(n.Path);if err!=nil{return 0,err}
 stage,target,before,err:=n4LiveMTUStageReceipt(n,j)
 if err!=nil{return 0,err}
 state,err:=stage.Inspect(ctx,n.Identity,before)
 if err!=nil{return 0,err}
 if state!=N4UnifiedOwned{return 0,ErrN4ForeignRoute}
 return target,nil
}
