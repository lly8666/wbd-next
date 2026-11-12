//go:build windows

package windowsclient

import (
 "context"
 "encoding/json"
 "fmt"
 "syscall"
 "unsafe"
)

// PLAN029 no-old-WFP native MTU stage. Reuse the original Win32
// GetIpInterfaceEntry/SetIpInterfaceEntry and exact interface snapshot.
// A successful Set by itself never proves Applied: the original unified
// WAL must hold an exact stage intent and independently read the OS row.
type n4WindowsNoWFPMTUStage struct {
 Target uint32
 Owner N4WindowsCreatedWintunReservation
 WALPath string
}
func(s n4WindowsNoWFPMTUStage) Name()string{return "mtu"}
func(s n4WindowsNoWFPMTUStage) check(ctx context.Context,id N4UnifiedIdentity)error{
 if err:=ctx.Err();err!=nil{return err}
 if s.WALPath==""||!id.valid(){return ErrN4JournalConflict}
 if err:=s.Owner.Verify(ctx,id);err!=nil{return err}
 pnp,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return err}
 if pnp.InstanceSHA256!=id.PnPInstanceSHA256{return ErrN4ForeignRoute}
 return nil
}
func(s n4WindowsNoWFPMTUStage) decode(id N4UnifiedIdentity,b json.RawMessage)(n4MTUStageBaseline,error){
 var rec n4MTUStageBaseline
 if err:=json.Unmarshal(b,&rec);err!=nil{return rec,ErrN4JournalConflict}
 if !id.valid()||rec.Before.Index!=id.WintunIndex||
  rec.Target!=s.Target||rec.Before.MTU==rec.Target||
  N4VerifyOwnedTunnelMTU(rec.Before,id.WintunIndex,s.Target)!=nil{
  return rec,ErrN4JournalConflict
 }
 return rec,nil
}
func(s n4WindowsNoWFPMTUStage) Snapshot(ctx context.Context,id N4UnifiedIdentity)(json.RawMessage,error){
 if err:=s.check(ctx,id);err!=nil{return nil,err}
 before,err:=(N4WindowsInterfaceReader{}).ReadIPv4(ctx,id.WintunIndex)
 if err!=nil{return nil,err}
 if err:=N4VerifyOwnedTunnelMTU(before,id.WintunIndex,s.Target);err!=nil{return nil,err}
 if before.MTU==s.Target{return nil,ErrNetworkPlan}
 return json.Marshal(n4MTUStageBaseline{Before:before,Target:s.Target})
}
func(s n4WindowsNoWFPMTUStage) Inspect(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)(N4UnifiedState,error){
 rec,err:=s.decode(id,b);if err!=nil{return "",err}
 if err:=s.check(ctx,id);err!=nil{return "",err}
 current,err:=(N4WindowsInterfaceReader{}).ReadIPv4(ctx,id.WintunIndex)
 if err!=nil{return "",err}
 if current==rec.Before{return N4UnifiedAbsent,nil}
 expected:=rec.Before;expected.MTU=rec.Target
 if current==expected{return N4UnifiedOwned,nil}
 return N4UnifiedForeign,nil
}
func(s n4WindowsNoWFPMTUStage) Apply(ctx context.Context,id N4UnifiedIdentity,b json.RawMessage)error{
 rec,err:=s.decode(id,b);if err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"mtu","applying","intent",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 row,err:=n4GetIPv4InterfaceRow(ctx,id.WintunIndex)
 if err!=nil{return err}
 if n4MTUSnapshotFromRow(row)!=rec.Before{return ErrN4ForeignRoute}
 if err:=ctx.Err();err!=nil{return err}
 if err:=n4SetIPInterface.Find();err!=nil{return err}
 n4PrepareIPv4MTUSetRow(&row,rec.Target)
 code,_,_:=n4SetIPInterface.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{return fmt.Errorf("v2 SetIpInterfaceEntry: %w",syscall.Errno(code))}
 state,err=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4RouteAmbiguous}
 return nil
}
func(s n4WindowsNoWFPMTUStage) Undo(ctx context.Context,id N4UnifiedIdentity,b json.RawMessage)error{
 rec,err:=s.decode(id,b);if err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"mtu","cleaning","owned",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4ForeignRoute}
 row,err:=n4GetIPv4InterfaceRow(ctx,id.WintunIndex)
 if err!=nil{return err}
 expected:=rec.Before;expected.MTU=rec.Target
 if n4MTUSnapshotFromRow(row)!=expected{return ErrN4ForeignRoute}
 if err:=ctx.Err();err!=nil{return err}
 if err:=n4SetIPInterface.Find();err!=nil{return err}
 // The old Wintun MTU may legitimately exceed the new 576..9000 input
 // range. It was saved from the OS and is CAS-protected, not user input.
 n4PrepareIPv4MTUSetRow(&row,rec.Before.MTU)
 code,_,_:=n4SetIPInterface.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{return fmt.Errorf("v2 restore SetIpInterfaceEntry: %w",syscall.Errno(code))}
 state,err=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4RouteAmbiguous}
 return nil
}
