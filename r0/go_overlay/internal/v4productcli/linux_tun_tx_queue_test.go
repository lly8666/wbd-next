//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import ("testing";"fmt")

func TestOwnedTunTxQueueReadbackExactAndRollback(t *testing.T){
    good:=[]byte(`[{"ifname":"wbdwl4","ifindex":3,"mtu":1400,"txqlen":2048,"link_type":"none","flags":["UP","POINTOPOINT","NOARP"]}]`)
    if err:=validateOwnedTunTxQueueReadback(good,"wbdwl4",2048);err!=nil{t.Fatal(err)}
    for _,entry:=range []struct{name string;n int;source []byte}{
        {"foreign",2048,good},{"wbdwl4",500,good},{"wbdwl4",2048,[]byte("[]")},
        {"wbdwl4",2048,[]byte("{")},
        {"wbdwl4",2048,[]byte(`[{"ifname":"wbdwl4","ifindex":3,"mtu":1400,"txqlen":2048,"link_type":"none","flags":["UP"]}]`)},
    }{if err:=validateOwnedTunTxQueueReadback(entry.source,entry.name,entry.n);err==nil{t.Fatalf("accepted non-owned queue %v",entry)}}
    base:=[]string{"--raw-interface","lo","--local-ip","127.0.0.2",
        "--peer-ip","127.0.0.1","--local-port","41031","--peer-port","443",
        "--tun-name","wbdwl4","--tun-ipv4","10.66.0.2/24",
        "--server-name","wbd-v4.example.test",
        "--route-key-hex","0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "--username","test","--password","test",
        "--tunnel-id","0102030405060708090a0b0c0d0e0f10"}
    for _,mode:=range []string{"normal","fec-fixed","fec-auto","game2","game4"}{
        args:=append(append([]string{},base...),"--mode",mode)
        c,err:=parse("client",args)
        if err!=nil||c.tunTxQLenPackets!=2048{t.Fatalf("%s default: %v %+v",mode,err,c)}
        rb,err:=parse("client",append(append([]string{},args...),"--tun-txqlen-packets","500"))
        if err!=nil||rb.tunTxQLenPackets!=500{t.Fatalf("%s rollback: %v",mode,err)}
        for _,bad:=range []int{0,1024,4096,8192,-1}{
            _,err:=parse("client",append(append([]string{},args...),"--tun-txqlen-packets",fmt.Sprint(bad)))
            if err==nil{t.Fatalf("%s accepted invalid %d",mode,bad)}
        }
    }
}
