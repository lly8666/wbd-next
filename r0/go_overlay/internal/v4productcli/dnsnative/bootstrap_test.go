package dnsnative

import (
    "context"
    "encoding/binary"
    "errors"
    "net"
    "net/netip"
    "testing"
)

func bootstrapTestDial(server *localDNS)DialFunc{
    return func(ctx context.Context,path Path,protocol,address string)(net.Conn,error){
        if path!=Physical||address!=ChinaDNS{
            return nil,errors.New("server bootstrap escaped exact physical 223.5.5.5:53")
        }
        return (&net.Dialer{}).DialContext(ctx,protocol,server.addr)
    }
}
func TestB2c3BootstrapPhysicalRealUDP53AndSameEndpointTCP(t *testing.T){
    physical:=serveDNS(t,[4]byte{203,0,113,91})
    dial:=bootstrapTestDial(physical)
    got,err:=ResolveBootstrapIPv4(context.Background(),"wbd.example.net",dial)
    if err!=nil||got!=netip.AddrFrom4(physical.ip){
        t.Fatal("real original Go physical bootstrap A not returned",got,err)
    }
    physical.truncate=true
    got,err=ResolveBootstrapIPv4(context.Background(),"wbd.example.org",dial)
    if err!=nil||got!=netip.AddrFrom4(physical.ip){
        t.Fatal("TC not retried as physical same-endpoint TCP",got,err)
    }
    if physical.udpCalls.Load()!=2||physical.tcpCalls.Load()!=1{
        t.Fatal("unexpected original DNS physical UDP/TCP socket counts")
    }
}
func TestB2c3BootstrapCompressedCNAMEAAndAnswerIdentity(t *testing.T){
    query:=makeQuery("edge.example.net",0x1234)
    answer:=append([]byte(nil),query...)
    binary.BigEndian.PutUint16(answer[2:4],0x8180)
    binary.BigEndian.PutUint16(answer[6:8],2)
    alias:=[]byte{4,'r','e','a','l',7,'e','x','a','m','p','l','e',3,'n','e','t',0}
    cname:=[]byte{0xc0,0x0c,0,5,0,1,0,0,0,60,0,byte(len(alias))}
    answer=append(answer,cname...)
    answer=append(answer,alias...)
    answer=append(answer,alias...)
    answer=append(answer,0,1,0,1,0,0,0,60,0,4,198,51,100,11)
    got,err:=bootstrapReplyIPv4("edge.example.net",answer)
    if err!=nil||got.String()!="198.51.100.11"{
        t.Fatal("valid CNAME->A rejected",got,err)
    }
    answer[3]=0x83 // NXDOMAIN must not yield a peer IP
    if _,err=bootstrapReplyIPv4("edge.example.net",answer);err==nil{
        t.Fatal("NXDOMAIN incorrectly granted a server underlay IPv4")
    }
}
func TestB2c3BootstrapRejectsMalformedNameOrUnavailablePhysical(t *testing.T){
    for _,host:=range []string{"","192.168.1.1","256.1.1.1",
        "bad..example","-bad.example","bad.example/evil","bad.example "}{
        if ValidBootstrapHostname(host){t.Fatalf("invalid bootstrap name accepted: %q",host)}
    }
    if !ValidBootstrapHostname("edge.example.net"){t.Fatal("valid hostname refused")}
    physical:=serveDNS(t,[4]byte{203,0,113,2})
    failDial:=func(context.Context,Path,string,string)(net.Conn,error){
        return nil,errors.New("physical network unavailable")
    }
    if _,err:=ResolveBootstrapIPv4(context.Background(),"edge.example.net",failDial);err==nil{
        t.Fatal("physical DNS failure silently fell back")
    }
    if physical.udpCalls.Load()!=0{
        t.Fatal("physical bootstrap used another DNS socket")
    }
    if _,err:=ResolveBootstrapIPv4(context.Background(),"edge.example.net",nil);!errors.Is(err,ErrUnbound){
        t.Fatal("missing physical DialFunc did not fail closed")
    }
}

func TestB35ConfiguredPhysicalBootstrapUsesRealUDPAndSameUpstreamTCP(t *testing.T){
    physical:=serveDNS(t,[4]byte{203,0,113,92})
    upstream:=netip.MustParseAddr("192.168.1.1")
    target:=upstream.String()+":53"
    dial:=func(ctx context.Context,path Path,protocol,address string)(net.Conn,error){
        if path!=Physical||address!=target||(protocol!="udp"&&protocol!="tcp"){
            return nil,errors.New("B35 bootstrap used an unselected DNS endpoint")
        }
        return (&net.Dialer{}).DialContext(ctx,protocol,physical.addr)
    }
    got,err:=ResolveBootstrapIPv4WithUpstream(context.Background(),
        "lan.example.test",dial,upstream)
    if err!=nil||got!=netip.AddrFrom4(physical.ip){
        t.Fatal("custom selected physical DNS UDP bootstrap failed",got,err)
    }
    physical.truncate=true
    got,err=ResolveBootstrapIPv4WithUpstream(context.Background(),
        "wbd.example.test",dial,upstream)
    if err!=nil||got!=netip.AddrFrom4(physical.ip){
        t.Fatal("custom selected DNS TC-to-TCP bootstrap failed",got,err)
    }
    if physical.udpCalls.Load()!=2||physical.tcpCalls.Load()!=1{
        t.Fatal("custom selected DNS must reuse the same upstream for UDP/TCP")
    }
    for _,bad:=range []string{"0.0.0.0","127.0.0.1","::1"}{
        if _,err:=ResolveBootstrapIPv4WithUpstream(context.Background(),
            "lan.example.test",dial,netip.MustParseAddr(bad));err==nil{
            t.Fatal("invalid bootstrap DNS destination accepted",bad)
        }
    }
}
