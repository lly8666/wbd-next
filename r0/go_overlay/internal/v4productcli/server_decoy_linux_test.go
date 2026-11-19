//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "strings"
    "testing"
)

func TestH2209ServerDecoyColdValidation(t *testing.T) {
 key:=strings.Repeat("ab",32)
 base:=[]string{"--raw-interface","eth0","--server-name","target.test",
     "--route-key-hex",key,"--username","alice","--password","test-secret",
     "--lease-pool","10.66.1.0/24","--tun-ipv4","10.66.0.1/16",
     "--tls-cert","server.crt","--tls-key","server.key",
 }
 valid:=append(append([]string{},base...), "--decoy","decoy.example:443")
 cfg,err:=parse("server",valid)
 if err!=nil||cfg.decoyTarget!="decoy.example:443"{
    t.Fatalf("fixed server decoy rejected: %v",err)
 }
 if _,err=parse("server",append(append([]string{},base...),"--decoy","self"));err==nil{
    t.Fatal("target without host:port accepted")
 }
 if _,err=parse("server",append(append([]string{},base...),"--decoy",":443"));err==nil{
    t.Fatal("empty decoy host accepted")
 }
 if _,err=parse("server",append(append([]string{},base...),"--decoy","decoy.example:0"));err==nil{
    t.Fatal("zero decoy port accepted")
 }
 if _,err=parse("server",append(append([]string{},base...),"--mode","game4","--decoy","decoy.example:443"));err==nil{
    t.Fatal("legacy fixed Game admission incorrectly accepted ordinary TLS decoy")
 }
 self:=append(append([]string{},base...),"--local-ip","192.168.1.10",
     "--decoy","192.168.1.10:443")
 if _,err=parse("server",self);err==nil{t.Fatal("same raw listener decoy loop accepted")}
 }
