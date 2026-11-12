//go:build windows

package windowsclient

// PLAN029 cold-only physical DNS bootstrap. Route lookup selects the
// original NIC, source IPv4, next-hop MAC and the NIC's DNS servers.
// The actual DNS query is a bounded physical NPF packet, not Winsock/TUN.
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

func appendBootstrapDNSUnique(dst []netip.Addr,v netip.Addr)[]netip.Addr{
 if !v.Is4()||v.IsUnspecified()||v.IsMulticast()||v.IsLoopback(){return dst}
 for _,old:=range dst{if old==v{return dst}}
 return append(dst,v)
}

// Query only the configured SERVER address. It cannot resolve ordinary
// business DNS and creates no app-global WFP permit or OS route mutation.
func ResolveServerAFromOriginalPhysical(ctx context.Context,host,alias string,
 resolver netip.Addr)(PhysicalServerResolution,error){
 if ctx.Err()!=nil||host==""||alias==""||!resolver.Is4()||resolver.IsUnspecified()||resolver.IsMulticast()||resolver.IsLoopback(){return PhysicalServerResolution{},ErrServerBootstrapDNS}
 var excluded uint32
 if itf,e:=net.InterfaceByName(alias);e==nil&&itf.Index>0{excluded=uint32(itf.Index)}
 // This probe only reads the default IPv4 physical route and gateway ARP.
 physical,e:=DiscoverPhysicalUnderlay(netip.MustParseAddr("9.9.9.9"),excluded)
 if e!=nil{return PhysicalServerResolution{},fmt.Errorf("%w: original physical route: %v",ErrServerBootstrapDNS,e)}
 if physical.InterfaceIndex==excluded||!physical.Source4.Is4(){return PhysicalServerResolution{},ErrServerBootstrapDNS}
 itf,e:=net.InterfaceByIndex(int(physical.InterfaceIndex))
 if e!=nil||itf==nil||itf.Name==alias{return PhysicalServerResolution{},ErrServerBootstrapDNS}
 // Exactly ONE configured dns.direct; no NIC DNS, no fallback list.
 servers:=[]netip.Addr{resolver}
 var last error
 for _,d:=range servers{
  if e:=ctx.Err();e!=nil{return PhysicalServerResolution{},e}
  u,e:=DiscoverPhysicalUnderlay(d,excluded)
  if e!=nil{last=e;continue}
  if u.InterfaceIndex!=physical.InterfaceIndex||u.Source4!=physical.Source4{
   last=ErrServerBootstrapDNS;continue
  }
  ips,e:=faketcp.LookupPhysicalServerA(ctx,faketcp.PhysicalDNSConfig{
   Device:u.PacketDevice,SourceMAC:u.SourceMAC,NextHopMAC:u.NextHopMAC,
   Source4:u.Source4,Resolver4:d},host)
  if e!=nil{last=e;continue}
  return PhysicalServerResolution{
   Selected4:ips[0],Candidate4:ips,Resolver4:d,
   PhysicalSource4:u.Source4,PhysicalIfIndex:u.InterfaceIndex,QueriedAt:time.Now(),
  },nil
 }
 return PhysicalServerResolution{},fmt.Errorf("%w: hostname %q: %v",ErrServerBootstrapDNS,host,last)
}
