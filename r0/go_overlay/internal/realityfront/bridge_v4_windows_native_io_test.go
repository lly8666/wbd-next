//go:build windows && wbd_v4_embedded_go

package realityfront

import ("testing";"unsafe")
func TestNativeV1ABIHasStablePointerTables(t *testing.T) {
    ptr:=unsafe.Sizeof(uintptr(0))
    if ptr!=8{t.Skip("Windows product is x64 only")}
    if unsafe.Sizeof(V4WindowsNpcapNativeFnsV1{})!=6*ptr ||
       unsafe.Sizeof(V4WindowsWintunNativeFnsV1{})!=4*ptr{
        t.Fatal("Rust NativeFn ABI changed")
    }
    var v V4WindowsNativeIOV1
    if unsafe.Offsetof(v.Npcap)%8!=0 ||
       unsafe.Offsetof(v.Wintun)!=unsafe.Offsetof(v.Npcap)+6*ptr{
        t.Fatal("ABI field table offsets changed")
    }
    if unsafe.Sizeof(V4WindowsNativeWorkerStatsV1{})!=48 {
        t.Fatal("Native status ABI changed")
    }
}
