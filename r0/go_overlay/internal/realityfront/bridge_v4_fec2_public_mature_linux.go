//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront
// Product uses same actual M4 copied source+parity and original M3
// authenticated M2 coverage, never a GUI/Go APPLIED assertion.
func v4PublicMatureFixedNative(
    b *v4EmbeddedNativeBridge,epoch [16]byte,revision uint64,
)error{return b.commitOriginalFixedMatureM2(epoch,revision)}
