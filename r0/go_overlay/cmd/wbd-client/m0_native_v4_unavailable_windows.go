//go:build windows && !wbd_v4_embedded_go
package main
import "errors"
func runM0NativeV4Windows(m0NativeV4Options)error{
 return errors.New("original Go credential TLS native Rust V4 owner requires the pinned wbd_v4_embedded_go build; no V3 fallback")
}

func m0WindowsV4StartupInnerMTU(_ string,_ uint32,_ uint32,
 _ m0WindowsV4Mode,_ bool)(int,error){
 return 0,errors.New("V4 Rust native cold MTU unavailable in this Windows build")
}
