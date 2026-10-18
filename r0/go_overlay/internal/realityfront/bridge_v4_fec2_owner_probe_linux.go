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
extern int32_t wbd_m0_embedded_go_fec2_probe_actual_peer_consume(
    uint64_t,const unsigned char *,size_t,unsigned char *,size_t,
    uint64_t *,uint8_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_fec2_probe_actual_m2_rx_feedback(
    uint64_t,uint64_t,uint8_t,uint32_t *,uint64_t *,uint64_t *,uint8_t *);
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

// Validated independent original Rust client receive-side AEAD/PN bitmap,
// using the immutable ORIGINAL Go TLS S2C direction keys. It is accessible
// only with the private feature+epoch bound sender owner still ACTIVE.
func (b *v4EmbeddedNativeBridge) fec2ProbeActualPeerConsume(
    cipherRecord []byte,
)(uint64,uint8,[]byte,error){
    if b.handle==0 || !b.committed || b.protectedFeatures!=7 ||
        len(cipherRecord)==0 {return 0,0,nil,errV4Embedded}
    decoded:=make([]byte,2048)
    var pn C.uint64_t
    var kind C.uint8_t
    var actual C.uint32_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_actual_peer_consume(
        C.uint64_t(b.handle),
        (*C.uchar)(unsafe.Pointer(&cipherRecord[0])),C.size_t(len(cipherRecord)),
        (*C.uchar)(unsafe.Pointer(&decoded[0])),C.size_t(len(decoded)),
        &pn,&kind,&actual)
    runtime.KeepAlive(cipherRecord)
    if rc!=0||int(actual)>len(decoded){
        return 0,0,nil,fmt.Errorf("%w: independent authenticated FEC2 peer %d",
            errV4Embedded,int(rc))
    }
    return uint64(pn),uint8(kind),decoded[:int(actual)],nil
}

// Actual M2 RX feedback draft only, NOT a cryptographically opened reverse
// receipt or a real on-wire send. Sent outcome is one of NotSent, Accepted,
// Uncertain, bound to the very same authenticated session/owner.
func (b *v4EmbeddedNativeBridge) fec2ProbeActualM2RxFeedback(
    nowNS uint64, outcome uint8,
)(uint32,uint64,uint64,uint8,error){
    if b.handle==0||!b.committed||b.protectedFeatures!=7{
        return 0,0,0,0,errV4Embedded
    }
    var seq C.uint32_t
    var max,base C.uint64_t
    var bits C.uint8_t
    rc:=C.wbd_m0_embedded_go_fec2_probe_actual_m2_rx_feedback(
        C.uint64_t(b.handle),C.uint64_t(nowNS),C.uint8_t(outcome),
        &seq,&max,&base,&bits)
    if rc!=0{return 0,0,0,0,
        fmt.Errorf("%w: authenticated M2 RX draft rc=%d",errV4Embedded,int(rc))}
    return uint32(seq),uint64(max),uint64(base),uint8(bits),nil
}
