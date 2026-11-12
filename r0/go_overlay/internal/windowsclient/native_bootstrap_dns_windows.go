//go:build windows

package windowsclient

// PLAN029 cold-only physical DNS bootstrap. The single configured direct
// resolver is also the physical route-selection target; no NIC DNS list,
// static probe IP, extra resolver or tunnel/system DNS fallback. Actual A
// queries are bounded physical NPF packets, not Winsock/TUN.
import (
 "context"
 "errors"
 "fmt"
 "net"
 "net/netip"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)

var ErrServerBootstrapDNS=errors.New("windowsclient: physical server DNS bootstrap unavailable")

type PhysicalServerResolution struct{
 Selected4 netip.Addr
 Candidate4 []netip.Addr
 Resolver4 netip.Addr
 PhysicalSource4 netip.Addr
 PhysicalIfIndex uint32
 QueriedAt time.Time
}

// Query only the configured SERVER address, using exactly its direct DNS
// endpoint to discover the original physical interface and next-hop. It never
// queries the system/NIC DNS list or another route-probe address.
func ResolveServerAFromOriginalPhysical(ctx context.Context,host,alias string,
 resolver netip.Addr)(PhysicalServerResolution,error){
 if ctx==nil||ctx.Err()!=nil||host==""||alias==""||
  !resolver.Is4()||!resolver.IsGlobalUnicast()||
  resolver.IsLoopback()||resolver.IsMulticast()||resolver.IsLinkLocalUnicast(){
  return PhysicalServerResolution{},ErrServerBootstrapDNS
 }
 var excluded uint32
 if itf,e:=net.InterfaceByName(alias);e==nil&&itf.Index>0{excluded=uint32(itf.Index)}
 // Exclude the owned Wintun from actual selected routes even after /1
 // capture; the underlay owns this source IP and packet device.
 physical,e:=DiscoverPhysicalUnderlay(resolver,excluded)
 if e!=nil{return PhysicalServerResolution{},fmt.Errorf("%w: original physical route for dns.direct %s: %v",ErrServerBootstrapDNS,resolver,e)}
 if physical.InterfaceIndex==0||physical.InterfaceIndex==excluded||
  !physical.Source4.Is4()||physical.PacketDevice==""{
  return PhysicalServerResolution{},ErrServerBootstrapDNS
 }
 itf,e:=net.InterfaceByIndex(int(physical.InterfaceIndex))
 if e!=nil||itf==nil||itf.Name==alias{return PhysicalServerResolution{},ErrServerBootstrapDNS}
 if e:=ctx.Err();e!=nil{return PhysicalServerResolution{},e}
 ips,e:=faketcp.LookupPhysicalServerA(ctx,faketcp.PhysicalDNSConfig{
  Device:physical.PacketDevice,SourceMAC:physical.SourceMAC,
  NextHopMAC:physical.NextHopMAC,Source4:physical.Source4,
  Resolver4:resolver},host)
 if e!=nil{return PhysicalServerResolution{},fmt.Errorf("%w: %s via single dns.direct %s: %v",ErrServerBootstrapDNS,host,resolver,e)}
 if len(ips)==0{return PhysicalServerResolution{},fmt.Errorf("%w: %s via dns.direct %s returned no usable A",ErrServerBootstrapDNS,host,resolver)}
 return PhysicalServerResolution{
  Selected4:ips[0],Candidate4:ips,Resolver4:resolver,
  PhysicalSource4:physical.Source4,PhysicalIfIndex:physical.InterfaceIndex,
  QueriedAt:time.Now(),
 },nil
}
