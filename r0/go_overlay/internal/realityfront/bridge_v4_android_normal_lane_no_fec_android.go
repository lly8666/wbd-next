//go:build android && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product

package realityfront

// This is the same original TLS-authenticated Normal lane type consumed by
// V4LinuxServerProduct.AdoptAuthenticatedNormalLane, compiled only for the
// existing source-locked Android feature3/Normal-off product edition.
//
// The full Game2/4 code is correctly excluded by !wbd_v4_fec2_product.
// A valid Normal lane still requires the real verified Go session, cold
// policy, original committed Rust owner and original FakeTCP association.
// No Game handshake, owner, M2 receipt, fake capability, or Go data pump.
import "github.com/lly8666/wobuzhidao/internal/faketcp"

type V4LinuxGameAuthenticatedLane struct {
    session *V4ServerSession
    bridge *v4EmbeddedNativeBridge
    assoc *faketcp.ServerAssociation
    peerMSS uint16
    epochs *V4EpochStore
    transferred bool
}

func (l *V4LinuxGameAuthenticatedLane) ProtectedMode()(
    normal bool,lanes uint8,gameFec uint8,err error,
){
    if l==nil||l.session==nil||l.bridge==nil||
       !l.bridge.committed||l.bridge.stopped||l.assoc==nil{
        return false,0,0,ErrAdmissionParams
    }
    if _,err=l.session.ColdSnapshot();err!=nil{
        return false,0,0,err
    }
    policy:=l.session.verifiedPolicy
    if err=policy.SupportedNow();err!=nil{
        return false,0,0,err
    }
    // This edition permits only the original-Go authenticated
    // Normal/off request. Normal Fixed/Auto and Game2/4 stay UNAVAILABLE
    // until the actual native M2/repair/Game owner is source-locked.
    if policy.Transport!=TransportNormal||policy.DesiredLanes!=1||
       l.session.verifiedGameFec!=0||l.session.verifiedNormalFec!=0{
        return false,0,0,ErrAdmissionUnsupported
    }
    return true,1,0,nil
}
