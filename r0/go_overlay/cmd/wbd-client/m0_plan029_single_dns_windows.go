//go:build windows
package main
import ("fmt";"net/netip";"strings")
func m0Plan029SingleDNS4(s,key string)(netip.Addr,error){
 a,e:=netip.ParseAddr(strings.TrimSpace(s))
 if e!=nil||!a.Is4()||a.IsUnspecified()||a.IsMulticast()||
   a.IsLoopback()||a.IsLinkLocalUnicast()||a==netip.MustParseAddr("255.255.255.255"){
  return netip.Addr{},fmt.Errorf("%s: exactly one usable IPv4 DNS, port 53",key)
 }
 return a.Unmap(),nil
}
// Old dns4 is migration-only. No backup, NIC resolvers, cross-side fallback.
func m0Plan029DNSSettings(directText,tunnelText,legacy string,explicitTunnel bool)(
 direct,tunnel netip.Addr,retired int,err error){
 direct,err=m0Plan029SingleDNS4(directText,"dns.direct");if err!=nil{return}
 tunnel,err=m0Plan029SingleDNS4(tunnelText,"dns.tunnel");if err!=nil{return}
 if strings.TrimSpace(legacy)==""{return}
 parts:=strings.FieldsFunc(legacy,func(r rune)bool{return r==','||r==';'})
 if len(parts)==0{err=fmt.Errorf("dns4: no legacy first resolver");return}
 old,e:=m0Plan029SingleDNS4(parts[0],"dns4");if e!=nil{err=e;return}
 for _,item:=range parts[1:]{
  if _,e:=m0Plan029SingleDNS4(item,"dns4 retired item");e!=nil{err=e;return}
  retired++
 }
 if explicitTunnel{
  if old!=tunnel{err=fmt.Errorf("dns4 conflicts with dns.tunnel: remove legacy dns4")}
  return
 }
 tunnel=old
 return
}
