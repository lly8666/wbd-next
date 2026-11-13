//go:build windows

package windowsclient

// PLAN029 H1704 one genuine, isolated signed Wintun + original generation
// lease borrowed by Rust (not a Go steady packet pump), then a connected
// physically-source+ifindex-bound UDP socket to an INDEPENDENT Ubuntu WSL2
// guest kernel. The guest sends an actual reverse reply; Rust constructs
// Wintun L3 response and the ORIGINAL Windows UDP application must read it.
// This is NOT a product Ready or TLS/Normal/Game4 admission.
import (
 "bufio"
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

type p029RustUdpTrial struct{
 Version,Size uint32
 Session,ReadEvent uintptr
 Receive,Release,Allocate,Send uintptr
 Client,Presented,Remote,PhysicalSource [4]byte
 Ifindex uint32
 ClientPort,TargetPort uint16
 InnerMTU,DeadlineMS uint32
 CurrentLUID uint64
 CurrentWintunIndex uint32
 Generation [16]byte
}
func p029GuestProcess(t *testing.T,port uint16)(func(),error){
 t.Helper()
 // This process is running in a REAL independently booted Ubuntu Linux
 // kernel on a different WSL2 NIC, not a Windows loopback listener.
 // No background Actions and no shell script installed on host.
 py:=fmt.Sprintf(`import socket,sys
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("0.0.0.0",%d))
s.settimeout(20)
print("P029_LINUX_GUEST_UDP_READY",flush=True)
try:
    b,peer=s.recvfrom(2048)
    if b==b"p029-linux-guest-udp-wire":
        s.sendto(b+b"-reply",peer)
        print("P029_LINUX_GUEST_WIRE_AND_REVERSE_PASS",flush=True)
    else:
        print("P029_LINUX_GUEST_WRONG_PACKET",repr(b),flush=True)
finally:
    s.close()
`,port)
 cmd:=exec.Command("wsl.exe","-d","Ubuntu","-u","root","--","python3","-u","-c",py)
 stdout,e:=cmd.StdoutPipe()
 if e!=nil{return nil,e}
 var stderr bytes.Buffer
 cmd.Stderr=&stderr
 if e=cmd.Start();e!=nil{return nil,e}
 closed:=false
 stop:=func(){
  if closed{return};closed=true
  if cmd.Process!=nil{_ = cmd.Process.Kill()}
  _=cmd.Wait()
 }
 ready:=make(chan error,1)
 go func(){
  line,err:=bufio.NewReader(stdout).ReadString('\n')
  if err==nil&&!strings.Contains(line,"P029_LINUX_GUEST_UDP_READY"){
   err=fmt.Errorf("guest did not announce readiness: %q",line)
  }
  ready<-err
 }()
 select{
 case e=<-ready:
  if e!=nil{stop();return nil,fmt.Errorf("guest startup: %w stderr=%s",e,stderr.String())}
 case <-time.After(30*time.Second):
  stop();return nil,fmt.Errorf("real guest startup timeout stderr=%s",stderr.String())
 }
 t.Log("P029_H1704_GENUINE_UBUNTU_GUEST_READY")
 return stop,nil
}

func TestPlan029H1704WintunRustBoundUdpIndependentLinuxGuestReverse(t *testing.T){
 if os.Getenv("WBD_P029_H1704_OWNED_GATE")!="1"||
  os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("only signed isolated Windows2025 WSL2 guest native test")
 }
 result:=map[string]any{
  "schema_version":1,"source_sha":os.Getenv("GITHUB_SHA"),
  "scope":"SIGNED_WINTUN_RUST_DIRECT_UDP_SEPARATE_LINUX_GUEST_DIAGNOSTIC_ONLY",
  "result":"FAIL_UNFINISHED","product_ready":"NOT_RUN",
  "original_authenticated_tls":"NOT_RUN","normal_game4":"NOT_RUN",
  "old_wfp_guard":"NOT_CREATED","go_steady_packet_pump":"NOT_USED",
 }
 defer func(){
  path:=os.Getenv("WBD_P029_H1704_RECEIPT")
  if path==""{t.Error("receipt path missing");return}
  if err:=os.MkdirAll(filepath.Dir(path),0700);err!=nil{t.Error(err);return}
  b,e:=json.MarshalIndent(result,"","  ");if e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Error(e)}
 }()
 guest,e:=netip.ParseAddr(os.Getenv("WBD_P029_H1704_GUEST_IP"))
 if e!=nil||!guest.Is4()||guest.IsLoopback()||guest.IsUnspecified(){
  result["result"]="FAIL_REAL_GUEST_ADDRESS"
  t.Fatalf("not an independent real IPv4 guest: %v %v",guest,e)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),72*time.Second)
 defer cancel()
 nonce:=[8]byte{}
 if _,e=rand.Read(nonce[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-DUDP-"+hex.EncodeToString(nonce[:]))
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
 const port uint16=46098
 stopGuest,e:=p029GuestProcess(t,port)
 if e!=nil{result["result"]="FAIL_GENUINE_UBUNTU_GUEST_SERVER";t.Fatal(e)}
 defer stopGuest()
 dllPath:=os.Getenv("WBD_P029_H1704_RUST_DLL")
 if dllPath==""||!filepath.IsAbs(dllPath){t.Fatal("Rust test DLL absolute path missing")}
 dll,e:=syscall.LoadDLL(dllPath)
 if e!=nil{result["result"]="FAIL_RUST_DLL_LOAD";t.Fatal(e)}
 defer dll.Release()
 fn,e:=dll.FindProc("wbd_m0_win_plan029_owned_udp_trial_v1")
 if e!=nil{result["result"]="FAIL_EXPLICIT_TEST_GATE_DLL_EXPORT";t.Fatal(e)}
 app,e:=net.DialUDP("udp4",&net.UDPAddr{IP:net.IP(lease4.AsSlice()),Port:0},
  &net.UDPAddr{IP:net.IP(fake4.AsSlice()),Port:int(port)})
 if e!=nil{result["result"]="FAIL_APP_CLIENT_BIND";t.Fatal(e)}
 defer app.Close()
 local:=app.LocalAddr().(*net.UDPAddr)
 if local.Port==0{t.Fatal("no actual client source port")}
 cfg:=p029RustUdpTrial{
  Version:1,Size:uint32(unsafe.Sizeof(p029RustUdpTrial{})),
  Session:native.Session,ReadEvent:native.ReadEvent,
  Receive:native.Fns.Receive,Release:native.Fns.Release,
  Allocate:native.Fns.Allocate,Send:native.Fns.Send,
  Client:lease4.As4(),Presented:fake4.As4(),Remote:guest.As4(),
  PhysicalSource:selected.source4.As4(),Ifindex:selected.interfaceIndex,
  ClientPort:uint16(local.Port),TargetPort:port,
  InnerMTU:1280,DeadlineMS:10000,
  CurrentLUID:current.LUID,CurrentWintunIndex:current.Index,
  Generation:generation,
 }
 rustRC:=make(chan uintptr,1)
 go func(){
  rv,_,_:=fn.Call(uintptr(unsafe.Pointer(&cfg)))
  runtime.KeepAlive(&cfg)
  rustRC<-rv
 }()
 // App sends one REAL kernel datagram. The OS chooses the owned Wintun
 // /32 route, Rust owns WintunReceivePacket and the physical UDP socket.
 // There is no Go WritePacket shortcut and no Go per-packet iteration.
 payload:=[]byte("p029-linux-guest-udp-wire")
 result["result"]="FAIL_WINTUN_APP_OR_REVERSE"
 n,appWriteErr:=app.Write(payload)
 if appWriteErr==nil&&n!=len(payload){appWriteErr=errors.New("short real app UDP send")}
 var response [256]byte
 _=app.SetReadDeadline(time.Now().Add(13*time.Second))
 count,appReadErr:=app.Read(response[:])
 // Rust must join before even the failure cleanup releases the original
 // borrowed Wintun functions/session. Always wait, no early t.Fatal here.
 var code uintptr
 select{
 case code=<-rustRC:
 case <-time.After(15*time.Second):
  result["result"]="FAIL_RUST_WORKER_NOT_JOINED_RETAIN_LOAN"
  // No unsafe early Wintun loan release or foreign adapter removal.
  t.Fatal("Rust bounded diagnostic did not join; retaining loan")
 }
 result["rust_ffi_return"]=uint32(code)
 if appWriteErr!=nil||appReadErr!=nil||code!=0||
  string(response[:count])!="p029-linux-guest-udp-wire-reply"{
  t.Fatalf("Wintun->Rust->independent Linux guest->Rust Wintun->real UDP app FAILED write=%v read=%v rust=%d len=%d reply=%q",
   appWriteErr,appReadErr,code,count,response[:count])
 }
 result["app_source4"]=lease4.String()
 result["app_presented_fake4"]=fake4.String()
 result["guest_reply"]="PASS_INDEPENDENT_LINUX_UDP_GUEST"
 result["rust_socket"]="PASS_PHYSICAL_SOURCE_BOUND_IFINDEX_AND_REPLY"
 result["rust_wintun"]="PASS_REAL_ONE_READER_RX_AND_TX_REVERSE"
 result["app_read"]="PASS_ORIGINAL_WINDOWS_UDP_APP_REVERSE"
 result["owned_stop"]="JOINED_RUST_RELEASE_PENDING_ORIGINAL_OWNED_CLEANUP"
 result["result"]="PASS_SCOPED_GENUINE_WINTUN_RUST_UDP_INDEPENDENT_GUEST_REVERSE"
 t.Log("PLAN029_H1704_GENUINE_WINTUN_RUST_DIRECT_UDP_GUEST_REVERSE_PASS_ONLY_NOT_PRODUCT")
}
