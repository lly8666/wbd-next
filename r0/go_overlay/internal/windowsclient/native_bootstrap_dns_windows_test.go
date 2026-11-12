//go:build windows
package windowsclient
import ("context";"errors";"net/netip";"testing")
func TestPlan029BootstrapRejectsMissingSingleDirectDNSWithoutNetwork(t *testing.T){
 for _,dns:=range []netip.Addr{{},netip.MustParseAddr("127.0.0.1"),
 netip.MustParseAddr("224.0.0.1"),netip.MustParseAddr("0.0.0.0"),
 netip.MustParseAddr("fe80::1"),netip.MustParseAddr("169.254.2.4")}{
  _,err:=ResolveServerAFromOriginalPhysical(context.Background(),"server.example","WBD",dns)
  if !errors.Is(err,ErrServerBootstrapDNS){t.Fatalf("resolver %s unexpectedly passed to physical IO: %v",dns,err)}
 }
}
