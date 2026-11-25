//go:build linux && !android

package rootjournal

import (
 "bytes"
 "context"
 "encoding/binary"
 "fmt"
 "io"
 "net"
 "os"
 "os/exec"
 "path/filepath"
 "syscall"
 "testing"
 "time"
)

// Real, disposable Linux network namespace only. The same Android exact
// netlink selector transport and production journal are invoked, not fake ip.
func TestB100IPv6SystemDNSRealNamespace(t *testing.T){
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
 p:=SystemDNSPlan{DNSPlan:DNSPlan{Tun:"wbdv40",Lease:"198.18.0.7/32",Port:port,UIDs:[]int{uid}},NetID:mark,IPv6:true}
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
 for _,bad:=range [][2]int{{uid+1,mark},{uid,mark+1}}{
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
 c,e:=dial("udp6",uid,mark);if e!=nil{t.Fatal(e)}
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
 c,e=dial("tcp6",uid,mark);if e!=nil{t.Fatal(e)}
 c.SetDeadline(time.Now().Add(5*time.Second))
 var size [2]byte;binary.BigEndian.PutUint16(size[:],uint16(len(q)))
 if _,e=c.Write(append(size[:],q...));e!=nil{c.Close();t.Fatal(e)}
 full:=make([]byte,len(q)+2)
 _,e=io.ReadFull(c,full);c.Close()
 if e!=nil||!bytes.Equal(full[2:],q){t.Fatalf("actual TCP redirect: %v",e)}
 if e=<-recv;e!=nil{t.Fatal(e)}
 t.Log("B100_HOST_IPV6_UID_MARK_UDP_TCP_REDIRECT_PASS")
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 if c,e=dial("tcp6",uid,mark);e==nil{c.Close();t.Fatal("redirect survived Stop")}
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatalf("journal remains: %v",e)}
 t.Log("B100_HOST_IPV6_OWNER_STOP_PASS")
}
