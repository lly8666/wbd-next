//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe

package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_bind_fec2_probe_after_verified_tls(
    uint64_t,const unsigned char *,size_t,uint16_t,uint8_t,uint64_t);
extern int32_t wbd_m0_embedded_go_fec2_probe_scope_status(
    uint64_t,const unsigned char *,size_t);
extern int32_t wbd_m0_embedded_go_fec2_probe_real_raw_tx(
    uint64_t,uint32_t,uint64_t *,uint64_t *,
    uint32_t *,uint32_t *,uint32_t *,uint32_t *);
*/
import "C"
import (
    "fmt"
    "runtime"
    "unsafe"
)

// Only this EXTRA opt-in test build may call this private owner binding
// after EstablishServerV4 has checked actual TLS credentials and Detach.
// Profile 5 / revision 1 is a FIXED PROBE, not the real applied GUI policy.
func v4Fec2ProbeAfterProtectedCommit(b *v4EmbeddedNativeBridge) error {
    if b.protectedFeatures==v4RequiredFeatures {
        return nil
    }
    if b.protectedFeatures!=v4RequiredFeatures|v4FeatureFEC2 ||
        b.protectedEpoch==[16]byte{} || b.handle==0 {
        return errV4Embedded
    }
    rc:=C.wbd_m0_embedded_go_bind_fec2_probe_after_verified_tls(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&b.protectedEpoch[0])),
        C.size_t(16),C.uint16_t(b.protectedFeatures),C.uint8_t(5),C.uint64_t(1))
    runtime.KeepAlive(b.protectedEpoch)
    if rc!=0{return fmt.Errorf("%w: private FEC2 owner grant %d",errV4Embedded,int(rc))}
    return nil
}
func (b *v4EmbeddedNativeBridge) fec2ProbeScope(epoch [16]byte) bool {
    if b.handle==0{return false}
    rc:=C.wbd_m0_embedded_go_fec2_probe_scope_status(
        C.uint64_t(b.handle),(*C.uchar)(unsafe.Pointer(&epoch[0])),C.size_t(16))
    runtime.KeepAlive(epoch)
    return rc==0
}

// Explicit EXTRA-test-only bound Go TLS owner M4 raw kernel FEC2 send.
// Not the real automatic M1 scheduler or RX repair, never a product API.
func (b *v4EmbeddedNativeBridge) fec2ProbeKernelRawTx(
    ifindex uint32,
)([2]uint64,[2]uint32,[2]uint32,error){
    var pn [2]uint64
    var seq [2]uint32
    var length [2]uint32
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return pn,seq,length,errV4Embedded
    }
    rc:=C.wbd_m0_embedded_go_fec2_probe_real_raw_tx(
        C.uint64_t(b.handle),C.uint32_t(ifindex),
        (*C.uint64_t)(unsafe.Pointer(&pn[0])),
        (*C.uint64_t)(unsafe.Pointer(&pn[1])),
        (*C.uint32_t)(unsafe.Pointer(&seq[0])),
        (*C.uint32_t)(unsafe.Pointer(&seq[1])),
        (*C.uint32_t)(unsafe.Pointer(&length[0])),
        (*C.uint32_t)(unsafe.Pointer(&length[1])))
    if rc!=0 {return pn,seq,length,fmt.Errorf("%w: native M4 FEC2 raw probe %d",errV4Embedded,int(rc))}
    return pn,seq,length,nil
}
