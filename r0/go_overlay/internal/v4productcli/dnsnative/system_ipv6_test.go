package dnsnative

import (
 "bytes"
 "context"
 "encoding/binary"
 "fmt"
 "io"
 "net"
 "net/netip"
 "testing"
 "time"
)
func TestB69IPv6DestinationRealUDPTCPSharedIPv4Upstream(t *testing.T){
 direct:=serveDNS(t,[4]byte{1,2,3,4});tunnel:=serveDNS(t,[4]byte{5,6,7,8})
 dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  if path==Physical&&endpoint==direct.addr{return (&net.Dialer{}).DialContext(ctx,network,direct.addr)}
  if path==Tunnel&&endpoint==TunnelDNS{return (&net.Dialer{}).DialContext(ctx,network,tunnel.addr)}
  return nil,ErrUnbound
 }
 s,e:=StartAppTCPDNS(dial,func(name string)bool{return name=="cn.example"},true,false,direct.addr)
 if e!=nil{t.Fatal(e)};defer s.Close()
 port,e:=s.EnableIPv6();if e!=nil{t.Fatal(e)}
 if again,e:=s.IPv6Port();e!=nil||again!=port{t.Fatal("App and system IPv6 DNS must share listener",again,e)}
 addr:=fmt.Sprintf("[::1]:%d",port)
 if s.ipv6TCP.Addr().String()!=addr{t.Fatal("not exact IPv6 local listener")}
 c,e:=net.Dial("udp6",addr);if e!=nil{t.Fatal(e)};defer c.Close()
 c.SetDeadline(time.Now().Add(3*time.Second))
 q:=makeQuery("cn.example",0x6901)
 if _,e=c.Write(q);e!=nil{t.Fatal(e)}
 var reply [MaxReply]byte
 n,e:=c.Read(reply[:]);if e!=nil{t.Fatal(e)}
 if n<4||!bytes.Equal(reply[:2],q[:2])||!bytes.Equal(reply[n-4:n],[]byte{1,2,3,4}){t.Fatal("wrong physical answer")}
 tcp,e:=net.Dial("tcp6",addr);if e!=nil{t.Fatal(e)};defer tcp.Close()
 tcp.SetDeadline(time.Now().Add(3*time.Second))
 q=makeQuery("global.example",0x6902)
 var length [2]byte;binary.BigEndian.PutUint16(length[:],uint16(len(q)))
 if _,e=tcp.Write(append(length[:],q...));e!=nil{t.Fatal(e)}
 if _,e=io.ReadFull(tcp,length[:]);e!=nil{t.Fatal(e)}
 n=int(binary.BigEndian.Uint16(length[:]));if n<4||n>len(reply){t.Fatal("bad frame")}
 if _,e=io.ReadFull(tcp,reply[:n]);e!=nil{t.Fatal(e)}
 if !bytes.Equal(reply[:2],q[:2])||!bytes.Equal(reply[n-4:n],[]byte{5,6,7,8}){t.Fatal("wrong tunnel answer")}
 if e=s.Close();e!=nil{t.Fatal(e)}
 if _,e=tcp.Read(reply[:1]);e==nil{t.Fatal("IPv6 DNS stream survived Stop")}
}

func TestB74IPv6DownstreamWithConfiguredTunnelUpstream(t *testing.T){
 tunnel:=serveDNS(t,[4]byte{9,8,7,6})
 const configured="9.9.9.9:53"
 dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  if path!=Tunnel||endpoint!=configured{return nil,ErrUnbound}
  return (&net.Dialer{}).DialContext(ctx,network,tunnel.addr)
 }
 s,e:=StartAppTCPDNS(dial,nil,false,false,ChinaDNS,configured)
 if e!=nil{t.Fatal(e)};defer s.Close()
 port,e:=s.EnableDownstream6(netip.IPv6Loopback(),netip.MustParsePrefix("::1/128"))
 if e!=nil{t.Fatal(e)}
 addr:=fmt.Sprintf("[::1]:%d",port)
 udp,e:=net.Dial("udp6",addr);if e!=nil{t.Fatal(e)};defer udp.Close()
 udp.SetDeadline(time.Now().Add(3*time.Second))
 q:=makeQuery("global.example",0x7401)
 if _,e=udp.Write(q);e!=nil{t.Fatal(e)}
 var reply [MaxReply]byte
 n,e:=udp.Read(reply[:]);if e!=nil||n<4||!bytes.Equal(reply[n-4:n],[]byte{9,8,7,6}){t.Fatal("wrong configured UDP answer",e)}
 tcp,e:=net.Dial("tcp6",addr);if e!=nil{t.Fatal(e)};defer tcp.Close()
 tcp.SetDeadline(time.Now().Add(3*time.Second))
 q=makeQuery("global.example",0x7402)
 var size [2]byte;binary.BigEndian.PutUint16(size[:],uint16(len(q)))
 if _,e=tcp.Write(append(size[:],q...));e!=nil{t.Fatal(e)}
 if _,e=io.ReadFull(tcp,size[:]);e!=nil{t.Fatal(e)}
 n=int(binary.BigEndian.Uint16(size[:]));if n<4||n>len(reply){t.Fatal("bad TCP frame")}
 if _,e=io.ReadFull(tcp,reply[:n]);e!=nil||!bytes.Equal(reply[n-4:n],[]byte{9,8,7,6}){t.Fatal("wrong configured TCP answer",e)}
 if e=s.Close();e!=nil{t.Fatal(e)}
 if _,e=tcp.Read(reply[:1]);e==nil{t.Fatal("IPv6 downstream TCP survived Stop")}
}
