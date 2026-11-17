//go:build android && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product

package realityfront

// Android ARM64's genuine Normal/off first-connection edition has NO
// original FEC2 source/parity/M2 product receiver. Explicitly reject
// unsupported Fixed/Auto at the same Go policy boundary before any
// native ABI call; never invent Rust fixed_stage_pending/readback symbols.
func (b *v4EmbeddedNativeBridge) stageOriginalFixedPending(
    cfg FecV2Config,prev FecV2State,_ [16]byte,
)(FecV2State,FecV2Ack,error){
    ack:=FecV2Ack{Client:cfg.Client,Direction:cfg.Direction,
        Revision:cfg.ConfigRevision,Rejected:true}
    return prev,ack,ErrAdmissionUnsupported
}
func (b *v4EmbeddedNativeBridge) stageOriginalAutoRevision(
    _ [16]byte,_ FecV2State,_ FecV2Intent,
)error{return ErrAdmissionUnsupported}
func (b *v4EmbeddedNativeBridge) readbackOriginalFixedPending(
    pending FecV2State,_ [16]byte,
)(FecV2State,FecV2Ack,error){
    return pending,FecV2Ack{Client:pending.Client,
        Direction:pending.Direction,Revision:pending.RequestedRevision,
        Profile:pending.Desired,Rejected:true},ErrAdmissionUnsupported
}
