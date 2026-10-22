//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront
/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_loop_fec_rx_proof(uint64_t,uint64_t*,size_t);
*/
import "C"
// Product uses same actual M4 copied source+parity and original M3
// authenticated M2 coverage, never a GUI/Go APPLIED assertion.
func v4PublicMatureFixedNative(
    b *v4EmbeddedNativeBridge,epoch [16]byte,revision uint64,
)error{return b.commitOriginalFixedMatureM2(epoch,revision)}

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
