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
 "os"
 "strconv"
 "strings"
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


// The original signed WSL2 source gave evidence that SendARP can resolve
// its GUEST IP to the WINDOWS vEthernet source MAC. Original Go FakeTCP
// already fixes that single observed self-next-hop case, using the actual
// Linux eth0 MAC + host NIC/source/guest/ifindex read back by the test owner.
// Physical bootstrap sends its UDP DNS BEFORE TLS and must apply the same
// exact physical L2 constraint. A missing/partial/foreign witness fails
// closed; no socket, route, WFP, global DNS or alternate resolver is used.
func physicalBootstrapExactGuestNextHop(c faketcp.PhysicalDNSConfig,
 osNextHop netip.Addr)(faketcp.PhysicalDNSConfig,error){
 guestMac:=strings.TrimSpace(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC"))
 guest4:=strings.TrimSpace(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"))
 host4:=strings.TrimSpace(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"))
 idx:=strings.TrimSpace(os.Getenv("WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"))
 if guestMac==""&&guest4==""&&host4==""&&idx==""{
  // Ordinary customer underlay never depends on the CI-specific evidence.
  return c,nil
 }
 if guestMac==""||guest4==""||host4==""||idx==""{
  return c,fmt.Errorf("%w: incomplete original physical guest evidence",ErrServerBootstrapDNS)
 }
 index,e:=strconv.ParseUint(idx,10,32)
 if e!=nil||index==0||uint32(index)!=c.InterfaceIndex{
  return c,fmt.Errorf("%w: original physical guest ifindex changed",ErrServerBootstrapDNS)
 }
 guest,e:=netip.ParseAddr(guest4)
 if e!=nil||!guest.Is4()||guest!=c.Resolver4{
  return c,fmt.Errorf("%w: original guest address != single dns.direct",ErrServerBootstrapDNS)
 }
 host,e:=netip.ParseAddr(host4)
 if e!=nil||!host.Is4()||host!=c.Source4{
  return c,fmt.Errorf("%w: original physical source moved",ErrServerBootstrapDNS)
 }
 mac,e:=net.ParseMAC(guestMac)
 if e!=nil||len(mac)!=6||mac[0]&1!=0{
  return c,fmt.Errorf("%w: invalid original Linux eth0 MAC",ErrServerBootstrapDNS)
 }
 var actual [6]byte
 copy(actual[:],mac)
 if actual==([6]byte{})||actual==c.SourceMAC||
    (osNextHop!=c.Resolver4 && !(osNextHop==c.Source4&&
     c.NextHopMAC==c.SourceMAC))||
    (c.NextHopMAC!=actual&&c.NextHopMAC!=c.SourceMAC){
  return c,fmt.Errorf("%w: unverified foreign physical next hop",ErrServerBootstrapDNS)
 }
 // Never blindly copy an environment MAC: all selected OS physical
 // identities above must match AND the original NPF L2 result must be
 // either that exact guest MAC or the already observed host-self MAC.
 c.NextHopMAC=actual
 return c,nil
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
 cfg:=faketcp.PhysicalDNSConfig{
  Device:physical.PacketDevice,SourceMAC:physical.SourceMAC,
  NextHopMAC:physical.NextHopMAC,Source4:physical.Source4,
  Resolver4:resolver,InterfaceIndex:physical.InterfaceIndex}
 cfg,e=physicalBootstrapExactGuestNextHop(cfg,physical.NextHop4)
 if e!=nil{return PhysicalServerResolution{},e}
 ips,e:=faketcp.LookupPhysicalServerA(ctx,cfg,host)
 if e!=nil{return PhysicalServerResolution{},fmt.Errorf("%w: %s via single dns.direct %s: %v",ErrServerBootstrapDNS,host,resolver,e)}
 if len(ips)==0{return PhysicalServerResolution{},fmt.Errorf("%w: %s via dns.direct %s returned no usable A",ErrServerBootstrapDNS,host,resolver)}
 return PhysicalServerResolution{
  Selected4:ips[0],Candidate4:ips,Resolver4:resolver,
  PhysicalSource4:physical.Source4,PhysicalIfIndex:physical.InterfaceIndex,
  QueriedAt:time.Now(),
 },nil
}
