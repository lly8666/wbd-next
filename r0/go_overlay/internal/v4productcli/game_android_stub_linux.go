//go:build linux && !android && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// This symbol exists only to satisfy the shared original-Go CLI compiler.
// Linux's existing Game2/4 path remains exclusively in game_linux.go.
func runAndroidGame(_ context.Context,_ config,_ uint32,_ *ownedTun,_ *bool)error{
    return realityfront.ErrAdmissionUnsupported
}
