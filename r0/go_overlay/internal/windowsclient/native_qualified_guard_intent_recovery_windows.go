//go:build windows
package windowsclient

// PLAN020 M0-only crash repair: the accepted frozen native WAL Recover
// refuses an interrupted guard INTENT whose persistent WFP sublayer/rules
// are only partially installed. Do NOT alter the frozen transaction source
// or authorize a second network lifecycle controller.
import (
 "context"
 "encoding/json"
 "errors"
 "os"
)

// Marker stays package-private: only the real M0-qualified native WFP
// product stage implements it outside the isolated test suite.
type n4QualifiedPersistentGuardOnly interface {
 N4UnifiedStage
 n4IsQualifiedPersistentWFPGuard()bool
}

// Normal recovery remains the FIRST and authoritative path. Only the
// specifically observed guard-only partial-intent ambiguity is reconciled;
// all foreign/lease/route/MTU/DNS uncertainty stays fail-closed.
func(n *N4NativeUnifiedTxn)n4RecoverQualifiedGuardOnlyIntent(ctx context.Context)error{
 if n==nil||ctx==nil||n.assemblyOnly{return ErrN4NativeGuard}
 original:=n.Recover(ctx)
 if !errors.Is(original,ErrN4RouteAmbiguous){return original}

 n.mu.Lock()
 defer n.mu.Unlock()
 release,err:=n.withGate(ctx)
 if err!=nil{return errors.Join(original,err)}
 defer release()
 j,err:=n4UnifiedRead(n.Path)
 if err!=nil{return errors.Join(original,err)}
 if j.Identity!=n.Identity||j.Phase!="cleaning"||
  len(j.Records)!=1||j.Records[0].Name!="guard"||
  j.Records[0].State!="intent"{
  return original
 }
 s,ok:=n.Stages[0].(n4QualifiedPersistentGuardOnly)
 if !ok||!s.n4IsQualifiedPersistentWFPGuard(){return original}
 rec:=j.Records[0]
 // Even without an owner WAL entry, no later exact owned route, lease,
 // MTU or DNS mutation may be silently ignored. Every independent stage
 // must attest absence under the same machine gate / Wintun reservation.
 // Missing stage, foreign state, active route sidecar or read errors
 // preserve the original WAL and the protective WFP subset.
 if _,e:=os.Lstat(n.Path+".routes");e==nil{return ErrN4JournalConflict
 }else if !errors.Is(e,os.ErrNotExist){return errors.Join(original,e)}
 for i:=1;i<len(n.Stages);i++{
  stage:=n.Stages[i]
  before,e:=stage.Snapshot(ctx,n.Identity)
  if e!=nil{return errors.Join(original,e)}
  if len(before)==0||!json.Valid(before){return errors.Join(original,ErrN4NativeGuard)}
  state,e:=stage.Inspect(ctx,n.Identity,before)
  if e!=nil{return errors.Join(original,e)}
  if state==N4UnifiedForeign{return ErrN4ForeignRoute}
  if state!=N4UnifiedAbsent{return errors.Join(original,ErrN4NativeGuard)}
 }
 state,err:=s.Inspect(ctx,n.Identity,rec.Before)
 if err!=nil{return errors.Join(original,err)}
 if state==N4UnifiedForeign{return ErrN4ForeignRoute}
 if state!=N4UnifiedPartial{return original}
 if err:=s.Undo(ctx,n.Identity,rec.Before);err!=nil{return errors.Join(original,err)}
 state,err=s.Inspect(ctx,n.Identity,rec.Before)
 if err!=nil{return errors.Join(original,err)}
 if state!=N4UnifiedAbsent{return errors.Join(original,ErrN4NativeGuard)}
 // After durable intent, later retry can safely see absent and retire
 // the WAL; exact cleanup succeeded only when the final unlink succeeds.
 return os.Remove(n.Path)
}
