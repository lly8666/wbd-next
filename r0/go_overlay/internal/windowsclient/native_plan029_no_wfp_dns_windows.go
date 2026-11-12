//go:build windows

package windowsclient

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "net/netip"
 "runtime"
 "slices"
 "syscall"
 "unsafe"

 "golang.org/x/sys/windows"
)

// PLAN029 v2 no-old-WFP DNS stage: ONLY the owned Wintun's one IPv4
// NameServer field. This neither sets physical-adapter DNS nor opens a
// machine-wide allow rule. The Rust DNS dispatcher owns query-level policy.
type n4WindowsNoWFPDNSStage struct {
 Servers []netip.Addr
 Owner N4WindowsCreatedWintunReservation
 WALPath string
}
func(s n4WindowsNoWFPDNSStage) Name()string{return "dns"}
func(s n4WindowsNoWFPDNSStage) check(ctx context.Context,id N4UnifiedIdentity)error{
 if err:=ctx.Err();err!=nil{return err}
 if s.WALPath==""||!id.valid()||len(s.Servers)!=1{return ErrNetworkPlan}
 if _,_,err:=n4StaticDNSRequest(s.Servers);err!=nil{return err}
 if err:=s.Owner.Verify(ctx,id);err!=nil{return err}
 pnp,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return err}
 if pnp.InstanceSHA256!=id.PnPInstanceSHA256{return ErrN4ForeignRoute}
 return nil
}
func(s n4WindowsNoWFPDNSStage) decode(id N4UnifiedIdentity,
 b json.RawMessage)(n4DNSStageBaseline,error){
 var rec n4DNSStageBaseline
 if err:=json.Unmarshal(b,&rec);err!=nil{return rec,ErrN4JournalConflict}
 if !id.valid()||rec.Index!=id.WintunIndex||
  !slices.Equal(rec.Servers,s.Servers)||
  n4ReadOwnedDNSBaseline(rec.Before)!=nil{
  return rec,ErrN4JournalConflict
 }
 return rec,nil
}
func(s n4WindowsNoWFPDNSStage) Snapshot(ctx context.Context,id N4UnifiedIdentity)(json.RawMessage,error){
 if err:=s.check(ctx,id);err!=nil{return nil,err}
 before,err:=(N4NativeDNSReader{}).Read(ctx,id.WintunIndex)
 if err!=nil{return nil,err}
 if err:=n4ReadOwnedDNSBaseline(before);err!=nil{return nil,err}
 return json.Marshal(n4DNSStageBaseline{Index:id.WintunIndex,
  Before:before,Servers:append([]netip.Addr(nil),s.Servers...)})
}
func(s n4WindowsNoWFPDNSStage) Inspect(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)(N4UnifiedState,error){
 rec,err:=s.decode(id,b);if err!=nil{return "",err}
 if err:=s.check(ctx,id);err!=nil{return "",err}
 now,err:=(N4NativeDNSReader{}).Read(ctx,id.WintunIndex)
 if err!=nil{return "",err}
 return n4DNSClassifyState(now,rec),nil
}
// writeSingleNameServer invokes the same verified Windows DNS API as the old
// writer but WITHOUT an old WFP guard. Owner/generation + durable v2 WAL
// intent were checked independently by Apply/Undo. Changes only NameServer.
func(s n4WindowsNoWFPDNSStage) writeSingleNameServer(ctx context.Context,
 id N4UnifiedIdentity,iface windows.GUID,req n4DNSInterfaceSettingsV1,storage []uint16)error{
 if err:=ctx.Err();err!=nil{return err}
 if iface==(windows.GUID{})||req.Version!=n4DNSSettingsVersion1||
  req.Flags!=n4DNSOwnedStaticMask{return ErrNetworkPlan}
 if err:=s.check(ctx,id);err!=nil{return err}
 actual,err:=n4NativeInterfaceGUID(id.WintunIndex)
 if err!=nil{return err}
 if actual!=iface{return ErrN4ForeignRoute}
 ver:=windows.RtlGetVersion()
 if err:=n4RequireNativeDNSBuild(ver.MajorVersion,ver.BuildNumber);err!=nil{return err}
 if err:=ctx.Err();err!=nil{return err}
 if err:=n4SetInterfaceDNS.Find();err!=nil{return err}
 code,_,_:=n4SetInterfaceDNS.Call(uintptr(unsafe.Pointer(&iface)),
  uintptr(unsafe.Pointer(&req)))
 runtime.KeepAlive(storage);runtime.KeepAlive(iface)
 if code!=0{return fmt.Errorf("v2 SetInterfaceDnsSettings: %w",syscall.Errno(code))}
 return nil
}
func(s n4WindowsNoWFPDNSStage) Apply(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 rec,err:=s.decode(id,b);if err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"dns","applying","intent",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4ForeignRoute}
 req,storage,err:=n4StaticDNSRequest(s.Servers)
 if err!=nil{return err}
 if err:=s.writeSingleNameServer(ctx,id,rec.Before.Interface,req,storage);err!=nil{return err}
 state,err=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4RouteAmbiguous}
 return nil
}
func(s n4WindowsNoWFPDNSStage) Undo(ctx context.Context,id N4UnifiedIdentity,
 b json.RawMessage)error{
 rec,err:=s.decode(id,b);if err!=nil{return err}
 if err:=s.check(ctx,id);err!=nil{return err}
 if err:=n4NoWFPStageWALPermission(s.WALPath,id,"dns","cleaning","owned",b);err!=nil{return err}
 state,err:=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedOwned{return ErrN4ForeignRoute}
 req:=n4DNSInterfaceSettingsV1{Version:n4DNSSettingsVersion1,Flags:n4DNSOwnedStaticMask}
 err=s.writeSingleNameServer(ctx,id,rec.Before.Interface,req,nil)
 if errors.Is(err,syscall.Errno(87)){
  // Older Windows needs a valid empty UTF-16 WCHAR instead of nil.
  fallback,buf:=n4DNSEmptyStringClearRequest()
  err=s.writeSingleNameServer(ctx,id,rec.Before.Interface,fallback,buf)
 }
 if err!=nil{return err}
 state,err=s.Inspect(ctx,id,b)
 if err!=nil{return err}
 if state!=N4UnifiedAbsent{return ErrN4RouteAmbiguous}
 return nil
}
