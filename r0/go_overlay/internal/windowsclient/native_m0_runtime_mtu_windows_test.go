//go:build windows

package windowsclient

import (
 "context"
 "errors"
 "encoding/json"
 "testing"
)

func TestM0WindowsOriginalNativeRuntimeMTURequiresFullOwnedWAL(t *testing.T){
 ctx:=context.Background()
 var zero *N4NativeUnifiedTxn
 if _,err:=zero.LiveConfiguredMTU(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("nil MTU native txn accepted without real OS owner: %v",err)
 }
 txn:=&N4NativeUnifiedTxn{assemblyOnly:true}
 if _,err:=txn.LiveConfiguredMTU(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("assembly-only MTU attempted to read/write Windows state: %v",err)
 }
 product:=&N4RealWindowsProduct{}
 if _,err:=product.RuntimeMTU(ctx);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("cold product promoted an unstaged M4 MTU receipt: %v",err)
 }
}

 
// PLAN029 H1716: the source-locked H1715 public executable applied FOUR
// no-WFP Win32 stages but old LiveConfiguredMTU expected FIVE and rejected
// Ready with inspected=0/ErrN4NativeGuard. These pure fixtures validate
// versioned record index/types only; the signed Windows test performs
// the actual same-generation native IPv4 interface Inspect.
func p029MTUOwnedJournal(tx *N4NativeUnifiedTxn)n4UnifiedJournal{
 order,_:=n4UnifiedOrderForSchema(tx.schema())
 j:=n4UnifiedJournal{Schema:tx.schema(),Identity:tx.Identity,Phase:"active"}
 for _,name:=range order{
  j.Records=append(j.Records,n4UnifiedRecord{
   Name:name,State:"owned",Before:json.RawMessage(`{}`),
  })
 }
 return j
}
func TestPlan029RuntimeMTUV2FourStageSelectionAndV1GuardCompatibility(t *testing.T){
 v2,_,_:=p029DryNoWFP(t)
 v2.Stages[1]=n4WindowsNoWFPMTUStage{Target:1329}
 record:=p029MTUOwnedJournal(v2)
 stage,mtu,_,err:=n4LiveMTUStageReceipt(v2,record)
 if _,ok:=stage.(n4WindowsNoWFPMTUStage);err!=nil||mtu!=1329||!ok{
  t.Fatalf("v2 live MTU selected legacy stage or guard: %d %v",mtu,err)
 }
 v1,_,_,_:=n4UnifiedTestTxn(t)
 v1.Stages[2]=n4WindowsMTUStage{Target:1329}
 old:=p029MTUOwnedJournal(v1)
 stage,mtu,_,err=n4LiveMTUStageReceipt(v1,old)
 if _,ok:=stage.(n4WindowsMTUStage);err!=nil||mtu!=1329||!ok{
  t.Fatalf("v1 legacy exact MTU guard layout not preserved: %d %v",mtu,err)
 }

}
func TestPlan029RuntimeMTURejectsCrossSchemaPartialForeignOrMock(t *testing.T){
 v2,_,_:=p029DryNoWFP(t)
 v2.Stages[1]=n4WindowsNoWFPMTUStage{Target:1280}
 j:=p029MTUOwnedJournal(v2)
 assertConflict:=func(label string,x n4UnifiedJournal){
  t.Helper()
  if _,_,_,err:=n4LiveMTUStageReceipt(v2,x);!errors.Is(err,ErrN4JournalConflict){
   t.Fatalf("%s: bad WAL produced live MTU %v",label,err)
  }
 }
 foreign:=j;foreign.Schema=n4UnifiedSchema
 assertConflict("retired five-stage schema",foreign)
 foreign=j;foreign.Phase="cleaning"
 assertConflict("not active",foreign)
 foreign=j;foreign.Identity.Generation[0]^=1
 assertConflict("foreign generation",foreign)
 foreign=j;foreign.Records=append([]n4UnifiedRecord(nil),j.Records...)
 foreign.Records[2].State="intent"
 assertConflict("unconfirmed dns",foreign)
 foreign=j;foreign.Records=append([]n4UnifiedRecord(nil),j.Records...)
 foreign.Records=foreign.Records[:3]
 assertConflict("partial four-stage WAL",foreign)
 foreign=j;foreign.Records=append([]n4UnifiedRecord(nil),j.Records...)
 foreign.Records[1].Name="guard"
 assertConflict("old WFP sentinel forged mtu",foreign)
 v2.Stages[4]=&n4UnifiedTestStage{name:"guard",trace:&[]string{}}
 if _,_,_,err:=n4LiveMTUStageReceipt(v2,j);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("fifth stage slipped into v2 live MTU: %v",err)
 }
 v2.Stages[4]=nil
 v2.Stages[1]=&n4UnifiedTestStage{name:"mtu",trace:&[]string{}}
 if _,_,_,err:=n4LiveMTUStageReceipt(v2,j);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("name-only fake MTU Inspect accepted as Win32: %v",err)
 }
 v2.Stages[1]=n4WindowsNoWFPMTUStage{Target:1280}
 v2.assemblyOnly=true
 if _,_,_,err:=n4LiveMTUStageReceipt(v2,j);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("unqualified assembly emitted owned MTU: %v",err)
 }
}
