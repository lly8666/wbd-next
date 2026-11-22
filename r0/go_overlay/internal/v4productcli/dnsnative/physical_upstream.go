package dnsnative

import (
    "fmt"
    "net/netip"
)

// ParsePhysicalDNSUpstreamIPv4 is the Android original-Go cold validator.
// No query socket is opened until the authenticated Rust M4 generation
// installs its already-existing physically network-bound UDP DNS owner.
func ParsePhysicalDNSUpstreamIPv4(input string)(netip.Addr,error){
    ip,e:=netip.ParseAddr(input)
    if e!=nil||!ip.Is4()||ip.IsUnspecified()||ip.IsLoopback()||
        ip.IsMulticast()||ip.IsLinkLocalUnicast()||
        ip.As4()[0]>=224||ip.String()!=input{
        return netip.Addr{},fmt.Errorf("physical app DNS upstream requires canonical routable IPv4")
    }
    return ip,nil
}
