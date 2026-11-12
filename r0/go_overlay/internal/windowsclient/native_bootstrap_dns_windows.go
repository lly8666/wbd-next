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
 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "golang.org/x/sys/windows"
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

func physicalIPv4DNSServers(index uint32)([]netip.Addr,error){
 if index==0{return nil,ErrServerBootstrapDNS}
 size:=uint32(16*1024)
 for attempt:=0;attempt<3;attempt++{
  buf:=make([]byte,size)
  first:=(*windows.IpAdapterAddresses)(unsafe.Pointer(&buf[0]))
  e:=windows.GetAdaptersAddresses(uint32(windows.AF_INET),
   windows.GAA_FLAG_INCLUDE_PREFIX,0,first,&size)
  if errors.Is(e,windows.ERROR_BUFFER_OVERFLOW){continue}
  if e!=nil{return nil,fmt.Errorf("%w: read physical DNS: %v",ErrServerBootstrapDNS,e)}
  for a:=first;a!=nil;a=a.Next{
   if a.IfIndex!=index{continue}
   if a.OperStatus!=windows.IfOperStatusUp||a.IfType==windows.IF_TYPE_SOFTWARE_LOOPBACK{
    return nil,ErrServerBootstrapDNS
   }
   var out []netip.Addr
   for d:=a.FirstDnsServerAddress;d!=nil&&len(out)<2;d=d.Next{
    ip:=d.Address.IP().To4();if ip==nil{continue}
    addr,ok:=netip.AddrFromSlice(ip);if !ok{continue}
    addr=addr.Unmap()
    if !addr.Is4()||addr.IsUnspecified()||addr.IsMulticast()||addr.IsLoopback(){continue}
    seen:=false;for _,v:=range out{if v==addr{seen=true;break}}
    if !seen{out=append(out,addr)}
   }
   return out,nil
  }
  return nil,ErrServerBootstrapDNS
 }
 return nil,fmt.Errorf("%w: adapter enumeration changed",ErrServerBootstrapDNS)
}

func appendBootstrapDNSUnique(dst []netip.Addr,v netip.Addr)[]netip.Addr{
 if !v.Is4()||v.IsUnspecified()||v.IsMulticast()||v.IsLoopback(){return dst}
 for _,old:=range dst{if old==v{return dst}}
 return append(dst,v)
}

// Query only the configured SERVER address. It cannot resolve ordinary
// business DNS and creates no app-global WFP permit or OS route mutation.
func ResolveServerAFromOriginalPhysical(ctx context.Context,host,alias string,
 fallback []netip.Addr)(PhysicalServerResolution,error){
 if ctx.Err()!=nil||host==""||alias==""{return PhysicalServerResolution{},ErrServerBootstrapDNS}
 var excluded uint32
 if itf,e:=net.InterfaceByName(alias);e==nil&&itf.Index>0{excluded=uint32(itf.Index)}
 // This probe only reads the default IPv4 physical route and gateway ARP.
 physical,e:=DiscoverPhysicalUnderlay(netip.MustParseAddr("9.9.9.9"),excluded)
 if e!=nil{return PhysicalServerResolution{},fmt.Errorf("%w: original physical route: %v",ErrServerBootstrapDNS,e)}
 if physical.InterfaceIndex==excluded||!physical.Source4.Is4(){return PhysicalServerResolution{},ErrServerBootstrapDNS}
 itf,e:=net.InterfaceByIndex(int(physical.InterfaceIndex))
 if e!=nil||itf==nil||itf.Name==alias{return PhysicalServerResolution{},ErrServerBootstrapDNS}
 list,e:=physicalIPv4DNSServers(physical.InterfaceIndex)
 if e!=nil{return PhysicalServerResolution{},e}
 var servers []netip.Addr
 for _,d:=range list{servers=appendBootstrapDNSUnique(servers,d)}
 if len(fallback)==0{fallback=[]netip.Addr{
  netip.MustParseAddr("1.1.1.1"),netip.MustParseAddr("8.8.8.8")}}
 for _,d:=range fallback{
  if len(servers)>=4{break}
  servers=appendBootstrapDNSUnique(servers,d)
 }
 if len(servers)==0{return PhysicalServerResolution{},ErrServerBootstrapDNS}
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
