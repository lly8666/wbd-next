//go:build windows

package windowsclient

// PLAN029 H1706 one genuine, isolated signed Wintun + original generation
// lease borrowed by Rust. The Windows UDP diagnostic already qualified;
// now a real Windows TCP application SYN is rewritten by Rust to an owned
// native kernel listener and reverse SYNACK is rewritten back. Accepted
// kernel TCP is relayed by ONE Rust physical-bound nonblocking TCP socket
// to a genuine Ubuntu guest and back. Ordinary Tunnel TCP is untouched.
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
 "io"
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

type p029RustTcpTrial struct{
 Version,Size uint32
 Session,ReadEvent uintptr
 Receive,Release,Allocate,Send uintptr
 Client,Presented,Synthetic,Remote,PhysicalSource [4]byte
 Ifindex uint32
 ListenerPort,TargetPort uint16
 InnerMTU,DeadlineMS uint32
 CurrentLUID uint64
 CurrentWintunIndex uint32
 Generation [16]byte
}
func p029GuestTCPProcess(t *testing.T,port uint16)(func(),error){
 t.Helper()
 // This process is running in a REAL independently booted Ubuntu Linux
 // kernel on a different WSL2 NIC, not a Windows loopback listener.
 // No background Actions and no shell script installed on host.
 py:=fmt.Sprintf(`import socket,sys
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.bind(("0.0.0.0",%d))
s.listen(1)
s.settimeout(20)
print("P029_LINUX_GUEST_TCP_READY",flush=True)
try:
    conn,peer=s.accept()
    conn.settimeout(12)
    received=b""
    with conn:
        while True:
            b=conn.recv(2048)
            if not b:break
            received+=b
            if len(received)>4096:break
        if received==b"p029-linux-guest-tcp-wire":
            conn.sendall(received+b"-reply")
            conn.shutdown(socket.SHUT_WR)
            print("P029_LINUX_GUEST_TCP_WIRE_AND_REVERSE_PASS",flush=True)
        else:
            print("P029_LINUX_GUEST_TCP_WRONG_PACKET",repr(received),flush=True)
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
  if err==nil&&!strings.Contains(line,"P029_LINUX_GUEST_TCP_READY"){
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
 t.Log("P029_H1706_GENUINE_UBUNTU_TCP_GUEST_READY")
 return stop,nil
}

func TestPlan029H1706WintunRustKernelTCPToLinuxGuestHalfClose(t *testing.T){
 if os.Getenv("WBD_P029_H1706_OWNED_TCP_GATE")!="1"||
  os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("only signed isolated Windows2025 WSL2 guest native test")
 }
 result:=map[string]any{
  "schema_version":1,"source_sha":os.Getenv("GITHUB_SHA"),
  "scope":"SIGNED_WINTUN_RUST_KERNEL_TCP_NAT_SEPARATE_LINUX_GUEST_DIAGNOSTIC_ONLY",
  "result":"FAIL_UNFINISHED","product_ready":"NOT_RUN",
  "original_authenticated_tls":"NOT_RUN","normal_game4":"NOT_RUN",
  "old_wfp_guard":"NOT_CREATED","go_steady_packet_pump":"NOT_USED","old_tcp_gvisor":"NOT_USED",
 }
 defer func(){
  path:=os.Getenv("WBD_P029_H1706_TCP_RECEIPT")
  if path==""{t.Error("receipt path missing");return}
  if err:=os.MkdirAll(filepath.Dir(path),0700);err!=nil{t.Error(err);return}
  b,e:=json.MarshalIndent(result,"","  ");if e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Error(e)}
 }()
 guest,e:=netip.ParseAddr(os.Getenv("WBD_P029_H1706_GUEST_IP"))
 if e!=nil||!guest.Is4()||guest.IsLoopback()||guest.IsUnspecified(){
  result["result"]="FAIL_REAL_GUEST_ADDRESS"
  t.Fatalf("not an independent real IPv4 guest: %v %v",guest,e)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),72*time.Second)
 defer cancel()
 nonce:=[8]byte{}
 if _,e=rand.Read(nonce[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-DTCP-"+hex.EncodeToString(nonce[:]))
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
 if e!=nil||found{result["result"]="FAIL_FOREIGN_TEST_ROUTE";t.Fatalf("existing fake route: %v %v",found,e)}
 if e=backend.CreateIfAbsent(ctx,route);e!=nil{
  result["result"]="FAIL_OWNED_FAKE_ROUTE_APPLY";t.Fatal(e)
 }
 t.Cleanup(func(){clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  if e:=backend.RemoveOwned(clean,route);e!=nil{t.Errorf("owned fake route CAS remove: %v",e)}
 })
 _,exact,e:=backend.Lookup(ctx,route)
 if e!=nil||!exact{t.Fatalf("fake route readback not exact-owned: %v",e)}
 // One constant synthetic-peer /32 route captures kernel SYNACKs from the
 // local listener. No route per destination/domain/application flow.
 synthetic4:=netip.MustParseAddr("198.19.87.99")
 reverseRoute:=NativeRouteKey{Prefix:netip.PrefixFrom(synthetic4,32),
  Interface:current.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 found,_,e=backend.Lookup(ctx,reverseRoute)
 if e!=nil||found{t.Fatalf("foreign synthetic route: %v %v",found,e)}
 if e=backend.CreateIfAbsent(ctx,reverseRoute);e!=nil{t.Fatal(e)}
 t.Cleanup(func(){clean,done:=context.WithTimeout(context.Background(),9*time.Second);defer done()
  if e:=backend.RemoveOwned(clean,reverseRoute);e!=nil{t.Errorf("owned synthetic route CAS remove: %v",e)}
 })
 _,exact,e=backend.Lookup(ctx,reverseRoute)
 if e!=nil||!exact{t.Fatalf("synthetic route not exact-owned: %v",e)}
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
 const guestPort uint16=46099
 const listenerPort uint16=46101
 stopGuest,e:=p029GuestTCPProcess(t,guestPort)
 if e!=nil{result["result"]="FAIL_GENUINE_UBUNTU_TCP_GUEST";t.Fatal(e)}
 defer stopGuest()
 exe,e:=os.Executable();if e!=nil{t.Fatal(e)}
 // Precisely one session-owned Windows Defender Allow for the actual
 // Rust kernel listener inbound 198.19.87.99→198.18.87.77:46101.
 // This is NOT a custom WFP guard and does not disable global firewall.
 rule:="WBD-P029-H1706-"+hex.EncodeToString(nonce[:])
 ps:=fmt.Sprintf("$ErrorActionPreference='Stop'; New-NetFirewallRule -Name '%s' -DisplayName '%s' -Direction Inbound -Action Allow -Enabled True -Protocol TCP -LocalAddress '%s' -RemoteAddress '%s' -LocalPort %d -Program '%s' -Profile Any | Out-Null",rule,rule,lease4.String(),synthetic4.String(),listenerPort,strings.ReplaceAll(exe,"'","''"))
 output,e:=exec.CommandContext(ctx,"powershell.exe","-NoProfile","-NonInteractive","-Command",ps).CombinedOutput()
 if e!=nil{result["result"]="FAIL_OWNED_TCP_DEFENDER_ALLOW";t.Fatalf("exact TCP listener rule: %v %s",e,output)}
 t.Cleanup(func(){
  clean,done:=context.WithTimeout(context.Background(),12*time.Second);defer done()
  script:=fmt.Sprintf("$ErrorActionPreference='Stop'; Remove-NetFirewallRule -Name '%s' -ErrorAction Stop; if(Get-NetFirewallRule -Name '%s' -ErrorAction SilentlyContinue){throw 'owned TCP listener rule remained'}",rule,rule)
  out,er:=exec.CommandContext(clean,"powershell.exe","-NoProfile","-NonInteractive","-Command",script).CombinedOutput()
  if er!=nil{t.Errorf("owned TCP firewall rule Stop: %v %s",er,out)}
 })
 result["defender_rule"]="ONE_EXACT_OWNED_TEMPORARY_TCP_LOCAL_LISTENER_ALLOW"
 dllPath:=os.Getenv("WBD_P029_H1706_RUST_DLL")
 if dllPath==""||!filepath.IsAbs(dllPath){t.Fatal("Rust test-only DLL absolute path missing")}
 dll,e:=syscall.LoadDLL(dllPath)
 if e!=nil{result["result"]="FAIL_RUST_DLL_LOAD";t.Fatal(e)}
 defer dll.Release()
 fn,e:=dll.FindProc("wbd_m0_win_plan029_owned_tcp_trial_v1")
 if e!=nil{result["result"]="FAIL_EXPLICIT_TEST_GATE_DLL_EXPORT";t.Fatal(e)}
 cfg:=p029RustTcpTrial{
  Version:1,Size:uint32(unsafe.Sizeof(p029RustTcpTrial{})),
  Session:native.Session,ReadEvent:native.ReadEvent,
  Receive:native.Fns.Receive,Release:native.Fns.Release,
  Allocate:native.Fns.Allocate,Send:native.Fns.Send,
  Client:lease4.As4(),Presented:fake4.As4(),Synthetic:synthetic4.As4(),
  Remote:guest.As4(),PhysicalSource:selected.source4.As4(),
  Ifindex:selected.interfaceIndex,
  ListenerPort:listenerPort,TargetPort:guestPort,
  InnerMTU:1280,DeadlineMS:17500,
  CurrentLUID:current.LUID,CurrentWintunIndex:current.Index,
  Generation:generation,
 }
 rustRC:=make(chan uintptr,1)
 go func(){
  rv,_,_:=fn.Call(uintptr(unsafe.Pointer(&cfg)))
  runtime.KeepAlive(&cfg)
  rustRC<-rv
 }()
 result["result"]="FAIL_TCP_KERNEL_NAT_OR_GUEST"
 dialer:=net.Dialer{LocalAddr:&net.TCPAddr{IP:net.IP(lease4.AsSlice())},
  Timeout:14*time.Second}
 app,appErr:=dialer.DialContext(ctx,"tcp4",net.JoinHostPort(fake4.String(),fmt.Sprint(guestPort)))
 var appReadErr error
 var reply []byte
 if appErr==nil{
  tcp,ok:=app.(*net.TCPConn)
  if !ok{appReadErr=fmt.Errorf("expected real Windows TCP app conn")}
  if ok{
   _=tcp.SetDeadline(time.Now().Add(15*time.Second))
   payload:=[]byte("p029-linux-guest-tcp-wire")
   n,werr:=tcp.Write(payload)
   if werr!=nil||n!=len(payload){appReadErr=fmt.Errorf("TCP app write n=%d err=%v",n,werr)}
   if appReadErr==nil{
    if werr=tcp.CloseWrite();werr!=nil{appReadErr=werr}
   }
   if appReadErr==nil{
    reply,appReadErr=io.ReadAll(io.LimitReader(tcp,2048))
   }
  }
  _=app.Close()
 }
 // Always join Rust borrowed Wintun worker before the original owned
 // lease is released. No Go TCP data proxy or second Wintun RX.
 var rc uintptr
 select{case rc=<-rustRC:
 case <-time.After(22*time.Second):
  result["result"]="FAIL_RUST_TCP_PROBE_NOT_JOINED"
  t.Fatal("bounded Rust TCP diagnostic worker not joined; no product Applied")
 }
 result["rust_ffi_return"]=uint32(rc)
 if appErr!=nil||appReadErr!=nil||rc!=0||
  string(reply)!="p029-linux-guest-tcp-wire-reply"{
  t.Fatalf("original signed Windows app SYN→Rust NAT→native kernel listener→physical TCP→Linux guest reverse FAIL dial=%v read=%v rust=%d reply=%q",
   appErr,appReadErr,rc,reply)
 }
 result["client_lease4"]=lease4.String()
 result["presented_fake4"]=fake4.String()
 result["synthetic_peer4"]=synthetic4.String()
 result["guest_tcp"]="PASS_SEPARATE_LINUX_TCP_GUEST_REAL_BYTES_AND_HALF_CLOSE"
 result["kernel_listener"]="PASS_NATIVE_WINDOWS_SYN_ACCEPT_REVERSE_SYNACK"
 result["rust_tcp_egress"]="PASS_PHYSICAL_SOURCE_IFINDEX_BOUND_NONBLOCKING"
 result["app_read"]="PASS_ORIGINAL_WINDOWS_TCP_APP_REVERSE"
 result["result"]="PASS_SCOPED_WINTUN_RUST_KERNEL_TCP_NAT_TO_SEPARATE_LINUX_GUEST"
 t.Log("PLAN029_H1706_GENUINE_NATIVE_KERNEL_TCP_RUST_WINTUN_NAT_GUEST_HALF_CLOSE_PASS_DIAGNOSTIC_ONLY")
}
