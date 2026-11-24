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
func TestB68DownstreamDNSRealSharedUDPTCPAndStop(t *testing.T){
 direct:=serveDNS(t,[4]byte{1,2,3,4});tunnel:=serveDNS(t,[4]byte{5,6,7,8})
 dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  if path==Physical&&endpoint==direct.addr{return (&net.Dialer{}).DialContext(ctx,network,direct.addr)}
  if path==Tunnel&&endpoint==TunnelDNS{return (&net.Dialer{}).DialContext(ctx,network,tunnel.addr)}
  return nil,ErrUnbound
 }
 s,e:=StartAppTCPDNS(dial,func(name string)bool{return name=="cn.example"},true,false,direct.addr)
 if e!=nil{t.Fatal(e)};defer s.Close()
 gateway:=netip.MustParseAddr("127.0.0.2");scope:=netip.MustParsePrefix("127.0.0.0/24")
 port,e:=s.EnableDownstream(gateway,scope);if e!=nil{t.Fatal(e)}
 if s.downstreamTCP.Addr().String()!=fmt.Sprintf("127.0.0.2:%d",port){t.Fatal("not exact downstream bind")}
 if _,e=s.EnableDownstream(gateway,scope);e==nil{t.Fatal("duplicate owner")}
 if allowedDNSPeer(&net.UDPAddr{IP:net.ParseIP("192.168.43.2")},scope){t.Fatal("foreign peer accepted")}
 addr:=fmt.Sprintf("127.0.0.2:%d",port)
 c,e:=net.Dial("udp4",addr);if e!=nil{t.Fatal(e)};defer c.Close()
 c.SetDeadline(time.Now().Add(3*time.Second))
 q:=makeQuery("cn.example",0x6801)
 if _,e=c.Write(q);e!=nil{t.Fatal(e)}
 var reply [MaxReply]byte
 n,e:=c.Read(reply[:]);if e!=nil{t.Fatal(e)}
 if n<4||!bytes.Equal(reply[n-4:n],[]byte{1,2,3,4}){t.Fatal("wrong physical answer")}
 tcp,e:=net.Dial("tcp4",addr);if e!=nil{t.Fatal(e)};defer tcp.Close()
 tcp.SetDeadline(time.Now().Add(3*time.Second))
 q=makeQuery("global.example",0x6802)
 var length [2]byte;binary.BigEndian.PutUint16(length[:],uint16(len(q)))
 if _,e=tcp.Write(append(length[:],q...));e!=nil{t.Fatal(e)}
 if _,e=io.ReadFull(tcp,length[:]);e!=nil{t.Fatal(e)}
 n=int(binary.BigEndian.Uint16(length[:]));if n<4||n>len(reply){t.Fatal("bad frame")}
 if _,e=io.ReadFull(tcp,reply[:n]);e!=nil{t.Fatal(e)}
 if !bytes.Equal(reply[n-4:n],[]byte{5,6,7,8}){t.Fatal("wrong tunnel answer")}
 if e=s.Close();e!=nil{t.Fatal(e)}
 if _,e=tcp.Read(reply[:1]);e==nil{t.Fatal("downstream stream survived Stop")}
}
