//go:build windows

package windowsclient

import (
 "bytes"
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "syscall"
 "time"
 "unsafe"
)

// PLAN029: real Win32 lease stage for the new four-stage no-WFP WAL.
// This is NOT an old WFP adapter or an inert "guard". Only the parent
// N4NativeUnifiedTxn may call Apply/Undo under its machine-wide exclusive
// gate and a held, generation-bound process-created Wintun reservation.
// Not yet wired to the production product entry; no OS Applied claim.
type n4WindowsNoWFPLeaseStage struct {
 Lease N4NativeLeaseIntent
 Owner N4WindowsCreatedWintunReservation
 WALPath string
}
func (s n4WindowsNoWFPLeaseStage) Name()string{return "lease"}

func n4NoWFPStageWALPermission(path string,id N4UnifiedIdentity,
 stage,phase,state string,b json.RawMessage)error{
 if path==""||!id.valid()||len(b)==0{return ErrN4JournalConflict}
 j,err:=n4UnifiedRead(path)
 if err!=nil{return err}
 if j.Schema!=n4UnifiedSchemaNoWFP||j.Identity!=id||j.Phase!=phase||
  len(j.Records)==0{return ErrN4JournalConflict}
 last:=j.Records[len(j.Records)-1]
 // Inspect other records isn't enough: an unconfirmed create must not be
 // mistaken for a confirmed Delete. Compare the exact persisted baseline.
 if last.Name!=stage||last.State!=state||
  !bytes.Equal(last.Before,b){return ErrN4JournalConflict}
 return nil
}
func (s n4WindowsNoWFPLeaseStage) check(ctx context.Context,id N4UnifiedIdentity)error{
 if err:=ctx.Err();err!=nil{return err}
 if s.WALPath==""||!id.valid()||
  n4ValidateLeaseIntent(s.Lease)!=nil||
  s.Lease.InterfaceIndex!=id.WintunIndex{
  return ErrNetworkPlan
 }
 if err:=s.Owner.Verify(ctx,id);err!=nil{return err}
 observed,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return err}
 if observed.InstanceSHA256!=id.PnPInstanceSHA256{
  return ErrN4ForeignRoute
 }
 return nil
}
func(s n4WindowsNoWFPLeaseStage) decode(id N4UnifiedIdentity,b json.RawMessage)error{
 var rec n4LeaseBaseline
 if err:=json.Unmarshal(b,&rec);err!=nil{return ErrN4JournalConflict}
 if !rec.Absent||rec.Index!=id.WintunIndex||
  rec.Address!=s.Lease.Prefix.String(){return ErrN4JournalConflict}
 return nil
}
func(s n4WindowsNoWFPLeaseStage) Snapshot(ctx context.Context,id N4UnifiedIdentity)(json.RawMessage,error){
 if err:=s.check(ctx,id);err!=nil{return nil,err}
 entries,err:=(N4WindowsAddressSnapshot{}).IPv4(ctx,id.WintunIndex)
 if err!=nil{return nil,err}
 if len(entries)!=0{return nil,ErrN4ForeignRoute}
 return json.Marshal(n4LeaseBaseline{Index:id.WintunIndex,
  Address:s.Lease.Prefix.String(),Absent:true})
}
func(s n4WindowsNoWFPLeaseStage) Inspect(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)(N4UnifiedState,error){
 if err:=s.decode(id,b);err!=nil{return "",err}
 if err:=s.check(ctx,id);err!=nil{return "",err}
 entries,err:=(N4WindowsAddressSnapshot{}).IPv4(ctx,id.WintunIndex)
 if err!=nil{return "",err}
 if len(entries)==0{return N4UnifiedAbsent,nil}
 if len(entries)!=1||entries[0].InterfaceIndex!=id.WintunIndex||
  entries[0].Address!=s.Lease.Prefix.Addr(){return N4UnifiedForeign,nil}
 row,found,err:=(N4WindowsLeaseReader{}).Lookup(ctx,s.Lease)
 if err!=nil{
  if errors.Is(err,ErrN4ForeignRoute){return N4UnifiedForeign,nil}
  return "",err
 }
 if !found{return N4UnifiedPartial,nil}
 if err:=N4NativeLeaseDADGate(row,s.Lease);err!=nil{
  if errors.Is(err,ErrN4LeaseNotPreferred){return N4UnifiedPartial,nil}
  if errors.Is(err,ErrN4ForeignRoute){return N4UnifiedForeign,nil}
  return "",err
 }
 return N4UnifiedOwned,nil
}
func(s n4WindowsNoWFPLeaseStage) Apply(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 if err:=s.decode(id,b);err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"lease","applying","intent",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 row,err:=n4NativeLeaseRow(s.Lease);if err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=n4CreateUnicast.Find();err!=nil{return err}
 code,_,_:=n4CreateUnicast.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{return fmt.Errorf("v2 CreateUnicastIpAddressEntry: %w",syscall.Errno(code))}
 // Windows DAD completion is required before the parent WAL may record
 // "owned". The durable intent is retained on any readback failure.
 timer:=time.NewTimer(8*time.Second);defer timer.Stop()
 ticker:=time.NewTicker(100*time.Millisecond);defer ticker.Stop()
 for{
  state,err:=s.Inspect(ctx,id,b)
  if err!=nil{return err}
  switch state{
  case N4UnifiedOwned:return nil
  case N4UnifiedPartial:
  default:return ErrN4RouteAmbiguous
  }
  select{
  case <-ctx.Done():return ctx.Err()
  case <-timer.C:return ErrN4LeaseNotPreferred
  case <-ticker.C:
  }
 }
}
func(s n4WindowsNoWFPLeaseStage) Undo(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 if err:=s.decode(id,b);err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"lease","cleaning","owned",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4ForeignRoute}
 row,present,err:=(N4WindowsLeaseReader{}).Lookup(ctx,s.Lease)
 if err!=nil{return err}
 if !present{return ErrN4RouteAmbiguous}
 if err:=N4NativeLeaseDADGate(row,s.Lease);err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=n4DeleteUnicast.Find();err!=nil{return err}
 code,_,_:=n4DeleteUnicast.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{return fmt.Errorf("v2 DeleteUnicastIpAddressEntry: %w",syscall.Errno(code))}
 state,err=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4RouteAmbiguous}
 return nil
}
