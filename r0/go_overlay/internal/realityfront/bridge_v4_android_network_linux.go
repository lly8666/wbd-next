//go:build linux && !android && cgo && wbd_v4_embedded_go

package realityfront

// The existing Linux raw carrier retains its proven exact ifindex, route
// watcher and MTU checks. Android-only network handles must never be mistaken
// for Linux routing or silently applied to a different platform.
func v4BindPlatformUnderlay(b *v4EmbeddedNativeBridge,cfg V4LinuxClientProductConfig)error{
    if b==nil||!b.committed||b.handle==0{return ErrAdmissionParams}
    if cfg.AndroidPhysicalNetworkHandle!=0||cfg.AndroidPhysicalMTU!=0{
        return ErrAdmissionParams
    }
    return nil
}
