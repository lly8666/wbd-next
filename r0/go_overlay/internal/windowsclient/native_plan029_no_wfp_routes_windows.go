//go:build windows

package windowsclient

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/netip"
 "os"
 "path/filepath"
 "slices"
)

// PLAN029 no-old-WFP route stage. Uses the original bounded Win32
// N4WindowsRouteBackend and the existing N4NativeUnifiedTxn v2 WAL:
// server /32 physical escape then precisely two /1 captures, plus only
// configured DNS /32. Never emits CN/LAN prefix routes or WFP filters.
// An interrupted multi-route write has a dedicated per-entry durable
// receipt; only confirmed owned entries may be deleted by exact CAS.
// A present unconfirmed intent remains ambiguous and retains both WALs.
type n4WindowsNoWFPRouteStage struct {
 Plan NetworkPlan
 Owner N4WindowsCreatedWintunReservation
 WALPath string
 Backend NativeRouteBackend
 SyntheticTCP4 netip.Addr // absent except independently owned TCP route
}
// Only 198.19/16 is reserved as this generation's local synthetic TCP
// peer. The original app lease, outer server, physical source and the
// two singleton DNS endpoints must never be captured by this extra key.
// The default 198.18/16 FakeIP pool is disjoint; the Rust cold validator
// separately checks any advanced pool bounds. This adds ONE owned key to
// the EXISTING 4th WAL routes stage, NOT a new fifth stage.
func n4NoWFPWithSyntheticTCPKey(
 original []NativeRouteKey,plan NetworkPlan,synthetic netip.Addr,
)([]NativeRouteKey,error){
 if !synthetic.IsValid(){return original,nil}
 if !synthetic.Is4()||synthetic.IsUnspecified()||
  synthetic.IsMulticast()||synthetic.IsLoopback()||
  synthetic==plan.Server4||synthetic==plan.Lease4.Addr()||
  synthetic==plan.Physical.Source4||
  len(original)<3||synthetic.As4()[0]!=198||
  synthetic.As4()[1]!=19||
  synthetic.As4()[3]==0||synthetic.As4()[3]==255{
  return nil,ErrNetworkPlan
 }
 for _,dns:=range plan.DNSServers4{
  if dns==synthetic{return nil,ErrNetworkPlan}
 }
 for _,key:=range original{
  if key.Prefix==netip.PrefixFrom(synthetic,32){return nil,ErrNetworkPlan}
 }
 if original[1].Interface==0||original[1].Interface!=original[2].Interface{
  return nil,ErrNetworkPlan
 }
 out:=append(append([]NativeRouteKey(nil),original...),
  NativeRouteKey{Prefix:netip.PrefixFrom(synthetic,32),
   Interface:original[1].Interface,NextHop:netip.IPv4Unspecified(),Metric:5})
 if err:=n4ValidateRouteBatch(out);err!=nil{return nil,err}
 return out,nil
}
func(s n4WindowsNoWFPRouteStage) Name()string{return "routes"}
func(s n4WindowsNoWFPRouteStage) expected(ctx context.Context,id N4UnifiedIdentity)([]NativeRouteKey,error){
 if err:=ctx.Err();err!=nil{return nil,err}
 if !id.valid()||s.WALPath==""||s.Backend==nil{return nil,ErrN4JournalConflict}
 if err:=s.Owner.Verify(ctx,id);err!=nil{return nil,err}
 pnp,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return nil,err}
 if pnp.InstanceSHA256!=id.PnPInstanceSHA256{return nil,ErrN4ForeignRoute}
 base,err:=N4BuildCompactNativeRouteKeys(s.Plan,id.WintunIndex)
 if err!=nil{return nil,err}
 return n4NoWFPWithSyntheticTCPKey(base,s.Plan,s.SyntheticTCP4)
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
 if _,err:=os.Lstat(s.WALPath+".routes");err==nil{return nil,ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return nil,err}
 return json.Marshal(n4CompactRouteBaseline{Keys:keys})
}
func(s n4WindowsNoWFPRouteStage) Inspect(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)(N4UnifiedState,error){
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return "",err}
 return s.inspectKeys(ctx,keys)
}
// Exact per-entry receipts are the sole v2 partial-route recovery authority;
// parent WAL intent alone never authorizes deletion of a matching route.
func(s n4WindowsNoWFPRouteStage) Apply(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","applying","intent",b);err!=nil{return err}
 state,err:=s.inspectKeys(ctx,keys)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 return n4NoWFPApplyRoutes(ctx,s.WALPath+".routes",id,keys,s.Backend)
}
func(s n4WindowsNoWFPRouteStage) Undo(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","cleaning","owned",b);err!=nil{return err}
 return n4NoWFPRecoverRoutes(ctx,s.WALPath+".routes",id,keys,s.Backend)
}
func(s n4WindowsNoWFPRouteStage) RecoverUnconfirmedRoutes(ctx context.Context,
 id N4UnifiedIdentity,b json.RawMessage)error{
 keys,err:=s.receipt(ctx,id,b);if err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"routes","cleaning","intent",b);err!=nil{return err}
 return n4NoWFPRecoverRoutes(ctx,s.WALPath+".routes",id,keys,s.Backend)
}

// PLAN029 v2 only: bounded per-route SHA receipt for the SAME parent
// installation/generation. Never reinterprets a retired v1 GuardArmed WAL,
// never installs a fake guard, and cannot delete other programs' rules.
const n4NoWFPRouteSidecarSchema="wbd-n4-no-wfp-route-receipts/v2"
type n4NoWFPRouteReceipt struct{
 Key NativeRouteKey `json:"key"`
 State string `json:"state"` // intent | confirmed owned
}
type n4NoWFPRouteSidecar struct{
 Schema string `json:"schema"`
 Identity N4UnifiedIdentity `json:"identity"`
 Phase string `json:"phase"`
 Entries []n4NoWFPRouteReceipt `json:"entries"`
}
type n4NoWFPRouteEnvelope struct{
 Data n4NoWFPRouteSidecar `json:"data"`
 SHA256 string `json:"sha256"`
}
func n4NoWFPValidateRouteSidecar(j n4NoWFPRouteSidecar,id N4UnifiedIdentity,
 keys []NativeRouteKey)error{
 if !id.valid()||n4ValidateRouteBatch(keys)!=nil||
  j.Schema!=n4NoWFPRouteSidecarSchema||j.Identity!=id||
  (j.Phase!="applying"&&j.Phase!="active"&&j.Phase!="cleaning")||
  len(j.Entries)>len(keys){return ErrN4JournalConflict}
 for i,entry:=range j.Entries{
  if entry.Key!=keys[i]||(entry.State!="intent"&&entry.State!="owned")||
   (entry.State=="intent"&&i!=len(j.Entries)-1){
   return ErrN4JournalConflict
  }
 }
 if j.Phase=="active"{
  if len(j.Entries)!=len(keys){return ErrN4JournalConflict}
  for _,entry:=range j.Entries{if entry.State!="owned"{return ErrN4JournalConflict}}
 }
 return nil
}
func n4NoWFPWriteRouteSidecar(path string,j n4NoWFPRouteSidecar,
 newFile bool)error{
 if path==""||j.Schema!=n4NoWFPRouteSidecarSchema{return ErrN4JournalConflict}
 payload,err:=json.Marshal(j);if err!=nil{return err}
 sum:=sha256.Sum256(payload)
 data,err:=json.Marshal(n4NoWFPRouteEnvelope{Data:j,SHA256:hex.EncodeToString(sum[:])})
 if err!=nil{return err}
 if len(data)>n4MaxJournalBytes{return ErrN4JournalConflict}
 dir:=filepath.Dir(path)
 if err:=os.MkdirAll(dir,0700);err!=nil{return err}
 if newFile{
  file,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
  if errors.Is(err,os.ErrExist){return ErrN4JournalConflict}
  if err!=nil{return err}
  _,err=file.Write(data)
  if err==nil{err=file.Sync()}
  return errors.Join(err,file.Close())
 }
 file,err:=os.CreateTemp(dir,".wbd-p029-routes-*")
 if err!=nil{return err}
 defer os.Remove(file.Name())
 if err=file.Chmod(0600);err!=nil{file.Close();return err}
 if _,err=file.Write(data);err!=nil{file.Close();return err}
 if err=file.Sync();err!=nil{file.Close();return err}
 if err=file.Close();err!=nil{return err}
 return os.Rename(file.Name(),path)
}
func n4NoWFPReadRouteSidecar(path string,id N4UnifiedIdentity,
 keys []NativeRouteKey)(n4NoWFPRouteSidecar,error){
 file,err:=os.Open(path);if err!=nil{return n4NoWFPRouteSidecar{},err}
 defer file.Close()
 bytes,err:=io.ReadAll(io.LimitReader(file,n4MaxJournalBytes+1))
 if err!=nil{return n4NoWFPRouteSidecar{},err}
 if len(bytes)>n4MaxJournalBytes{return n4NoWFPRouteSidecar{},ErrN4JournalConflict}
 var env n4NoWFPRouteEnvelope
 if err:=json.Unmarshal(bytes,&env);err!=nil{return n4NoWFPRouteSidecar{},ErrN4JournalConflict}
 payload,err:=json.Marshal(env.Data)
 if err!=nil{return n4NoWFPRouteSidecar{},ErrN4JournalConflict}
 sum:=sha256.Sum256(payload)
 if env.SHA256!=hex.EncodeToString(sum[:])||
   n4NoWFPValidateRouteSidecar(env.Data,id,keys)!=nil{
  return n4NoWFPRouteSidecar{},ErrN4JournalConflict
 }
 return env.Data,nil
}

func n4NoWFPApplyRoutes(ctx context.Context,sidecar string,id N4UnifiedIdentity,
 keys []NativeRouteKey,backend NativeRouteBackend)error{
 if sidecar==""||backend==nil||!id.valid()||n4ValidateRouteBatch(keys)!=nil{
  return ErrN4JournalConflict
 }
 // This create-exclusion receipt is committed AFTER the parent durable
 // route intent, BEFORE the first Win32 route mutation.
 j:=n4NoWFPRouteSidecar{Schema:n4NoWFPRouteSidecarSchema,
  Identity:id,Phase:"applying",Entries:[]n4NoWFPRouteReceipt{}}
 if err:=n4NoWFPWriteRouteSidecar(sidecar,j,true);err!=nil{return err}
 for _,key:=range keys{
  if err:=ctx.Err();err!=nil{return err}
  present,_,err:=backend.Lookup(ctx,key);if err!=nil{return err}
  if present{return ErrN4ForeignRoute}
  j.Entries=append(j.Entries,n4NoWFPRouteReceipt{Key:key,State:"intent"})
  if err:=n4NoWFPWriteRouteSidecar(sidecar,j,false);err!=nil{return err}
  if err:=backend.CreateIfAbsent(ctx,key);err!=nil{return err}
  present,exact,err:=backend.Lookup(ctx,key)
  if err!=nil{return err}
  if !present||!exact{return ErrN4RouteAmbiguous}
  j.Entries[len(j.Entries)-1].State="owned"
  if err:=n4NoWFPWriteRouteSidecar(sidecar,j,false);err!=nil{return err}
 }
 j.Phase="active"
 return n4NoWFPWriteRouteSidecar(sidecar,j,false)
}
func n4NoWFPRecoverRoutes(ctx context.Context,sidecar string,id N4UnifiedIdentity,
 keys []NativeRouteKey,backend NativeRouteBackend)error{
 if sidecar==""||backend==nil||!id.valid()||n4ValidateRouteBatch(keys)!=nil{
  return ErrN4JournalConflict
 }
 j,err:=n4NoWFPReadRouteSidecar(sidecar,id,keys)
 if errors.Is(err,os.ErrNotExist){
  // Stop may have unlinked the completed sidecar but not yet advanced the
  // parent record. Absent keys mean no OS writes are necessary.
  for _,key:=range keys{
   if err:=ctx.Err();err!=nil{return err}
   present,_,e:=backend.Lookup(ctx,key);if e!=nil{return e}
   if present{return ErrN4RouteAmbiguous}
  }
  return nil
 }
 if err!=nil{return err}
 // Complete bounded read-only preflight before the FIRST delete. Refuse
 // an unconfirmed present key or foreign exact match without partially
 // removing earlier owned entries. Recheck CAS at each actual removal.
 for i,key:=range keys{
  if err:=ctx.Err();err!=nil{return err}
  present,exact,e:=backend.Lookup(ctx,key)
  if e!=nil{return e}
  if present&&!exact{return ErrN4ForeignRoute}
  if !present{continue}
  if i>=len(j.Entries)||j.Entries[i].State!="owned"{
   return ErrN4RouteAmbiguous
  }
 }
 if j.Phase!="cleaning"{
  j.Phase="cleaning"
  if err:=n4NoWFPWriteRouteSidecar(sidecar,j,false);err!=nil{return err}
 }
 for len(j.Entries)>0{
  if err:=ctx.Err();err!=nil{return err}
  i:=len(j.Entries)-1
  entry:=j.Entries[i]
  present,exact,e:=backend.Lookup(ctx,entry.Key)
  if e!=nil{return e}
  if present&&!exact{return ErrN4ForeignRoute}
  if entry.State=="intent"&&present{
   // Write may have succeeded before child receipt was confirmed. A
   // matching route without an "owned" entry remains ambiguous.
   return ErrN4RouteAmbiguous
  }
  if present{
   if e:=backend.RemoveOwned(ctx,entry.Key);e!=nil{return e}
   after,_,e:=backend.Lookup(ctx,entry.Key)
   if e!=nil{return e}
   if after{return ErrN4RouteAmbiguous}
  }
  j.Entries=j.Entries[:i]
  if err:=n4NoWFPWriteRouteSidecar(sidecar,j,false);err!=nil{return err}
 }
 // Every route that never had an owned entry must still be absent:
 // preserve parent WAL if some other process wrote an unrecorded key.
 for _,key:=range keys{
  if err:=ctx.Err();err!=nil{return err}
  present,_,e:=backend.Lookup(ctx,key)
  if e!=nil{return e}
  if present{return ErrN4RouteAmbiguous}
 }
 return os.Remove(sidecar)
}
