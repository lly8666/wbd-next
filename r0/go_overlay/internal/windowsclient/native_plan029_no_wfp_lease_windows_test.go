//go:build windows

package windowsclient

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "testing"
)

// Software-only native journal permission tests. No fake Wintun is opened,
// no Win32 address is created, and no product Applied/Stop is claimed.
func TestPlan029NoWFPLeaseRequiresExactPersistedWin32Intent(t *testing.T){
 tx,_,_:=p029DryNoWFP(t)
 baseline:=json.RawMessage(`{"index":21,"address":"198.18.8.9/32","absent":true}`)
 j:=n4UnifiedJournal{Schema:n4UnifiedSchemaNoWFP,Identity:tx.Identity,
  Phase:"applying",Records:[]n4UnifiedRecord{{Name:"lease",State:"intent",Before:baseline}}}
 if err:=n4UnifiedWrite(tx.Path,j,true);err!=nil{t.Fatal(err)}
 allow:=func(phase,state string,b json.RawMessage)error{
  return n4NoWFPStageWALPermission(tx.Path,tx.Identity,"lease",phase,state,b)
 }
 if err:=allow("applying","intent",baseline);err!=nil{t.Fatalf("exact durable v2 lease intent refused: %v",err)}
 for _,tc:=range []struct{name,phase,state string;before json.RawMessage}{
  {"not_done","cleaning","owned",baseline},
  {"not_unconfirmed_owned","applying","owned",baseline},
  {"wrong_stage","applying","intent",json.RawMessage(`{"index":21,"address":"198.18.8.10/32","absent":true}`)},
 }{
  t.Run(tc.name,func(t *testing.T){
   if err:=allow(tc.phase,tc.state,tc.before);!errors.Is(err,ErrN4JournalConflict){
    t.Fatalf("unowned action permitted by v2 WAL: %v",err)
   }
  })
 }
 swapped:=tx.Identity;swapped.Generation[0]++
 if err:=n4NoWFPStageWALPermission(tx.Path,swapped,"lease","applying","intent",baseline);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("wrong generation access allowed: %v",err)
 }
 j.Phase="cleaning";j.Records[0].State="owned"
 if err:=n4UnifiedWrite(tx.Path,j,false);err!=nil{t.Fatal(err)}
 if err:=allow("cleaning","owned",baseline);err!=nil{t.Fatalf("owned v2 rollback disallowed: %v",err)}
 if err:=allow("applying","intent",baseline);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("cleaning journal allowed new create: %v",err)
 }
 // v1 was WFP-guarded; it can NEVER be read as v2 authorization.
 j.Schema=n4UnifiedSchema
 j.Records=[]n4UnifiedRecord{{Name:"guard",State:"owned",Before:json.RawMessage(`{}`)},
 {Name:"lease",State:"owned",Before:baseline}}
 if err:=n4UnifiedWrite(tx.Path,j,false);err!=nil{t.Fatal(err)}
 if err:=allow("cleaning","owned",baseline);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("legacy WFP journal granted guard-free Win32 mutation: %v",err)
 }
 payload,err:=os.ReadFile(tx.Path);if err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(tx.Path,bytes.Replace(payload,[]byte("guard"),[]byte("xxxxx"),1),0600);err!=nil{t.Fatal(err)}
 if err:=allow("cleaning","owned",baseline);err==nil{
  t.Fatal("corrupted WAL unexpectedly authorized native mutation")
 }
}
