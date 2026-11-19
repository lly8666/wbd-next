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

func TestH2212DecoyQuotaOnlyWhenEnabled(t *testing.T){
  if originalV4DecoySlots(config{})!=nil {t.Fatal("disabled decoy allocated quota")}
  slots:=originalV4DecoySlots(config{decoyTarget:"127.0.0.1:8443"})
  if slots==nil||cap(slots)!=8||len(slots)!=0{t.Fatal("decoy should have exactly eight independent transfer slots")}
}

func TestH2213Rust32Cold64Ordinary8SeparateResources(t *testing.T){
    if originalV4NativeLaneSlots!=32 {t.Fatal("Rust authenticated native lane cap drifted")}
    if originalV4ColdAssociationSlots!=64 {t.Fatal("FakeTCP cold table must leave onboarding/Decoy headroom")}
    if originalV4MaxDecoySplices!=8{t.Fatal("ordinary TLS transfer quota drifted")}
    if originalV4ColdAssociationSlots<
        originalV4NativeLaneSlots+originalV4MaxDecoySplices {
        t.Fatal("new WBD lanes could exhaust all ordinary TLS cold associations")
    }
    decoy:=originalV4ServerDecoy(config{
        decoyTarget:"127.0.0.1:8443",serverName:"target.test"})
    if decoy==nil||decoy.SessionTimeout.Seconds()!=45||decoy.MaxBytes!=64<<20 {
        t.Fatal("ordinary TLS must be time and byte bounded")
    }
    if originalV4ServerDecoy(config{})!=nil{t.Fatal("disabled decoy allocated resources")}
}
