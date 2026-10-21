//go:build windows

package windowsclient

// Native Win32 Wintun ring COPY boundary for an authenticated original-Go
// product generation. This is NOT an AEAD decoder or a product Applied grant.
// Rust M1/M3 must authenticate a packet BEFORE passing it through the
// package-private delivery method. No alternative cipher/crypto owner here.
import (
    "context"
    "errors"
    "io"
    "sync"
    "syscall"
    "unsafe"
)

var ErrN4NativeNoPacket=errors.New("original native Wintun kernel ring has no packet ready")

type N4RealKernelPacketCounts struct {
    KernelReceived uint64
    KernelCopied uint64
    Rejected uint64
    Stopped bool
}

// N4OriginalKernelPacketLease is bound to the exact live process-created
// Wintun GUID/LUID/index, installation and generation. No saved alias,
// externally supplied packet or Rust token is authorization by itself.
type N4OriginalKernelPacketLease struct{
    mu sync.Mutex
    tun *TUN
    holder N4WindowsCreatedWintunReservation
    id N4UnifiedIdentity
    stopped bool
    received,copied,rejected uint64
    // Serializes only one finite kernel ring call. No goroutine blocks in
    // ReadPacket's unbounded wait while holding this lease's lock.
}
func n4CreateOriginalKernelPacketLease(ctx context.Context,tun *TUN,id N4UnifiedIdentity)(
    *N4OriginalKernelPacketLease,error,
){
    if ctx==nil||tun==nil||!id.valid()||!tun.createdByProcess||
        id.AdapterAlias==""||id.WintunGUID==""||id.PnPInstanceSHA256==""{
        return nil,ErrN4NativeGuard
    }
    holder:=N4WindowsCreatedWintunReservation{
        Tunnel:tun,Installation:id.Installation,Generation:id.Generation,
    }
    if err:=holder.Verify(ctx,id);err!=nil{return nil,err}
    return &N4OriginalKernelPacketLease{tun:tun,id:id,holder:holder},nil
}
func (d *N4OriginalKernelPacketLease) check(ctx context.Context)error{
    if d==nil||ctx==nil{return ErrN4NativeGuard}
    if err:=ctx.Err();err!=nil{return err}
    if d.stopped{return ErrN4NativeGuard}
    return d.holder.Verify(ctx,d.id)
}
// n4DeliverAuthenticatedIPv4 is deliberately NOT exported. Caller must
// hold M0 original-Go TLS+Rust AEAD first-delivery receipt; this method
// itself counts only a real WintunSendPacket kernel copy, not authentication.
func (d *N4OriginalKernelPacketLease) n4DeliverAuthenticatedIPv4(
    ctx context.Context,payload []byte,
)(int,error){
    if d==nil{return 0,ErrN4NativeGuard}
    d.mu.Lock();defer d.mu.Unlock()
    if err:=d.check(ctx);err!=nil{return 0,err}
    if len(payload)<20||len(payload)>65535||!isIPv4Packet(payload){
        d.rejected++;return 0,ErrInvalidBinding
    }
    // TUN.WritePacket owns the real WintunAllocateSendPacket/SendPacket
    // copy and holds its native handle until released. No fabricated delivery.
    n,err:=d.tun.WritePacket(payload)
    if err!=nil||n!=len(payload){
        d.rejected++
        if err==nil{err=io.ErrShortWrite}
        return n,err
    }
    d.copied++
    return n,nil
}
// n4ReceiveReadyIPv4 reads exactly ONE already available native Windows
// Wintun ring packet. No WaitForMultipleObjects(INFINITE), no blocking
// mutex across idle kernel poll, no empty queue busy-loop. Upper actor is
// responsible for validating its source and handing to actual Rust M3 AEAD.
func (d *N4OriginalKernelPacketLease) n4ReceiveReadyIPv4(
    ctx context.Context,dst []byte,
)(int,error){
    if d==nil{return 0,ErrN4NativeGuard}
    d.mu.Lock();defer d.mu.Unlock()
    if err:=d.check(ctx);err!=nil{return 0,err}
    if len(dst)==0{return 0,io.ErrShortBuffer}
    if !d.tun.beginCall(){return 0,ErrN4NativeGuard}
    defer d.tun.endCall()
    var packetSize uint32
    packet,_,callErr:=wintunReceivePacket.Call(
        d.tun.session,uintptr(unsafe.Pointer(&packetSize)),
    )
    if packet==0{
        if wintunErrno(callErr)==errorNoMoreItems{return 0,ErrN4NativeNoPacket}
        if wintunErrno(callErr)==errorHandleEOF{return 0,io.EOF}
        d.rejected++
        return 0,wintunCallError("WintunReceivePacket",callErr,nil)
    }
    defer wintunReleaseReceivePacket.Call(d.tun.session,packet)
    if packetSize>uint32(len(dst)) || packetSize<20{
        d.rejected++;return 0,io.ErrShortBuffer
    }
    wire:=unsafe.Slice((*byte)(unsafe.Pointer(packet)),int(packetSize))
    if !isIPv4Packet(wire){
        d.rejected++;return 0,ErrInvalidBinding
    }
    n:=copy(dst,wire)
    d.received++
    return n,nil
}
func (d *N4OriginalKernelPacketLease) Counts()(N4RealKernelPacketCounts,error){
    if d==nil{return N4RealKernelPacketCounts{},ErrN4NativeGuard}
    d.mu.Lock();defer d.mu.Unlock()
    return N4RealKernelPacketCounts{
        KernelReceived:d.received,KernelCopied:d.copied,
        Rejected:d.rejected,Stopped:d.stopped,
    },nil
}
func (d *N4OriginalKernelPacketLease) Stop(ctx context.Context)error{
    if d==nil||ctx==nil{return ErrN4NativeGuard}
    d.mu.Lock();defer d.mu.Unlock()
    if d.stopped{return nil}
    if err:=ctx.Err();err!=nil{return err}
    d.stopped=true
    // No device close or OS routes are stolen here. The original product
    // Stop joins this lease before stopping Rust then WAL CAS and TUN.Close.
    return nil
}
var _ syscall.Errno = errorNoMoreItems
