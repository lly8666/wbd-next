//go:build windows
package windowsclient
import("context";"errors";"os";"testing")
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
