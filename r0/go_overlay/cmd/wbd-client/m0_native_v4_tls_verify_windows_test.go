//go:build windows && wbd_v4_embedded_go
package main
import "testing"
func TestH2214NativeWindowsTLSVerifySwitch(t *testing.T) {
 var opts m0NativeV4Options
 if opts.TLSVerifyServer {t.Fatal("default must be false")}
 opts.TLSVerifyServer=true
 if !opts.TLSVerifyServer {t.Fatal("true option must be preserved")}
}
