//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

// Original-Go verified client-side V4 FEC2 release-code native RX.
// This file never exists in ordinary (feature3/default) Go builds.
// It consumes only an unmodified real TLS V4ClientSession ColdSnapshot;
// raw ciphertext must be supplied by the original checked kernel ingress.
// A decoder plus TUN writer is NOT a complete product Connect/Auto/M2 grant.
package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_release_client_fec2_prepare(
    const unsigned char *,size_t,int32_t,const unsigned char *,size_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_release_client_fec2_receive(
    uint64_t,const unsigned char *,size_t,const unsigned char *,size_t,
    uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_release_client_fec2_stop(
    uint64_t,const unsigned char *,size_t);
*/
import "C"
import (
    "fmt"
    "runtime"
    "unsafe"
)

type v4Fec2ReleaseClientRx struct {
    owner uint64
    epoch [16]byte
    stopped bool
}
type v4Fec2NativeReceipt struct {
    KernelDelivered uint32
    Recovered uint32
}
// Called only AFTER original Go protected Client V4 TLS verification, and
// only for exact feature7. The Go OS owner must have created a real native
// IFF_TUN+NO_PI descriptor. Rust dup's it and rejects names/modes/scopes.
func (s *V4ClientSession) prepareFec2ReleaseClientTun(
    fd uintptr,name string,
)(*v4Fec2ReleaseClientRx,error){
    if s==nil||fd<3||len(name)==0||len(name)>15 {
        return nil,ErrAdmissionParams
    }
    authenticated,err:=s.ColdSnapshot()
    if err!=nil{return nil,err}
    if authenticated.server ||
        authenticated.features!=v4RequiredFeatures|v4FeatureFEC2 ||
        authenticated.epoch==[16]byte{}{
        return nil,ErrAdmissionUnsupported
    }
    cold,err:=authenticated.MarshalColdBundle()
    if err!=nil{return nil,err}
    nameBytes:=[]byte(name)
    var handle C.uint64_t
    rc:=C.wbd_m0_embedded_go_release_client_fec2_prepare(
        (*C.uchar)(unsafe.Pointer(&cold[0])),C.size_t(len(cold)),
        C.int32_t(fd),(*C.uchar)(unsafe.Pointer(&nameBytes[0])),
        C.size_t(len(nameBytes)),&handle)
    runtime.KeepAlive(cold);runtime.KeepAlive(nameBytes)
    if rc!=0||handle==0{
        return nil,fmt.Errorf("%w: verified client RX prepare=%d",errV4Embedded,int(rc))
    }
    return &v4Fec2ReleaseClientRx{owner:uint64(handle),
        epoch:authenticated.epoch},nil
}
// Called by the real OS owner after the original client flow tuple/TCP
// checksum and generation have been checked. Only native M3 AEAD/unique
// PN and native M4 TUN kernel copy can increment this scoped receipt.
func (r *v4Fec2ReleaseClientRx) consumeAuthenticatedKernelRecord(
    wire []byte,
)(v4Fec2NativeReceipt,error){
    var zero v4Fec2NativeReceipt
    if r==nil||r.owner==0||r.stopped||len(wire)<31||len(wire)>2048{
        return zero,ErrAdmissionParams
    }
    var copied,recovered C.uint32_t
    rc:=C.wbd_m0_embedded_go_release_client_fec2_receive(
        C.uint64_t(r.owner),(*C.uchar)(unsafe.Pointer(&r.epoch[0])),
        C.size_t(16),(*C.uchar)(unsafe.Pointer(&wire[0])),
        C.size_t(len(wire)),&copied,&recovered)
    runtime.KeepAlive(wire)
    if rc!=0{return zero,fmt.Errorf("%w: authenticated client RX=%d",
        errV4Embedded,int(rc))}
    return v4Fec2NativeReceipt{
        KernelDelivered:uint32(copied),Recovered:uint32(recovered),
    },nil
}
// Stop is terminal; an incomplete Rust kernel borrowing drain retains
// ownership so Go can retry and does not issue a false Disconnect.
func (r *v4Fec2ReleaseClientRx) stop()error{
    if r==nil{return ErrAdmissionParams}
    if r.stopped&&r.owner==0{return nil}
    if r.owner==0{return ErrAdmissionParams}
    rc:=C.wbd_m0_embedded_go_release_client_fec2_stop(
        C.uint64_t(r.owner),(*C.uchar)(unsafe.Pointer(&r.epoch[0])),
        C.size_t(16))
    if rc!=0{return fmt.Errorf("%w: client FEC2 stop=%d",errV4Embedded,int(rc))}
    r.owner=0;r.stopped=true
    return nil
}
