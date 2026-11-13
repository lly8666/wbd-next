//go:build windows
package windowsclient
import("context";"errors";"net/netip";"os";"testing")
type n4ProductTestProof struct{authErr,flowErr,drainErr error; auth,flow,drain int}
func(p *n4ProductTestProof)VerifyOriginalCredentialAndKernelOwner(_ context.Context,_ N4UnifiedIdentity)error{p.auth++;return p.authErr}
func(p *n4ProductTestProof)VerifyBidirectionalAuthenticatedFirstDelivery(_ context.Context,_ N4UnifiedIdentity)error{p.flow++;return p.flowErr}
func(p *n4ProductTestProof)DrainCryptoAndKernelLoans(_ context.Context,_ N4UnifiedIdentity)error{p.drain++;return p.drainErr}
func TestM0PLAN020NativeProductOSOwnerPacketConnectAndStop(t *testing.T){
 ctx:=context.Background()
 txn,st,_,_:=n4UnifiedTestTxn(t)
 proof:=&n4ProductTestProof{}
 txn.assemblyOnly=true
 if _,err:=n4NewWindowsNativeProductController(txn,proof);!errors.Is(err,ErrN4NativeGuard){t.Fatalf("assemblyOnly bypass %v",err)}
 txn.assemblyOnly=false
 c,err:=n4NewWindowsNativeProductController(txn,proof);if err!=nil{t.Fatal(err)}
 proof.authErr=ErrN4NativeGuard
 if _,err:=c.Connect(ctx);!errors.Is(err,ErrN4NativeGuard){t.Fatalf("unauthenticated Connect %v",err)}
 if _,err:=os.Stat(txn.Path);!errors.Is(err,os.ErrNotExist){t.Fatal(err)}
 proof.authErr=nil;proof.flowErr=ErrN4NativeGuard
 if _,err:=c.Connect(ctx);!errors.Is(err,ErrN4NativeGuard){t.Fatalf("missing app flow %v",err)}
 if proof.drain!=1||c.state!="requested"{t.Fatalf("failed flow did not drain %+v",proof)}
 proof.flowErr=nil
 receipt,err:=c.Connect(ctx)
 if err!=nil||!receipt.AllNativeOSApplied||c.state!="applied"{t.Fatalf("same session positive receipt %+v %v",receipt,err)}
 if _,err:=c.Connect(ctx);!errors.Is(err,ErrN4JournalConflict){t.Fatalf("double Connect %v",err)}
 proof.drainErr=ErrN4NativeGuard
 if err:=c.Disconnect(ctx);!errors.Is(err,ErrN4NativeGuard){t.Fatalf("outstanding loan Stop %v",err)}
 if _,err:=os.Stat(txn.Path);err!=nil{t.Fatal("WAL erased while crypto loans still held")}
 proof.drainErr=nil;st[2].state=N4UnifiedForeign
 if err:=c.Disconnect(ctx);!errors.Is(err,ErrN4ForeignRoute){t.Fatalf("foreign MTU CAS %v",err)}
 if _,err:=os.Stat(txn.Path);err!=nil{t.Fatal("foreign WAL erased")}
 st[2].state=N4UnifiedOwned
 if err:=c.Disconnect(ctx);err!=nil{t.Fatal(err)}
 if c.state!="disconnected"{t.Fatal(c.state)}
 if _,err:=os.Stat(txn.Path);!errors.Is(err,os.ErrNotExist){t.Fatal(err)}
 if err:=c.Disconnect(ctx);!errors.Is(err,ErrN4JournalConflict){t.Fatal(err)}
}

func TestPlan029NoWFPControllerUsesFourOwnedStagesWithoutLegacyGuard(t *testing.T){
 ctx:=context.Background()
 txn,st,trace:=p029DryNoWFP(t)
 proof:=&n4ProductTestProof{}
 controller,err:=n4NewWindowsNativeProductController(txn,proof)
 if err!=nil{t.Fatal(err)}
 receipt,err:=controller.Connect(ctx)
 if err!=nil||receipt.Schema!=N4NativeLiveOSSchemaNoWFP||
  receipt.GuardOwned||!receipt.AllNativeOSApplied{
  t.Fatalf("v2 pure fixture falsely denied/qualified: %+v %v",receipt,err)
 }
 if err:=controller.Disconnect(ctx);err!=nil{t.Fatal(err)}
 for i:=0;i<4;i++{
  if st[i].state!=N4UnifiedAbsent||st[i].undoCount!=1{
   t.Fatalf("v2 stage %d not retired once: %+v",i,st[i])
  }
 }
 for _,line:=range *trace{
  if line=="apply:guard"||line=="undo:guard"{
   t.Fatalf("v2 controller touched old WFP guard: %s",line)
  }
 }
 if proof.drain!=1{t.Fatalf("v2 Stop not drained exactly once: %+v",proof)}
 txn.assemblyOnly=true
 if _,err:=n4NewWindowsNativeProductController(txn,proof);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("v2 unqualified assemblyOnly promoted: %v",err)
 }
}

func TestPlan029OnlyAuthenticatedConcreteNoWFPStagesMayExitAssembly(t *testing.T){
 ctx:=context.Background()
 txn,_,_:=p029DryNoWFP(t)
 proof:=&n4ProductTestProof{}
 // A name-only mock is insufficient even if the four stage names match.
 txn.assemblyOnly=true
 if err:=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,proof);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("unqualified mock promoted: %v",err)
 }
 if !txn.assemblyOnly||proof.auth!=0{t.Fatal("mock admission mutated owner/lease")}
 // Real Go stage TYPES with exact WAL affiliation are mandatory; this
 // exercises the pure cold admission decision without touching Win32.
 txn.Stages[0]=n4WindowsNoWFPLeaseStage{
  Lease:N4NativeLeaseIntent{InterfaceIndex:txn.Identity.WintunIndex,
   Prefix:netip.MustParsePrefix("198.18.87.77/32")},
  WALPath:txn.Path,
 }
 txn.Stages[1]=n4WindowsNoWFPMTUStage{Target:1280,WALPath:txn.Path}
 txn.Stages[2]=n4WindowsNoWFPDNSStage{
  Servers:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},WALPath:txn.Path,
 }
 txn.Stages[3]=n4WindowsNoWFPRouteStage{
  WALPath:txn.Path,Backend:&p029JournalRouteBackend{},
 }
 proof.authErr=ErrN4NativeGuard
 if err:=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,proof);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("missing real owner credential approval: %v",err)
 }
 if !txn.assemblyOnly{t.Fatal("bad credential proof lifted assembly barrier")}
 proof.authErr=nil
 txn.Stages[4]=&n4UnifiedTestStage{name:"guard",trace:&[]string{}}
 if err:=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,proof);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("legacy WFP stage admitted: %v",err)
 }
 txn.Stages[4]=nil
 if err:=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,proof);err!=nil{t.Fatal(err)}
 if txn.assemblyOnly||proof.auth!=2{t.Fatalf("real typed four-stage cold admission failed: proof=%+v",proof)}
 if err:=n4AdmitAuthenticatedNoWFPProduct(ctx,txn,proof);!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("assembly reused by second caller: %v",err)
 }
 // No stage Apply or fake WFP guard happened: only a live original owner
 // may later enter controller Connect (which still checks real OS).
 if _,err:=os.Stat(txn.Path);!errors.Is(err,os.ErrNotExist){t.Fatal(err)}
}
