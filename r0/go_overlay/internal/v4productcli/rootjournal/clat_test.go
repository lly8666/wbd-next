package rootjournal
import (
 "net/netip"
 "testing"
)
func TestB67CLATScopeOriginalIPv4OnIPv6Underlay(t *testing.T){
 ip:=netip.MustParseAddr("192.0.0.4")
 if !ValidCLATScope("rmnet0","v4-rmnet0","64:ff9b::/96",ip){t.Fatal("valid CLAT scope refused")}
 for _,x:=range []struct{parent,iface,prefix,ip string}{
  {"rmnet0","v4-rmnet1","64:ff9b::/96","192.0.0.4"},
  {"rmnet0","v4-rmnet0","64:ff9b::/64","192.0.0.4"},
  {"rmnet0","v4-rmnet0","64:ff9b::/96","192.0.0.8"},
  {"rmnet0","v4-rmnet0","64:ff9b::/96","10.0.0.4"},
 }{if ValidCLATScope(x.parent,x.iface,x.prefix,netip.MustParseAddr(x.ip)){t.Fatal("foreign CLAT scope",x)}}
}
