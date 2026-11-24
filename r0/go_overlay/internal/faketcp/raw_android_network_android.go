//go:build android && cgo
package faketcp
/*
#cgo LDFLAGS: -landroid
#include <android/multinetwork.h>
*/
import "C"
import (
    "fmt"
    "net"
    "syscall"
)
// BindAndroidNetwork is original-Go cold SYN/TLS socket binding, not a
// second transport, identity provider, packet pump or steady DATA loop.
func (e *RawIPv4Endpoint) BindAndroidNetwork(
    handle uint64, interfaceName string, expectedIfindex int, expectedMTU int,
) error {
    if e==nil||handle==0||expectedIfindex<=0||expectedMTU<68||expectedMTU>65535{
        return fmt.Errorf("faketcp: no physical Android Network")
    }
    iface,err:=net.InterfaceByName(interfaceName)
    if err!=nil||iface==nil||iface.Index!=expectedIfindex||
        iface.MTU!=expectedMTU{
        return fmt.Errorf("faketcp: physical interface/MTU changed")
    }
    e.mu.Lock()
    defer e.mu.Unlock()
    if e.closed||e.sendFD<0||e.recvFD<0{
        return fmt.Errorf("faketcp: closed raw endpoint")
    }
    // Only this IPPROTO_RAW TX fd receives netd's per-Network routing mark.
    // Original AF_PACKET RX was already bound to this exact ifindex+port.
    rc:=C.android_setsocknetwork(C.net_handle_t(handle),C.int(e.sendFD))
    if rc!=0{
        code:=int(rc);if code<0{code=-code}
        return fmt.Errorf("faketcp: physical Android Network bind: %w",syscall.Errno(code))
    }
    if err=syscall.SetsockoptString(e.sendFD,syscall.SOL_SOCKET,
        syscall.SO_BINDTODEVICE,interfaceName);err!=nil{
        return fmt.Errorf("faketcp: physical Android interface bind: %w",err)
    }
    // On any failure the original caller closes both raw FDs before SYN.
    return nil
}
