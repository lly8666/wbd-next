//go:build linux && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product
package realityfront
// Missing native FEC2 product feature is NOT a protocol/fixture APPLIED
// success. Real public CLI mode must be built with both Go and Rust release.
func v4PublicMatureFixedNative(_ *v4EmbeddedNativeBridge,_ [16]byte,_ uint64)error{
    return ErrAdmissionUnsupported
}
