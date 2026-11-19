//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import ("strings";"testing")

func TestH2214ClientTLSVerifySwitch(t *testing.T) {
 base:=[]string{"--raw-interface","eth0","--local-ip","192.0.2.10",
 "--peer-ip","192.0.2.11","--local-port","50001","--peer-port","443",
 "--tun-name","wbd4","--tun-ipv4","10.188.0.2/24","--server-name","tls.example",
 "--username","alice","--password","test-secret","--route-key-hex",strings.Repeat("ab",32),
 "--tunnel-id","000102030405060708090a0b0c0d0e0f"}
 for _,tc:=range []struct{name string;args []string;want bool}{
 {"default-off",nil,false},{"explicit-off",[]string{"--tls-verify-server=false"},false},
 {"explicit-on",[]string{"--tls-verify-server=true"},true},
 }{t.Run(tc.name,func(t *testing.T){
  cfg,err:=parse("client",append(append([]string{},base...),tc.args...))
  if err!=nil {t.Fatal(err)}
  if cfg.tlsVerifyServer!=tc.want {t.Fatalf("verify=%v want=%v",cfg.tlsVerifyServer,tc.want)}
 })}
}
func TestH2214ServerRejectsClientTLSVerifyFlag(t *testing.T) {
 base:=[]string{"--raw-interface","eth0","--server-name","tls.example","--route-key-hex",strings.Repeat("ab",32),
 "--username","alice","--password","test-secret","--lease-pool","10.66.1.0/24",
 "--tun-ipv4","10.66.0.1/16","--tls-cert","server.crt","--tls-key","server.key"}
 if _,err:=parse("server",append(base,"--tls-verify-server=true"));err==nil{t.Fatal("server accepted client verification flag")}
}
