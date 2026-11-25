//go:build linux && !android && cgo && wbd_v4_embedded_go

package v4productcli

import "context"

// Keep all existing original Linux routes under their original owner. The
// Android dedicated uidrange table is not accepted on Linux and cannot be
// accidentally installed by a Linux source-locked product build.
func androidRootRouteAfterNative(
    _ config,_ *ownedTun,_ string,
)(func()error,error){return nil,nil}

func checkOriginalAndroidTether(_ config)(func()error,error){return nil,nil}
func recoverOriginalAndroidTetherOffload()error{return nil}

func startOriginalAndroidTetherWatch(_ config,_ context.CancelFunc)(func(),error){return func(){},nil}
