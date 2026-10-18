//go:build linux && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_owner_probe

package realityfront

// Ordinary build has NO Rust FEC2 owner binding function or symbol.
// The private bit2 handshake remains metadata-only, product FEC2 OFF.
func v4Fec2ProbeAfterProtectedCommit(_ *v4EmbeddedNativeBridge) error {
    return nil
}
