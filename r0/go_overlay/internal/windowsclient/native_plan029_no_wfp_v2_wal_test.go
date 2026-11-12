package windowsclient

// PLAN029 V2 durable transaction grammar tests are software-only. They reuse
// the original frozen stage TEST double and do NOT qualify Windows OS writes,
// native Wintun, WFP migration, authenticated owner or product Applied.
import(
 "context"
 "encoding/json"
 "errors"
 "os"
 "testing"
)
func p029DryNoWFP(t *testing.T)(*N4NativeUnifiedTxn,*[5]*n4UnifiedTestStage,*[]string){
 t.Helper()
 tx,st,trace,_:=n4UnifiedTestTxn(t)
 tx.noLegacyWFP=true
 for i,name:=range n4UnifiedOrderNoWFP{st[i].name=name}
 tx.Stages[len(n4UnifiedOrderNoWFP)]=nil
 if err:=tx.preflight();err!=nil{t.Fatal(err)}
 return tx,st,trace
}
func TestPlan029NoWFPV2WALFourOwnedStagesAndReverseStopPure(t *testing.T){
 tx,st,trace:=p029DryNoWFP(t)
 if err:=tx.Apply(context.Background());err!=nil{t.Fatal(err)}
 j,err:=n4UnifiedRead(tx.Path)
 if err!=nil||j.Schema!=n4UnifiedSchemaNoWFP||j.Phase!="active"||
  len(j.Records)!=len(n4UnifiedOrderNoWFP){
  t.Fatalf("v2 WAL must attest only 4 actual owned stage names: %+v %v",j,err)
 }
 for _,x:=range j.Records{if x.Name=="guard"{t.Fatal("v2 WAL contains forbidden WFP guard")}}
 for _,x:=range *trace{if x=="snapshot:guard"||x=="apply:guard"{t.Fatal("v2 touched legacy WFP guard")}}
 // A second v2 controller may only re-open the SAME installation/generation
 // after authenticated owner proof; this test checks WAL parse/ordering only.
 fresh:=&N4NativeUnifiedTxn{Path:tx.Path,Identity:tx.Identity,Gate:tx.Gate,
  Owner:tx.Owner,Stages:tx.Stages,noLegacyWFP:true}
 if err:=fresh.Recover(context.Background());err!=nil{t.Fatal(err)}
 if err:=fresh.Recover(context.Background());err!=nil{t.Fatal(err)}
 for i:=0;i<len(n4UnifiedOrderNoWFP);i++{
  if st[i].state!=N4UnifiedAbsent||st[i].undoCount!=1{t.Fatalf("stage %d not retired: %+v",i,st[i])}
 }
 var undo []string
 for _,step:=range *trace{if len(step)>5&&step[:5]=="undo:"{undo=append(undo,step)}}
 for i,stage:=range []string{"undo:routes","undo:dns","undo:mtu","undo:lease"}{
  if len(undo)<=i||undo[i]!=stage{t.Fatalf("reverse owned WAL order %v",undo)}
 }
 if _,err:=os.Stat(tx.Path);!errors.Is(err,os.ErrNotExist){t.Fatalf("WAL not retired: %v",err)}
}
func TestPlan029NoWFPV2CannotCrossRecoverLegacyV1Journal(t *testing.T){
 tx,_,_:=p029DryNoWFP(t)
 if err:=tx.Apply(context.Background());err!=nil{t.Fatal(err)}
 v1,_,_,_:=n4UnifiedTestTxn(t);v1.Path=tx.Path
 if err:=v1.Recover(context.Background());!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("legacy WFP-based transaction must not consume v2 WAL: %v",err)
 }
 if _,err:=os.Stat(tx.Path);err!=nil{t.Fatalf("cross-schema attempt deleted v2 WAL: %v",err)}
 if err:=tx.Recover(context.Background());err!=nil{t.Fatal(err)}
}
func TestPlan029NoWFPV2UnconfirmedLeaseWriteNeverGuessedOwned(t *testing.T){
 tx,st,_:=p029DryNoWFP(t)
 j:=n4UnifiedJournal{Schema:n4UnifiedSchemaNoWFP,Identity:tx.Identity,Phase:"applying",
  Records:[]n4UnifiedRecord{{Name:"lease",State:"intent",Before:json.RawMessage(`{}`)}}}
 if err:=n4UnifiedWrite(tx.Path,j,true);err!=nil{t.Fatal(err)}
 st[0].state=N4UnifiedOwned // OS create may have happened before crash
 if err:=tx.Recover(context.Background());!errors.Is(err,ErrN4RouteAmbiguous){
  t.Fatalf("unconfirmed no-WFP lease cannot be guessed safe: %v",err)
 }
 if st[0].undoCount!=0{t.Fatal("ambiguous lease was deleted")}
 if _,err:=os.Stat(tx.Path);err!=nil{t.Fatal("ambiguous WAL was lost")}
}
func TestPlan029NoWFPV2RejectsFakeGuardAndInvalidOrder(t *testing.T){
 tx,_,_:=p029DryNoWFP(t)
 tx.Stages[4]=&n4UnifiedTestStage{name:"guard",trace:&[]string{}}
 if err:=tx.preflight();!errors.Is(err,ErrNetworkPlan){t.Fatalf("v2 accepted fake fifth guard: %v",err)}
 tx.Stages[4]=nil
 j:=n4UnifiedJournal{Schema:n4UnifiedSchemaNoWFP,Identity:tx.Identity,Phase:"applying",
  Records:[]n4UnifiedRecord{{Name:"guard",State:"intent",Before:json.RawMessage(`{}`)}}}
 if err:=n4UnifiedWrite(tx.Path,j,true);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("v2 WAL accepted legacy guard: %v",err)
 }
 j.Records[0].Name="routes"
 if err:=n4UnifiedWrite(tx.Path,j,true);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("v2 WAL accepted out-of-order route: %v",err)
 }
 if _,err:=os.Stat(tx.Path);!errors.Is(err,os.ErrNotExist){
  t.Fatalf("invalid v2 WAL created: %v",err)
 }
}
