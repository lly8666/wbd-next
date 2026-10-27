//go:build windows

package windowsclient

import (
 "context"
 "errors"
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
