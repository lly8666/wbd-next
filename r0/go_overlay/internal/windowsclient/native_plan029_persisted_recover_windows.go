//go:build windows

package windowsclient

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "net/netip"
 "os"
)

// Crash recovery has no live Go/Wintun owner. The existing WAL records
// the original private interface identity. Reuse the native stage
// readers/writers against that exact surviving interface, not its alias.
type n4StoppedNoWFPOwner struct{ id N4UnifiedIdentity }
func(o n4StoppedNoWFPOwner) Verify(ctx context.Context,id N4UnifiedIdentity)error{
 if id!=o.id{return ErrN4JournalConflict}
 return n4OriginalWintunPersistedExact(ctx,id)
}

// A disappeared original interface cannot retain usable IP routes. Other
// routes (for example the physical server /32) still use the existing exact
// receipt and native CAS cleanup.
type n4StoppedNoWFPRoutes struct{
 N4WindowsRouteBackend
 id N4UnifiedIdentity
 gone bool
}
func(b n4StoppedNoWFPRoutes) Lookup(ctx context.Context,key NativeRouteKey)(bool,bool,error){
 if b.gone&&key.Interface==b.id.WintunIndex{
  return false,false,nil
 }
 return b.N4WindowsRouteBackend.Lookup(ctx,key)
}
func(b n4StoppedNoWFPRoutes) RemoveOwned(ctx context.Context,key NativeRouteKey)error{
 if b.gone&&key.Interface==b.id.WintunIndex{return nil}
 return b.N4WindowsRouteBackend.RemoveOwned(ctx,key)
}

// Called by --recover-network after the existing GUI/client machine slot
// has been acquired. No new WFP, adapter, monitoring or route creation.
// Restore only actual v2 receipts, in reverse stage order. A removed
// Wintun needs no MTU/address/DNS reset on another physical interface.
func n4RecoverNoWFPPersisted(ctx context.Context,path string)error{
 release,err:=(N4WindowsMachineGate{}).Acquire(ctx)
 if err!=nil{return err};defer release()
 j,err:=n4UnifiedRead(path)
 if errors.Is(err,os.ErrNotExist){return nil}
 if err!=nil{return err}
 if j.Schema!=n4UnifiedSchemaNoWFP{return ErrN4JournalConflict}
 id:=j.Identity
 original,err:=n4InspectOriginalWintunForRecovery(ctx,id)
 if err!=nil{return fmt.Errorf("inspect original Wintun: %w",err)}
 if original!=N4UnifiedOwned&&original!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 gone:=original==N4UnifiedAbsent
 missingIP:=gone
 if !gone {
  // A common TerminateProcess result is an exact original ghost adapter
  // with no IPv4 row. Do not require restoring an MTU on a vanished row.
  if _,err:=n4ProbePinnedOriginalWintunPnP(ctx,id);err!=nil{return fmt.Errorf("inspect original Wintun PnP: %w",err)}
  rows,err:=n4ProbeOriginalIPRows(ctx,id)
  if err!=nil{return fmt.Errorf("inspect original Wintun IP rows: %w",err)}
  missingIP=rows.IPv4=="MISSING_1168"
 }
 owner:=n4StoppedNoWFPOwner{id}
 if len(j.Records)<4 {
  if _,err:=os.Stat(path+".routes");err==nil{return ErrN4JournalConflict
  }else if !errors.Is(err,os.ErrNotExist){return err}
 }
 j.Phase="cleaning"
 if err:=n4UnifiedWrite(path,j,false);err!=nil{return err}
 for len(j.Records)>0{
  if err:=ctx.Err();err!=nil{return err}
  i:=len(j.Records)-1;rec:=j.Records[i]
  var stage N4UnifiedStage
  switch rec.Name {
  case "routes":
   var before n4CompactRouteBaseline
   if err:=json.Unmarshal(rec.Before,&before);err!=nil{return err}
   if err:=n4NoWFPRecoverRoutes(ctx,path+".routes",id,before.Keys,n4StoppedNoWFPRoutes{id:id,gone:gone});err!=nil{return fmt.Errorf("restore routes: %w",err)}
  case "dns":
   var before n4DNSStageBaseline
   if err:=json.Unmarshal(rec.Before,&before);err!=nil{return err}
   if !gone {stage=n4WindowsNoWFPDNSStage{Servers:before.Servers,Owner:owner,WALPath:path}}
  case "mtu":
   var before n4MTUStageBaseline
   if err:=json.Unmarshal(rec.Before,&before);err!=nil{return err}
   if !missingIP {stage=n4WindowsNoWFPMTUStage{Target:before.Target,Owner:owner,WALPath:path}}
  case "lease":
   var before n4LeaseBaseline
   if err:=json.Unmarshal(rec.Before,&before);err!=nil{return err}
   prefix,err:=netip.ParsePrefix(before.Address);if err!=nil{return err}
   if !missingIP {stage=n4WindowsNoWFPLeaseStage{Lease:N4NativeLeaseIntent{InterfaceIndex:id.WintunIndex,Prefix:prefix},Owner:owner,WALPath:path}}
  }
  if stage!=nil{
   state,err:=stage.Inspect(ctx,id,rec.Before)
   if err!=nil{return fmt.Errorf("restore %s: %w",rec.Name,err)}
   switch state{
   case N4UnifiedAbsent:
   case N4UnifiedOwned:
    // An interrupted interface-local write can be recognized by the same
    // saved baseline and exact original device readback. Complete its
    // receipt before reusing the existing Undo implementation.
    if rec.State=="intent"{
     j.Records[i].State="owned"
     if err:=n4UnifiedWrite(path,j,false);err!=nil{return err}
    }
    if err:=stage.Undo(ctx,id,rec.Before);err!=nil{return fmt.Errorf("restore %s: %w",rec.Name,err)}
   default:return fmt.Errorf("restore %s: %w",rec.Name,ErrN4RouteAmbiguous)
   }
  }
  j.Records=j.Records[:i]
  if err:=n4UnifiedWrite(path,j,false);err!=nil{return err}
 }
 return os.Remove(path)
}
