//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront
import ("errors";"testing")
func TestM0Plan019NativeGameGroupRejectsMissingCommittedOriginalTLS(t *testing.T){
    var zero *V4LinuxGameVerifiedGroup
    if _,err:=zero.joinAuthenticatedOriginalRust(&v4EmbeddedNativeBridge{},&v4EmbeddedNativeBridge{});!errors.Is(err,ErrAdmissionParams){
        t.Fatalf("nil verified group got %v",err)
    }
    // No Go caller can create a native shared Game AEAD group out of
    // arbitrary references that merely have fabricated Go handle fields.
    g:=&V4LinuxGameVerifiedGroup{}
    if _,err:=g.joinAuthenticatedOriginalRust(&v4EmbeddedNativeBridge{
        handle:1,committed:true,protectedLane:1,
    },&v4EmbeddedNativeBridge{
        handle:2,committed:true,protectedLane:2,
    });!errors.Is(err,ErrAdmissionUnsupported){
        t.Fatalf("unverified cold became Game shared owner: %v",err)
    }
    t.Log("M0_PLAN019_NATIVE_GAME_SHARED_ORIGINAL_TLS_MISSING_AUTH_DENIED native_driver_NOT_RUN=1")
}
