//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "os"
    "path/filepath"
    "testing"
)

// All cases are valid on NON-admin hosted Windows CI and do not write host
// network configuration. Each test independently refuses false product PASS.
func TestPLAN010NativeOriginalProductPreflightReadOnlyDenied(t *testing.T){
    p:=filepath.Join(t.TempDir(),"state.json")
    ctx:=context.Background()
    r,err:=N4ReadOnlyProductPreflight(ctx,p)
    if err!=nil{t.Fatal(err)}
    if r.Schema!=N4ProductPreflightSchema || r.DiskState!="absent" ||
        r.Ready||r.WFPInstallQualified||len(r.Blockers)==0{
        t.Fatalf("read-only prerequisites became product admission: %+v",r)
    }
    if _,err:=os.Stat(p);!errors.Is(err,os.ErrNotExist){t.Fatalf("preflight mutated state: %v",err)}
    hasBlocker:=func(r N4ProductPreflight,key string)bool{
        for _,v:=range r.Blockers{if v==key{return true}}
        return false
    }
    if !hasBlocker(r,"wfp_guard_and_authenticated_stop_not_qualified"){
        t.Fatal("WFP/Stop product hard gate disappeared")
    }
    legacy:=[]byte(`{"old_network_script":true}`)
    if err:=os.WriteFile(p,legacy,0600);err!=nil{t.Fatal(err)}
    r,err=N4ReadOnlyProductPreflight(ctx,p)
    if err!=nil||r.DiskState!="legacy_journal"||r.Ready||
        !hasBlocker(r,"network_state_not_empty"){
        t.Fatalf("old script state incorrectly accepted %+v %v",r,err)
    }
    actual,err:=os.ReadFile(p)
    if err!=nil||string(actual)!=string(legacy){t.Fatal("legacy state changed",err)}
    if err:=os.Remove(p);err!=nil{t.Fatal(err)}
    wal:=p+".n4-owned-wal"
    corrupt:=[]byte("not SHA-authenticated owned native WAL")
    if err:=os.WriteFile(wal,corrupt,0600);err!=nil{t.Fatal(err)}
    r,err=N4ReadOnlyProductPreflight(ctx,p)
    if err!=nil||r.DiskState!="invalid_native_wal"||r.Ready||
        !hasBlocker(r,"owned_disk_state_unverified"){
        t.Fatalf("invalid WAL accepted %+v %v",r,err)
    }
    actual,err=os.ReadFile(wal)
    if err!=nil||string(actual)!=string(corrupt){t.Fatal("untrusted WAL changed",err)}
    if err:=os.Remove(wal);err!=nil{t.Fatal(err)}
    route:=wal+".routes"
    if err:=os.WriteFile(route,[]byte("pending route intent"),0600);err!=nil{t.Fatal(err)}
    r,err=N4ReadOnlyProductPreflight(ctx,p)
    if err!=nil||r.DiskState!="orphan_route_intent"||r.Ready||!r.RouteIntent {
        t.Fatalf("orphan route intent falsely cleared %+v %v",r,err)
    }
    if _,err:=os.Stat(route);err!=nil{t.Fatal("route receipt removed",err)}
    cancelCtx,cancel:=context.WithCancel(ctx);cancel()
    if _,err:=N4ReadOnlyProductPreflight(cancelCtx,p);!errors.Is(err,context.Canceled){
        t.Fatalf("cancellation ignored: %v",err)
    }
    if _,err:=N4ReadOnlyProductPreflight(ctx,"relative");!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
    if _,err:=N4ReadOnlyProductPreflight(nil,p);!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
}
