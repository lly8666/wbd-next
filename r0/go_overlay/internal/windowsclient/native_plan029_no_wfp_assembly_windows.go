//go:build windows

package windowsclient

import (
 "context"
 "errors"
 "net/netip"
 "os"
)

// PLAN029 no-old-WFP: one shared four-stage transaction implementation with
// real Win32 writers. This is an ASSEMBLY/PREFLIGHT ONLY entry until exact
// OS capability, crash recovery and signed Rust packet owner are qualified.
// Never replace the old 5-stage recovery or manufacture a fake WFP guard.
func n4AssembleWindowsNoWFPNativeTxn(
 ctx context.Context,tun *TUN,plan NetworkPlan,id N4UnifiedIdentity,
 tcpSynthetic4 ...netip.Addr,
)(*N4NativeUnifiedTxn,error){
 if err:=ctx.Err();err!=nil{return nil,err}
 if tun==nil||!tun.createdByProcess||!id.valid()||
  plan.Schema!=StateSchema||plan.StatePath==""||
  plan.AdapterAlias==""||tun.Name()!=plan.AdapterAlias||
  id.AdapterAlias!=plan.AdapterAlias||id.WintunGUID==""||
  len(id.WintunGUID)>64||len(id.AdapterAlias)>128{
  return nil,ErrN4ForeignRoute
 }
 // Only ONE tunnel resolver is the native Windows OS static DNS. The
 // direct resolver is a separate physical bootstrap/DNS worker endpoint.
 if len(plan.DNSServers4)!=1{return nil,ErrNetworkPlan}
 if _,_,err:=n4StaticDNSRequest(plan.DNSServers4);err!=nil{return nil,err}
 var tcpPeer netip.Addr
 if len(tcpSynthetic4)>1{return nil,ErrNetworkPlan}
 if len(tcpSynthetic4)==1{tcpPeer=tcpSynthetic4[0]}
 keys,err:=N4BuildCompactNativeRouteKeys(plan,id.WintunIndex)
 if err!=nil{return nil,err}
 if _,err:=n4NoWFPWithSyntheticTCPKey(keys,plan,tcpPeer);err!=nil{return nil,err}
 if _,err:=n4StageLeaseIntent(id.WintunIndex,plan.Lease4);err!=nil{return nil,err}
 // The old PowerShell state is a different owner; never steal it or
 // cross-recover a v1 WFP transaction using the new v2 stage set.
 if _,err:=os.Stat(plan.StatePath);err==nil{return nil,ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return nil,err}
 owner:=N4WindowsCreatedWintunReservation{Tunnel:tun,
  Installation:id.Installation,Generation:id.Generation}
 if err:=owner.Verify(ctx,id);err!=nil{return nil,err}
 observed,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{return nil,err}
 if observed.InstanceSHA256!=id.PnPInstanceSHA256{return nil,ErrN4ForeignRoute}
 wal:=plan.StatePath+".n4-owned-wal"
 n:=&N4NativeUnifiedTxn{
  Path:wal,Identity:id,Gate:N4WindowsMachineGate{},Owner:owner,
  noLegacyWFP:true,assemblyOnly:true,
  Stages:[5]N4UnifiedStage{
   n4WindowsNoWFPLeaseStage{Lease:N4NativeLeaseIntent{InterfaceIndex:id.WintunIndex,
    Prefix:plan.Lease4},Owner:owner,WALPath:wal},
   n4WindowsNoWFPMTUStage{Target:plan.TunnelMTU,Owner:owner,WALPath:wal},
   n4WindowsNoWFPDNSStage{Servers:append([]netip.Addr(nil),plan.DNSServers4...),
    Owner:owner,WALPath:wal},
   n4WindowsNoWFPRouteStage{Plan:plan,Owner:owner,
    WALPath:wal,Backend:N4WindowsRouteBackend{},SyntheticTCP4:tcpPeer},
  },
 }
 if err:=n.preflight();err!=nil{return nil,err}
 return n,nil
}
