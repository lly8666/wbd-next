package rootjournal

import (
 "net/netip"
 "strings"
)
// AOSP ClatCoordinator allocates 192.0.0.0/29 addresses on v4-<parent>,
// with a /32 kernel address and NAT64 /96. This checks the cold scope,
// not IPv6 forwarding, and does not mutate the translator.
func ValidCLATScope(parent,translated,prefix string,local netip.Addr)bool{
 if !nameOK(parent)||len(parent)>12||strings.HasPrefix(parent,"v4-")||translated!="v4-"+parent||
  !local.Is4(){return false}
 v:=local.As4()
 p,e:=netip.ParsePrefix(prefix)
 return v[0]==192&&v[1]==0&&v[2]==0&&v[3]>=1&&v[3]<=7&&
  e==nil&&p.Addr().Is6()&&!p.Addr().Is4In6()&&p.Bits()==96&&p==p.Masked()
}
