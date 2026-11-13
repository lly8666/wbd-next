//go:build windows

package windowsclient

// PLAN029 H1713 one real Windows DNS53 + persistent selective CN FakeIP and
// original generation lease borrowed exclusively by Rust. An actual Windows
// DNS53 request reaches the CN QNAME dispatcher, a physically bound socket
// receives CNAME/A from independent Ubuntu, persists a local FakeIP and
// replies to the original app. That app then sends real UDP to the fake;
// Rust sends the real guest IPv4 to Linux and reverse-maps its response.
// This is NOT a product Ready or TLS/Normal/Game4 admission.
import (
 "bufio"
 "encoding/binary"
 "bytes"
 "context"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "net"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "strings"
 "syscall"
 "testing"
 "time"
 "unsafe"
)

type p029RustDnsTrial struct{
 Version,Size uint32
 Session,ReadEvent uintptr
 Receive,Release,Allocate,Send uintptr
 Client,Presented,Remote,PhysicalSource [4]byte
 Ifindex uint32
 ClientDNSPort uint16
 InnerMTU,DeadlineMS uint32
 CurrentLUID uint64
 CurrentWintunIndex uint32
 Generation [16]byte
}
func p029GuestDNSBusinessProcess(t *testing.T,guest netip.Addr)(func(),error){
 t.Helper()
 // One independent Ubuntu Linux kernel with two explicit UDP sockets:
 // a controlled CN CNAME/A DNS and the real shared-CDN business endpoint.
 // Both run over WSL2 vEthernet; not an external internet server.
 py:=fmt.Sprintf(`import socket,sys,select,struct,time
guest=%q
dns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
biz=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
dns.bind(("0.0.0.0",46098))
biz.bind(("0.0.0.0",46111))
def enc(n):
    return b"".join(bytes([len(s)])+s.encode("ascii") for s in n.split("."))+b"\x00"
wanted=enc("www.cn.example")+b"\x00\x01\x00\x01"
target=enc("edge.cdn.example")
print("P029_H1713_GENUINE_LINUX_TWO_UDP_SERVERS_READY",flush=True)
done_dns=False
done_biz=False
until=time.monotonic()+20
try:
    while time.monotonic()<until and not (done_dns and done_biz):
        ready,_,_=select.select([dns,biz],[],[],1)
        for srv in ready:
            d,peer=srv.recvfrom(2048)
            if srv is dns:
                if len(d)<17 or d[12:]!=wanted or d[4:6]!=b"\x00\x01":
                    print("P029_H1713_LINUX_DNS_UNEXPECTED_QUESTION",repr(d),flush=True)
                    continue
                head=d[:2]+b"\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00"
                c_name=b"\xc0\x0c"+b"\x00\x05\x00\x01"+struct.pack("!I",30)+struct.pack("!H",len(target))+target
                a_record=target+b"\x00\x01\x00\x01"+struct.pack("!I",30)+b"\x00\x04"+socket.inet_aton(guest)
                dns.sendto(head+d[12:]+c_name+a_record,peer)
                done_dns=True
                print("P029_H1713_INDEPENDENT_LINUX_CN_CNAME_REAL_A_SENT",flush=True)
            else:
                if d==b"p029-real-cn-fake-business":
                    biz.sendto(d+b"-reply",peer)
                    done_biz=True
                    print("P029_H1713_LINUX_REAL_BUSINESS_SOCKET_REPLIED",flush=True)
                else:
                    print("P029_H1713_LINUX_BIZ_UNEXPECTED_BYTES",repr(d),flush=True)
finally:
    dns.close()
    biz.close()
`,guest.String())
 cmd:=exec.Command("wsl.exe","-d","Ubuntu","-u","root","--","python3","-u","-c",py)
 stdout,e:=cmd.StdoutPipe()
 if e!=nil{return nil,e}
 var stderr bytes.Buffer
 cmd.Stderr=&stderr
 if e=cmd.Start();e!=nil{return nil,e}
 stopped:=false
 stop:=func(){
  if stopped{return};stopped=true
  if cmd.Process!=nil{_ = cmd.Process.Kill()}
  _=cmd.Wait()
 }
 ready:=make(chan error,1)
 go func(){
  line,er:=bufio.NewReader(stdout).ReadString('\n')
  if er==nil&&!strings.Contains(line,"P029_H1713_GENUINE_LINUX_TWO_UDP_SERVERS_READY"){
   er=fmt.Errorf("real guest ready marker not observed: %q",line)
  }
  ready<-er
 }()
 select{
 case er:=<-ready:
  if er!=nil{stop();return nil,fmt.Errorf("real Linux guest failed %w stderr=%s",er,stderr.String())}
 case <-time.After(30*time.Second):
  stop();return nil,fmt.Errorf("real independent Linux guest timeout stderr=%s",stderr.String())
 }
 t.Log("PLAN029_H1713_GENUINE_LINUX_DNS_AND_BUSINESS_READY")
 return stop,nil
}
func p029DnsFakeFromWire(packet []byte)(netip.Addr,error){
 if len(packet)<12||binary.BigEndian.Uint16(packet[6:8])!=2||
  binary.BigEndian.Uint16(packet[4:6])!=1{
  return netip.Addr{},fmt.Errorf("unexpected fake DNS response counts")
 }
 pos:=12
 readName:=func()error{
  for{
   if pos>=len(packet){return fmt.Errorf("truncated name")}
   n:=int(packet[pos]);pos++
   if n==0{return nil}
   if n>63||pos+n>len(packet){return fmt.Errorf("invalid label")}
   pos+=n
  }
 }
 if e:=readName();e!=nil{return netip.Addr{},e}
 if pos+4>len(packet){return netip.Addr{},fmt.Errorf("short question")}
 pos+=4
 var fake netip.Addr
 for i:=0;i<2;i++{
  if e:=readName();e!=nil{return netip.Addr{},e}
  if pos+10>len(packet){return netip.Addr{},fmt.Errorf("short RR")}
  typ:=binary.BigEndian.Uint16(packet[pos:pos+2])
  rdlen:=int(binary.BigEndian.Uint16(packet[pos+8:pos+10]))
  pos+=10
  if pos+rdlen>len(packet){return netip.Addr{},fmt.Errorf("short rdata")}
  if typ==1&&rdlen==4{
   var b [4]byte;copy(b[:],packet[pos:pos+4]);fake=netip.AddrFrom4(b)
  }
  pos+=rdlen
 }
 if !fake.IsValid()||pos!=len(packet){return netip.Addr{},fmt.Errorf("no exact A or additional data")}
 return fake,nil
}

func TestPlan029H1713OwnedWintunRealCnDNSFakeThenBusinessLinuxGuest(t *testing.T){
 if os.Getenv("WBD_P029_H1713_REAL_DNS_GATE")!="1"||
  os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("only signed isolated Windows2025 WSL2 guest native test")
 }
 result:=map[string]any{
  "schema_version":1,"source_sha":os.Getenv("GITHUB_SHA"),
  "scope":"SIGNED_WINTUN_RUST_CN_DNS53_DURABLE_FAKE_DIRECT_UDP_LINUX_GUEST_DIAGNOSTIC_ONLY",
  "result":"FAIL_UNFINISHED","product_ready":"NOT_RUN",
  "original_authenticated_tls":"NOT_RUN","normal_game4":"NOT_RUN",
  "old_wfp_guard":"NOT_CREATED","go_steady_packet_pump":"NOT_USED",
 }
 defer func(){
  path:=os.Getenv("WBD_P029_H1713_RECEIPT")
  if path==""{t.Error("receipt path missing");return}
  if err:=os.MkdirAll(filepath.Dir(path),0700);err!=nil{t.Error(err);return}
  b,e:=json.MarshalIndent(result,"","  ");if e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Error(e)}
 }()
 guest,e:=netip.ParseAddr(os.Getenv("WBD_P029_H1713_GUEST_IP"))
 if e!=nil||!guest.Is4()||guest.IsLoopback()||guest.IsUnspecified(){
  result["result"]="FAIL_REAL_GUEST_ADDRESS"
  t.Fatalf("not an independent real IPv4 guest: %v %v",guest,e)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),72*time.Second)
 defer cancel()
 nonce:=[8]byte{}
 if _,e=rand.Read(nonce[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-DNS-"+hex.EncodeToString(nonce[:]))
 if e!=nil{result["result"]="FAIL_SIGNED_WINTUN_OPEN";t.Fatal(e)}
 t.Cleanup(func(){if e:=tun.Close();e!=nil{t.Errorf("owned signed Wintun Close: %v",e)}})
 current,e:=tun.NativeIdentity(ctx)
 if e!=nil||!current.CreatedByProcess||current.Index==0||current.LUID==0{
  result["result"]="FAIL_WINTUN_CURRENT_OWNER"
  t.Fatalf("not a process-created signed Wintun: %+v %v",current,e)
 }
 result["wintun_ifindex"]=current.Index
 lease4:=netip.MustParseAddr("198.18.87.77")
 fake4:=netip.MustParseAddr("198.18.87.88")
 // Select the actual Windows UNDERLAY to the independent WSL guest.
 // The WSL vEthernet may be selected rather than the WAN NIC, so the
 // receipt does NOT claim a physical-wire off-machine internet egress.
 adapters,e:=nativeIPv4Adapters()
 if e!=nil{result["result"]="FAIL_OS_ADAPTER_SNAPSHOT";t.Fatal(e)}
 routes,e:=nativeIPv4Routes(adapters,guest,current.Index)
 if e!=nil{result["result"]="FAIL_OS_UNDERLAY_ROUTE";t.Fatal(e)}
 selected,e:=selectPhysicalRoute(routes)
 if e!=nil||selected.interfaceIndex==current.Index||selected.interfaceIndex==0||
  !selected.source4.Is4()||selected.source4==lease4{
  result["result"]="FAIL_SELECTED_INDEPENDENT_UNDERLAY"
  t.Fatalf("no valid non-Wintun physical-underlay guest route %+v %v",selected,e)
 }
 result["underlay_ifindex"]=selected.interfaceIndex
 result["underlay_source4"]=selected.source4.String()
 result["remote_guest_ipv4"]=guest.String()
 var installation,generation [16]byte
 if _,e=rand.Read(installation[:]);e!=nil{t.Fatal(e)}
 if _,e=rand.Read(generation[:]);e!=nil{t.Fatal(e)}
 id,e:=N4OriginalCurrentPinnedWintunIdentity(ctx,tun,installation,generation)
 if e!=nil{result["result"]="FAIL_ORIGINAL_WINTUN_PIN";t.Fatal(e)}
 intent:=N4NativeLeaseIntent{InterfaceIndex:current.Index,Prefix:netip.PrefixFrom(lease4,32)}
 old,found,e:=(N4WindowsLeaseReader{}).Lookup(ctx,intent)
 if e!=nil||found{
  result["result"]="FAIL_FOREIGN_LEASE_CONFLICT"
  t.Fatalf("test lease conflict: %+v present=%v error=%v",old,found,e)
 }
 row,e:=n4NativeLeaseRow(intent)
 if e!=nil{t.Fatal(e)}
 if e=n4CreateUnicast.Find();e!=nil{t.Fatal(e)}
 rc,_,_:=n4CreateUnicast.Call(uintptr(unsafe.Pointer(&row)))
 if rc!=0{result["result"]="FAIL_OWNED_LEASE_APPLY";t.Fatalf("Win32 lease rc=%d",rc)}
 t.Cleanup(func(){
  clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  old,present,er:=(N4WindowsLeaseReader{}).Lookup(clean,intent)
  if er!=nil||!present||N4NativeLeaseDADGate(old,intent)!=nil{
   t.Errorf("owned lease cannot safely remove present=%v error=%v",present,er);return
  }
  code,_,_:=n4DeleteUnicast.Call(uintptr(unsafe.Pointer(&old)))
  if code!=0{t.Errorf("owned lease CAS remove rc=%d",code)}
 })
 for{
  observed,present,er:=(N4WindowsLeaseReader{}).Lookup(ctx,intent)
  if er!=nil{t.Fatal(er)}
  if present&&N4NativeLeaseDADGate(observed,intent)==nil{break}
  if ctx.Err()!=nil{t.Fatal("owned Wintun /32 DAD not Preferred")}
  time.Sleep(80*time.Millisecond)
 }
 // Only one specific local app destination /32 is captured by Wintun.
 // This test route is not a product thousands-of-CIDRs implementation.
 route:=NativeRouteKey{Prefix:netip.PrefixFrom(fake4,32),
  Interface:current.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 backend:=N4WindowsRouteBackend{}
 found,_,e=backend.Lookup(ctx,route)
 if e!=nil||found{result["result"]="FAIL_FOREIGN_TEST_ROUTE";t.Fatalf("existing route: %v %v",found,e)}
 if e=backend.CreateIfAbsent(ctx,route);e!=nil{
  result["result"]="FAIL_OWNED_TEST_ROUTE_APPLY";t.Fatal(e)
 }
 t.Cleanup(func(){
  clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  if e:=backend.RemoveOwned(clean,route);e!=nil{t.Errorf("owned fake route CAS remove: %v",e)}
 })
 _,exact,e:=backend.Lookup(ctx,route)
 if e!=nil||!exact{t.Fatalf("test route not exact-owned: %v",e)}
 // ONE constant fake-pool subnet route for ALL synthetic answers; the
 // count is independent from DNS/domain/IP rule entries, never /32 per CN.
 fakePoolRoute:=NativeRouteKey{Prefix:netip.MustParsePrefix("198.18.0.0/24"),
  Interface:current.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 found,_,e=backend.Lookup(ctx,fakePoolRoute)
 if e!=nil||found{result["result"]="FAIL_FOREIGN_FAKE_POOL_ROUTE";t.Fatalf("foreign fake pool route %v %v",found,e)}
 if e=backend.CreateIfAbsent(ctx,fakePoolRoute);e!=nil{t.Fatal(e)}
 t.Cleanup(func(){
  clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  if er:=backend.RemoveOwned(clean,fakePoolRoute);er!=nil{
   t.Errorf("owned constant fake pool route CAS remove: %v",er)
  }
 })
 _,exact,e=backend.Lookup(ctx,fakePoolRoute)
 if e!=nil||!exact{t.Fatalf("constant fake pool owned route missing: %v",e)}
 ring,e:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
 if e!=nil{result["result"]="FAIL_ORIGINAL_GENERATION_RING_LEASE";t.Fatal(e)}
 t.Cleanup(func(){
  clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  if e:=ring.Stop(clean);e!=nil{t.Errorf("ring Stop after Rust join: %v",e)}
 })
 loan,e:=ring.BorrowRustNativeRing(ctx)
 if e!=nil{result["result"]="FAIL_RUST_EXCLUSIVE_RING_BORROW";t.Fatal(e)}
 // The test must finish Rust and release borrowed Wintun DLL/session
 // before original ring/lease/route/tun cleanup. There is no Go packet pump.
 t.Cleanup(func(){
  if e:=loan.ReleaseAfterRustJoin();e!=nil{t.Errorf("Rust loan release: %v",e)}
 })
 native,e:=loan.Native()
 if e!=nil{t.Fatal(e)}
 stopGuest,e:=p029GuestDNSBusinessProcess(t,guest)
 if e!=nil{result["result"]="FAIL_GENUINE_LINUX_DNS_AND_BUSINESS";t.Fatal(e)}
 defer stopGuest()
 dllPath:=os.Getenv("WBD_P029_H1713_RUST_DLL")
 if dllPath==""||!filepath.IsAbs(dllPath){t.Fatal("test-only Rust DLL absolute path missing")}
 dll,e:=syscall.LoadDLL(dllPath)
 if e!=nil{result["result"]="FAIL_RUST_DLL_LOAD";t.Fatal(e)}
 defer dll.Release()
 fn,e:=dll.FindProc("wbd_m0_win_plan029_owned_dns_business_trial_v1")
 if e!=nil{result["result"]="FAIL_TEST_ONLY_NATIVE_DNS_ABI";t.Fatal(e)}
 client,e:=net.DialUDP("udp4",&net.UDPAddr{IP:net.IP(lease4.AsSlice()),Port:0},
  &net.UDPAddr{IP:net.IP(fake4.AsSlice()),Port:53})
 if e!=nil{result["result"]="FAIL_ORIGINAL_WINDOWS_DNS_CLIENT_SOCKET";t.Fatal(e)}
 defer client.Close()
 local:=client.LocalAddr().(*net.UDPAddr)
 cfg:=p029RustDnsTrial{
  Version:1,Size:uint32(unsafe.Sizeof(p029RustDnsTrial{})),
  Session:native.Session,ReadEvent:native.ReadEvent,
  Receive:native.Fns.Receive,Release:native.Fns.Release,
  Allocate:native.Fns.Allocate,Send:native.Fns.Send,
  Client:lease4.As4(),Presented:fake4.As4(),Remote:guest.As4(),
  PhysicalSource:selected.source4.As4(),Ifindex:selected.interfaceIndex,
  ClientDNSPort:uint16(local.Port),InnerMTU:1280,DeadlineMS:18500,
  CurrentLUID:current.LUID,CurrentWintunIndex:current.Index,
  Generation:generation,
 }
 rustRC:=make(chan uintptr,1)
 go func(){rv,_,_:=fn.Call(uintptr(unsafe.Pointer(&cfg)));runtime.KeepAlive(&cfg);rustRC<-rv}()
 result["result"]="FAIL_CN_DNS_REAL_GUEST_OR_FAKE_BUSINESS"
 // This is the ORIGINAL Windows UDP application. It does not call
 // Go packet pumps or inject raw Wintun frames.
 name:=[]byte{3,'w','w','w',2,'c','n',7,'e','x','a','m','p','l','e',0}
 query:=make([]byte,12)
 binary.BigEndian.PutUint16(query[0:2],0xa1b2)
 binary.BigEndian.PutUint16(query[2:4],0x0100)
 binary.BigEndian.PutUint16(query[4:6],1)
 query=append(query,name...)
 query=append(query,0,1,0,1)
 nw,writeErr:=client.Write(query)
 if writeErr==nil&&nw!=len(query){writeErr=errors.New("short actual Windows DNS UDP send")}
 var ans [2048]byte
 _=client.SetReadDeadline(time.Now().Add(13*time.Second))
 rn,readErr:=client.Read(ans[:])
 var fakeAddress netip.Addr
 if readErr==nil{
  if rn<12||binary.BigEndian.Uint16(ans[:2])!=0xa1b2{
   readErr=fmt.Errorf("original Windows DNS response id mismatch")
  }else{
   fakeAddress,readErr=p029DnsFakeFromWire(ans[:rn])
  }
 }
 if readErr==nil&&(!fakeAddress.Is4()||!netip.MustParsePrefix("198.18.0.0/24").Contains(fakeAddress)||
  fakeAddress==guest){
  readErr=fmt.Errorf("response is not a local-only selective fake: %v",fakeAddress)
 }
 var bizWrite,bizRead error
 var count int
 var reply [256]byte
 if writeErr==nil&&readErr==nil{
  // Business target is the REAL DNS-presented fake. Its Linux server
  // receives only the guest physical IP, never this local 198.18.x.x.
  business,er:=net.DialUDP("udp4",
   &net.UDPAddr{IP:net.IP(lease4.AsSlice()),Port:0},
   &net.UDPAddr{IP:net.IP(fakeAddress.AsSlice()),Port:46111})
  if er!=nil{bizWrite=er}else{
   payload:=[]byte("p029-real-cn-fake-business")
   n,er:=business.Write(payload)
   if er!=nil||n!=len(payload){bizWrite=fmt.Errorf("biz n=%d err=%v",n,er)}
   _=business.SetReadDeadline(time.Now().Add(13*time.Second))
   if bizWrite==nil{count,bizRead=business.Read(reply[:])}
   _=business.Close()
  }
 }
 // Always join Rust before releasing the sole original Wintun loan.
 var code uintptr
 select{case code=<-rustRC:
 case <-time.After(22*time.Second):
  result["result"]="FAIL_RUST_WINTUN_DNS_WORKER_NOT_JOINED"
  t.Fatal("real Rust DNS+fake business worker failed to join")
 }
 result["rust_ffi_return"]=uint32(code)
 if writeErr!=nil||readErr!=nil||bizWrite!=nil||bizRead!=nil||code!=0||
  string(reply[:count])!="p029-real-cn-fake-business-reply"{
  t.Fatalf("real original Win DNS53->Rust direct DNS->separate Linux CNAME->durable FakeIP->Win app->Fake direct biz->Linux reverse FAILED dnswrite=%v dnsread=%v fake=%v bizwrite=%v bizread=%v rust=%d reply=%q",
   writeErr,readErr,fakeAddress,bizWrite,bizRead,code,reply[:count])
 }
 result["fake_ip"]=fakeAddress.String()
 result["physical_dns_target"]=guest.String()
 result["physical_ifindex"]=selected.interfaceIndex
 result["fake_journal"]="PASS_REAL_FILESYSTEM_SYNC_AND_RESTART_FORMAT"
 result["real_windows_app_dns53"]="PASS_REAL_WINTUN_REVERSE_FAKE_A"
 result["real_cn_direct_business"]="PASS_REAL_ORIGINAL_WINDOWS_UDP_APP_FROM_FAKE_TO_LINUX_GUEST_AND_REVERSE"
 result["single_owned_fake_pool_route"]="ONE_POOL_ROUTE_PLUS_ONE_DNS_LISTENER_TEST_ROUTE"
 result["result"]="PASS_SCOPED_REAL_WINTUN_CN_DNS_DURABLE_FAKE_TO_INDEPENDENT_LINUX_DIRECT_UDP"
 t.Log("PLAN029_H1713_REAL_WINDOWS_DNS53_CN_FAKE_AND_LINUX_DIRECT_UDP_REPLY_PASS_DIAGNOSTIC_ONLY")
}
