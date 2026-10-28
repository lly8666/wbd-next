//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "testing"
    "unsafe"
)
func TestN4RustNativeWintunABIAndStopFence(t *testing.T) {
    width:=unsafe.Sizeof(uintptr(0))
    if unsafe.Sizeof(N4RustWintunFnsV1{})!=4*width {
        t.Fatal("WintunFns V1 != four WIN32 function pointers")
    }
    d:=&N4OriginalKernelPacketLease{nativeRustLoan:true}
    if err:=d.Stop(context.Background());!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("Go Stop must refuse while Rust owns ring: %v",err)
    }
    l:=&N4RustWintunLoan{owner:d,native:N4RustWintunNativeV1{Session:1}}
    if _,err:=l.Native();err!=nil{t.Fatal(err)}
    // No fake Rust worker in this fixture: just prove Go fence semantics.
    // The actual release requires a real OS-owned TUN/active call.
    l.closed=true
    if _,err:=l.Native();!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("stale Wintun loan exposed native session: %v",err)
    }
}
