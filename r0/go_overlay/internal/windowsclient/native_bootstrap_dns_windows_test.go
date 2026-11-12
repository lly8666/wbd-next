//go:build windows
package windowsclient
import ("net/netip";"testing")
func TestPlan029BootstrapDNSBoundedPhysicalCandidates(t *testing.T){
 a,b:=netip.MustParseAddr("192.168.1.1"),netip.MustParseAddr("1.1.1.1")
 var got []netip.Addr
 for _,x:=range []netip.Addr{a,b,a,netip.IPv6Loopback(),b}{got=appendBootstrapDNSUnique(got,x)}
 if len(got)!=2||got[0]!=a||got[1]!=b{t.Fatalf("wanted only distinct original DNS4: %v",got)}
}
