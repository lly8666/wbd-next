//go:build windows

package windowsclient

import (
 "context"
 "encoding/json"
 "slices"
)

// PLAN029 no-old-WFP route stage. Uses the original bounded Win32
// N4WindowsRouteBackend and the existing N4NativeUnifiedTxn v2 WAL:
// server /32 physical escape then precisely two /1 captures, plus only
// configured DNS /32. Never emits CN/LAN prefix routes or WFP filters.
// An interrupted multi-route write with present intent is intentionally
// ambiguous; without per-entry durable proof it MUST NOT delete a route
// merely because it matches a desired key. Normal fully confirmed Apply
// and reverse Stop use exact CAS; crash test remains OPEN until qualified.
type n4WindowsNoWFPRouteStage struct {
 Plan NetworkPlan
 Owner N4WindowsCreatedWintunReservation
 WALPath string
 Backend NativeRouteBackend
}
func(s n4WindowsNoWFPRouteStage) Name()string{return "routes"}
func(s n4WindowsNoWFPRouteStage) expected(ctx context.Context,id N4UnifiedIdentity)([]NativeRouteKey,error){
 if err:=ctx.Err();err!=nil{return nil,err}
 if !id.valid()||s.WALPath==""||s.Backend==nil{return nil,ErrN4JournalConflict}
 if err:=s.Owner.Verify(ctx,id);err!=nil{return nil,err}
 pnp,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return nil,err}
 if pnp.InstanceSHA256!=id.PnPInstanceSHA256{return nil,ErrN4ForeignRoute}
 return N4BuildCompactNativeRouteKeys(s.Plan,id.WintunIndex)
}
func(s n4WindowsNoWFPRouteStage) receipt(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)([]NativeRouteKey,error){
 keys,err:=s.expected(ctx,id);if err!=nil{return nil,err}
 var saved n4CompactRouteBaseline
 if err:=json.Unmarshal(b,&saved);err!=nil{return nil,ErrN4JournalConflict}
 if !slices.Equal(saved.Keys,keys){return nil,ErrN4JournalConflict}
 return keys,nil
}
func(s n4WindowsNoWFPRouteStage) inspectKeys(ctx context.Context,keys []NativeRouteKey)(N4UnifiedState,error){
 var present int
 for _,key:=range keys{
  if err:=ctx.Err();err!=nil{return "",err}
  exists,exact,err:=s.Backend.Lookup(ctx,key)
  if err!=nil{return "",err}
  if !exists{continue}
  if !exact{return N4UnifiedForeign,nil}
  present++
 }
 if present==0{return N4UnifiedAbsent,nil}
 if present==len(keys){return N4UnifiedOwned,nil}
 return N4UnifiedPartial,nil
}
func(s n4WindowsNoWFPRouteStage) Snapshot(ctx context.Context,id N4UnifiedIdentity)(json.RawMessage,error){
 keys,err:=s.expected(ctx,id);if err!=nil{return nil,err}
 state,err:=s.inspectKeys(ctx,keys)
 if err!=nil{return nil,err}
 if state!=N4UnifiedAbsent{return nil,ErrN4ForeignRoute}
 return json.Marshal(n4CompactRouteBaseline{Keys:keys})
}
func(s n4WindowsNoWFPRouteStage) Inspect(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)(N4UnifiedState,error){
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return "",err}
 return s.inspectKeys(ctx,keys)
}
func(s n4WindowsNoWFPRouteStage) Apply(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","applying","intent",b);err!=nil{return err}
 state,err:=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 for _,key:=range keys{
  if err:=ctx.Err();err!=nil{return err}
  // Lookup refuses both foreign and identical preexisting keys. A route
  // that exists during a resumed intent is NOT automatically ours.
  exists,_,err:=s.Backend.Lookup(ctx,key)
  if err!=nil{return err}
  if exists{return ErrN4ForeignRoute}
  if err:=s.Backend.CreateIfAbsent(ctx,key);err!=nil{return err}
  exists,exact,err:=s.Backend.Lookup(ctx,key)
  if err!=nil{return err}
  if !exists||!exact{return ErrN4RouteAmbiguous}
 }
 state,err=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4RouteAmbiguous}
 return nil
}
func(s n4WindowsNoWFPRouteStage) Undo(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","cleaning","owned",b);err!=nil{return err}
 state,err:=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state==N4UnifiedForeign||state==N4UnifiedAbsent{return ErrN4ForeignRoute}
 for i:=len(keys)-1;i>=0;i--{
  // The parent already durably confirmed the entire route batch as owned.
  // Reverse CAS, never delete a mismatching route; a crash in Undo may
  // leave Partial and the owner must hold the same generation when retrying.
  found,match,err:=s.Backend.Lookup(ctx,keys[i])
  if err!=nil{return err}
  if !found{continue}
  if !match{return ErrN4ForeignRoute}
  if err:=s.Backend.RemoveOwned(ctx,keys[i]);err!=nil{return err}
 }
 state,err=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4RouteAmbiguous}
 return nil
}
// Routes are the final v2 stage, so parent Recover needs a precise
// resolution for a crash between "intent" and "owned". With NO durable
// per-entry ownership proof, refuse to delete ANY present key.
func(s n4WindowsNoWFPRouteStage) RecoverUnconfirmedRoutes(ctx context.Context,
 id N4UnifiedIdentity,b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","cleaning","intent",b);err!=nil{return err}
 state,err:=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4RouteAmbiguous}
 return nil
}
