//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_loop_fec_rx_proof(uint64_t,uint64_t*,size_t);
extern int32_t wbd_m0_embedded_go_loop_fec_rx_ip_classes(uint64_t,uint64_t*,size_t);
extern int32_t wbd_m0_embedded_go_loop_fec_m1_ingress(uint64_t,uint64_t*,size_t);
extern int32_t wbd_m0_embedded_go_loop_fec_m1_stage(uint64_t,uint64_t*,size_t);
*/
import "C"
// Product uses same actual M4 copied source+parity and original M3
// authenticated M2 coverage, never a GUI/Go APPLIED assertion.
func v4PublicMatureFixedNative(
    b *v4EmbeddedNativeBridge,epoch [16]byte,revision uint64,
)error{return b.commitOriginalFixedMatureM2(epoch,revision)}

// Authenticated same native owner, read-only post-TUN stage outcomes.
// No alternate Go sender; no payload/endpoint/record identifiers.
func v4ReadOriginalFecM1Stage(b *v4EmbeddedNativeBridge)(V4PublicFecM1Stage,error){
    var zero V4PublicFecM1Stage
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,ErrAdmissionUnsupported}
    var n [6]C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_fec_m1_stage(C.uint64_t(b.handle),&n[0],C.size_t(len(n)))
    if rc!=0{return zero,ErrAdmissionUnsupported}
    return V4PublicFecM1Stage{
        Attempted:uint64(n[0]),Queued:uint64(n[1]),
        NotReady:uint64(n[2]),Error:uint64(n[3]),
        OversizePrecheck:uint64(n[4]),ModeSkipped:uint64(n[5]),
    },nil
}

// Original credential-bound Rust TX worker counters. No second Go TUN
// reader and no inference from raw socket/ACK/packet shape.
func v4ReadOriginalFecM1Ingress(b *v4EmbeddedNativeBridge)(V4PublicFecM1Ingress,error){
    var zero V4PublicFecM1Ingress
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,ErrAdmissionUnsupported}
    var n [5]C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_fec_m1_ingress(C.uint64_t(b.handle),&n[0],C.size_t(len(n)))
    if rc!=0{return zero,ErrAdmissionUnsupported}
    return V4PublicFecM1Ingress{
        ReadIPv4:uint64(n[0]),SmallLoaned:uint64(n[1]),
        SmallArenaFail:uint64(n[2]),Jumbo:uint64(n[3]),
        Rejected:uint64(n[4]),
    },nil
}

// Exact original M4-success IPv4 protocol/ACK-class numeric-only snapshot.
// No Go classifier, no packet bytes, no endpoint address, no second opener.
func v4ReadOriginalFecRxIpClass(b *v4EmbeddedNativeBridge)(V4PublicFecRxIpClass,error){
    var zero V4PublicFecRxIpClass
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,ErrAdmissionUnsupported}
    var n [8]C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_fec_rx_ip_classes(C.uint64_t(b.handle),&n[0],C.size_t(len(n)))
    if rc!=0{return zero,ErrAdmissionUnsupported}
    return V4PublicFecRxIpClass{
        SystematicUDP:uint64(n[0]),RecoveredUDP:uint64(n[1]),
        SystematicTCP:uint64(n[2]),RecoveredTCP:uint64(n[3]),
        OtherIP:uint64(n[4]),TCPAckOnly:uint64(n[5]),
        TCPData:uint64(n[6]),TCPOther:uint64(n[7]),
    },nil
}

// Original M3/M4 numeric counters; once before native Stop.
func v4ReadOriginalFecRxProof(b *v4EmbeddedNativeBridge)(V4PublicFecRxProof,error){
    var zero V4PublicFecRxProof
    if b==nil||!b.committed||b.stopped||b.handle==0{return zero,ErrAdmissionUnsupported}
    var n [11]C.uint64_t
    rc:=C.wbd_m0_embedded_go_loop_fec_rx_proof(C.uint64_t(b.handle),&n[0],C.size_t(len(n)))
    if rc!=0{return zero,ErrAdmissionUnsupported}
    return V4PublicFecRxProof{SourceSeen:uint64(n[0]),SourceAccepted:uint64(n[1]),
        ParitySeen:uint64(n[2]),ParityAccepted:uint64(n[3]),
        SystematicCandidate:uint64(n[4]),RecoveredCandidate:uint64(n[5]),
        SystematicTun:uint64(n[6]),RecoveredTun:uint64(n[7]),
        TunFailed:uint64(n[8]),DecoderRejected:uint64(n[9]),
        AdmissionDisabled:uint64(n[10])},nil
}
