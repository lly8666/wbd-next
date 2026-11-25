//go:build linux && !android

package rootjournal

import (
 "bytes"
 "context"
 "encoding/binary"
 "fmt"
 "io"
 "net"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "syscall"
 "strings"
 "strconv"
 "unsafe"
 "testing"
 "time"
)

// Real, disposable Linux network namespace only. The same Android exact
// netlink selector transport and production journal are invoked, not fake ip.
func TestB100IPv6SystemDNSRealNamespace(t *testing.T){testIPv6SystemDNSNamespace(t,false)}
func TestB120ManagedDNSRealNamespace(t *testing.T){testIPv6SystemDNSNamespace(t,true)}
func testIPv6SystemDNSNamespace(t *testing.T,managed bool){
 if os.Getenv("WBD_B100_REAL_NS")!="1"{t.Skip("requires isolated CI netns")}
 if os.Geteuid()!=0{t.Fatal("requires root inside isolated netns")}
 runner:=func(name string)Runner{
  return func(args ...string)(string,error){
   out,e:=exec.Command(name,args...).CombinedOutput()
   if e!=nil{return string(out),fmt.Errorf("%s %v: %w: %s",name,args,e,out)}
   return string(out),nil
  }
 }
 ip,fw:=runner("ip"),runner("ip6tables")
 if out,e:=ip("-6","route","show","default");e!=nil||out!=""{t.Fatalf("not an isolated netns: %q %v",out,e)}
 l,e:=net.Listen("tcp6","[::1]:0");if e!=nil{t.Fatal(e)};defer l.Close()
 port:=l.Addr().(*net.TCPAddr).Port
 u,e:=net.ListenPacket("udp6",fmt.Sprintf("[::1]:%d",port));if e!=nil{t.Fatal(e)};defer u.Close()
 const uid=10220
 const mark=105
 path:=filepath.Join(t.TempDir(),"owned","system-dns6-journal.json")
 p:=SystemDNSPlan{DNSPlan:DNSPlan{Tun:"wbdv40",Lease:"198.18.0.7/32",Port:port,UIDs:[]int{uid}},NetID:mark,IPv6:true,Managed:managed}
 transport:=&SystemDNSRuleIO{Read:systemDNSNetlinkRead,Change:systemDNSNetlinkChange}
 owner,e:=NewSystemDNS(ip,fw,nil,nil,path,p,transport)
 if e!=nil{t.Fatal(e)}
 defer owner.Stop()
 q:=[]byte("B100_REAL_DNS6_REDIRECT")
 dial:=func(network string,id,fwmark int)(net.Conn,error){
  d:=net.Dialer{Timeout:2*time.Second,Control:func(network,address string,raw syscall.RawConn)error{
   var e error
   if err:=raw.Control(func(fd uintptr){
    e=syscall.SetsockoptInt(int(fd),syscall.SOL_SOCKET,syscall.SO_MARK,fwmark)
    if e==nil{e=syscall.Fchown(int(fd),id,-1)}
   });err!=nil{return err};return e
  }}
  return d.DialContext(context.Background(),network,"[fd00::53]:53")
 }
 bads:=[][2]int{{uid+1,mark}};if !managed{bads=append(bads,[2]int{uid,mark+1})}
 for _,bad:=range bads{
  if c,e:=dial("tcp6",bad[0],bad[1]);e==nil{c.Close();t.Fatal("wrong UID or netid captured")}
 }
 recv:=make(chan error,1)
 go func(){
  buf:=make([]byte,128)
  u.SetDeadline(time.Now().Add(5*time.Second))
  n,addr,e:=u.ReadFrom(buf)
  if e==nil&&!bytes.Equal(buf[:n],q){e=fmt.Errorf("UDP fixture bytes differ")}
  if e==nil{_,e=u.WriteTo(q,addr)}
  recv<-e
 }()
 udpMark:=mark;if managed{udpMark=0}
 c,e:=dial("udp6",uid,udpMark);if e!=nil{t.Fatal(e)}
 c.SetDeadline(time.Now().Add(5*time.Second))
 if _,e=c.Write(q);e!=nil{c.Close();t.Fatal(e)}
 got:=make([]byte,128)
 n,e:=c.Read(got);c.Close()
 if e!=nil||!bytes.Equal(got[:n],q){t.Fatalf("actual UDP redirect: %d %v",n,e)}
 if e=<-recv;e!=nil{t.Fatal(e)}
 go func(){
  l.(*net.TCPListener).SetDeadline(time.Now().Add(5*time.Second))
  conn,e:=l.Accept()
  if e!=nil{recv<-e;return}
  defer conn.Close()
  conn.SetDeadline(time.Now().Add(5*time.Second))
  var size [2]byte
  if _,e=io.ReadFull(conn,size[:]);e!=nil{recv<-e;return}
  if int(binary.BigEndian.Uint16(size[:]))!=len(q){recv<-fmt.Errorf("TCP length differs");return}
  got:=make([]byte,len(q))
  _,e=io.ReadFull(conn,got)
  if e==nil&&!bytes.Equal(got,q){e=fmt.Errorf("TCP fixture differs")}
  if e==nil{_,e=conn.Write(append(size[:],q...))}
  recv<-e
 }()
 tcpMark:=mark;if managed{tcpMark=mark+1}
 c,e=dial("tcp6",uid,tcpMark);if e!=nil{t.Fatal(e)}
 c.SetDeadline(time.Now().Add(5*time.Second))
 var size [2]byte;binary.BigEndian.PutUint16(size[:],uint16(len(q)))
 if _,e=c.Write(append(size[:],q...));e!=nil{c.Close();t.Fatal(e)}
 full:=make([]byte,len(q)+2)
 _,e=io.ReadFull(c,full);c.Close()
 if e!=nil||!bytes.Equal(full[2:],q){t.Fatalf("actual TCP redirect: %v",e)}
 if e=<-recv;e!=nil{t.Fatal(e)}
 if managed{t.Log("B120_HOST_MANAGED_DNS6_UDP_TCP_ANY_MARK_PASS")}else{t.Log("B100_HOST_IPV6_UID_MARK_UDP_TCP_REDIRECT_PASS")}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 if c,e=dial("tcp6",uid,mark);e==nil{c.Close();t.Fatal("redirect survived Stop")}
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatalf("journal remains: %v",e)}
 t.Log("B100_HOST_IPV6_OWNER_STOP_PASS")
}

func TestB120IPv6EntryRealNamespace(t *testing.T){
 if os.Getenv("WBD_B100_REAL_NS")!="1"{t.Skip("isolated netns only")}
 if os.Geteuid()!=0{t.Fatal("root required")}
 runner:=func(name string)Runner{return func(a ...string)(string,error){b,e:=exec.Command(name,a...).CombinedOutput();if e!=nil{return string(b),fmt.Errorf("%s %v: %w %s",name,a,e,b)};return string(b),nil}}
 ip:=runner("ip")
 run:=func(a ...string){t.Helper();if _,e:=ip(a...);e!=nil{t.Fatal(e)}}
 fd,e:=os.OpenFile("/dev/net/tun",os.O_RDWR,0);if e!=nil{t.Fatal(e)};defer fd.Close()
 var ifr [40]byte;copy(ifr[:],"wbd120tun");binary.NativeEndian.PutUint16(ifr[16:18],0x1001)
 if _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,fd.Fd(),0x400454ca,uintptr(unsafe.Pointer(&ifr[0])));errno!=0{t.Fatal(errno)}
 if e=syscall.SetNonblock(int(fd.Fd()),true);e!=nil{t.Fatal(e)}
 run("link","set","dev","wbd120tun","mtu","1400","up")
 p:=IPv6Plan{Drop:true,Tun:"wbd120tun",Local4:"10.66.0.8",MTU:1400,UIDs:[]int{10220}}
 path:=filepath.Join(t.TempDir(),"owned",ipv6CarrierJournal)
 owner,e:=NewIPv6Carrier(ip,runner("iptables"),runner("ip6tables"),path,p);if e!=nil{t.Fatal(e)}
 defer owner.Stop()
 dst:="fd00:120::53"
 d:=net.Dialer{Timeout:time.Second,Control:func(network,address string,raw syscall.RawConn)error{var ch error;e:=raw.Control(func(fd uintptr){ch=syscall.Fchown(int(fd),10220,-1)});if e!=nil{return e};return ch}}
 c,e:=d.DialContext(context.Background(),"udp6","["+dst+"]:443");if e!=nil{t.Fatal(e)}
 payload:=[]byte("B120_IPV6_ENTRY")
 _,e=c.Write(payload);c.Close();if e!=nil{t.Fatal(e)}
 seen:=false;buf:=make([]byte,2048)
 for end:=time.Now().Add(2*time.Second);time.Now().Before(end);{
  n,e:=syscall.Read(int(fd.Fd()),buf)
  if e!=nil&&e!=syscall.EAGAIN{t.Fatal(e)}
  if n>=40&&buf[0]>>4==6&&bytes.Contains(buf[:n],payload){seen=true;break}
  time.Sleep(10*time.Millisecond)
 }
 if !seen{t.Fatal("actual IPv6 app payload did not enter owned TUN")}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 if got,e:=ip("-6","rule","show");e!=nil||strings.Contains(got,ipv6CarrierTable){t.Fatalf("IPv6 rule survived Stop %s %v",got,e)}
 p.MTU=1200
 owner,e=NewIPv6Carrier(ip,runner("iptables"),runner("ip6tables"),path,p);if e!=nil{t.Fatal(e)}
 if got,e:=ip("-6","route","show","table",ipv6CarrierTable);e!=nil||!strings.Contains(got,"blackhole default"){t.Fatal(got,e)}
 // Reproduce the previous release leaving its journal and low-MTU
 // route installed after its readback mismatch; recover using new code.
 if e=owner.lock.Close();e!=nil{t.Fatal(e)};owner.lock=nil
 if e=RecoverIPv6Carrier(ip,runner("iptables"),runner("ip6tables"),path);e!=nil{t.Fatal(e)}
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("old journal survived recovery",e)}
 if got,e:=ip("-6","rule","show");e!=nil||strings.Contains(got,ipv6CarrierTable){t.Fatalf("IPv6 rule survived recovery %s %v",got,e)}
 owner,e=NewIPv6Carrier(ip,runner("iptables"),runner("ip6tables"),path,p);if e!=nil{t.Fatal(e)}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 t.Log("B121_HOST_BLACKHOLE_OLD_JOURNAL_RECOVERY_AND_RESTART_PASS")
 t.Log("B120_HOST_REAL_TUN_IPV6_ENTRY_AND_LOW_MTU_DROP_STOP_PASS")
}


// Actual ICMPv6 RA packets through the selected downstream OUTPUT hook.
// The peer veth represents a different interface, not a real device.
func TestB123DownstreamRARealNamespace(t *testing.T){
 if os.Getenv("WBD_B100_REAL_NS")!="1"{t.Skip("isolated netns only")}
 if os.Geteuid()!=0{t.Fatal("root required")}
 runner:=func(name string)Runner{return func(a ...string)(string,error){b,e:=exec.Command(name,a...).CombinedOutput();if e!=nil{return string(b),fmt.Errorf("%s %v: %w %s",name,a,e,b)};return string(b),nil}}
 ip,fw6:=runner("ip"),runner("ip6tables")
 run:=func(a ...string){t.Helper();if _,e:=ip(a...);e!=nil{t.Fatal(e)}}
 run("link","add","wbd123ap","type","veth","peer","name","wbd123peer")
 defer ip("link","del","wbd123ap")
 run("link","set","dev","wbd123ap","up")
 run("link","set","dev","wbd123peer","up")
 run("-6","addr","add","fe80::123:1/64","dev","wbd123ap","nodad")
 run("-6","addr","add","fe80::123:2/64","dev","wbd123peer","nodad")
 // Use the low-MTU path to verify RA suppression even without a TUN
 // IPv6 address. The existing real TUN test covers the other path.
 p:=IPv6Plan{Drop:true,SuppressRA:true,Tun:"wbd123tun",Local4:"10.66.0.8",MTU:1200,UIDs:[]int{10220},Downstream:"wbd123ap"}
 path:=filepath.Join(t.TempDir(),"owned",ipv6CarrierJournal)
 owner,e:=NewIPv6Carrier(ip,runner("iptables"),fw6,path,p);if e!=nil{t.Fatal(e)}
 defer owner.Stop()
 send:=func(iface string,typ byte)error{
  nic,e:=net.InterfaceByName(iface);if e!=nil{return e}
  fd,e:=syscall.Socket(syscall.AF_INET6,syscall.SOCK_RAW,syscall.IPPROTO_ICMPV6);if e!=nil{return e};defer syscall.Close(fd)
  if e=syscall.SetsockoptInt(fd,syscall.IPPROTO_IPV6,syscall.IPV6_MULTICAST_IF,nic.Index);e!=nil{return e}
  if e=syscall.SetsockoptInt(fd,syscall.IPPROTO_IPV6,syscall.IPV6_MULTICAST_HOPS,255);e!=nil{return e}
  dst:=syscall.SockaddrInet6{Addr:netip.MustParseAddr("ff02::1").As16(),ZoneId:uint32(nic.Index)}
  msg:=make([]byte,16);msg[0]=typ
  return syscall.Sendto(fd,msg,0,&dst)
 }
 count:=func()uint64{
  t.Helper()
  out,e:=fw6("-w","2","-t","filter","-L","OUTPUT","-v","-n","-x");if e!=nil{t.Fatal(e)}
  for _,line:=range strings.Split(out,"\n"){if strings.Contains(line,ipv6CarrierMarker){w:=strings.Fields(line);n,e:=strconv.ParseUint(w[0],10,64);if e!=nil{t.Fatal(line,e)};return n}}
  t.Fatal("missing owned RA counter",out);return 0
 }
 if got:=count();got!=0{t.Fatal("unexpected initial RA counter",got)}
 if e=send("wbd123ap",134);e!=nil&&e!=syscall.EPERM&&e!=syscall.EACCES{t.Fatal("selected RA send",e)}
 if got:=count();got!=1{t.Fatal("selected downstream RA not intercepted",got)}
 if e=send("wbd123peer",134);e!=nil{t.Fatal("unselected RA send",e)}
 if e=send("wbd123ap",133);e!=nil{t.Fatal("non-RA ICMPv6 send",e)}
 if got:=count();got!=1{t.Fatal("rule intercepted unrelated interface or ICMPv6",got)}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 out,e:=fw6("-w","2","-t","filter","-S","OUTPUT");if e!=nil||strings.Contains(out,ipv6CarrierMarker){t.Fatal("RA rule survived Stop",out,e)}
 if e=send("wbd123ap",134);e!=nil{t.Fatal("RA not restored",e)}
 t.Log("B123_HOST_REAL_RA_SELECTED_INTERFACE_ONLY_STOP_PASS")
}
