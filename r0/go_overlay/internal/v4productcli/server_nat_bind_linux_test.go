//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
 "net"
 "net/netip"
 "strings"
 "testing"
)

func addrForNATTest(ip string, mask int) net.Addr {
 addr := netip.MustParseAddr(ip)
 bits := addr.As4()
 return &net.IPNet{IP: net.IPv4(bits[0],bits[1],bits[2],bits[3]),Mask:net.CIDRMask(mask,32)}
}
func TestH2206ServerNATExactInterfaceIPv4Selection(t *testing.T) {
 cases:=[]struct {
  name string
  addresses []net.Addr
  want string
  errContains string
 }{
  {"private-v4-behind-nat",[]net.Addr{addrForNATTest("192.168.50.15",24)},"192.168.50.15",""},
  {"cloud-vpc-private",[]net.Addr{addrForNATTest("172.31.18.8",20)},"172.31.18.8",""},
  {"interface-v4-with-ipv6",[]net.Addr{addrForNATTest("10.8.1.4",24),&net.IPNet{IP:net.ParseIP("fe80::9"),Mask:net.CIDRMask(64,128)}},"10.8.1.4",""},
  {"interface-loopback",[]net.Addr{addrForNATTest("127.0.0.1",8)},"","no usable"},
  {"link-local-only",[]net.Addr{addrForNATTest("169.254.2.8",16)},"","no usable"},
  {"no-address",nil,"","no usable"},
  {"two-distinct-v4-must-be-explicit",[]net.Addr{addrForNATTest("10.0.0.5",24),addrForNATTest("10.0.0.6",24)},"","multiple IPv4"},
  {"duplicate-v4-no-ambiguity",[]net.Addr{addrForNATTest("10.0.0.5",24),addrForNATTest("10.0.0.5",24)},"10.0.0.5",""},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  got,err:=chooseUnderlayIPv4(tc.addresses)
  if tc.errContains!=""{
   if err==nil||!strings.Contains(err.Error(),tc.errContains){
    t.Fatalf("wanted reject %q, got addr=%v err=%v",tc.errContains,got,err)
   }
   return
  }
  if err!=nil||got.String()!=tc.want{
   t.Fatalf("wanted %s got %v error %v",tc.want,got,err)
  }
 })}
}

func TestH2206ServerNATCLIUnspecifiedIsDeferredOnlyForServer(t *testing.T){
 key:=strings.Repeat("ab",32)
 base:=[]string{"--raw-interface","eth0","--server-name","wbd.test",
  "--route-key-hex",key,"--username","alice","--password","test-secret",
  "--lease-pool","10.66.0.0/24"}
 for _,raw:=range []string{"","0.0.0.0","192.168.50.15"}{
  args:=append([]string(nil),base...)
  if raw!=""{args=append(args,"--local-ip",raw)}
  cfg,err:=parse("server",args)
  if err!=nil{t.Fatalf("server raw=%q rejected: %v",raw,err)}
  if raw==""||raw=="0.0.0.0"{
   if !cfg.localIP.IsUnspecified(){t.Fatalf("server raw=%q must defer exact interface IP, got %v",raw,cfg.localIP)}
  }else if cfg.localIP.String()!=raw{t.Fatalf("server explicit private changed to %v",cfg.localIP)}
 }
 clientArgs:=[]string{"--raw-interface","eth0","--local-ip","0.0.0.0","--server-name","wbd.test", "--route-key-hex",key,"--username","alice","--password","test-secret","--local-port","45000","--peer-ip","192.168.50.1","--peer-port","443"}
 cfg,err:=parse("client",clientArgs)
 if err==nil||!strings.Contains(err.Error(),"server-only") && !strings.Contains(err.Error(),"client local-ip"){
  t.Fatalf("client wildcard must reject; cfg=%v err=%v",cfg.localIP,err)
 }
}
