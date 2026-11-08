//go:build windows

package windowsclient

// H1369: two simultaneous, distinct, genuine signed Wintun devices.
// This is an original native Windows driver/OS app isolation witness,
// not a forged TLS/Rust M4 ownership or a product authentication pass.
import (
 "context"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "errors"
 "net"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "testing"
 "time"
)

type p028DualWintun struct {
 adapter *TUN
 ring *N4OriginalKernelPacketLease
 identity N4UnifiedIdentity
 local,remote [4]byte
 socket *net.UDPConn
 port uint16
}

func TestM0PLAN028TwoSignedWindowsWintunKernelSocketIsolation(t *testing.T) {
 if os.Getenv("WBD_M0_PLAN028_TWO_WINTUN")!="1" || os.Getenv("GITHUB_ACTIONS")!="true" {
  t.Skip("NOT_RUN: requires real signed Windows Wintun, GitHub Windows runner and ownership")
 }
 receipt:=map[string]any{
  "source_sha":os.Getenv("GITHUB_SHA"),
  "classification":"NOT_RUN",
  "platform":"Windows real signed Wintun / Win32 UDP sockets",
  "original_tls_rust_authentication":"NOT_RUN",
  "original_npcap_outer_wire":"NOT_RUN",
  "single_shared_product_server443":"NOT_RUN",
  "two_original_product_accounts":"NOT_RUN",
  "original_windows_global_routes_wfp":"NOT_RUN",
 }
 defer func(){
  path:=os.Getenv("WBD_M0_PLAN028_TWO_WINTUN_REPORT")
  if path=="" {t.Error("report path required");return}
  b,err:=json.MarshalIndent(receipt,"","  ");if err!=nil{t.Error(err);return}
  if err=os.MkdirAll(filepath.Dir(path),0700);err!=nil{t.Error(err);return}
  if err=os.WriteFile(path,append(b,'\n'),0600);err!=nil{t.Error(err)}
 }()
 if receipt["source_sha"]==""{t.Fatal("unlocked original source")}
 ctx,cancel:=context.WithTimeout(context.Background(),70*time.Second)
 defer cancel()
 var salt [8]byte
 if _,e:=rand.Read(salt[:]);e!=nil{t.Fatal(e)}
 tag:=hex.EncodeToString(salt[:])
 local:=[][4]byte{{198,18,233,11},{198,18,233,22}}
 remote:=[][4]byte{{198,18,233,101},{198,18,233,102}}
 clients:=make([]*p028DualWintun,0,2)
 for i:=0;i<2;i++{
  j:=i
  dev,e:=OpenTUN("WBD-P028-2NATIVE-"+strconv.Itoa(i)+"-"+tag)
  if e!=nil{t.Fatalf("signed Windows Wintun device%d unsupported: %v",i,e)}
  t.Cleanup(func(){if e:=dev.Close();e!=nil{t.Errorf("device%d native Close: %v",j,e)}})
  actual,e:=dev.NativeIdentity(ctx)
  if e!=nil||!actual.CreatedByProcess||actual.Index==0||actual.LUID==0{
   t.Fatalf("actual signed device%d GUID/LUID/ifindex: %+v %v",i,actual,e)
  }
  var install,gen [16]byte
  if _,e=rand.Read(install[:]);e!=nil{t.Fatal(e)}
  if _,e=rand.Read(gen[:]);e!=nil{t.Fatal(e)}
  guid,e:=n4NativeInterfaceGUID(actual.Index);if e!=nil{t.Fatal(e)}
  id:=N4UnifiedIdentity{Installation:install,Generation:gen,
   WintunLUID:actual.LUID,WintunIndex:actual.Index,
   WintunGUID:guid.String(),AdapterAlias:dev.Name()}
  pnp,e:=n4ProbeOriginalWintunPnP(ctx,id)
  if e!=nil{t.Fatalf("device%d actual PnP identity: %v",i,e)}
  id.PnPInstanceSHA256=pnp.InstanceSHA256
  if !n4ValidPinnedPnPHash(id.PnPInstanceSHA256){t.Fatal("invalid signed original native PnP pin")}
  ring,e:=n4CreateOriginalKernelPacketLease(ctx,dev,id)
  if e!=nil{t.Fatalf("device%d native ring original lease: %v",i,e)}
  t.Cleanup(func(){
   cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done()
   if e:=ring.Stop(cl);e!=nil{t.Errorf("device%d native ring Stop: %v",j,e)}
  })
  sourceIP:=net.IP(local[i][:]).String()
  foreignIP:=net.IP(remote[i][:]).String()
  lease:=N4NativeLeaseIntent{InterfaceIndex:actual.Index,
   Prefix:netip.MustParsePrefix(sourceIP+"/32")}
  writer:=N4WindowsLeaseWriter{Guard:&n4FakeGuard{durable:true,active:true},
   Adapter:dev,Snapshot:N4WindowsAddressSnapshot{}}
  token,e:=writer.Create(ctx,lease)
  if e!=nil{t.Fatalf("device%d Windows IP Helper test-only /32: %v",i,e)}
  t.Cleanup(func(){
   cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done()
   if e:=writer.DeleteConfirmed(cl,token);e!=nil{t.Errorf("device%d exact IPv4 cleanup: %v",j,e)}
  })
  for {
   osIP,found,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
   if e!=nil{t.Fatal(e)}
   if found&&N4NativeLeaseDADGate(osIP,lease)==nil{break}
   if ctx.Err()!=nil{t.Fatalf("device%d real IPv4 DAD readback: %v",i,ctx.Err())}
   time.Sleep(100*time.Millisecond)
  }
  socket,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:net.IP(local[i][:]),Port:0})
  if e!=nil{t.Fatalf("device%d bind Windows real UDP socket: %v",i,e)}
  t.Cleanup(func(){if e:=socket.Close();e!=nil{t.Errorf("device%d socket close: %v",j,e)}})
  port:=uint16(socket.LocalAddr().(*net.UDPAddr).Port)
  rule:="WBD-P028-TWO-WINTUN-"+strconv.Itoa(i)+"-"+tag
  out,e:=exec.CommandContext(ctx,"netsh","advfirewall","firewall","add","rule",
   "name="+rule,"dir=in","action=allow","enable=yes","protocol=UDP",
   "localip="+sourceIP,"remoteip="+foreignIP,
   "localport="+strconv.Itoa(int(port)),"profile=any").CombinedOutput()
  if e!=nil{t.Fatalf("device%d narrow Defender UDP grant: %v %q",i,e,string(out))}
  t.Cleanup(func(){
   cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done()
   out,e:=exec.CommandContext(cl,"netsh","advfirewall","firewall","delete","rule","name="+rule).CombinedOutput()
   if e!=nil{t.Errorf("device%d exact Defender rule cleanup: %v %q",j,e,string(out))}
   verify,_:=exec.CommandContext(cl,"netsh","advfirewall","firewall","show","rule","name="+rule).CombinedOutput()
   if containsRuleName(string(verify),rule){t.Errorf("device%d test-only firewall rule survived cleanup",j)}
  })
  clients=append(clients,&p028DualWintun{
   adapter:dev,ring:ring,identity:id,local:local[i],remote:remote[i],
   socket:socket,port:port})
 }
 a,b:=clients[0],clients[1]
 if a.identity.WintunIndex==b.identity.WintunIndex||
  a.identity.WintunLUID==b.identity.WintunLUID||
  a.identity.WintunGUID==b.identity.WintunGUID||
  a.identity.AdapterAlias==b.identity.AdapterAlias {
  t.Fatal("two claimed Windows Wintun devices have overlapping OS native identities")
 }
 if _,e:=n4CreateOriginalKernelPacketLease(ctx,b.adapter,a.identity);e==nil{
  t.Fatal("foreign A generation adopted independent live B ring")
 }
 deliver:=func(c *p028DualWintun,s string){
  t.Helper()
  pkt:=n4MakeKernelUDP(c.remote,c.local,41161,c.port,[]byte(s))
  n,e:=c.ring.n4DeliverAuthenticatedIPv4(ctx,pkt)
  if e!=nil||n!=len(pkt){t.Fatalf("real WintunSendPacket native copy: %d %v",n,e)}
  if e:=c.socket.SetReadDeadline(time.Now().Add(5*time.Second));e!=nil{t.Fatal(e)}
  buf:=make([]byte,2048)
  count,from,e:=c.socket.ReadFromUDP(buf)
  if e!=nil{t.Fatalf("actual Windows UDP application lost signed Wintun ingress: %v",e)}
  if count!=len(s)||string(buf[:count])!=s||from==nil||!from.IP.Equal(net.IP(c.remote[:])){
   t.Fatalf("Windows true UDP app payload/source mismatch count=%d peer=%v",count,from)
  }
 }
 deliver(a,"H1369-A-original-kernel-app")
 deliver(b,"H1369-B-concurrent-original-kernel-app")
 if e:=a.ring.Stop(ctx);e!=nil{t.Fatalf("A exact Stop: %v",e)}
 if _,e:=a.ring.n4DeliverAuthenticatedIPv4(ctx,
  n4MakeKernelUDP(a.remote,a.local,41161,a.port,[]byte("A-stale")));
  !errors.Is(e,ErrN4NativeGuard){
  t.Fatalf("stopped A still wrote real Windows native ring: %v",e)
 }
 deliver(b,"H1369-B-remains-live-after-A-Stop")
 route:=NativeRouteKey{
  Prefix:netip.MustParsePrefix("198.18.233.102/32"),
  Interface:b.identity.WintunIndex,
  NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 backend:=N4WindowsRouteBackend{}
 present,_,e:=backend.Lookup(ctx,route)
 if e!=nil||present{t.Fatalf("B reverse real /32 host route preflight: %v %v",present,e)}
 if e:=backend.CreateIfAbsent(ctx,route);e!=nil{t.Fatalf("B reverse native route create: %v",e)}
 routeLive:=true
 t.Cleanup(func(){
  if !routeLive{return}
  cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done()
  if e:=backend.RemoveOwned(cl,route);e!=nil{t.Errorf("B reverse route exact cleanup: %v",e)}
 })
 if has,exact,e:=backend.Lookup(ctx,route);e!=nil||!has||!exact{
  t.Fatalf("B original Windows IP Helper route OS readback %v %v %v",has,exact,e)
 }
 reverse:=[]byte("H1369-B-kernel-reverse-after-A-Stop")
 n,e:=b.socket.WriteToUDP(reverse,&net.UDPAddr{IP:net.IP(b.remote[:]),Port:41162})
 if e!=nil||n!=len(reverse){t.Fatalf("real B Windows UDP socket reverse: %d %v",n,e)}
 observed:=false
 buffer:=make([]byte,65535)
 for deadline:=time.Now().Add(5*time.Second);time.Now().Before(deadline);{
  size,e:=b.ring.n4ReceiveReadyIPv4(ctx,buffer)
  if errors.Is(e,ErrN4NativeNoPacket){time.Sleep(10*time.Millisecond);continue}
  if e!=nil{t.Fatalf("live B native Wintun reverse ring read: %v",e)}
  if size<28||buffer[0]>>4!=4||buffer[9]!=17{continue}
  ihl:=int(buffer[0]&0xf)*4
  if ihl<20||size<ihl+8+len(reverse){continue}
  if !net.IP(buffer[12:16]).Equal(net.IP(b.local[:]))||
   !net.IP(buffer[16:20]).Equal(net.IP(b.remote[:])){continue}
  if string(buffer[ihl+8:ihl+8+len(reverse)])==string(reverse){observed=true;break}
 }
 if !observed{t.Fatal("genuine B reverse Windows socket packet absent after A native Stop")}
 if e:=backend.RemoveOwned(ctx,route);e!=nil{t.Fatalf("B reverse route exact Stop: %v",e)}
 routeLive=false
 if found,_,e:=backend.Lookup(ctx,route);e!=nil||found{
  t.Fatalf("B reverse /32 survived owned deletion: %v %v",found,e)
 }
 if e:=b.ring.Stop(ctx);e!=nil{t.Fatalf("B final exact Stop: %v",e)}
 if _,e:=b.ring.n4DeliverAuthenticatedIPv4(ctx,
  n4MakeKernelUDP(b.remote,b.local,41161,b.port,[]byte("B-stale")));
  !errors.Is(e,ErrN4NativeGuard){t.Fatalf("stopped B wrote kernel: %v",e)}
 ca,ea:=a.ring.Counts();cb,eb:=b.ring.Counts()
 if ea!=nil||eb!=nil||!ca.Stopped||!cb.Stopped||
  ca.KernelCopied!=1||cb.KernelCopied!=2||cb.KernelReceived<1{
  t.Fatalf("original kernel counters A=%+v B=%+v error=%v/%v",ca,cb,ea,eb)
 }
 receipt["real_signed_wintun_devices"]=2
 receipt["distinct_original_GUID_LUID_IFINDEX_alias"]=true
 receipt["real_windows_udp_app_A_and_B"]=true
 receipt["B_native_kernel_app_after_A_stop"]=true
 receipt["B_windows_udp_socket_reverse_ring_after_A_stop"]=true
 receipt["exact_both_native_stops_and_stale_denial"]=true
 receipt["native_copied_A_B"]=[]uint64{ca.KernelCopied,cb.KernelCopied}
 receipt["native_B_received"]=cb.KernelReceived
 receipt["classification"]="PASS_SCOPED_REAL_TWO_SIGNED_WINDOWS_WINTUN_NATIVE_KERNEL_UDP_ISOLATED_STOP_NO_AUTH"
 t.Log("M0_PLAN028_H1369_TWO_REAL_SIGNED_WINTUN_NATIVE_KERNEL_UDP_AND_STOP_ISOLATION_PASS")
}
