//go:build linux && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product

package v4productcli

import (
    "context"
    "fmt"
)

// Original Go V4 Game2/4 is an explicit source-locked native product
// capability. A build without the authenticated Rust Game owner cannot
// start a partial Go-only session, even when --mode game2/4 parses.
func runGame(_ context.Context,c config,_ uint32,_ *ownedTun,_ *bool)error{
    return fmt.Errorf("original Go V4 Game%d native M4 product not compiled",c.gameLanes)
}
