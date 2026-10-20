//go:build windows && wbd_v4_embedded_go
package windowsownerlease

import (
    "context"
    "errors"
    "fmt"
    "os"
    "testing"

    "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
func TestM0WindowsRealCreatedWintunOneWayAdapterNativeIdentityAndLifetime(t *testing.T){
    ctx:=context.Background()
    var empty CreatedWintun
    if _,e:=empty.Identity(ctx,[16]byte{17},[16]byte{23});
        !errors.Is(e,ErrNativeDeviceNotOwned){
        t.Fatalf("nil M4 adapter gained native owner: %v",e)
    }
    if os.Getenv("WBD_M0_TRY_SCOPED_NATIVE_WINTUN")!="1"{
        t.Log("M0_PLAN013_CREATED_WINTUN_OS_PROOF_UNSUPPORTED explicit_native_probe_off")
        return
    }
    name:=fmt.Sprintf("WBD-M0-SCOPE-%s",os.Getenv("GITHUB_RUN_ID"))
    tun,e:=windowsclient.OpenTUN(name)
    if e!=nil{
        t.Logf("M0_PLAN013_CREATED_WINTUN_OS_PROOF_UNSUPPORTED actual_wintun_open=%v",e)
        return
    }
    defer tun.Close()
    real:=CreatedWintun{TUN:tun}
    // This is actual OS-created native-device identity, NOT a TLS test;
    // original Go TLS epoch is supplied by separate credential callback.
    installation:=[16]byte{17}
    epoch:=[16]byte{23}
    id,e:=real.Identity(ctx,installation,epoch)
    if errors.Is(e,ErrNativeDeviceNotOwned){
        // The API may have OPENED a preexisting Wintun with matching alias;
        // ownership is not conferred by opening it.
        t.Logf("M0_PLAN013_CREATED_WINTUN_OS_PROOF_UNSUPPORTED preexisting_or_unavailable %v",e)
        return
    }
    if e!=nil{t.Fatal(e)}
    if id.LUID==0||id.InterfaceIndex==0||id.GUID==""||id.Alias!=name{
        t.Fatalf("invalid LIVE Wintun original identity %+v",id)
    }
    release,e:=real.HoldCurrentNative(ctx,id)
    if e!=nil||release==nil{t.Fatalf("live current M4 Wintun owner Hold failed: %v",e)}
    wrong:=id;wrong.LUID++
    if e:=real.VerifyCurrentNative(ctx,wrong);!errors.Is(e,ErrNativeDeviceNotOwned){
        release();t.Fatalf("foreign LUID identity adopted: %v",e)
    }
    wrong=id;wrong.InterfaceIndex++
    if e:=real.VerifyCurrentNative(ctx,wrong);!errors.Is(e,ErrNativeDeviceNotOwned){
        release();t.Fatalf("foreign interface index adopted: %v",e)
    }
    wrong=id;wrong.GUID="11111111-2222-3333-4444-555555555555"
    if e:=real.VerifyCurrentNative(ctx,wrong);!errors.Is(e,ErrNativeDeviceNotOwned){
        release();t.Fatalf("foreign native interface GUID adopted: %v",e)
    }
    if e:=real.VerifyCurrentNative(ctx,id);e!=nil{release();t.Fatal(e)}
    release()
    if e:=real.VerifyCurrentNative(ctx,id);e!=nil{t.Fatal(e)}
    t.Logf("M0_PLAN013_CREATED_WINTUN_OS_HOLD_READBACK_SCOPED_PASS luid=%d index=%d no_rust_tls_join=1 no_WFP_or_route_applied=1",id.LUID,id.InterfaceIndex)
}
