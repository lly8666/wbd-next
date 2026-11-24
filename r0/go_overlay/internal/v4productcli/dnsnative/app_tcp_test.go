package dnsnative

import (
 "bytes"
 "context"
 "encoding/binary"
 "fmt"
 "io"
 "net"
 "testing"
 "time"
)

func TestB64ActualAppTCPDNSPhysicalTunnelAndCN(t *testing.T){
 direct:=serveDNS(t,[4]byte{1,2,3,4})
 tunnel:=serveDNS(t,[4]byte{5,6,7,8})
 // Real two independent TCP upstream listeners; the exact production
 // App listener/framing/selection/validation is exercised on loopback.
 dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  if network!="tcp"{return nil,fmt.Errorf("App TCP must use TCP upstream")}
  switch path{
  case Physical: if endpoint!=direct.addr{return nil,ErrUnbound}
  case Tunnel: if endpoint!=TunnelDNS{return nil,ErrUnbound};endpoint=tunnel.addr
  default:return nil,ErrUnbound
  }
  return (&net.Dialer{}).DialContext(ctx,network,endpoint)
 }
 for _,mode:=range []struct{name string;split,physical bool;first,last [4]byte}{
  {"tunnel",false,false,[4]byte{5,6,7,8},[4]byte{5,6,7,8}},
  {"physical",false,true,[4]byte{1,2,3,4},[4]byte{1,2,3,4}},
  {"cn",true,false,[4]byte{1,2,3,4},[4]byte{5,6,7,8}},
 }{
  t.Run(mode.name,func(t *testing.T){
   owner,e:=StartAppTCPDNS(dial,func(name string)bool{return name=="cn.example"},
    mode.split,mode.physical,direct.addr)
   if e!=nil{t.Fatal(e)}
   defer owner.Close()
   c,e:=net.Dial("tcp4",fmt.Sprintf("127.0.0.1:%d",owner.Port()))
   if e!=nil{t.Fatal(e)}
   defer c.Close()
   c.SetDeadline(time.Now().Add(3*time.Second))
   for i,name:=range []string{"cn.example","global.example"}{
    q:=makeQuery(name,uint16(0x1200+i))
    var size [2]byte
    binary.BigEndian.PutUint16(size[:],uint16(len(q)))
    if _,e=c.Write(size[:1]);e!=nil{t.Fatal(e)}
    if _,e=c.Write(append(size[1:],q...));e!=nil{t.Fatal(e)}
    if _,e=io.ReadFull(c,size[:]);e!=nil{t.Fatal(e)}
    answer:=make([]byte,binary.BigEndian.Uint16(size[:]))
    if _,e=io.ReadFull(c,answer);e!=nil{t.Fatal(e)}
    expected:=mode.first;if i==1{expected=mode.last}
    if !bytes.Equal(answer[:2],q[:2])||
       !bytes.Equal(answer[len(answer)-4:],expected[:]){t.Fatalf("wrong DNS path/ID: %x",answer)}
   }
   if e=owner.Close();e!=nil{t.Fatal(e)}
   if _,e=c.Read(make([]byte,1));e==nil{t.Fatal("Stop left application stream live")}
  })
 }
 if direct.udpCalls.Load()!=0||tunnel.udpCalls.Load()!=0||
    direct.tcpCalls.Load()!=3||tunnel.tcpCalls.Load()!=3{
  t.Fatal("TCP DNS used wrong number or transport of real upstream queries")
 }
}
