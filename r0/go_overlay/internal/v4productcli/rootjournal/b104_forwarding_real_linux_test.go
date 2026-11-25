//go:build linux && !android

package rootjournal

import (
 "bufio"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
)

// Real network namespaces and kernel links; the veth labelled "business"
// stands in for the native TUN path. No original WBD wire peer is simulated.
type b104Topology struct{ t *testing.T; ns []string; fixture string }
func (x *b104Topology) command(name string,args ...string)string{
 x.t.Helper()
 b,e:=exec.Command(name,args...).CombinedOutput()
 if e!=nil{x.t.Fatalf("%s %v: %v: %s",name,args,e,b)}
 return string(b)
}
func(x *b104Topology) newNS(suffix string)string{
 name:=fmt.Sprintf("wbd104-%d-%s",os.Getpid(),suffix)
 x.command("ip","netns","add",name)
 x.ns=append(x.ns,name)
 x.t.Cleanup(func(){if b,e:=exec.Command("ip","netns","del",name).CombinedOutput();e!=nil{x.t.Errorf("namespace cleanup %s: %v %s",name,e,b)}})
 x.in(name,"ip","link","set","lo","up")
 return name
}
func(x *b104Topology) in(ns,tool string,args ...string)string{
 return x.command("ip",append([]string{"netns","exec",ns,tool},args...)...)
}
func(x *b104Topology) runner(ns,tool string)Runner{
 return func(args ...string)(string,error){
  b,e:=exec.Command("ip",append([]string{"netns","exec",ns,tool},args...)...).CombinedOutput()
  if e!=nil{return string(b),fmt.Errorf("%s %v: %w: %s",tool,args,e,b)}
  if tool=="ip"&&strings.Join(args," ")=="-d -o link show"{
   for _,line:=range strings.Split(string(b),"\n"){if strings.Contains(line,"wbd_sit0"){x.t.Log("B105_SIT_KERNEL_READBACK",ns,line)}}
  }
  return string(b),nil
 }
}
func(x *b104Topology) link(a,an,b,bn string){
 x.command("ip","link","add",an,"netns",a,"type","veth","peer","name",bn,"netns",b)
 for _,p:=range [][2]string{{a,an},{b,bn}}{x.in(p[0],"ip","link","set",p[1],"up")}
}
func(x *b104Topology) addr(ns,dev,cidr string){
 if strings.Contains(cidr,":"){x.in(ns,"ip","-6","addr","add",cidr,"dev",dev,"nodad")}else{x.in(ns,"ip","addr","add",cidr,"dev",dev)}
}
func(x *b104Topology) server(ns,addr,port,source,kind string){
 x.t.Helper()
 c:=exec.Command("ip","netns","exec",ns,"python3","-u",x.fixture,"serve",addr,port,source,kind)
 pipe,e:=c.StdoutPipe();if e!=nil{x.t.Fatal(e)}
 c.Stderr=os.Stderr
 if e=c.Start();e!=nil{x.t.Fatal(e)}
 x.t.Cleanup(func(){_ = c.Process.Kill();_ = c.Wait()})
 line,e:=bufio.NewReader(pipe).ReadString('\n');if e!=nil||strings.TrimSpace(line)!="B104_SOCKET_READY"{x.t.Fatalf("socket fixture admission %q %v",line,e)}
}
func(x *b104Topology) client(ns,addr,port,kind string){
 x.t.Helper()
 out:=x.in(ns,"python3",x.fixture,"client",addr,port,kind)
 if !strings.Contains(out,"B104_SOCKET_ROUNDTRIP_PASS"){x.t.Fatalf("no actual socket result %s",out)}
 x.t.Log(strings.TrimSpace(out))
}
func(x *b104Topology) absent(ns string,table,marker string,ipv6 bool){
 x.t.Helper()
 family:="-4";if ipv6{family="-6"}
 for _,args:=range [][]string{{family,"rule","show"},{family,"route","show","table","all"}}{
  s:=x.in(ns,"ip",args...)
  if strings.Contains(s,"lookup "+table)||strings.Contains(s,"table "+table){x.t.Fatalf("owned routing remains: %s",s)}
 }
 tool:="iptables";if ipv6{tool="ip6tables"}
 for _,table:=range []string{"filter","nat"}{
  if s:=x.in(ns,tool,"-w","2","-t",table,"-S");strings.Contains(s,marker){x.t.Fatalf("owned firewall remains: %s",s)}
 }
}
func b104Setup(t *testing.T)*b104Topology{
 t.Helper()
 if os.Getenv("WBD_B104_REAL_NS")!="1"{t.Skip("requires disposable CI host namespaces")}
 if os.Geteuid()!=0{t.Fatal("requires root")}
 fixture:=os.Getenv("WBD_B104_SOCKET_FIXTURE")
 if !filepath.IsAbs(fixture){t.Fatal("absolute fixture required")}
 return &b104Topology{t:t,fixture:fixture}
}

func TestB104TetherIPv4RealDownstream(t *testing.T){
 x:=b104Setup(t)
 down,r,tun,wan:=x.newNS("down"),x.newNS("router"),x.newNS("business"),x.newNS("direct")
 x.link(down,"down0",r,"ap0")
 x.link(r,"wbdtun0",tun,"tunpeer0")
 x.link(r,"wan0",wan,"wanpeer0")
 x.addr(down,"down0","192.168.43.2/24");x.addr(r,"ap0","192.168.43.1/24")
 x.addr(r,"wbdtun0","10.66.0.2/32");x.addr(tun,"tunpeer0","10.66.0.1/24")
 x.addr(r,"wan0","172.20.0.1/24");x.addr(wan,"wanpeer0","172.20.0.2/24")
 x.addr(tun,"tunpeer0","192.0.2.10/32")
 x.addr(wan,"wanpeer0","192.0.2.10/32");x.addr(wan,"wanpeer0","192.0.2.20/32")
 x.in(down,"ip","route","add","default","via","192.168.43.1")
 x.in(r,"ip","route","add","192.0.2.10/32","dev","wan0")
 x.in(r,"ip","route","add","192.0.2.20/32","dev","wan0")
 x.in(wan,"ip","route","add","192.168.43.0/24","via","172.20.0.1")
 x.in(r,"sysctl","-qw","net.ipv4.ip_forward=1")
 // This disposable namespace has two paths to the same service address.
 // Model normal policy-routed forwarding, not host strict reverse-path
 // filtering. No host-global or production Android setting is changed.
 for _,dev:=range []string{"all","wbdtun0","wan0","ap0"}{
  x.in(r,"sysctl","-qw","net.ipv4.conf."+dev+".rp_filter=0")
 }
 // The TUN substitute must be the actual next hop after the owned rule.
 // Both paths have identical service IP; response identity + source
 // distinguishes real direct routing from SNAT over the tunnel link.
 x.server(tun,"192.0.2.10","18080","10.66.0.2","business")
 x.server(wan,"192.0.2.10","18080","192.168.43.2","direct")
 x.server(wan,"192.0.2.20","18080","192.168.43.2","direct")
 x.server(r,"192.168.43.1","15353","192.168.43.2","dns")
 x.client(down,"192.0.2.10","18080","direct")
 path:=filepath.Join(t.TempDir(),"owner","tether-journal.json")
 owner,e:=NewTether(x.runner(r,"ip"),x.runner(r,"iptables"),path,TetherPlan{
  Tun:"wbdtun0",Downstream:"ap0",Subnet:"192.168.43.0/24",Lease:"10.66.0.2/32",
  DirectCIDRs:[]string{"192.0.2.20/32"},DNSAddress:"192.168.43.1",DNSPort:15353,
 })
 if e!=nil{t.Fatal(e)}
 defer owner.Stop()
 x.client(down,"192.0.2.10","18080","business")
 x.client(down,"192.0.2.20","18080","direct")
 x.client(down,"192.0.2.53","53","dns")
 t.Log("B104_TETHER_IPV4_FORWARD_SNAT_DIRECT_DNS_PASS")
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 x.absent(r,"19844","wbd-next-root-tether-v1",false)
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("journal remains",e)}
 x.client(down,"192.0.2.10","18080","direct")
 t.Log("B104_TETHER_IPV4_STOP_RESTORED_PASS")
}

func TestB104IPv6CarrierRealDownstream(t *testing.T){
 x:=b104Setup(t)
 down,c,s,eg:=x.newNS("down"),x.newNS("client"),x.newNS("server"),x.newNS("egress")
 x.link(down,"down0",c,"ap0");x.link(c,"wbdtun0",s,"wbdtun0");x.link(s,"wan0",eg,"wanpeer0")
 x.addr(c,"wbdtun0","10.66.0.2/24");x.addr(s,"wbdtun0","10.66.0.1/24")
 x.addr(c,"ap0","fd12:34::1/64");x.addr(down,"down0","fd12:34::2/64")
 x.addr(s,"wan0","fd12:56::1/64");x.addr(eg,"wanpeer0","fd12:56::2/64")
 x.in(down,"ip","-6","route","add","default","via","fd12:34::1")
 for _,ns:=range []string{c,s}{x.in(ns,"sysctl","-qw","net.ipv6.conf.all.forwarding=1")}
 x.server(eg,"fd12:56::2","18080","fd12:56::1","business")
 x.server(c,"fd12:34::1","15353","fd12:34::2","dns")
 dir:=t.TempDir()
 pathS:=filepath.Join(dir,"server","ipv6-carrier-journal.json")
 pathC:=filepath.Join(dir,"client","ipv6-carrier-journal.json")
 so,e:=NewIPv6Carrier(x.runner(s,"ip"),x.runner(s,"iptables"),x.runner(s,"ip6tables"),pathS,
  IPv6Plan{Server:true,Tun:"wbdtun0",Local4:"10.66.0.1",Gateway4:"10.66.0.1",Egress:"wan0",MTU:1369})
 if e!=nil{t.Fatal(e)}
 defer so.Stop()
 co,e:=NewIPv6Carrier(x.runner(c,"ip"),x.runner(c,"iptables"),x.runner(c,"ip6tables"),pathC,
  IPv6Plan{Tun:"wbdtun0",Local4:"10.66.0.2",Gateway4:"10.66.0.1",MTU:1369,UIDs:[]int{10220},
   Downstream:"ap0",Downstream6:[]string{"fd12:34::1/64"},DownstreamDNSPorts:[]int{15353}})
 if e!=nil{t.Fatal(e)}
 defer co.Stop()
 x.in(c,"ping","-6","-I","fd65:5742:7636:2::1","-c","2","-W","2","fd65:5742:7636:1::1")
 // Ordinary non-root local socket plus an actual independent downstream.
 // Read the same source as root, then execute it as the actual ordinary
 // UID. The Actions checkout parent is private; do not chmod it or run
 // the ordinary client as root just to make the test pass.
 code,e:=os.ReadFile(x.fixture);if e!=nil{t.Fatal(e)}
 out:=x.in(c,"setpriv","--reuid=10220","--regid=10220","--clear-groups","python3","-c",string(code),"client","fd12:56::2","18080","business")
 if !strings.Contains(out,"B104_SOCKET_ROUNDTRIP_PASS"){t.Fatal(out)}
 t.Log(strings.TrimSpace(out))
 x.client(down,"fd12:56::2","18080","business")
 x.client(down,"fd12:99::53","53","dns")
 t.Log("B104_IPV6_CARRIER_UID_DOWNSTREAM_DNS_PASS")
 if e=co.Stop();e!=nil{t.Fatal(e)}
 if e=so.Stop();e!=nil{t.Fatal(e)}
 for _,ns:=range []string{c,s}{
  x.absent(ns,"19847","wbd-next-ipv6-carrier-v1",true)
  x.absent(ns,"19847","wbd-next-ipv6-carrier-v1",false)
  if _,e=exec.Command("ip","-n",ns,"link","show","dev","wbd_sit0").CombinedOutput();e==nil{t.Fatal("SIT link remains",ns)}
 }
 for _,p:=range []string{pathC,pathS}{if _,e=os.Stat(p);!os.IsNotExist(e){t.Fatal("journal remains",e)}}
 t.Log("B104_IPV6_CARRIER_STOP_PASS")
}
