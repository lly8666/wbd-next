//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli
import("os";"path/filepath";"strings";"testing"
"github.com/lly8666/wobuzhidao/internal/realityfront")
func TestPLAN028AccountBoundManualLeaseConfig(t *testing.T){
 d:=t.TempDir()
 put:=func(n,s string)string{p:=filepath.Join(d,n);if e:=os.WriteFile(p,[]byte(s),0600);e!=nil{t.Fatal(e)};return p}
 users:=put("users.json",`{"alice":"alice-only","bob":"bob-only"}`)
 mapping:=put("mapping.json",`{"alice":"10.66.0.2/32","bob":"10.66.0.3/32"}`)
 base:=[]string{"--raw-interface","underlay0","--local-ip","10.25.0.1","--local-port","443","--tun-name","tuns0","--tun-ipv4","10.66.0.1/24","--server-name","wbd-v4.example.test","--route-key-hex",strings.Repeat("12",32),"--tls-cert","cert.pem","--tls-key","key.pem","--users-file",users,"--manual-client-leases-file",mapping}
 got,e:=parse("server",base);if e!=nil{t.Fatal(e)}
 if got.leasePool.IsValid()||got.manualClientLease4.IsValid()||len(got.manualClientLeases4)!=2||got.manualClientLeases4["alice"]!="10.66.0.2/32"||got.manualClientLeases4["bob"]!="10.66.0.3/32"{t.Fatalf("wrong protected account map: %+v",got)}
 cases:=[]struct{name,content string}{
  {"duplicate",`{"alice":"10.66.0.2/32","bob":"10.66.0.2/32"}`},
  {"cross-account",`{"alice":"10.66.0.2/32","mallory":"10.66.0.3/32"}`},
  {"server-own-IP",`{"alice":"10.66.0.1/32","bob":"10.66.0.3/32"}`},
  {"outside-subnet",`{"alice":"10.99.0.2/32","bob":"10.66.0.3/32"}`},
  {"incomplete",`{"alice":"10.66.0.2/32"}`},
  {"non32",`{"alice":"10.66.0.2/24","bob":"10.66.0.3/32"}`},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){file:=put(tc.name+".json",tc.content);a:=append([]string(nil),base...);a[len(a)-1]=file;if _,e:=parse("server",a);e==nil{t.Fatal("unsafe account map accepted")}})}
 if _,e:=parse("server",append(append([]string(nil),base...),"--lease-pool","10.66.0.128/25"));e==nil{t.Fatal("pool+manual account map accepted")}
 if _,e:=parse("client",base);e==nil{t.Fatal("client passed server-owned map")}
}

func TestPLAN028AccountManualProtectedTunnelIdentity(t *testing.T){
 c:=config{manualClientLeases4:map[string]string{"alice":"10.66.0.2/32","bob":"10.66.0.3/32"}}
 fixed:=make([]byte,16);fixed[0]=1
 for _,username:=range []string{"alice","bob"}{
  req:=realityfront.AdmissionRequest{Username:username,TunnelID:fixed}
  if err:=originalV4ManualAccountTunnelAfterAuth(c,req);err!=nil{t.Fatalf("protected user %s: %v",username,err)}
 }
 for _,req:=range []realityfront.AdmissionRequest{
  {Username:"mallory",TunnelID:fixed},
  {Username:"alice",TunnelID:make([]byte,16)},
  {Username:"alice",TunnelID:fixed,AutoLease:true},
  {Username:"alice",TunnelID:[]byte{1}},
 }{
  if err:=originalV4ManualAccountTunnelAfterAuth(c,req);err==nil{t.Fatalf("unverified manual identity accepted %+v",req)}
 }
 c.manualClientLeases4=nil;c.tunnel[0]=2
 if err:=originalV4ManualAccountTunnelAfterAuth(c,realityfront.AdmissionRequest{Username:"alice",TunnelID:fixed});err==nil{t.Fatal("legacy single incorrect tunnel accepted")}
 same:=make([]byte,16);same[0]=2
 if err:=originalV4ManualAccountTunnelAfterAuth(c,realityfront.AdmissionRequest{Username:"alice",TunnelID:same});err!=nil{t.Fatal("legacy single exact tunnel rejected",err)}
}
