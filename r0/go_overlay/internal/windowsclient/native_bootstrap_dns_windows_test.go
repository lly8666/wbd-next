//go:build windows
package windowsclient
import ("context";"errors";"net/netip";"testing";"github.com/lly8666/wobuzhidao/internal/faketcp")
func TestPlan029BootstrapRejectsMissingSingleDirectDNSWithoutNetwork(t *testing.T){
 for _,dns:=range []netip.Addr{{},netip.MustParseAddr("127.0.0.1"),
 netip.MustParseAddr("224.0.0.1"),netip.MustParseAddr("0.0.0.0"),
 netip.MustParseAddr("fe80::1"),netip.MustParseAddr("169.254.2.4")}{
  _,err:=ResolveServerAFromOriginalPhysical(context.Background(),"server.example","WBD",dns)
  if !errors.Is(err,ErrServerBootstrapDNS){t.Fatalf("resolver %s unexpectedly passed to physical IO: %v",dns,err)}
 }
}


func TestPlan029OriginalPhysicalBootstrapGuestMACExactAttestedNotGlobalOverride(t *testing.T){
 c:=faketcp.PhysicalDNSConfig{
  Device:"\\Device\\NPF_{12345678-1234-1234-1234-123456789abc}",
  SourceMAC:[6]byte{0,0x15,0x5d,1,2,3},
  NextHopMAC:[6]byte{0,0x15,0x5d,1,2,3},
  Source4:netip.MustParseAddr("172.23.96.1"),
  Resolver4:netip.MustParseAddr("172.23.104.49"),
  InterfaceIndex:23,
 }
 // Without any attestation no code changes the normal physical MAC.
 for _,k:=range []string{
  "WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC",
  "WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4",
  "WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4",
  "WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"}{t.Setenv(k,"")}
 normal,e:=physicalBootstrapExactGuestNextHop(c,c.Source4)
 if e!=nil||normal.NextHopMAC!=c.SourceMAC{t.Fatalf("normal route changed: %v",e)}
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC","00:15:5d:66:77:88")
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4",c.Resolver4.String())
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4",c.Source4.String())
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_IFINDEX","23")
 verified,e:=physicalBootstrapExactGuestNextHop(c,c.Source4)
 if e!=nil||verified.NextHopMAC==c.SourceMAC||
  verified.NextHopMAC!=([6]byte{0,0x15,0x5d,0x66,0x77,0x88}){
  t.Fatalf("original physically verified guest MAC not selected: %v %v",verified.NextHopMAC,e)
 }
 // Third party MAC/gateway is neither self next-hop nor exact guest.
 foreign:=c;foreign.NextHopMAC=[6]byte{0,0x11,0x22,0x33,0x44,0x55}
 if _,e=physicalBootstrapExactGuestNextHop(foreign,c.Source4);!errors.Is(e,ErrServerBootstrapDNS){
  t.Fatalf("foreign physical gateway accepted: %v",e)
 }
 if _,e=physicalBootstrapExactGuestNextHop(c,netip.MustParseAddr("172.23.96.254"));!errors.Is(e,ErrServerBootstrapDNS){
  t.Fatalf("unverified route next hop accepted: %v",e)
 }
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4","172.23.104.50")
 if _,e=physicalBootstrapExactGuestNextHop(c,c.Source4);!errors.Is(e,ErrServerBootstrapDNS){
  t.Fatalf("foreign guest resolver accepted: %v",e)
 }
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4",c.Resolver4.String())
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_IFINDEX","24")
 if _,e=physicalBootstrapExactGuestNextHop(c,c.Source4);!errors.Is(e,ErrServerBootstrapDNS){
  t.Fatalf("wrong physical ifindex accepted: %v",e)
 }
 t.Setenv("WBD_PLAN024_NATIVE_VERIFIED_IFINDEX","")
 if _,e=physicalBootstrapExactGuestNextHop(c,c.Source4);!errors.Is(e,ErrServerBootstrapDNS){
  t.Fatalf("partial OS evidence accepted: %v",e)
 }
}
