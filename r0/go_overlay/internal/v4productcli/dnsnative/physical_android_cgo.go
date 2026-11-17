//go:build android && cgo

package dnsnative

/*
#cgo LDFLAGS: -landroid
#include <android/multinetwork.h>
*/
import "C"

import (
 "context"
 "fmt"
 "syscall"
)

// NewAndroidPhysicalDNSDialer provides REAL netd pre-connect binding for
// DNS UDP and TCP sockets to the selected physical Android Network.
// The returned dialer rejects Tunnel and all endpoints except 223.5.5.5:53.
// NO socket is opened until Resolve selects Physical; no default route,
// per-UID system exemption, Java packet forwarding or VpnService is used.
//
// The original client may construct this at cold validation. Creating it
// does not prove the Android DNS system ingress or a successful DNS query.
func NewAndroidPhysicalDNSDialer(s PhysicalScope)(DialFunc,error){
 if s.LocalIPv4.IsLoopback()||s.LocalIPv4.IsLinkLocalUnicast(){
  return nil,fmt.Errorf("%w: physical DNS scope cannot be loopback or link-local",ErrUnbound)
 }
 return newScopedPhysicalDialer(s,ChinaDNS,
  func(ctx context.Context,network string,conn syscall.RawConn)error{
   if err:=ctx.Err();err!=nil{return err}
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
    name,e:=syscall.GetsockoptString(int(fd),syscall.SOL_SOCKET,
     syscall.SO_BINDTODEVICE)
    if e!=nil||name!=s.InterfaceName{
     markErr=fmt.Errorf("%w: Android physical socket device readback failed",ErrUnbound)
     return
    }
   })
   if err!=nil{return fmt.Errorf("DNS scoped socket control: %w",err)}
   return markErr
  },
 )
}
