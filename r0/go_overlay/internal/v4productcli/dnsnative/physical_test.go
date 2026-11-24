package dnsnative

import (
 "context"
 "errors"
 "fmt"
 "net"
 "net/netip"
 "strings"
 "sync/atomic"
 "syscall"
 "testing"
)

func hostPhysicalLoopback(t *testing.T) PhysicalScope {
 t.Helper()
 nic,e:=net.InterfaceByName("lo")
 if e!=nil{t.Skip("host Linux loopback interface unavailable");return PhysicalScope{}}
 return PhysicalScope{
  NetworkHandle:123456789,
  InterfaceName:nic.Name,
  IfIndex:nic.Index,
  MTU:nic.MTU,
  LocalIPv4:netip.MustParseAddr("127.0.0.1"),
 }
}
func realSocketTypeBinder(t *testing.T,calls *atomic.Int32) socketBind{
 t.Helper()
 return func(ctx context.Context,network string,raw syscall.RawConn)error{
  if !strings.HasPrefix(network,"udp")&&!strings.HasPrefix(network,"tcp"){
   return fmt.Errorf("invalid pre-connect network %s",network)
  }
  var callbackError error
  err:=raw.Control(func(fd uintptr){
   sockType,e:=syscall.GetsockoptInt(int(fd),syscall.SOL_SOCKET,syscall.SO_TYPE)
   if e!=nil{callbackError=e;return}
   expected:=syscall.SOCK_DGRAM
   if strings.HasPrefix(network,"tcp"){expected=syscall.SOCK_STREAM}
   if sockType!=expected{
    callbackError=fmt.Errorf("pre-connect fd type %d, wanted %d",sockType,expected)
    return
   }
   calls.Add(1)
  })
  if err!=nil{return err}
  return callbackError
 }
}
func TestB2cPhysicalScopeRealUDPAndTruncatedSameScopedTCP(t *testing.T){
 server:=serveDNS(t,[4]byte{203,0,113,36})
 server.truncate=true
 scope:=hostPhysicalLoopback(t)
 var socketCallbacks atomic.Int32
 dial,e:=newScopedPhysicalDialer(scope,server.addr,realSocketTypeBinder(t,&socketCallbacks))
 if e!=nil{t.Fatal(e)}
 resolver,e:=New(dial,func(string)bool{return true},true)
 if e!=nil{t.Fatal(e)}
 resolver.direct=server.addr
 answer,e:=resolver.Resolve(context.Background(),makeQuery("www.baidu.com",0x7788),false)
 if e!=nil||lastIP(t,answer)!=server.ip{
  t.Fatal("real scoped UDP then TCP DNS failed",e)
 }
 if server.udpCalls.Load()!=1||server.tcpCalls.Load()!=1||
   socketCallbacks.Load()!=2{
  t.Fatalf("scoped UDP/TCP must bind two separate real sockets: UDP=%d TCP=%d bind=%d",
   server.udpCalls.Load(),server.tcpCalls.Load(),socketCallbacks.Load())
 }
}
func TestB2cPhysicalScopeRejectsTunnelEndpointAndUnboundCallback(t *testing.T){
 server:=serveDNS(t,[4]byte{203,0,113,45})
 scope:=hostPhysicalLoopback(t)
 var called atomic.Int32
 binder:=realSocketTypeBinder(t,&called)
 if _,err:=newScopedPhysicalDialer(scope,server.addr,nil);!errors.Is(err,ErrUnbound){
  t.Fatal("unbound fd callback accepted")
 }
 dial,e:=newScopedPhysicalDialer(scope,server.addr,binder)
 if e!=nil{t.Fatal(e)}
 for _,tc:=range []struct{path Path;transport,target string}{
  {Tunnel,"udp",server.addr},
  {Physical,"udp","1.1.1.1:53"},
  {Physical,"tcp","223.5.5.5:53"},
  {Physical,"tcp6",server.addr},
 }{
  if c,err:=dial(context.Background(),tc.path,tc.transport,tc.target);err==nil{
   c.Close()
   t.Fatalf("cross-path/upstream/AF request allowed: %+v",tc)
  }
 }
 if server.udpCalls.Load()!=0||server.tcpCalls.Load()!=0||called.Load()!=0{
  t.Fatal("untrusted target opened a network socket")
 }
 if c,err:=NewAndroidPhysicalDNSDialer(scope);err==nil{
  _,_ = c(context.Background(),Physical,"udp",ChinaDNS)
  // Android cgo-qualified path can construct, but the Linux host stub
  // MUST reject using a default net.Dialer instead of the NDK.
  t.Fatal("host accepted Android-only netd physical binding")
 }
}
func TestB2cPhysicalSocketBindFailureNeverSendsAndNeverFallsBack(t *testing.T){
 server:=serveDNS(t,[4]byte{203,0,113,46})
 scope:=hostPhysicalLoopback(t)
 denied:=errors.New("simulated netd mark denied")
 var callbacks atomic.Int32
 dial,e:=newScopedPhysicalDialer(scope,server.addr,
  func(ctx context.Context,network string,raw syscall.RawConn)error{
   callbacks.Add(1)
   return denied
  })
 if e!=nil{t.Fatal(e)}
 _,err:=dial(context.Background(),Physical,"udp",server.addr)
 if !errors.Is(err,denied){t.Fatal("netd mark error swallowed or fallback attempted",err)}
 if callbacks.Load()!=1||server.udpCalls.Load()!=0{
  t.Fatal("outbound DNS datagram escaped before successful socket mark")
 }
}
func TestB2cPhysicalScopeMustMatchOriginalKernelInterfaceIPv4AndMTU(t *testing.T){
 server:=serveDNS(t,[4]byte{203,0,113,47})
 scope:=hostPhysicalLoopback(t)
 var callbackCount atomic.Int32
 binder:=realSocketTypeBinder(t,&callbackCount)
 invalid:=[]PhysicalScope{
  func()PhysicalScope{x:=scope;x.NetworkHandle=0;return x}(),
  func()PhysicalScope{x:=scope;x.IfIndex++;return x}(),
  func()PhysicalScope{x:=scope;x.MTU++;return x}(),
  func()PhysicalScope{x:=scope;x.InterfaceName="unknown-device";return x}(),
  func()PhysicalScope{x:=scope;x.LocalIPv4=netip.MustParseAddr("127.0.0.2");return x}(),
  func()PhysicalScope{x:=scope;x.LocalIPv4=netip.MustParseAddr("::1");return x}(),
 }
 for i,sc:=range invalid{
  if _,err:=newScopedPhysicalDialer(sc,server.addr,binder);err==nil{
   t.Fatalf("invalid physical Network scope %d passed",i)
  }
 }
 if callbackCount.Load()!=0||server.udpCalls.Load()!=0{
  t.Fatal("invalid scope entered socket data path")
 }
}
