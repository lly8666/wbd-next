//go:build android && cgo && wbd_v4_embedded_go && wbd_android_specialty_test

// CI only: calls original Go TUN, rootjournal and Bionic DNS. Test /32 is
// an isolated kernel component input, not a fabricated server admission.
package v4productcli

import (
 "bytes"
 "context"
 "encoding/binary"
 "fmt"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "sort"
 "strconv"
 "strings"
 "syscall"
 "time"

 "github.com/lly8666/wobuzhidao/internal/v4productcli/dnsnative"
 "github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal"
)

func b90IP(args ...string)(string,error){
 b,e:=exec.Command("/system/bin/ip",args...).CombinedOutput()
 if e!=nil{return string(b),fmt.Errorf("ip %v: %w: %s",args,e,b)}
 return string(b),nil
}
func b90UsesTun(uid int,dest,tun string,want bool)error{
 out,e:=b90IP("-4","route","get",dest,"uid",strconv.Itoa(uid))
 if e!=nil{return e}
 if rootjournal.SelectedUIDRouteGetUsesTun(out,tun)!=want{
  return fmt.Errorf("uid=%d dest=%s want_tun=%t: %s",uid,dest,want,out)
 }
 return nil
}
func b90Packet(tun *ownedTun,uid int)error{
 ctx,cancel:=context.WithTimeout(context.Background(),12*time.Second);defer cancel()
 out,e:=exec.CommandContext(ctx,"/system/bin/am","instrument","-w","-r","-e","uid_probe","1","org.wbdnext.testtraffic/.TrafficInstrumentation").CombinedOutput()
 if e!=nil||!strings.Contains(string(out),fmt.Sprintf("uid_probe_sent=%d",uid))||!strings.Contains(string(out),"INSTRUMENTATION_CODE: -1"){return fmt.Errorf("ordinary App send: %v: %s",e,out)}
 if e=syscall.SetNonblock(int(tun.f.Fd()),true);e!=nil{return e}
 buf:=make([]byte,2048)
 deadline:=time.Now().Add(2*time.Second)
 for time.Now().Before(deadline){
  n,e:=syscall.Read(int(tun.f.Fd()),buf)
  if e==syscall.EAGAIN||e==syscall.EINTR{time.Sleep(20*time.Millisecond);continue}
  if e!=nil{return e}
  if n<28||buf[0]>>4!=4||buf[9]!=17{continue}
  h:=int(buf[0]&15)*4
  if h<20||n<h+8||!bytes.Equal(buf[16:20],[]byte{192,0,2,1}){continue}
  if binary.BigEndian.Uint16(buf[h+2:h+4])==43999&&bytes.Equal(buf[h+8:n],[]byte("WBD_B90_UID")){return nil}
 }
 return fmt.Errorf("ordinary UID datagram absent on original TUN")
}
type b90Stop interface{Stop()error}
func b90Routes(scope dnsnative.PhysicalScope,uid,bypass,own,manager int,snapshot []byte) (ret error){
 const dev="wbdb90"
 const lease="198.18.0.1/32"
 const peer="10.0.2.2"
 const dest="192.0.2.1"
 if _,e:=b90IP("link","show","dev",dev);e==nil{return fmt.Errorf("test TUN exists")}
 dir,e:=os.MkdirTemp("/data/local/tmp","wbd-b90-");if e!=nil{return e}
 defer func(){if ret==nil{_ = os.RemoveAll(dir)}}()
 tun,e:=openTun(dev,lease,1389);if e!=nil{return e}
 defer func(){if e:=tun.Close();ret==nil{ret=e}}()
 actual,e:=readOwnedTunIPv4(dev);if e!=nil||actual.String()!=lease{return fmt.Errorf("test TUN /32: %v %v",actual,e)}
 cidrs,e:=rootjournal.MergeCountryDirectCIDRs(nil,string(snapshot),peer);if e!=nil{return e}
 if len(cidrs)<100{return fmt.Errorf("CN snapshot too small")}
 cn,e:=netip.ParsePrefix(cidrs[0]);if e!=nil{return e}
 path:=filepath.Join(dir,"route.json")
 group:=[]int{uid,bypass};sort.Ints(group)
 exclusions:=[]int{own%100000,manager%100000,bypass%100000};sort.Ints(exclusions)
 if uid==bypass||!rootjournal.ValidAllAppExclusions(exclusions){return fmt.Errorf("invalid fixture UIDs")}
 for _,id:=range []int{uid,bypass,own,manager,0}{
  if e=b90UsesTun(id,dest,dev,false);e!=nil{return fmt.Errorf("baseline: %w",e)}
 }
 fmt.Println("B90_ROUTE_BASELINE_PASS")
 for _,mode:=range []string{"single","group","all"}{
  var owner b90Stop
  switch mode{
  case "single":
   owner,e=rootjournal.New(b90IP,path,rootjournal.Plan{UID:uid,Tun:dev,Lease:lease,ServerIP:peer,DirectCIDRs:cidrs,Underlay:scope.InterfaceName,NetworkHandle:scope.NetworkHandle,IfIndex:scope.IfIndex},androidDNSIPBatch)
  case "group":
   owner,e=rootjournal.NewGroup(b90IP,path,rootjournal.GroupPlan{UIDs:group,Tun:dev,Lease:lease,ServerIP:peer,DirectCIDRs:cidrs,Underlay:scope.InterfaceName,NetworkHandle:scope.NetworkHandle,IfIndex:scope.IfIndex},androidDNSIPBatch)
  case "all":
   owner,e=rootjournal.NewAllApps(b90IP,path,rootjournal.AllAppPlan{ExcludedAppIDs:exclusions,Tun:dev,Lease:lease,ServerIP:peer,DirectCIDRs:cidrs,Underlay:scope.InterfaceName,NetworkHandle:scope.NetworkHandle,IfIndex:scope.IfIndex},androidDNSIPBatch)
  }
  if e!=nil{return fmt.Errorf("%s owner: %w",mode,e)}
  check:=func()error{
   for _,c:=range []struct{id int; dest string; tun bool}{
    {uid,dest,true},{bypass,dest,mode=="group"},{own,dest,false},{manager,dest,false},{0,dest,false},
    {uid,peer,false},{uid,cn.Addr().String(),false},
   }{if e:=b90UsesTun(c.id,c.dest,dev,c.tun);e!=nil{return e}}
   return b90Packet(tun,uid)
  }()
  if e=owner.Stop();e!=nil{return fmt.Errorf("%s Stop: %w",mode,e)}
  for _,id:=range []int{uid,bypass,own,manager,0}{
   if e=b90UsesTun(id,dest,dev,false);e!=nil{return fmt.Errorf("%s restored lookup: %w",mode,e)}
  }
  fmt.Printf("B90_ROUTE_%s_STOP_PASS\n",strings.ToUpper(mode))
  if check!=nil{return fmt.Errorf("%s kernel/packet: %w",mode,check)}
  fmt.Printf("B90_ROUTE_%s_UID_PACKET_CN_PASS prefixes=%d\n",strings.ToUpper(mode),len(cidrs))
 }
 return nil
}
func b90DNS(scope dnsnative.PhysicalScope)error{
 upstream:=netip.MustParseAddr("10.0.2.2")
 dial,e:=dnsnative.NewAndroidPhysicalDNSDialerWithUpstream(scope,upstream);if e!=nil{return e}
 for _,name:=range []string{"udp.wbd-b90.test","tc.wbd-b90.test"}{
  ctx,cancel:=context.WithTimeout(context.Background(),6*time.Second)
  ip,e:=dnsnative.ResolveBootstrapIPv4WithUpstream(ctx,name,dial,upstream);cancel()
  if e!=nil||ip.String()!="192.0.2.55"{return fmt.Errorf("%s physical DNS: %v %v",name,ip,e)}
  fmt.Printf("B90_PHYSICAL_DNS_%s_PASS\n",strings.ToUpper(strings.Split(name,".")[0]))
 }
 return nil
}
func RunAndroidSpecialtyCI(a []string)int{
 if len(a)!=11||os.Geteuid()!=0{fmt.Println("B90_INPUT_FAIL");return 2}
 handle,e:=strconv.ParseUint(a[1],10,64);if e!=nil{return 2}
 index,e:=strconv.Atoi(a[3]);if e!=nil{return 2}
 mtu,e:=strconv.Atoi(a[4]);if e!=nil{return 2}
 local,e:=netip.ParseAddr(a[5]);if e!=nil{return 2}
 scope:=dnsnative.PhysicalScope{NetworkHandle:handle,InterfaceName:a[2],IfIndex:index,MTU:mtu,LocalIPv4:local}
 switch a[0]{
 case "dns":
  if e=b90DNS(scope);e!=nil{fmt.Println("B90_DNS_FAIL",e);return 1}
 case "routes":
  ids:=make([]int,4);for i:=range ids{ids[i],e=strconv.Atoi(a[6+i]);if e!=nil||ids[i]<10000{return 2}}
  raw,e:=os.ReadFile(a[10]);if e!=nil{fmt.Println("B90_CN_INPUT_FAIL",e);return 1}
  if e=b90Routes(scope,ids[0],ids[1],ids[2],ids[3],raw);e!=nil{fmt.Println("B90_ROUTES_FAIL",e);return 1}
  if _,e=b90IP("link","show","dev","wbdb90");e==nil{fmt.Println("B90_TUN_CLOSE_FAIL");return 1}
  fmt.Println("B90_TUN_CLOSE_PASS")
 default:return 2
 }
 return 0
}
