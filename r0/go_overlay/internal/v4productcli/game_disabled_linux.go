//go:build linux && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product

package v4productcli

import (
    "context"
    "fmt"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// Original Go V4 Game2/4 is an explicit source-locked native product
// capability. A build without the authenticated Rust Game owner cannot
// start a partial Go-only session, even when --mode game2/4 parses.
func runGame(_ context.Context,c config,_ uint32,_ *ownedTun,_ *logicaltunnel.LeaseRegistry,_ *realityfront.V4EpochStore,_ *bool)error{
    return fmt.Errorf("original Go V4 Game%d native M4 product not compiled",c.gameLanes)
}

// The exact same physical-path client supervisor compiles on builds where
// Game M4 is intentionally absent. No synthetic handshake/owner fallback.
func runGameClientGeneration(
 _ context.Context,c config,_ uint32,_ *ownedTun,
 _ *bool,_ chan<- struct{},
)error{
 return fmt.Errorf("original Go V4 Game%d native M4 product not compiled",c.gameLanes)
}
