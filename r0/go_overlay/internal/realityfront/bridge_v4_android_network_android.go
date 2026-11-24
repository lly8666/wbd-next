//go:build android && cgo && wbd_v4_embedded_go

package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_android_bind_physical(
    uint64_t,uint64_t,uint32_t,uint32_t,const unsigned char *,size_t);
*/
import "C"
import (
    "fmt"
    "runtime"
    "unsafe"
)

// Cold-only. The exact Network handle must originate from Android
// ConnectivityManager on the same root worker generation; no global process
// bind, no root-UID bypass, no fallback to the platform default network.
func v4BindPlatformUnderlay(b *v4EmbeddedNativeBridge,cfg V4LinuxClientProductConfig)error{
    if b==nil||!b.committed||b.handle==0||cfg.AndroidPhysicalNetworkHandle==0||
        cfg.AndroidPhysicalMTU<68||cfg.AndroidPhysicalMTU>65535||
        cfg.NetworkIfIndex==0||len(cfg.NetworkInterface)==0||len(cfg.NetworkInterface)>15{
        return ErrAdmissionParams
    }
    name:=[]byte(cfg.NetworkInterface)
    rc:=C.wbd_m0_embedded_go_android_bind_physical(
        C.uint64_t(b.handle),C.uint64_t(cfg.AndroidPhysicalNetworkHandle),
        C.uint32_t(cfg.NetworkIfIndex),C.uint32_t(cfg.AndroidPhysicalMTU),
        (*C.uchar)(unsafe.Pointer(&name[0])),C.size_t(len(name)))
    runtime.KeepAlive(name)
    if rc!=0{
        return fmt.Errorf("%w: authenticated Android Network scope=%d",
            &v4EmbeddedNativeStatus{Operation:"android_underlay_bind",Code:int(rc)},int(rc))
    }
    return nil
}
