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
    if unsafe.Sizeof(v)!=192 ||
       unsafe.Offsetof(v.RXCapture)!=80 ||
       unsafe.Offsetof(v.Npcap)!=112 ||
       unsafe.Offsetof(v.Wintun)!=160 {
        t.Fatal("Rust NativeOwner C attach V1 byte layout changed")
    }
    if unsafe.Offsetof(v.Npcap)%8!=0 ||
       unsafe.Offsetof(v.Wintun)!=unsafe.Offsetof(v.Npcap)+6*ptr{
        t.Fatal("ABI field table offsets changed")
    }
    if unsafe.Sizeof(V4WindowsNativeWorkerStatsV1{})!=48 {
        t.Fatal("Native status ABI changed")
    }
}

func TestNativeFixedAutoV2PreservesOriginalV1Layout(t *testing.T) {
    var v1 V4WindowsNativeIOV1
    var v2 V4WindowsNativeIOV2
    if got,want:=unsafe.Sizeof(v2),unsafe.Sizeof(v1)+16;got!=want{
        t.Fatalf("native V2 size=%d want=%d",got,want)
    }
    if unsafe.Offsetof(v2.Mode)!=8||unsafe.Offsetof(v2.Normal)!=16{
        t.Fatalf("native V2 fields are not a 16-byte cold wrapper")
    }
}
