//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
    "os"
    "path/filepath"
    "strings"
    "testing"

    "github.com/lly8666/wobuzhidao/internal/realityfront"
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

// Actual public CLI cold-path budget. Include asymmetric authenticated limits,
// a smaller interface, and a too-small path; never turn an oversize reject off.
func TestOriginalProductAutomaticTunnelMTU(t *testing.T){
    for _,tc:=range []struct{
        name string
        outer,device int
        mss,record uint16
        mode realityfront.FecV2Mode
        game bool
        wire uint16
        inner int
    }{
        {"normal",1500,1500,1360,0,realityfront.FecV2Off,false,1360,1329},
        {"fixed",1500,1500,1360,0,realityfront.FecV2Fixed,false,1360,1315},
        {"auto",1500,1500,1360,0,realityfront.FecV2Auto,false,1360,1315},
        {"game",1500,1500,1360,0,realityfront.FecV2Off,true,1360,1313},
        {"configured-small",1280,1500,1360,0,realityfront.FecV2Fixed,false,1240,1195},
        {"device-small",1500,1280,1360,0,realityfront.FecV2Auto,false,1240,1195},
        {"peer-mss",1500,1500,1200,0,realityfront.FecV2Fixed,false,1200,1155},
        {"peer-record",1500,1500,1360,1180,realityfront.FecV2Fixed,false,1180,1135},
        {"jumbo-still-peer-limited",9000,9000,1360,0,realityfront.FecV2Off,false,1360,1329},
    }{
        t.Run(tc.name,func(t *testing.T){
            wire,inner,err:=deriveMTUBudget(tc.outer,tc.device,tc.mss,tc.record,tc.mode,tc.game)
            if err!=nil||wire!=tc.wire||inner!=tc.inner {
                t.Fatalf("wire=%d inner=%d err=%v; want %d/%d",wire,inner,err,tc.wire,tc.inner)
            }
        })
    }
    if _,_,err:=deriveMTUBudget(1500,1500,536,0,realityfront.FecV2Fixed,false);err==nil{
        t.Fatal("unsupported small path must fail explicitly before TUN worker starts")
    }
}

// Real v3 cold path derives the maximum record offer from outer MTU and
// advertised SYN MSS. Legacy 1180/1280 are no longer product ceilings.
func TestV3PublicDynamicRecordWireBudget(t *testing.T){
    cases:=[]struct{
        outer,peer,record uint16
        mode realityfront.FecV2Mode
        wantWire,wantTun int
    }{
        {1500,1460,0,realityfront.FecV2Off,1460,1429},
        {1500,1460,0,realityfront.FecV2Fixed,1460,1415},
        {1500,1460,0,realityfront.FecV2Auto,1460,1415},
        {1400,1360,0,realityfront.FecV2Off,1360,1329},
        {1280,1240,0,realityfront.FecV2Fixed,1240,1195},
        {1500,1360,0,realityfront.FecV2Off,1360,1329},
        {1500,1460,1280,realityfront.FecV2Off,1280,1249},
    }
    for _,tt:=range cases{
        wire,tun,err:=deriveMTUBudget(int(tt.outer),int(tt.outer),tt.peer,tt.record,tt.mode,false)
        if err!=nil||int(wire)!=tt.wantWire||tun!=tt.wantTun{
            t.Fatalf("outer=%d peer=%d record=%d mode=%s wire=%d tun=%d err=%v want=%d/%d",
                tt.outer,tt.peer,tt.record,tt.mode,wire,tun,err,tt.wantWire,tt.wantTun)
        }
    }
}


func TestGame4Fixed6StaggerDefaultAndGame2Unchanged(t *testing.T){
    dir:=t.TempDir()
    pass:=filepath.Join(dir,"password")
    route:=filepath.Join(dir,"route")
    if e:=os.WriteFile(pass,[]byte("test-password\n"),0600);e!=nil{t.Fatal(e)}
    if e:=os.WriteFile(route,[]byte(strings.Repeat("ab",32)+"\n"),0600);e!=nil{t.Fatal(e)}
    base:=[]string{
      "--raw-interface","lo","--local-ip","192.0.2.10",
      "--peer-ip","192.0.2.11","--local-port","50001","--peer-port","443",
      "--tun-name","wbd4","--tun-ipv4","10.188.0.2/24",
      "--server-name","test.example","--username","test",
      "--password-file",pass,"--route-key-hex-file",route,
      "--tunnel-id","000102030405060708090a0b0c0d0e0f",
    }
    cases:=[]struct{name string;flags []string;enabled bool;valid bool}{
      {"game4_default_fixed6",[]string{"--mode","game4","--game-fec","fixed6"},true,true},
      {"game4_default_off",[]string{"--mode","game4","--game-fec","off"},true,true},
      {"game4_explicit_immediate",[]string{"--mode","game4","--game-fec","fixed6","--game4-copy-schedule","immediate"},false,true},
      {"game2_fixed6_unchanged",[]string{"--mode","game2","--game-fec","fixed6"},false,true},
      {"normal_unchanged",[]string{"--mode","normal"},false,true},
      {"game2_reject_stagger",[]string{"--mode","game2","--game4-copy-schedule","stagger-4-20-60"},false,false},
    }
    for _,tc:=range cases{
        t.Run(tc.name,func(t *testing.T){
            cfg,err:=parse("client",append(append([]string(nil),base...),tc.flags...))
            if (err==nil)!=tc.valid {t.Fatalf("valid=%v err=%v",tc.valid,err)}
            if err==nil&&cfg.game4CopyStagger!=tc.enabled {
                t.Fatalf("got stagger=%v expected=%v",cfg.game4CopyStagger,tc.enabled)
            }
        })
    }
}
