//go:build linux && !android && cgo && wbd_v4_embedded_go

package realityfront

// Android has its own original native M4 counter ABI.
func (p *V4LinuxClientProduct) OriginalAndroidFixedM4Counters()([9]uint64,error){
    return [9]uint64{},ErrAdmissionUnsupported
}
