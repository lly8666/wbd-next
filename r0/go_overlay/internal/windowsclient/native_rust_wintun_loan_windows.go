//go:build windows

package windowsclient

// PLAN026: one verified Go-owned Wintun session, borrowed by TWO Rust workers.
// This is a cold control-plane operation, NEVER a per-packet Go callback.
// The Rust functions are real exports from the same pinned wintun.dll loaded
// for the Go native OS owner; the module/session must outlive Rust Join.
import (
    "context"
    "sync"
)

// Exact pointer-width layout for the Rust windows_native_io::WintunFns.
// Function addresses are WINAPI/extern "system", not Go function pointers.
type N4RustWintunFnsV1 struct {
    Receive uintptr
    Release uintptr
    Allocate uintptr
    Send uintptr
}
type N4RustWintunNativeV1 struct {
    Session uintptr
    ReadEvent uintptr
    Fns N4RustWintunFnsV1
    WintunLUID uint64
    WintunIndex uint32
    Reserved uint32
}
type N4RustWintunLoan struct {
    mu sync.Mutex
    owner *N4OriginalKernelPacketLease
    native N4RustWintunNativeV1
    closed bool
}

// BorrowRustNativeRing uses the EXACT N4OriginalKernelPacketLease that was
// already authenticated and OS-pinned by the original Go/TLS+Rust owner.
// While borrowed, Go ring read/write/wait and Go N4 Stop refuse new work;
// TUN.Close is independently held by its active-call fence. The caller must
// call ReleaseAfterRustJoin only after every Rust RX/TX worker has joined and
// every Wintun packet loan was returned. Never create a second Wintun session.
func(d *N4OriginalKernelPacketLease) BorrowRustNativeRing(
    ctx context.Context,
)(*N4RustWintunLoan,error){
    if d==nil||ctx==nil{return nil,ErrN4NativeGuard}
    d.mu.Lock()
    defer d.mu.Unlock()
    if err:=d.check(ctx);err!=nil{return nil,err}
    if d.nativeRustLoan || d.tun==nil || !d.tun.beginCall(){
        return nil,ErrN4NativeGuard
    }
    // Proc addresses are resolved once on this cold path. The real Wintun
    // module is kept alive by the original Go owner until Rust quiescence.
    native:=N4RustWintunNativeV1{
        Session:d.tun.session,
        ReadEvent:d.tun.readEvt,
        WintunLUID:d.id.WintunLUID,
        WintunIndex:d.id.WintunIndex,
        Fns:N4RustWintunFnsV1{
            Receive:wintunReceivePacket.Addr(),
            Release:wintunReleaseReceivePacket.Addr(),
            Allocate:wintunAllocateSendPacket.Addr(),
            Send:wintunSendPacket.Addr(),
        },
    }
    if native.Session==0||native.ReadEvent==0||native.Fns.Receive==0||
       native.Fns.Release==0||native.Fns.Allocate==0||native.Fns.Send==0 {
        d.tun.endCall()
        return nil,ErrN4NativeGuard
    }
    d.nativeRustLoan=true
    return &N4RustWintunLoan{owner:d,native:native},nil
}
// Native returns native HANDLE/function addresses, not Go memory. The
// authenticated Rust V4 owner must still pin its session epoch/LUID/ifindex.
func(l *N4RustWintunLoan) Native()(N4RustWintunNativeV1,error){
    if l==nil{return N4RustWintunNativeV1{},ErrN4NativeGuard}
    l.mu.Lock()
    defer l.mu.Unlock()
    if l.closed||l.owner==nil{return N4RustWintunNativeV1{},ErrN4NativeGuard}
    return l.native,nil
}
func(l *N4RustWintunLoan) ReleaseAfterRustJoin()error{
    if l==nil{return nil}
    l.mu.Lock()
    defer l.mu.Unlock()
    if l.closed{return nil}
    d:=l.owner
    if d==nil{return ErrN4NativeGuard}
    d.mu.Lock()
    if !d.nativeRustLoan {
        d.mu.Unlock()
        return ErrN4NativeGuard
    }
    d.nativeRustLoan=false
    d.tun.endCall()
    d.mu.Unlock()
    l.closed=true
    l.owner=nil
    return nil
}
