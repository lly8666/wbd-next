package dnsnative

// Physical DNS is scoped to the exact user-selected Android Network and
// original IPv4 underlay. The component NEVER guesses net.DefaultResolver
// or falls back from Physical to Tunnel (or vice versa).
//
// Android netd socket binding lives in physical_android_cgo.go. The shared
// transport is real Go TCP/UDP and is tested with real host sockets using
// a strict injected kernel-FD control function, not a mock DNS answer.
import (
 "context"
 "fmt"
 "net"
 "net/netip"
 "syscall"
)

// PhysicalScope is an immutable snapshot from Android's selected Network,
// its matching OS ifindex/MTU and original LinkProperties IPv4.
type PhysicalScope struct {
 NetworkHandle uint64
 InterfaceName string
 IfIndex int
 MTU int
 LocalIPv4 netip.Addr
}

type socketBind func(context.Context, string, syscall.RawConn) error

func (s PhysicalScope) check() error {
 if s.NetworkHandle==0||s.InterfaceName==""||s.IfIndex<=0||
  s.MTU<68||s.MTU>1<<20||!s.LocalIPv4.IsValid()||
  !s.LocalIPv4.Is4()||s.LocalIPv4.IsUnspecified()||
  s.LocalIPv4.IsMulticast(){
  return fmt.Errorf("%w: invalid selected Android physical Network scope",ErrUnbound)
 }
 nic,err:=net.InterfaceByName(s.InterfaceName)
 if err!=nil{return fmt.Errorf("%w: selected physical device missing: %v",ErrUnbound,err)}
 if nic.Index!=s.IfIndex||nic.MTU!=s.MTU||nic.Flags&net.FlagUp==0{
  return fmt.Errorf("%w: physical device ifindex/MTU/up changed",ErrUnbound)
 }
 addresses,err:=nic.Addrs()
 if err!=nil{return fmt.Errorf("%w: physical IPv4 not readable: %v",ErrUnbound,err)}
 for _,addr:=range addresses {
  ip,e:=netip.ParsePrefix(addr.String())
  if e==nil&&ip.Addr().Unmap()==s.LocalIPv4.Unmap(){return nil}
 }
 return fmt.Errorf("%w: selected physical IPv4 no longer belongs to interface",ErrUnbound)
}

// newScopedPhysicalDialer is an unexported test seam for real loopback
// sockets. The public Android constructor passes only a genuine netd
// android_setsocknetwork callback and the fixed production 223.5.5.5:53.
func newScopedPhysicalDialer(
 scope PhysicalScope,expected string,bind socketBind,
)(DialFunc,error) {
 if bind==nil{return nil,ErrUnbound}
 ep,err:=netip.ParseAddrPort(expected)
 if err!=nil||!ep.Addr().Is4()||ep.Port()==0||
  ep.Addr().IsMulticast()||ep.Addr().IsUnspecified(){
  return nil,fmt.Errorf("%w: invalid fixed IPv4 DNS endpoint",ErrUnbound)
 }
 if err=scope.check();err!=nil{return nil,err}
 return func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
  if path!=Physical||endpoint!=expected{
   return nil,fmt.Errorf("%w: DNS path/physical endpoint mismatch",ErrUnbound)
  }
  if network!="udp"&&network!="tcp"{
   return nil,fmt.Errorf("%w: unsupported DNS network protocol",ErrUnbound)
  }
  if err:=ctx.Err();err!=nil{return nil,err}
  if err:=scope.check();err!=nil{return nil,err}
  local:=net.IP(scope.LocalIPv4.AsSlice())
  d:=net.Dialer{}
  if network=="udp"{
   d.LocalAddr=&net.UDPAddr{IP:local}
  }else{
   d.LocalAddr=&net.TCPAddr{IP:local}
  }
  // net.Dialer calls ControlContext on the real socket descriptor before
  // connect/send. Failure aborts the fd, never performing a default dial.
  d.ControlContext=func(c context.Context,n,a string,fd syscall.RawConn)error{
   if e:=scope.check();e!=nil{return e}
   return bind(c,n,fd)
  }
  // Literal IPv4 and forced *4 family avoid hostname-resolver bootstraps
  // and hidden IPv6, VPN or OS DNS dependency.
  network4:=network+"4"
  conn,err:=d.DialContext(ctx,network4,expected)
  if err!=nil{return nil,err}
  if err=scope.check();err!=nil{
   _=conn.Close()
   return nil,err
  }
  return conn,nil
 },nil
}
