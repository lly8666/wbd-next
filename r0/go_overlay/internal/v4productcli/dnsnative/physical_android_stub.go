//go:build !android || !cgo

package dnsnative

// Never silently substitute a host net.Dialer for an Android Network
// handle. This stub also keeps source-locked CGO_ENABLED=0 ARM64 Go test
// ELF builds and original Linux server/library builds explicit.
func NewAndroidPhysicalDNSDialer(PhysicalScope)(DialFunc,error){
 return nil,ErrUnbound
}
