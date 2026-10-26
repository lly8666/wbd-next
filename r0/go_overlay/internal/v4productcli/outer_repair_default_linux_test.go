//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import "testing"

func TestPublicOuterDataRepairDefaultsOnAcrossAllModes(t *testing.T) {
    base:=[]string{
        "--raw-interface","lo","--local-ip","127.0.0.2",
        "--peer-ip","127.0.0.1","--local-port","41031","--peer-port","443",
        "--tun-name","wbntun0","--tun-ipv4","10.20.0.2/24",
        "--server-name","wbd-v4.example.test",
        "--route-key-hex","0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "--username","test","--password","test",
        "--tunnel-id","0102030405060708090a0b0c0d0e0f10",
    }
    for _,test:=range []struct{ mode, gameFec string }{
        {"normal","off"},{"fec-fixed","off"},{"fec-auto","off"},
        {"game2","off"},{"game2","fixed6"},{"game4","off"},{"game4","fixed6"},
    } {
        t.Run(test.mode+"_"+test.gameFec,func(t *testing.T){
            args:=append(append([]string{},base...),"--mode",test.mode)
            if test.gameFec!="off"{args=append(args,"--game-fec",test.gameFec)}
            cfg,err:=parse("client",args)
            if err!=nil{t.Fatalf("parse default: %v",err)}
            if cfg.disableOuterRepair{t.Fatal("outer DATA repair must default ON")}
            disabled,err:=parse("client",append(append([]string{},args...),"--outer-repair","off"))
            if err!=nil{t.Fatalf("parse manual OFF rollback: %v",err)}
            if !disabled.disableOuterRepair{t.Fatal("explicit outer-repair off must stay off")}
        })
    }
}
