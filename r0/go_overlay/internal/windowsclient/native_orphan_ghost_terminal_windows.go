//go:build windows

package windowsclient

import (
 "context"
 "encoding/json"
 "errors"
 "net/netip"
 "os"
)

// n4RetirePinnedGhostPreRouteWAL is a distinct terminal *device-gone*
// recovery, NOT an assertion that MTU on the disappeared interface was
// restored. This is never called for a live Wintun or any route-stage WAL.
// Every write is under the original cross-process machine exclusion and
// only the original checksum-valid generation and pinned PnP is accepted.
// It is deliberately private: production WFP Arm and public CLI still gate.
func n4RetirePinnedGhostPreRouteWAL(
 ctx context.Context,path string,id N4UnifiedIdentity,g CrashPersistentGuard,
)error{
 if ctx==nil{return ErrN4NativeGuard}
 if err:=ctx.Err();err!=nil{return err}
 if path==""||!id.valid()||!n4ValidPinnedPnPHash(id.PnPInstanceSHA256)||
  g==nil||!g.Durable(){return ErrN4JournalConflict}
 gate,err:=(N4WindowsMachineGate{}).Acquire(ctx)
 if err!=nil{return err}
 defer gate()
 j,err:=n4UnifiedRead(path)
 if err!=nil{return err}
 if err:=n4ValidatePersistedPreRouteJournal(j,id);err!=nil{return err}
 if j.Phase!="cleaning"||(len(j.Records)!=3&&len(j.Records)!=1)||
  j.Records[0].Name!="guard"||j.Records[0].State!="owned"{
  return ErrN4JournalConflict
 }
 // An occupied sidecar means the transaction MAY have installed global
 // capture routes. Never retire the sole persistent guard in that case.
 if _,err=os.Lstat(path+".routes");err==nil{return ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return err}
 inspectGhost:=func()error{
  if err:=n4OriginalWintunPersistedExact(ctx,id);err!=nil{return err}
  p,err:=n4ProbePinnedOriginalWintunPnP(ctx,id)
  if err!=nil{return err}
  if p.State!="EXACT_PNP_DEVNODE_GONE_13"{return ErrN4NativeGuard}
  rows,err:=n4ProbeOriginalIPRows(ctx,id)
  if err!=nil{return err}
  if rows.IPv4!="MISSING_1168"||rows.IPv6!="MISSING_1168"{
   return ErrN4NativeGuard
  }
  all,err:=(N4WindowsAddressSnapshot{}).IPv4(ctx,id.WintunIndex)
  if err!=nil{return err}
  if len(all)!=0{return ErrN4RouteAmbiguous}
  return nil
 }
 if err:=inspectGhost();err!=nil{return err}
 // Prove no original /1 capture route survived outside the pre-route WAL.
 // Do not delete any foreign route or trust the deleted NIC's current alias.
 for _,half:=range []string{"0.0.0.0/1","128.0.0.0/1"}{
  key:=NativeRouteKey{Prefix:netip.MustParsePrefix(half),
   Interface:id.WintunIndex,NextHop:netip.IPv4Unspecified(),Metric:5}
  present,_,err:=(N4WindowsRouteBackend{}).Lookup(ctx,key)
  if err!=nil{return err}
  if present{return ErrN4RouteAmbiguous}
 }
 if len(j.Records)==3{
  if j.Records[1].Name!="lease"||j.Records[1].State!="owned"||
   j.Records[2].Name!="mtu"||j.Records[2].State!="owned"{
   return ErrN4JournalConflict
  }
  // Parse and validate BOTH durable original receipts. A missing IP Helper
  // row alone does not prove that either receipt is safe to retire.
  var lease n4LeaseBaseline
  if err:=json.Unmarshal(j.Records[1].Before,&lease);err!=nil{return ErrN4JournalConflict}
  prefix,err:=netip.ParsePrefix(lease.Address)
  if err!=nil||!lease.Absent||lease.Index!=id.WintunIndex||
   !prefix.Addr().Is4()||prefix.Bits()!=32{return ErrN4JournalConflict}
  intent:=N4NativeLeaseIntent{InterfaceIndex:id.WintunIndex,Prefix:prefix}
  if err:=n4ValidateLeaseIntent(intent);err!=nil{return ErrN4JournalConflict}
  var mtu n4MTUStageBaseline
  if err:=json.Unmarshal(j.Records[2].Before,&mtu);err!=nil{return ErrN4JournalConflict}
  if mtu.Before.Index!=id.WintunIndex||mtu.Before.MTU==mtu.Target||
   N4VerifyOwnedTunnelMTU(mtu.Before,id.WintunIndex,mtu.Target)!=nil{
   return ErrN4JournalConflict
  }
  _,present,err:=(N4WindowsLeaseReader{}).Lookup(ctx,intent)
  if err!=nil{return err}
  if present{return ErrN4RouteAmbiguous}
 }
 armed,err:=g.Verify(ctx)
 if err!=nil{return err}
 if len(j.Records)==3{
  // A previously disarmed guard with remaining WAL is foreign or a failed
  // recovery, not authority for silently dropping the original records.
  if !armed{return ErrN4NativeGuard}
  if err:=inspectGhost();err!=nil{return err}
  // DNS must already have been independently CAS-cleared and fsynced by
  // n4RestoreGhostDNSOnly; this record set is exactly guard+lease+MTU.
  // Atomic shrink is crash-replayable and makes ZERO native MTU writes.
  j.Records=j.Records[:1]
  if err:=n4UnifiedWrite(path,j,false);err!=nil{return err}
 }
 if err:=inspectGhost();err!=nil{return err}
 if armed{
  if err:=n4FinishGuardAfterRoutes(ctx,g);err!=nil{return err}
 }
 remains,err:=g.Verify(ctx)
 if err!=nil{return err}
 if remains{return ErrN4NativeGuard}
 if err:=inspectGhost();err!=nil{return err}
 now,err:=n4UnifiedRead(path)
 if err!=nil{return err}
 if now.Identity!=id||now.Phase!="cleaning"||
  len(now.Records)!=1||now.Records[0].Name!="guard"{
  return ErrN4JournalConflict
 }
 if _,err:=os.Lstat(path+".routes");err==nil{return ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return err}
 // Only the exact now-dead original is retired. No alias reopening,
 // driver removal, OS MTU setter, DNS reset, or global route mutation.
 return os.Remove(path)
}
