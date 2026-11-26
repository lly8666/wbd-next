// Lab reference: real TCP/IPv4 from a pinned external BBRv3 netstack, not WBD product.
package main

import (
 "crypto/sha256"
 "fmt"
 "io"
 "os"
 "syscall"
 "time"
 "unsafe"
 "gvisor.dev/gvisor/pkg/tcpip"
 "gvisor.dev/gvisor/pkg/tcpip/adapters/gonet"
 "gvisor.dev/gvisor/pkg/tcpip/header"
 "gvisor.dev/gvisor/pkg/tcpip/link/fdbased"
 "gvisor.dev/gvisor/pkg/tcpip/network/ipv4"
 "gvisor.dev/gvisor/pkg/tcpip/stack"
 "gvisor.dev/gvisor/pkg/tcpip/transport/tcp"
 "gvisor.dev/gvisor/pkg/waiter"
)
func must(e tcpip.Error) { if e!=nil {panic(e.String())} }
func check(e error) {if e!=nil {panic(e)}}
func main(){
 cc:=os.Getenv("BBR_LAB_CC")
 if cc!="bbr"&&cc!="cubic"{panic("explicit bbr or cubic required")}
 f,e:=os.OpenFile("/dev/net/tun",os.O_RDWR|syscall.O_NONBLOCK,0);check(e);defer f.Close()
 // x86_64 Linux ifreq: named persistent TUN created by the fixture.
 var req [40]byte
 copy(req[:16],"bbrtest")
 *(*uint16)(unsafe.Pointer(&req[16]))=0x1001 // IFF_TUN | IFF_NO_PI
 _,_,eno:=syscall.Syscall(syscall.SYS_IOCTL,f.Fd(),0x400454ca,uintptr(unsafe.Pointer(&req[0])))
 if eno!=0 {panic(eno)}
 le,e:=fdbased.New(&fdbased.Options{FDs:[]int{int(f.Fd())},MTU:1500,EthernetHeader:false});check(e)
 st:=stack.New(stack.Options{NetworkProtocols:[]stack.NetworkProtocolFactory{ipv4.NewProtocol},TransportProtocols:[]stack.TransportProtocolFactory{tcp.NewProtocol}})
 defer st.Destroy()
 avail:=tcpip.TCPAvailableCongestionControlOption("reno cubic bbr")
 must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&avail))
 chosen:=tcpip.CongestionControlOption(cc)
 must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&chosen))
 sack:=tcpip.TCPSACKEnabled(true);must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&sack))
 rate:=tcpip.TCPDeliveryRateSamplingEnabled(true);must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&rate))
 must(st.CreateNIC(1,le))
 address:=tcpip.AddrFrom4([4]byte{10,249,90,2})
 must(st.AddProtocolAddress(1,tcpip.ProtocolAddress{Protocol:ipv4.ProtocolNumber,AddressWithPrefix:tcpip.AddressWithPrefix{Address:address,PrefixLen:24}},stack.AddressProperties{}))
 st.SetRouteTable([]tcpip.Route{{Destination:header.IPv4EmptySubnet,NIC:1}})
 var wq waiter.Queue
 listen,err:=st.NewEndpoint(tcp.ProtocolNumber,ipv4.ProtocolNumber,&wq);must(err)
 defer listen.Close()
 must(listen.Bind(tcpip.FullAddress{NIC:1,Addr:address,Port:5300}));must(listen.Listen(8))
 event,notify:=waiter.NewChannelEntry(waiter.ReadableEvents)
 wq.EventRegister(&event);defer wq.EventUnregister(&event)
 fmt.Printf("BBR_LAB_READY cc=%s\n",cc)
 var conn *gonet.TCPConn
 var ep tcpip.Endpoint
 for {
   n,q,err:=listen.Accept(nil)
   if _,ok:=err.(*tcpip.ErrWouldBlock);ok {select{case <-notify:continue;case <-time.After(60*time.Second):panic("accept deadline")}}
   must(err);ep=n;conn=gonet.NewTCPConn(q,n);break
 }
 defer conn.Close()
 var actual tcpip.CongestionControlOption
 must(ep.GetSockOpt(&actual))
 if string(actual)!=cc {panic(fmt.Sprintf("actual CC %s != %s",actual,cc))}
 fmt.Printf("BBR_LAB_ACCEPT actual_cc=%s\n",actual)
 check(conn.SetDeadline(time.Now().Add(120*time.Second)))
 var request [1]byte
 _,e=io.ReadFull(conn,request[:]);check(e)
 payload:=make([]byte,512*1024)
 for i:=range payload {payload[i]=byte(i*31+7)}
 start:=time.Now()
 n,e:=conn.Write(payload);check(e)
 if n!=len(payload){panic("short application write")}
 var info tcpip.TCPInfoOption
 must(ep.GetSockOpt(&info));fmt.Printf("BBR_LAB_TCP_INFO %+v\n",info)
 check(conn.CloseWrite())
 expected:=fmt.Sprintf("%x",sha256.Sum256(payload))
 var receipt [64]byte
 _,e=io.ReadFull(conn,receipt[:]);check(e)
 if string(receipt[:])!=expected{panic("receiver hash mismatch")}
 must(ep.GetSockOpt(&info))
 fmt.Printf("BBR_LAB_FINAL_TCP_INFO %+v\n",info)
 fmt.Printf("BBR_LAB_REAL_TCP_PASS actual_cc=%s bytes=%d sha256=%s elapsed=%s\n",actual,n,expected,time.Since(start))
}
