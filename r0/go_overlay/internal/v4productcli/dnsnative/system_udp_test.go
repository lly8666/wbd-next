package dnsnative

import (
 "bytes"
 "context"
 "fmt"
 "net"
 "testing"
 "time"
)
func TestB66SystemDNSRealUDPTCPModeAndStop(t *testing.T){
 direct:=serveDNS(t,[4]byte{1,2,3,4})
 tunnel:=serveDNS(t,[4]byte{5,6,7,8})
 direct.truncate=true
 dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  switch path{
  case Physical:if endpoint!=direct.addr{return nil,ErrUnbound}
  case Tunnel:if endpoint!=TunnelDNS{return nil,ErrUnbound};endpoint=tunnel.addr
  default:return nil,ErrUnbound
  }
  return (&net.Dialer{}).DialContext(ctx,network,endpoint)
 }
 owner,e:=StartAppTCPDNS(dial,func(name string)bool{return name=="cn.example"},true,false,direct.addr)
 if e!=nil{t.Fatal(e)}
 defer owner.Close()
 if e=owner.EnableUDP();e!=nil{t.Fatal(e)}
 c,e:=net.Dial("udp4",fmt.Sprintf("127.0.0.1:%d",owner.Port()))
 if e!=nil{t.Fatal(e)}
 defer c.Close();c.SetDeadline(time.Now().Add(3*time.Second))
 for i,name:=range []string{"cn.example","global.example"}{
  q:=makeQuery(name,uint16(0x6600+i))
  if _,e=c.Write(q);e!=nil{t.Fatal(e)}
  var reply [MaxReply]byte
  n,e:=c.Read(reply[:]);if e!=nil{t.Fatal(e)}
  want:=[]byte{1,2,3,4};if i==1{want=[]byte{5,6,7,8}}
  if !bytes.Equal(reply[:2],q[:2])||!bytes.Equal(reply[n-4:n],want){t.Fatal("wrong real DNS answer")}
 }
 if direct.udpCalls.Load()!=1||direct.tcpCalls.Load()!=1||tunnel.udpCalls.Load()!=1||tunnel.tcpCalls.Load()!=0{
  t.Fatal("system relay did not use selected physical TCP fallback/tunnel UDP")
 }
 if e=owner.Close();e!=nil{t.Fatal(e)}
}
