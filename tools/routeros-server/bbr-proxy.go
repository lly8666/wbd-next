// Experiment only: real TCP endpoint through a separate kernel-routed TUN.
// The WBD Rust owner and wire protocol are unchanged.
package main
import (
 "context"
 "fmt"
 "io"
 "net"
 "os"
 "os/signal"
 "strconv"
 "sync"
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
func must(e tcpip.Error){if e!=nil{panic(e.String())}}
func check(e error){if e!=nil{panic(e)}}
func main(){
 cc:=os.Args[1]
 if cc!="bbr"&&cc!="cubic"{panic("explicit cc required")}
 ctx,stop:=signal.NotifyContext(context.Background(),syscall.SIGTERM,syscall.SIGINT);defer stop()
 f,e:=os.OpenFile("/dev/net/tun",os.O_RDWR|syscall.O_NONBLOCK,0);check(e);defer f.Close()
 var req [40]byte;copy(req[:16],"bbrtun")
 *(*uint16)(unsafe.Pointer(&req[16]))=0x1001
 _,_,eno:=syscall.Syscall(syscall.SYS_IOCTL,f.Fd(),0x400454ca,uintptr(unsafe.Pointer(&req[0])));if eno!=0{panic(eno)}
 le,e:=fdbased.New(&fdbased.Options{FDs:[]int{int(f.Fd())},MTU:1500,EthernetHeader:false});check(e)
 st:=stack.New(stack.Options{NetworkProtocols:[]stack.NetworkProtocolFactory{ipv4.NewProtocol},TransportProtocols:[]stack.TransportProtocolFactory{tcp.NewProtocol}})
 avail:=tcpip.TCPAvailableCongestionControlOption("reno cubic bbr");must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&avail))
 selected:=tcpip.CongestionControlOption(cc);must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&selected))
 sack:=tcpip.TCPSACKEnabled(true);must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&sack))
 rate:=tcpip.TCPDeliveryRateSamplingEnabled(true);must(st.SetTransportProtocolOption(tcp.ProtocolNumber,&rate))
 must(st.CreateNIC(1,le))
 addr:=tcpip.AddrFrom4([4]byte{10,249,90,2})
 must(st.AddProtocolAddress(1,tcpip.ProtocolAddress{Protocol:ipv4.ProtocolNumber,AddressWithPrefix:tcpip.AddressWithPrefix{Address:addr,PrefixLen:30}},stack.AddressProperties{}))
 must(st.SetPromiscuousMode(1,true));must(st.SetSpoofing(1,true))
 st.SetRouteTable([]tcpip.Route{{Destination:header.IPv4EmptySubnet,NIC:1}})
 var wg sync.WaitGroup
 fw:=tcp.NewForwarder(st,0,1024,func(r *tcp.ForwarderRequest){
   wg.Add(1);defer wg.Done()
   id:=r.ID()
   target:=net.JoinHostPort(id.LocalAddress.String(),strconv.Itoa(int(id.LocalPort)))
   remote,err:=(&net.Dialer{Timeout:30*time.Second}).DialContext(ctx,"tcp4",target)
   if err!=nil{r.Complete(true);fmt.Printf("WBD_BBR_PROXY_DIAL_ERROR target=%s err=%v\n",target,err);return}
   upstream:=remote.(*net.TCPConn);defer upstream.Close()
   var q waiter.Queue
   ep,er:=r.CreateEndpoint(&q)
   if er!=nil{r.Complete(true);fmt.Printf("WBD_BBR_PROXY_ACCEPT_ERROR target=%s err=%s\n",target,er.String());return}
   r.Complete(false)
   client:=gonet.NewTCPConn(&q,ep);defer client.Close()
   var actual tcpip.CongestionControlOption;must(ep.GetSockOpt(&actual))
   if string(actual)!=cc{panic(fmt.Sprintf("actual cc %s != %s",actual,cc))}
   fmt.Printf("WBD_BBR_PROXY_ACCEPT target=%s cc=%s\n",target,actual)
   cancel:=context.AfterFunc(ctx,func(){client.Close();upstream.Close()});defer cancel()
   type result struct{n int64;err error}
   upload:=make(chan result,1)
   go func(){n,e:=io.CopyBuffer(upstream,client,make([]byte,64*1024));if e==nil{e=upstream.CloseWrite()};upload<-result{n,e}}()
   down,de:=io.CopyBuffer(client,upstream,make([]byte,64*1024))
   if de==nil{de=client.CloseWrite()}
   if de!=nil{client.Close();upstream.Close()}
   up:=<-upload
   var info tcpip.TCPInfoOption
   must(ep.GetSockOpt(&info))
   fmt.Printf("WBD_BBR_PROXY_DONE target=%s cc=%s up=%d down=%d ok=%t info=%+v\n",target,actual,up.n,down,up.err==nil&&de==nil,info)
 })
 st.SetTransportProtocolHandler(tcp.ProtocolNumber,fw.HandlePacket)
 fmt.Printf("WBD_BBR_PROXY_READY cc=%s\n",cc)
 <-ctx.Done()
 st.Close()
 st.Wait()
 wg.Wait()
 fmt.Println("WBD_BBR_PROXY_STOP")
}
