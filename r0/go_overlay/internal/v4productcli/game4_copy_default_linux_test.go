//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import "testing"

// Parse the real original-Go public flags: no copied parity, transport,
// FEC, or outer-repair policy is mocked here.
func TestGame4PublicDefaultWideStaggerAndExplicitFallbacks(t *testing.T) {
    base:=[]string{
        "--raw-interface","lo",
        "--local-ip","127.0.0.2",
        "--peer-ip","127.0.0.1",
        "--local-port","41031",
        "--peer-port","443",
        "--tun-name","wbntun0",
        "--tun-ipv4","10.20.0.2/24",
        "--server-name","wbd-v4.example.test",
        "--route-key-hex","0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "--username","test",
        "--password","test",
        "--tunnel-id","0102030405060708090a0b0c0d0e0f10",
    }
    cases:=[]struct{
        label string
        flags []string
        stagger bool
        wide bool
    }{
        {"game4-default",[]string{"--mode","game4"},true,true},
        {"game4-default-fixed6",[]string{"--mode","game4","--game-fec","fixed6"},true,true},
        {"game4-explicit-wide",[]string{"--mode","game4","--game4-copy-schedule","stagger-4-50-140"},true,true},
        {"game4-legacy-fallback",[]string{"--mode","game4","--game4-copy-schedule","stagger-4-20-60"},true,false},
        {"game4-immediate-rollback",[]string{"--mode","game4","--game4-copy-schedule","immediate"},false,false},
        {"game2-unaffected",[]string{"--mode","game2"},false,false},
        {"normal-unaffected",[]string{"--mode","normal"},false,false},
    }
    for _,test:=range cases {
        t.Run(test.label,func(t *testing.T){
            args:=append(append([]string{},base...),test.flags...)
            cfg,err:=parse("client",args)
            if err!=nil{t.Fatalf("real public CLI parse: %v",err)}
            if cfg.game4CopyStagger!=test.stagger||cfg.game4CopyWideStagger!=test.wide{
                t.Fatalf("schedule flags stagger=%v wide=%v, want stagger=%v wide=%v",
                    cfg.game4CopyStagger,cfg.game4CopyWideStagger,test.stagger,test.wide)
            }
        })
    }
}
