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
    WFPLayersReadable bool `json:"wfp_layers_readable"` // retired under v2
    Elevated bool `json:"elevated"`
    DiskState string `json:"disk_state"`
    NativeWAL bool `json:"native_wal"`
    RouteIntent bool `json:"route_intent"`
    Ready bool `json:"ready"`
    WFPInstallQualified bool `json:"wfp_install_qualified"` // retired under v2
    Blockers []string `json:"blockers"`
}

const N4ProductPreflightSchema = "wbd-native-product-preflight/v1"

// N4ReadOnlyProductPreflight checks the real Win32 privilege and system API
// availability, plus the existing exact disk inspector. It MUST NEVER open
// a Wintun session, create a firewall filter, alter DNS or install routes.
// This is a read-only inspector, not an authenticated TLS/current-generation
// packet owner. Ready and retired WFPInstallQualified are always false here.
// The real product Connect checks live four-stage Win32 Apply/OS readback,
// packet first+reverse and owned Stop separately.
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
    // No old-WFP API read or guard is a PLAN029 prerequisite. Keep the
    // legacy JSON field for compatible CLI reads, always false.
    p.WFPLayersReadable=false
    p.Elevated=windows.GetCurrentProcessToken().IsElevated()
    if !p.Elevated{p.Blockers=append(p.Blockers,"requires_elevated_original_client")}
    // Read-only inspection cannot produce a current-generation owned Rust
    // data-plane/Win32 Applied receipt. This is not the old circular
    // "four stages cannot be executed until tested" guard: authenticated
    // N4PrepareRealWindowsProduct may perform the actual live transaction.
    p.Blockers=append(p.Blockers,"authenticated_live_owner_and_applied_receipt_not_inspected")
    if len(p.Blockers)==0{return p,fmt.Errorf("%w: missing production blocker",ErrN4NativeGuard)}
    return p,ctx.Err()
}
