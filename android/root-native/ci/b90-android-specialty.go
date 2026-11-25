//go:build android && cgo && wbd_v4_embedded_go && wbd_android_specialty_test

// CI only: calls original Go TUN, rootjournal and Bionic DNS. Test /32 is
// an isolated kernel component input, not a fabricated server admission.
package v4productcli

import (
 "bytes"
 "context"
 "encoding/binary"
 "errors"
 "fmt"
 "net"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "sort"
 "strconv"
 "strings"
 "syscall"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
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
func b91Instrument(ctx context.Context,uid int,extras ...string)error{
 args:=[]string{"instrument","-w","-r"}
 args=append(args,extras...)
 args=append(args,"org.wbdnext.testtraffic/.TrafficInstrumentation")
 out,e:=exec.CommandContext(ctx,"/system/bin/am",args...).CombinedOutput()
 if e!=nil||!strings.Contains(string(out),"INSTRUMENTATION_CODE: -1")||!strings.Contains(string(out),"foreground=1")||
   !(strings.Contains(string(out),fmt.Sprintf("uid_probe_sent=%d",uid))||strings.Contains(string(out),fmt.Sprintf("dns_probe_uid=%d ",uid))||strings.Contains(string(out),fmt.Sprintf("uid_probe_rejected=%d errno=EMSGSIZE",uid))){
  return fmt.Errorf("ordinary App instrumentation: %v: %s",e,out)
 }
 return nil
}
// The reply is only an isolated TUN/kernel fixture, never a WBD M4 peer.
func b91UDPReply(ip []byte,h int,payload []byte)[]byte{
 n:=20+8+len(payload)
 out:=make([]byte,n)
 out[0]=0x45;out[8]=64;out[9]=17
 binary.BigEndian.PutUint16(out[2:4],uint16(n))
 copy(out[12:16],ip[16:20]);copy(out[16:20],ip[12:16])
 copy(out[20:22],ip[h+2:h+4]);copy(out[22:24],ip[h:h+2])
 binary.BigEndian.PutUint16(out[24:26],uint16(8+len(payload)))
 copy(out[28:],payload)
 var sum uint32
 for i:=0;i<20;i+=2{sum+=uint32(binary.BigEndian.Uint16(out[i:i+2]))}
 for sum>>16!=0{sum=(sum&65535)+(sum>>16)}
 binary.BigEndian.PutUint16(out[10:12],^uint16(sum))
 // IPv4 UDP allows checksum zero; the IP header checksum is real.
 return out
}
func b91ServeTUN(ctx context.Context,tun *ownedTun,dest [4]byte,port uint16,
 reply func([]byte)([]byte,bool))error{
 // Cache the FD before setting O_NONBLOCK: os.File.Fd may restore blocking
 // mode on a Go pollable file. Do not call Fd again inside the loop.
 fd:=int(tun.f.Fd())
 if e:=syscall.SetNonblock(fd,true);e!=nil{return e}
 buf:=make([]byte,2048)
 for ctx.Err()==nil{
  n,e:=syscall.Read(fd,buf)
  if e==syscall.EAGAIN||e==syscall.EINTR{time.Sleep(10*time.Millisecond);continue}
  if e!=nil{return e}
  if n<28||buf[0]>>4!=4||buf[9]!=17{continue}
  h:=int(buf[0]&15)*4
  if h<20||n<h+8||!bytes.Equal(buf[16:20],dest[:])||binary.BigEndian.Uint16(buf[h+2:h+4])!=port{continue}
  size:=int(binary.BigEndian.Uint16(buf[h+4:h+6]))
  if size<8||h+size>n{continue}
  payload,ok:=reply(buf[h+8:h+size]);if !ok{continue}
  packet:=b91UDPReply(buf[:n],h,payload)
  written,e:=syscall.Write(fd,packet)
  if e!=nil||written!=len(packet){return fmt.Errorf("real TUN reply: %d/%d %v",written,len(packet),e)}
 }
 return nil
}
func b94PacketOnce(tun *ownedTun,uid int,probe,payload string)error{
 ctx,cancel:=context.WithTimeout(context.Background(),15*time.Second);defer cancel()
 done:=make(chan error,1)
 seen:=make(chan struct{},1)
 go func(){done<-b91ServeTUN(ctx,tun,[4]byte{192,0,2,1},43999,func(q []byte)([]byte,bool){
  if !bytes.Equal(q,[]byte(payload)){return nil,false}
  select{case seen<-struct{}{}:default:}
  return q,true
 })}()
 fmt.Println("B94_UID_ECHO_BEGIN",probe)
 e:=b91Instrument(ctx,uid,"-e","uid_probe",probe)
 fmt.Println("B93_UID_INSTRUMENT_END",e)
 cancel()
 e=errors.Join(e,<-done)
 fmt.Println("B93_UID_TUN_READER_JOINED")
 if len(seen)!=1{return errors.Join(e,fmt.Errorf("ordinary UID datagram absent on original TUN"))}
 if e==nil{fmt.Println("B94_UID_SOCKET_ROUNDTRIP_PASS",probe)}
 return e
}
func b90Packet(tun *ownedTun,uid int)error{
 var ret error
 for i:=1;i<=2;i++{
  fmt.Println("B95_UID_ECHO_TRIAL",i)
  a:=b94PacketOnce(tun,uid,"echo","WBD_B90_UID")
  b:=b94PacketOnce(tun,uid,"echo4","WBD_B94_UID4")
  ret=errors.Join(ret,a,b)
 }
 return ret
}
func b94BaselineUID(uid int)error{
 var ret error
 for _,probe:=range []string{"baseline","baseline4"}{
  ctx,cancel:=context.WithTimeout(context.Background(),10*time.Second)
  e:=b91Instrument(ctx,uid,"-e","uid_probe",probe);cancel()
  if e==nil{fmt.Println("B94_UID_PHYSICAL_BASELINE_PASS",probe)}else{fmt.Println("B94_UID_PHYSICAL_BASELINE_FAIL",probe,e)}
  ret=errors.Join(ret,e)
 }
 return ret
}
type b90Stop interface{Stop()error}
func b90Routes(scope dnsnative.PhysicalScope,uid,bypass,own,manager int,snapshot []byte,mode string) (ret error){
 const dev="wbdb90"
 const lease="198.18.0.1/32"
 const peer="10.0.2.2"
 const dest="192.0.2.1"
 if _,e:=b90IP("link","show","dev",dev);e==nil{return fmt.Errorf("test TUN exists")}
 dir,e:=os.MkdirTemp("/data/local/tmp","wbd-b90-");if e!=nil{return e}
 defer func(){if ret==nil{_ = os.RemoveAll(dir)}}()
 tun,e:=openTun(dev,lease,1389);if e!=nil{return e}
 defer func(){ret=errors.Join(ret,tun.Close())}()
 actual,e:=readOwnedTunIPv4(dev);if e!=nil||actual.String()!=lease{return fmt.Errorf("test TUN /32: %v %v",actual,e)}
 cidrs,e:=rootjournal.MergeCountryDirectCIDRs(nil,string(snapshot),peer);if e!=nil{return e}
 if len(cidrs)<100{return fmt.Errorf("CN snapshot too small")}
 cn,e:=netip.ParsePrefix(cidrs[0]);if e!=nil{return e}
 path:=filepath.Join(dir,"route-journal.json")
 group:=[]int{uid,bypass};sort.Ints(group)
 exclusions:=[]int{own%100000,manager%100000,bypass%100000};sort.Ints(exclusions)
 if uid==bypass||!rootjournal.ValidAllAppExclusions(exclusions){return fmt.Errorf("invalid fixture UIDs")}
 for _,id:=range []int{uid,bypass,own,manager,0}{
  if e=b90UsesTun(id,dest,dev,false);e!=nil{return fmt.Errorf("baseline: %w",e)}
 }
 fmt.Println("B90_ROUTE_BASELINE_PASS")
 baseline:=b94BaselineUID(uid)
 for _,mode:=range []string{mode}{
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
  fmt.Printf("B93_UID_FIB_INSTALLED mode=%s prefixes=%d\n",mode,len(cidrs))
  // Register exact Stop before any instrumentation or route readback.
  defer func(){ret=errors.Join(ret,owner.Stop())}()
  check:=func()error{
   for _,c:=range []struct{id int; dest string; tun bool}{
    {uid,dest,true},{bypass,dest,mode=="group"},{own,dest,false},{manager,dest,false},{0,dest,false},
    {uid,peer,false},{uid,cn.Addr().String(),false},
   }{if e:=b90UsesTun(c.id,c.dest,dev,c.tun);e!=nil{return e}}
   fmt.Println("B93_UID_ROUTE_GET_PASS",mode)
   return b90Packet(tun,uid)
  }()
  fmt.Println("B93_UID_STOP_BEGIN",mode)
  if e=owner.Stop();e!=nil{return fmt.Errorf("%s Stop: %w",mode,e)}
  for _,id:=range []int{uid,bypass,own,manager,0}{
   if e=b90UsesTun(id,dest,dev,false);e!=nil{return fmt.Errorf("%s restored lookup: %w",mode,e)}
  }
  fmt.Printf("B90_ROUTE_%s_STOP_PASS\n",strings.ToUpper(mode))
  fmt.Println("B95_UID_RESTORED_PHYSICAL_BEGIN",mode)
  restored:=b94BaselineUID(uid)
  if check!=nil||baseline!=nil||restored!=nil{return fmt.Errorf("%s kernel/packet: %w",mode,errors.Join(check,baseline,restored))}
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
 if strings.HasPrefix(a[0],"mtu-"){
  spec:=strings.TrimPrefix(a[0],"mtu-")
  cut:=strings.LastIndexByte(spec,'-');if cut<0{return 2}
  mode,setting:=spec[:cut],spec[cut+1:]
  outer,cap:=0,uint16(0)
  switch setting{case "1280":outer=1280;case "1460":outer=1460;case "1500":outer=1500;case "peer1200":outer=1500;cap=1200;default:return 2}
  uid,e:=strconv.Atoi(a[6]);if e!=nil{return 2}
  if e=b91Native(scope,uid,mode,outer,cap,true);e!=nil{fmt.Println("B98_MTU_FAIL",a[0],e);return 1}
  fmt.Println("B98_MTU_SCENE_PASS",a[0])
  return 0
 }
 switch a[0]{
 case "dns":
  if e=b90DNS(scope);e!=nil{fmt.Println("B90_DNS_FAIL",e);return 1}
 case "route-single","route-group","route-all":
  ids:=make([]int,4);for i:=range ids{ids[i],e=strconv.Atoi(a[6+i]);if e!=nil||ids[i]<10000{return 2}}
  raw,e:=os.ReadFile(a[10]);if e!=nil{fmt.Println("B90_CN_INPUT_FAIL",e);return 1}
  if e=b90Routes(scope,ids[0],ids[1],ids[2],ids[3],raw,strings.TrimPrefix(a[0],"route-"));e!=nil{fmt.Println("B90_ROUTES_FAIL",e);return 1}
  if _,e=b90IP("link","show","dev","wbdb90");e==nil{fmt.Println("B90_TUN_CLOSE_FAIL");return 1}
  fmt.Println("B90_TUN_CLOSE_PASS")
 case "system-physical","system-physical-tc","system-tunnel","system-cn":
  uid,e:=strconv.Atoi(a[6]);if e!=nil{return 2}
  if e=b91SystemDNS(scope,uid,a[0]);e!=nil{fmt.Println("B91_SYSTEM_DNS_FAIL",e);return 1}
 case "normal","fec-fixed","fec-auto","game2","game2-fixed","game4","game4-fixed":
  uid,e:=strconv.Atoi(a[6]);if e!=nil{return 2}
  if e=b91Native(scope,uid,a[0],1460,0,false);e!=nil{fmt.Println("B91_NATIVE_FAIL",e);return 1}
 default:return 2
 }
 return 0
}

// The actual system DNS ingress/relay component runs independently of the
// remote WBD path. A local test /32 is never called an authenticated lease.
func b91DNSAnswer(q []byte)([]byte,bool){
 if len(q)<17||binary.BigEndian.Uint16(q[4:6])!=1{return nil,false}
 i:=12;var labels []string
 for i<len(q)&&q[i]!=0{
  n:=int(q[i]);i++;if n>63||i+n>len(q){return nil,false}
  labels=append(labels,string(q[i:i+n]));i+=n
 }
 if i+5>len(q){return nil,false}
 name:=strings.Join(labels,".")
 if name!="tunnel.wbd-b91.test"&&name!="noncn.wbd-b91.test"{return nil,false}
 a:=binary.BigEndian.Uint16(q[i+1:i+3])==1
 out:=append([]byte(nil),q[:i+5]...)
 binary.BigEndian.PutUint16(out[2:4],0x8180)
 for j:=6;j<12;j++{out[j]=0}
 if a{out[7]=1;out=append(out,0xc0,0x0c,0,1,0,1,0,0,0,60,0,4,192,0,2,56)}
 return out,true
}
func b91SystemDNS(scope dnsnative.PhysicalScope,uid int,mode string)(ret error){
 const dev="wbdb91dns"
 const lease="198.18.0.2/32"
 dir,e:=os.MkdirTemp("/data/local/tmp","wbd-b91-dns-");if e!=nil{return e}
 defer func(){if ret==nil{_ = os.RemoveAll(dir)}}()
 tun,e:=openTun(dev,lease,1389);if e!=nil{return e}
 defer func(){ret=errors.Join(ret,tun.Close())}()
 owner,e:=rootjournal.New(b90IP,filepath.Join(dir,"route-journal.json"),
  rootjournal.Plan{UID:uid,Tun:dev,Lease:lease,ServerIP:"10.0.2.2",Underlay:scope.InterfaceName,NetworkHandle:scope.NetworkHandle,IfIndex:scope.IfIndex},androidDNSIPBatch)
 if e!=nil{return e}
 defer func(){ret=errors.Join(ret,owner.Stop())}()
 c:=config{androidRouteUID:uid,androidNetworkHandle:scope.NetworkHandle,
  androidAppTCPDNS:true,androidSystemDNS:true,
  androidPhysicalDNSUpstream:netip.MustParseAddr("10.0.2.2"),
  androidTunnelDNSUpstream:netip.MustParseAddr("192.0.2.53")}
 c.androidPhysicalDNS=mode=="system-physical"||mode=="system-physical-tc"
 c.androidTunnelDNS=mode=="system-tunnel"
 c.androidCNDNSSplit=mode=="system-cn"
 if c.androidPhysicalDNS||c.androidCNDNSSplit{
  c.androidPhysicalDNSDial,e=dnsnative.NewAndroidPhysicalDNSDialerWithUpstream(scope,c.androidPhysicalDNSUpstream)
  if e!=nil{return e}
 }
 if c.androidCNDNSSplit{
  c.androidCNSnapshot,e=dnsnative.LoadCN([]byte("domain:cn.wbd-b91.test\n"))
  if e!=nil{return e}
 }
 stop,e:=startAndroidAppTCPDNS(c,tun,netip.MustParsePrefix(lease),b90IP,owner.Stop)
 if e!=nil{return e}
 fmt.Println("B95_SYSTEM_DNS_OWNER_READY",mode)
 defer func(){e:=stop();ret=errors.Join(ret,e);if e==nil{fmt.Println("B91_SYSTEM_DNS_STOP_PASS",mode)}}()
 ctx,cancel:=context.WithTimeout(context.Background(),25*time.Second)
 defer cancel()
 var done chan error
 if c.androidTunnelDNS||c.androidCNDNSSplit{
  done=make(chan error,1)
  go func(){done<-b91ServeTUN(ctx,tun,[4]byte{192,0,2,53},53,b91DNSAnswer)}()
  defer func(){cancel();ret=errors.Join(ret,<-done)}()
 }
 query:=func(name,expected string)error{
  qctx,qcancel:=context.WithTimeout(ctx,10*time.Second);defer qcancel()
  return b91Instrument(qctx,uid,"-e","dns_probe","system","-e","network_handle",strconv.FormatUint(scope.NetworkHandle,10),"-e","dns_name",name,"-e","expected_ip",expected)
 }
 if c.androidPhysicalDNS{
  name:="system.wbd-b91.test";if mode=="system-physical-tc"{name="tc.wbd-b90.test"}
  if e=query(name,"192.0.2.55");e!=nil{return e}
 }
 if c.androidTunnelDNS{if e=query("tunnel.wbd-b91.test","192.0.2.56");e!=nil{return e}}
 if c.androidCNDNSSplit{
  if e=query("cn.wbd-b91.test","192.0.2.55");e!=nil{return e}
  if e=query("noncn.wbd-b91.test","192.0.2.56");e!=nil{return e}
 }
 fmt.Println("B91_SYSTEM_DNS_QUERY_PASS",mode)
 return nil
}

// Exact production openTun, lease/MTU callbacks, original UID route owner,
// and original product Connect/Close. Only the cold wire is in-process.
func b91Native(scope dnsnative.PhysicalScope,uid int,mode string,outer int,peerCap uint16,boundary bool)(ret error){
 const dev="wbdb91m4"
 c:=config{role:"client",rawInterface:scope.InterfaceName,localIP:scope.LocalIPv4,
  peerIP:netip.MustParseAddr("10.0.2.2"),peerPort:443,outerMTU:outer,recordLimit:0,
  androidNetworkHandle:scope.NetworkHandle,androidPhysicalMTU:uint32(scope.MTU),androidRouteUID:uid,
  fecMode:realityfront.FecV2Off,disableOuterRepair:true,androidNativeHealthSeconds:15,
  androidPhysicalDNSUpstream:netip.MustParseAddr("223.5.5.5")}
 switch mode{
 case "normal":
 case "fec-fixed":c.fecMode=realityfront.FecV2Fixed;c.fecProfile=realityfront.FecV2Profile(6)
 case "fec-auto":c.fecMode=realityfront.FecV2Auto
 case "game2","game2-fixed":c.gameLanes=2;c.gameFecEnabled=mode=="game2-fixed";c.gameFecProfile=6
 case "game4","game4-fixed":c.gameLanes=4;c.gameFecEnabled=mode=="game4-fixed";c.gameFecProfile=6
 default:return fmt.Errorf("invalid mode %s",mode)
 }
 // Identical pre-SYN initialization to the original CLI Run. No default
 // MSS or fabricated record cap; both fixture endpoints use this budget.
 cold,e:=realityfront.V4DeriveColdMTUBudget(realityfront.V4ColdMTUBudgetInput{
  ConfiguredOuterIPMTU:uint32(c.outerMTU),PhysicalOuterIPMTU:uint32(scope.MTU),
  IPv4HeaderBytes:20,TCPDataHeaderBytes:20,Mode:0})
 if e!=nil{return e}
 mss:=cold.LocalSYNAdvertisedMSS
 if mss<536||mss>1460{return fmt.Errorf("invalid original MSS %d",mss)}
 if e=faketcp.SetPublicV4AdvertisedMSS(uint16(mss));e!=nil{return e}
 c.recordLimit,c.innerMTU,e=deriveMTUBudget(c.outerMTU,scope.MTU,uint16(mss),0,c.fecMode,c.gameLanes!=0,c.gameFecEnabled)
 if e!=nil{return e}
 serverLimit:=c.recordLimit
 if peerCap!=0&&peerCap<serverLimit{serverLimit=peerCap}
 _,expectedMTU,e:=deriveMTUBudget(c.outerMTU,scope.MTU,uint16(mss),serverLimit,c.fecMode,c.gameLanes!=0,c.gameFecEnabled)
 if e!=nil{return e}
 fmt.Printf("B93_ORIGINAL_COLD_MTU_PASS mode=%s mss=%d record=%d inner=%d\n",mode,mss,c.recordLimit,c.innerMTU)
 if boundary{fmt.Printf("B98_MTU_EXPECTED mode=%s configured=%d physical=%d client_record=%d server_record=%d expected_tun=%d\n",mode,outer,scope.MTU,c.recordLimit,serverLimit,expectedMTU)}
 tun,e:=openTun(dev,"198.18.0.3/32",c.innerMTU);if e!=nil{return e}
 defer func(){closeErr:=tun.Close();ret=errors.Join(ret,closeErr)
  if _,e:=net.InterfaceByName(dev);e==nil{ret=errors.Join(ret,fmt.Errorf("native TUN still exists"))}else if closeErr==nil{fmt.Println("B91_NATIVE_TUN_CLOSE_PASS",mode)}
 }()
 normal:=realityfront.V4LinuxClientProductConfig{
  NetworkInterface:c.rawInterface,NetworkIfIndex:uint32(scope.IfIndex),AndroidPhysicalNetworkHandle:c.androidNetworkHandle,AndroidPhysicalMTU:c.androidPhysicalMTU,
  Tun:tun.f,TunName:dev,CleanupOwnedNetwork:func()error{return nil},ConfigureTunnelMTU:configureTunnelMTU(c,tun),ConfigureLeaseIPv4:configureAuthenticatedClientIPv4(tun),
  FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:true,OuterIPMTU:outer,HealthKeepaliveSeconds:15,HealthDeadAfterSeconds:90}
 game:=realityfront.V4AndroidGameConfig{Lanes:c.gameLanes,GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
  OuterIPMTU:outer,DisableOuterRepair:true,NetworkInterface:c.rawInterface,NetworkIfIndex:uint32(scope.IfIndex),
  AndroidPhysicalNetworkHandle:c.androidNetworkHandle,AndroidPhysicalMTU:c.androidPhysicalMTU,
  Tun:tun.f,TunName:dev,ConfigureTunnelMTU:configureTunnelMTU(c,tun),ConfigureLeaseIPv4:configureAuthenticatedClientIPv4(tun),
  HealthSeconds:15,PhysicalDNSUpstream:c.androidPhysicalDNSUpstream}
 ctx,cancel:=context.WithTimeout(context.Background(),75*time.Second);defer cancel()
 route:=func(lease string)(func()error,error){
  if boundary{
   actual,e:=readOwnedTunMTU(tun.name)
   if e!=nil||actual!=expectedMTU||tun.mtu!=expectedMTU{return nil,fmt.Errorf("authenticated TUN MTU actual=%d owner=%d want=%d: %v",actual,tun.mtu,expectedMTU,e)}
   fmt.Printf("B98_MTU_OS_READBACK_PASS mode=%s actual=%d\n",mode,actual)
  }
  return androidRootRouteAfterNative(c,tun,lease)
 }
 send:=func(probe string)error{
  qctx,qcancel:=context.WithTimeout(ctx,12*time.Second);defer qcancel()
  if strings.HasPrefix(probe,"mtu-"){
   size:=tun.mtu
   if probe=="mtu-minus"{size--}
   if probe=="mtu-over"{size++}
   e:=b91Instrument(qctx,uid,"-e","uid_probe",probe,"-e","ip_size",strconv.Itoa(size))
   if e==nil{fmt.Printf("B98_MTU_APP_RESULT mode=%s probe=%s ip_size=%d\n",mode,probe,size)}
   return e
  }
  return b91Instrument(qctx,uid,"-e","uid_probe",probe)
 }
 return realityfront.B91RunNativeCI(ctx,scope.LocalIPv4,c.peerIP,normal,game,mode,c.recordLimit,serverLimit,boundary,route,send)
}
