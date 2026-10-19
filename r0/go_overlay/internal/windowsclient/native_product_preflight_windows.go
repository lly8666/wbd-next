//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "fmt"

    "golang.org/x/sys/windows"
)

// N4ProductPreflight is a bounded READ-ONLY diagnosis, not a network-ready
// capability ticket. No JSON field can authorize WFP rule installation.
type N4ProductPreflight struct {
    Schema string `json:"schema"`
    NativeAPIs bool `json:"native_apis"`
    WFPLayersReadable bool `json:"wfp_layers_readable"`
    Elevated bool `json:"elevated"`
    DiskState string `json:"disk_state"`
    NativeWAL bool `json:"native_wal"`
    RouteIntent bool `json:"route_intent"`
    Ready bool `json:"ready"`
    WFPInstallQualified bool `json:"wfp_install_qualified"`
    Blockers []string `json:"blockers"`
}

const N4ProductPreflightSchema = "wbd-native-product-preflight/v1"

// N4ReadOnlyProductPreflight checks the real Win32 privilege and system API
// availability, plus the existing exact disk inspector. It MUST NEVER open
// a Wintun session, create a firewall filter, alter DNS or install routes.
// Until the original Go authenticated Stop, WFP Arm and owned rollback are
// proven together, Ready and WFPInstallQualified are always false.
func N4ReadOnlyProductPreflight(ctx context.Context, statePath string)(N4ProductPreflight,error){
    p:=N4ProductPreflight{
        Schema:N4ProductPreflightSchema, Blockers:[]string{},
        Ready:false, WFPInstallQualified:false, DiskState:"unverified",
    }
    if ctx==nil{return p,ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return p,err}
    // Preserve the existing strict absolute-path rule. No config-file,
    // credentials, driver or mutable network state is required.
    state,err:=N4NativeInspectState(ctx,statePath)
    p.DiskState=state.State
    p.NativeWAL=state.NativeWAL
    p.RouteIntent=state.RouteIntent
    if err!=nil{
        if errors.Is(err,context.Canceled)||errors.Is(err,context.DeadlineExceeded)||
            errors.Is(err,ErrNetworkPlan){return p,err}
        p.Blockers=append(p.Blockers,"owned_disk_state_unverified")
    }
    if state.State!="absent" {
        p.Blockers=append(p.Blockers,"network_state_not_empty")
    }
    if err:=ctx.Err();err!=nil{return p,err}
    _,capErr:=N4ScriptlessWindowsCapability()
    p.NativeAPIs=capErr==nil
    if capErr!=nil{p.Blockers=append(p.Blockers,"native_windows_api_unavailable")}
    // WFP layer open/get is a READ-ONLY engine query. A successful layer
    // read DOES NOT prove rule matching or that filters are installed.
    layerErr:=(N4NativeWFPReader{}).VerifyLayers()
    p.WFPLayersReadable=layerErr==nil
    if layerErr!=nil{p.Blockers=append(p.Blockers,"wfp_layer_read_unavailable")}
    p.Elevated=windows.GetCurrentProcessToken().IsElevated()
    if !p.Elevated{p.Blockers=append(p.Blockers,"requires_elevated_original_client")}
    // Never interpret lack of these blockers as readiness. This final
    // production gate is unconditional until end-to-end real native proof.
    p.Blockers=append(p.Blockers,"wfp_guard_and_authenticated_stop_not_qualified")
    if len(p.Blockers)==0{return p,fmt.Errorf("%w: missing production blocker",ErrN4NativeGuard)}
    return p,ctx.Err()
}
