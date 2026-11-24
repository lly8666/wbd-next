//go:build android && cgo && wbd_v4_embedded_go

package v4productcli

import "errors"

// PLAN030 management is a Linux server feature, not an Android client
// dependency. Shared Run always supplies nil for the Android client.
type serverManagement struct{}

func prepareManagedNetwork(config)(func()error,error){
    return nil,errors.New("Linux server management is not available on Android")
}
func ManageServer([]string)error{
    return errors.New("Linux server management is not available on Android")
}
