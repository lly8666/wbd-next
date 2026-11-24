//go:build linux && !android && cgo && wbd_v4_embedded_go

package v4productcli

// Keep all existing original Linux routes under their original owner. The
// Android dedicated uidrange table is not accepted on Linux and cannot be
// accidentally installed by a Linux source-locked product build.
func androidRootRouteAfterNative(
    _ config,_ *ownedTun,_ string,
)(func()error,error){return nil,nil}
