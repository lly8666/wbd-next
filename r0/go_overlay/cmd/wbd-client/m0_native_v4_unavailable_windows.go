//go:build windows && !wbd_v4_embedded_go
package main
import "errors"
func runM0NativeV4Windows(m0NativeV4Options)error{
 return errors.New("original Go credential TLS native Rust V4 owner requires the pinned wbd_v4_embedded_go build; no V3 fallback")
}
