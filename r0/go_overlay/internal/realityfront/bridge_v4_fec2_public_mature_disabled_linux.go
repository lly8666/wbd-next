//go:build linux && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product
package realityfront
// Missing native FEC2 product feature is NOT a protocol/fixture APPLIED
// success. Real public CLI mode must be built with both Go and Rust release.
func v4PublicMatureFixedNative(_ *v4EmbeddedNativeBridge,_ [16]byte,_ uint64)error{
    return ErrAdmissionUnsupported
}

func v4ReadOriginalFecRxIpClass(_ *v4EmbeddedNativeBridge)(V4PublicFecRxIpClass,error){
    return V4PublicFecRxIpClass{},ErrAdmissionUnsupported
}

func v4ReadOriginalFecM1Ingress(_ *v4EmbeddedNativeBridge)(V4PublicFecM1Ingress,error){
    return V4PublicFecM1Ingress{},ErrAdmissionUnsupported
}

// No product feature: no fake zero recovered-counter result.
func v4ReadOriginalFecRxProof(_ *v4EmbeddedNativeBridge)(V4PublicFecRxProof,error){
    return V4PublicFecRxProof{},ErrAdmissionUnsupported
}
