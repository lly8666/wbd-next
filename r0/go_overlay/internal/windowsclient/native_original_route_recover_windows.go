//go:build windows

package windowsclient

import (
 "context"
 "errors"
 "os"
)

// An original-identity-checked backend exists ONLY for confirmed crash WAL
// cleanup. It cannot create routes or silently "repair" a foreign row.
// The caller must check the original PnP pin and guard on every operation.
type n4OriginalRouteCleanupBackend struct {
 ID N4UnifiedIdentity
 Guard CrashPersistentGuard
 Route NativeRouteBackend
 VerifyOriginal func(context.Context,N4UnifiedIdentity)error
}
func(b n4OriginalRouteCleanupBackend)check(ctx context.Context)error{
 if err:=ctx.Err();err!=nil{return err}
 if err:=b.VerifyOriginal(ctx,b.ID);err!=nil{return err}
 armed,err:=b.Guard.Verify(ctx)
 if err!=nil{return err}
 if !armed{return ErrN4NativeGuard}
 return nil
}
func(b n4OriginalRouteCleanupBackend)Lookup(ctx context.Context,k NativeRouteKey)(bool,bool,error){
 if err:=b.check(ctx);err!=nil{return false,false,err}
 return b.Route.Lookup(ctx,k)
}
func(n4OriginalRouteCleanupBackend)CreateIfAbsent(context.Context,NativeRouteKey)error{
 return ErrN4NativeGuard
}
func(b n4OriginalRouteCleanupBackend)RemoveOwned(ctx context.Context,k NativeRouteKey)error{
 if err:=b.check(ctx);err!=nil{return err}
 return b.Route.RemoveOwned(ctx,k)
}

// Reconcile ONLY the fifth original route stage. Original five-stage
// production recovery is NOT activated until real WFP/route crash evidence
// qualifies it; no shell or ghost adapter fallback. Under the one Windows
// machine gate, a checksum-valid sidecar and matching original parent must
// attest every present route as CONFIRMED owned before deletion.
// Ambiguous intent, lost PnP or foreign CAS always retains both WALs.
func n4RetireOriginalConfirmedRouteStage(ctx context.Context,path string,
 id N4UnifiedIdentity,g CrashPersistentGuard,route NativeRouteBackend,
 verifyOriginal func(context.Context,N4UnifiedIdentity)error,
)error{
 if ctx==nil{return ErrNetworkPlan}
 if err:=ctx.Err();err!=nil{return err}
 if path==""||!n4ValidPinnedPnPHash(id.PnPInstanceSHA256) ||
  g==nil||!g.Durable()||route==nil||verifyOriginal==nil{
  return ErrN4NativeGuard
 }
 release,err:=(N4WindowsMachineGate{}).Acquire(ctx)
 if err!=nil{return err}
 defer release()
 j,err:=n4UnifiedRead(path)
 if err!=nil{return err}
 // This phase is only for complete parent WAL route intent/owned.
 // A pre-route-only receipt remains the responsibility of the original
 // N4WindowsRecoverPersistedPreRouteWAL path.
 var child *n4Journal
 sidecar:=path+".routes"
 info,err:=os.Lstat(sidecar)
 if err==nil{
  if info.Mode()&os.ModeSymlink!=0 || !info.Mode().IsRegular(){
   return ErrN4JournalConflict
  }
  recovered,err:=n4ReadJournal(sidecar)
  if err!=nil{return err}
  child=&recovered
 }else if !errors.Is(err,os.ErrNotExist){return err}
 keys,err:=n4ValidatePersistedFullRouteReceipts(j,id,child)
 if err!=nil{return err}
 guarded:=n4OriginalRouteCleanupBackend{ID:id,Guard:g,Route:route,VerifyOriginal:verifyOriginal}
 // COMPLETE preflight before the first OS route setter.
 for i,key:=range keys{
  present,exact,err:=guarded.Lookup(ctx,key)
  if err!=nil{return err}
  if !present{continue}
  if !exact{return ErrN4ForeignRoute}
  if child==nil || i>=len(child.Entries) ||
   child.Entries[i].State!="owned"{
   return ErrN4RouteAmbiguous
  }
 }
 if child!=nil{
  owned:=&N4OwnedRoutes{Path:sidecar,Route:guarded,Guard:n4SharedPersistentGuard{parent:g}}
  if err:=owned.Recover(ctx);err!=nil{return err}
 }
 // The parent may retire its route record only after the old per-route
 // journal has been removed and every old exact route is still absent.
 for _,key:=range keys{
  exists,_,err:=guarded.Lookup(ctx,key)
  if err!=nil{return err}
  if exists{return ErrN4RouteAmbiguous}
 }
 if _,err:=os.Lstat(sidecar);err==nil{return ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return err}
 j.Phase="cleaning"
 j.Records=j.Records[:4]
 return n4UnifiedWrite(path,j,false)
}
