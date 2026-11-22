package dnsnative

import "testing"

func TestB34PhysicalDnsUpstreamIPv4Cold(t *testing.T){
 for _,s:=range []string{"223.5.5.5","192.168.1.1","10.42.0.1","1.1.1.1"}{
  ip,e:=ParsePhysicalDNSUpstreamIPv4(s)
  if e!=nil||ip.String()!=s{t.Fatalf("valid physical DNS %s refused: %v",s,e)}
 }
 for _,s:=range []string{"","0.0.0.0","127.0.0.1","224.0.0.1",
  "169.254.1.1","255.255.255.255","2001:db8::1","223.005.5.5","hello.example"}{
  if _,e:=ParsePhysicalDNSUpstreamIPv4(s);e==nil{t.Fatalf("unsafe physical DNS accepted %q",s)}
 }
}
