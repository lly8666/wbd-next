//go:build android && cgo

package dnsnative

/*
#cgo LDFLAGS: -landroid
#include <android/multinetwork.h>
#include <errno.h>
#include <net/if.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

// Android Go syscall intentionally omits GetsockoptString. Read back the
// SAME socket's SO_BINDTODEVICE through a length-bounded Bionic NDK call;
// never drop this safety check merely to make the ARM64 build succeed.
static int wbd_dns_socket_device_matches(int fd,const char *expected){
 char actual[IFNAMSIZ]={0};
 socklen_t n=(socklen_t)sizeof(actual);
 if(getsockopt(fd,SOL_SOCKET,SO_BINDTODEVICE,actual,&n)!=0)return -errno;
 if(n==0||n>sizeof(actual))return 0;
 actual[IFNAMSIZ-1]='\0';
 return strcmp(actual,expected)==0?1:0;
}
*/
import "C"

import (
 "context"
 "fmt"
 "net/netip"
 "syscall"
 "unsafe"
)

// NewAndroidPhysicalDNSDialer provides REAL netd pre-connect binding for
// DNS UDP and TCP sockets to the selected physical Android Network.
// The returned dialer rejects Tunnel and any endpoint other than its exact
// cold-selected IPv4:53. Legacy callers still default to 223.5.5.5.
// NO socket is opened until Resolve selects Physical; no default route,
// per-UID system exemption, Java packet forwarding or VpnService is used.
//
// The original client may construct this at cold validation. Creating it
// does not prove the Android DNS system ingress or a successful DNS query.
func NewAndroidPhysicalDNSDialer(s PhysicalScope)(DialFunc,error){
 return NewAndroidPhysicalDNSDialerWithUpstream(s,netip.MustParseAddr("223.5.5.5"))
}

func NewAndroidPhysicalDNSDialerWithUpstream(
 s PhysicalScope,upstream netip.Addr,
)(DialFunc,error){
 if _,err:=ParsePhysicalDNSUpstreamIPv4(upstream.String());err!=nil{
  return nil,err
 }
 if s.LocalIPv4.IsLoopback()||s.LocalIPv4.IsLinkLocalUnicast(){
  return nil,fmt.Errorf("%w: physical DNS scope cannot be loopback or link-local",ErrUnbound)
 }
 return newScopedPhysicalDialer(s,upstream.String()+":53",
  func(ctx context.Context,network string,conn syscall.RawConn)error{
   if err:=ctx.Err();err!=nil{return err}
   name:=C.CString(s.InterfaceName)
   defer C.free(unsafe.Pointer(name))
   var markErr error
   err:=conn.Control(func(fd uintptr){
    // The same API is already used for the original Go RAW SYN/TLS fd.
    // We apply it individually to each new UDP and TCP DNS socket before
    // connection; no socket is inherited from a default Network.
    rc:=C.android_setsocknetwork(C.net_handle_t(s.NetworkHandle),C.int(fd))
    if rc!=0{
     code:=int(rc)
     if code<0{code=-code}
     markErr=fmt.Errorf("DNS Android netd selected Network bind: %w",syscall.Errno(code))
     return
    }
    if e:=syscall.SetsockoptString(int(fd),syscall.SOL_SOCKET,
      syscall.SO_BINDTODEVICE,s.InterfaceName);e!=nil{
     markErr=fmt.Errorf("DNS Android physical device bind: %w",e)
     return
    }
    readback:=int(C.wbd_dns_socket_device_matches(C.int(fd),name))
    if readback!=1{
     if readback<0{
      markErr=fmt.Errorf("DNS Android physical device readback: %w",
       syscall.Errno(-readback))
     }else{
      markErr=fmt.Errorf("%w: Android socket device does not match selected interface",ErrUnbound)
     }
     return
    }
   })
   if err!=nil{return fmt.Errorf("DNS scoped socket control: %w",err)}
   return markErr
  },
 )
}
