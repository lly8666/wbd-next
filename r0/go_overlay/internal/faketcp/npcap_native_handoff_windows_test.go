//go:build windows

package faketcp

import (
    "errors"
    "io"
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

func TestNpcapNativeGameColdReadTimeoutYieldsBeforeCaptureLoan(t *testing.T){
 e:=&NpcapEndpoint{gate:newNpcapCallGate(1)}
 done:=make(chan struct{});reads:=0
 _,_,err:=e.readSegmentUntil(1,done,func(_ **pcapHeader,_ *uintptr)int32{
  reads++;if reads==3{close(done)};return 0
 })
 if !errors.Is(err,ErrNpcapClosed)||reads!=3{t.Fatalf("idle NPF never yielded: %d %v",reads,err)}
 if !e.gate.close(){t.Fatal("NPF gate cannot join after signal")}
 e.gate.wait()
}
func TestNpcapNativeGameColdReadKeepsGenuineEOF(t *testing.T){
 e:=&NpcapEndpoint{gate:newNpcapCallGate(1)};done:=make(chan struct{})
 _,_,err:=e.readSegmentUntil(1,done,func(_ **pcapHeader,_ *uintptr)int32{return -2})
 if !errors.Is(err,io.EOF){t.Fatalf("unexpected NPF EOF masked: %v",err)}
 close(done);reads:=0
 _,_,err=e.readSegmentUntil(1,done,func(_ **pcapHeader,_ *uintptr)int32{reads++;return -2})
 if !errors.Is(err,ErrNpcapClosed)||reads!=0{t.Fatalf("read after transfer: %d %v",reads,err)}
}
