//go:build windows

package faketcp

import (
    "errors"
    "testing"
    "unsafe"
)

// A pure ABI/layout test; does not pretend to own a real pcap_t or give
// original-Go TLS credentials to a fake driver.
func TestNpcapNativeFnsV1Layout(t *testing.T) {
    pointer := unsafe.Sizeof(uintptr(0))
    if unsafe.Sizeof(NpcapNativeFnsV1{}) != 6*pointer {
        t.Fatal("Rust NpcapFns sendqueue layout changed")
    }
    if unsafe.Offsetof(NpcapNativeFnsV1{}.SendPacket) != pointer ||
        unsafe.Offsetof(NpcapNativeFnsV1{}.GetEvent) != 2*pointer ||
        unsafe.Offsetof(NpcapNativeFnsV1{}.QueueAlloc) != 3*pointer ||
        unsafe.Offsetof(NpcapNativeFnsV1{}.QueueTransmit) != 4*pointer ||
        unsafe.Offsetof(NpcapNativeFnsV1{}.QueueDestroy) != 5*pointer {
        t.Fatal("C function table field offsets changed")
    }
}
func TestNpcapNativeCaptureRequiresLiveOwnedLoan(t *testing.T) {
    lease := &NpcapNativeCaptureLease{}
    if _,err:=lease.Native();!errors.Is(err,ErrNpcapClosed){
        t.Fatalf("empty lease produced native authority: %v",err)
    }
    if err:=lease.CloseAfterRustJoin();err!=nil{t.Fatal(err)}
    if err:=lease.CloseAfterRustJoin();err!=nil{t.Fatal(err)}
    if _,err:=lease.Native();!errors.Is(err,ErrNpcapClosed){
        t.Fatalf("closed lease produced native authority: %v",err)
    }
}
