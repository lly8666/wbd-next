//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func TestArm64V4PrivateCredentialsNoArgv(t *testing.T) {
    d:=t.TempDir()
    pass:=filepath.Join(d,"password")
    key:=filepath.Join(d,"route")
    if err:=os.WriteFile(pass,[]byte("pinned-secret\n"),0600);err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(key,[]byte(strings.Repeat("ab",32)+"\n"),0600);err!=nil{t.Fatal(err)}
    args:=[]string{
      "--raw-interface","lo","--local-ip","192.0.2.10",
      "--peer-ip","192.0.2.11","--local-port","50001","--peer-port","443",
      "--tun-name","wbd4","--tun-ipv4","10.188.0.2/24",
      "--server-name","test.example","--username","test",
      "--password-file",pass,"--route-key-hex-file",key,
      "--tunnel-id","000102030405060708090a0b0c0d0e0f",
    }
    got,err:=parse("client",args)
    if err!=nil{t.Fatal(err)}
    if got.password!="pinned-secret"||len(got.routeKey)!=32{
      t.Fatal("trusted fd-only config not applied")
    }
    if err:=os.Chmod(pass,0644);err!=nil{t.Fatal(err)}
    if _,err:=parse("client",args);err==nil{t.Fatal("world-readable password accepted")}
    if err:=os.Chmod(pass,0600);err!=nil{t.Fatal(err)}
    link:=filepath.Join(d,"symlink")
    if err:=os.Symlink(pass,link);err!=nil{t.Fatal(err)}
    shifted:=append([]string{},args...)
    for i,v:=range shifted{if v==pass {shifted[i]=link;break}}
    if _,err:=parse("client",shifted);err==nil{t.Fatal("symlink accepted")}
    if _,err:=parse("client",append(args,"--password","plaintext"));err==nil{
      t.Fatal("secret argv mixed with fd input")
    }
}
