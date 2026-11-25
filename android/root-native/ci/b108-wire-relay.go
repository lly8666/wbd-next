//go:build ignore

// CI-only carrier: unchanged IPv4/TCP bytes between two disposable veth
// peers. No TLS keys, TCP state machine, FakeTCP, payload logging, or
// production link. ADB reverse is the test carrier, not a product protocol.
package main

import (
 "bytes"
 "encoding/binary"
 "fmt"
 "io"
 "net"
 "os"
 "os/signal"
 "sync/atomic"
 "syscall"
 "time"
)

const ethIP=0x0008 // htons(ETH_P_IP), x86_64 guest/runner
const control="127.0.0.1:18443"
func allowed(p []byte,src,dst net.IP,server bool)bool{
 if len(p)<40||p[0]>>4!=4||p[9]!=6||int(binary.BigEndian.Uint16(p[2:4]))!=len(p){return false}
 h:=int(p[0]&15)*4
 if h<20||len(p)<h+20||binary.BigEndian.Uint16(p[6:8])&0x3fff!=0{return false}
 if !src.Equal(net.IP(p[12:16]))||!dst.Equal(net.IP(p[16:20])){return false}
 at:=h+2;if server{at=h}
 return binary.BigEndian.Uint16(p[at:at+2])==443
}
// Observe only genuine SYN/SYNACK on each distinct TCP flow; no bytes
// are changed and no response is generated here. Each map belongs to
// one relay direction; ordinals are CI-local counts, not credentials.
func observeCold(p []byte,server bool,seen map[uint16]bool,role,direction string){
 h:=int(p[0]&15)*4
 flags:=p[h+13]
 if (!server&&flags&0x12!=0x02)||(server&&flags&0x12!=0x12){return}
 at:=h;if server{at=h+2}
 port:=binary.BigEndian.Uint16(p[at:at+2])
 if seen[port]{return};seen[port]=true
 kind:="SYN";if server{kind="SYNACK"}
 fmt.Printf("B110_WIRE_%s role=%s direction=%s distinct=%d\n",kind,role,direction,len(seen))
}
func run()error{
 if len(os.Args)!=6{return fmt.Errorf("usage: host|guest interface client-ip server-ip destination-mac")}
 host:=os.Args[1]=="host"
 if !host&&os.Args[1]!="guest"{return fmt.Errorf("role")}
 iface,e:=net.InterfaceByName(os.Args[2]);if e!=nil{return e}
 client,server:=net.ParseIP(os.Args[3]).To4(),net.ParseIP(os.Args[4]).To4()
 mac,e:=net.ParseMAC(os.Args[5]);if e!=nil||len(mac)!=6||len(iface.HardwareAddr)!=6||client==nil||server==nil{return fmt.Errorf("address")}
 fd,e:=syscall.Socket(syscall.AF_PACKET,syscall.SOCK_RAW|syscall.SOCK_CLOEXEC,ethIP);if e!=nil{return e}
 defer syscall.Close(fd)
 if e=syscall.Bind(fd,&syscall.SockaddrLinklayer{Protocol:ethIP,Ifindex:iface.Index});e!=nil{return e}
 var c net.Conn
 if host{
  l,e:=net.Listen("tcp4",control);if e!=nil{return e}
  defer l.Close()
  fmt.Println("B108_RELAY_LISTENING")
  if e=l.(*net.TCPListener).SetDeadline(time.Now().Add(45*time.Second));e!=nil{return e}
  c,e=l.Accept();if e!=nil{return e}
 }else{
  c,e=net.DialTimeout("tcp4",control,10*time.Second);if e!=nil{return e}
 }
 defer c.Close()
 c.(*net.TCPConn).SetNoDelay(true)
 fmt.Println("B108_RELAY_CONNECTED",os.Args[1])
 var tx,rx atomic.Uint64
 var lossArmed atomic.Bool
 var eligible,dropped atomic.Uint64
 if host{
  lossSignal:=make(chan os.Signal,1)
  signal.Notify(lossSignal,syscall.SIGUSR1)
  go func(){<-lossSignal;lossArmed.Store(true);fmt.Println("B111_DOWNLINK_LOSS_ARMED") }()
 }
 done:=make(chan error,2)
 // Direction is defined by the original IP tuple, not TCP stream contents.
 from,to:=client,server;if host{from,to=server,client}
 go func(){
  b:=make([]byte,65536)
  var hdr [2]byte
  seen:=make(map[uint16]bool)
  for {
   n,a,e:=syscall.Recvfrom(fd,b,0);if e!=nil{done<-e;return}
   link,ok:=a.(*syscall.SockaddrLinklayer)
   if !ok||link.Pkttype==4||n<54||binary.BigEndian.Uint16(b[12:14])!=0x0800{continue}
   total:=int(binary.BigEndian.Uint16(b[16:18]))
   if total<40||total>n-14{continue}
   p:=b[14:14+total]
   if !allowed(p,from,to,host){continue}
   // Test only: drop every 100th established payload-bearing frame
   // after authenticated READY, downlink only. Never edit or forge bytes.
   h:=int(p[0]&15)*4
   th:=int(p[h+12]>>4)*4
   if host&&lossArmed.Load()&&th>=20&&h+th<len(p)&&p[h+13]&7==0{
    if eligible.Add(1)%100==0{dropped.Add(1);continue}
   }
   binary.BigEndian.PutUint16(hdr[:],uint16(total))
   if _,e=io.Copy(c,io.MultiReader(bytes.NewReader(hdr[:]),bytes.NewReader(p)));e!=nil{done<-e;return}
   if tx.Add(1)==1{fmt.Println("B108_RELAY_FIRST_TX",os.Args[1])}
   observeCold(p,host,seen,os.Args[1],"tx")
  }
 }()
 go func(){
  var hdr [2]byte
  b:=make([]byte,65549)
  copy(b[:6],mac);copy(b[6:12],iface.HardwareAddr);binary.BigEndian.PutUint16(b[12:14],0x0800)
  addr:=&syscall.SockaddrLinklayer{Protocol:ethIP,Ifindex:iface.Index,Halen:6}
  copy(addr.Addr[:],mac)
  seen:=make(map[uint16]bool)
  for {
   if _,e:=io.ReadFull(c,hdr[:]);e!=nil{done<-e;return}
   n:=int(binary.BigEndian.Uint16(hdr[:]))
   if n<40{done<-fmt.Errorf("short frame");return}
   if _,e:=io.ReadFull(c,b[14:14+n]);e!=nil{done<-e;return}
   if !allowed(b[14:14+n],to,from,!host){done<-fmt.Errorf("wrong original tuple");return}
   if e:=syscall.Sendto(fd,b[:14+n],0,addr);e!=nil{done<-e;return}
   if rx.Add(1)==1{fmt.Println("B108_RELAY_FIRST_RX",os.Args[1])}
   observeCold(b[14:14+n],!host,seen,os.Args[1],"rx")
  }
 }()
 sig:=make(chan os.Signal,1);signal.Notify(sig,syscall.SIGTERM,syscall.SIGINT)
 select{case e=<-done:case <-sig:e=nil}
 fmt.Printf("B108_RELAY_COUNTS role=%s tx=%d rx=%d\n",os.Args[1],tx.Load(),rx.Load())
 if host&&lossArmed.Load(){fmt.Printf("B111_DOWNLINK_LOSS_COUNTS eligible=%d dropped=%d\n",eligible.Load(),dropped.Load())}
 return e
}

func main(){if e:=run();e!=nil{fmt.Println("B108_RELAY_ERROR",e);os.Exit(1)}}
