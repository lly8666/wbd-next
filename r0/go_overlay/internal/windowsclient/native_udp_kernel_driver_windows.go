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
    "time"
    "unsafe"
)

var ErrN4NativeNoPacket=errors.New("original native Wintun kernel ring has no packet ready")

// Exactly one live native kernel sender/receiver lease can own a particular
// process-created Wintun. An attacker-provided generation with the SAME
// adapter/LUID must not claim an independent lease while the original Go
// TLS+Rust generation still holds it. M4's original PnP checks alone
// validate the device, not that generation exclusion.
var n4OriginalRingOwners = struct{
    sync.Mutex
    held map[*TUN]N4UnifiedIdentity
}{held:make(map[*TUN]N4UnifiedIdentity)}


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
    // The exact real M4-owned TUN/generation and Stop are serialized on
    // every ring op. The expensive GUID/LUID/PnP OS proof is reaudited at
    // most once per second; a failed refresh permanently fences this lease.
    lastVerifiedAt time.Time
    identityRevoked bool
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
    n4OriginalRingOwners.Lock()
    defer n4OriginalRingOwners.Unlock()
    if _,exists:=n4OriginalRingOwners.held[tun];exists {
        // A second lease is not legitimate even if it supplies the exact
        // generation. This also denies a new invented generation.
        return nil,ErrN4NativeGuard
    }
    n4OriginalRingOwners.held[tun]=id
    return &N4OriginalKernelPacketLease{
        tun:tun,id:id,holder:holder,lastVerifiedAt:time.Now(),
    },nil
}
// Called only while d.mu is held, so Stop and all ring I/O are mutually
// exclusive and no native Wintun loan crosses a revalidation boundary.
func n4RealOriginalWintunAuditDue(last,now time.Time)bool{
    return last.IsZero()||now.Before(last)||now.Sub(last)>=time.Second
}
func (d *N4OriginalKernelPacketLease) check(ctx context.Context)error{
    if d==nil||ctx==nil{return ErrN4NativeGuard}
    if err:=ctx.Err();err!=nil{return err}
    if d.stopped||d.identityRevoked||d.tun==nil||
       d.id.Generation==[16]byte{}||d.id.Installation==[16]byte{}{
        return ErrN4NativeGuard
    }
    now:=time.Now()
    if !n4RealOriginalWintunAuditDue(d.lastVerifiedAt,now){
        return nil
    }
    if err:=d.holder.Verify(ctx,d.id);err!=nil{
        // Even if a transient PnP reappearance later uses the same alias,
        // this original protected Rust/TLS epoch must Stop and re-establish.
        d.identityRevoked=true
        return errors.Join(ErrN4NativeGuard,err)
    }
    d.lastVerifiedAt=now
    return nil
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
// n4ReceiveReadyIPv4 returns at most ONE IPv4 packet from the true
// Wintun receive ring, without waiting on an idle queue. Windows may emit
// unsolicited IPv6 control frames immediately after a signed adapter is
// created, even when this product has not enabled IPv6. The pinned original
// Go TUN ReadPacket already discards non-IPv4 frames. Mirror that behavior
// here, but with a strict eight-frame work limit to avoid an idle CPU loop,
// cross-lane HOL or holding kernel ring loans across future polls.
func (d *N4OriginalKernelPacketLease) n4ReceiveReadyIPv4(
    ctx context.Context,dst []byte,
)(int,error){
    if d==nil{return 0,ErrN4NativeGuard}
    d.mu.Lock();defer d.mu.Unlock()
    if err:=d.check(ctx);err!=nil{return 0,err}
    if len(dst)==0{return 0,io.ErrShortBuffer}
    if !d.tun.beginCall(){return 0,ErrN4NativeGuard}
    defer d.tun.endCall()
    const maxNativeRingFramesPerPoll=8
    for scanned:=0;scanned<maxNativeRingFramesPerPoll;scanned++{
        // No pointer from an earlier frame may remain outstanding while
        // asking Wintun for another. No deferred per-frame release.
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
        wire:=unsafe.Slice((*byte)(unsafe.Pointer(packet)),int(packetSize))
        // Unrelated IPv6/control packets must be consumed from the real
        // native ring but never delivered into the IPv4-only Rust owner.
        if packetSize>=1 && wire[0]>>4!=4{
            wintunReleaseReceivePacket.Call(d.tun.session,packet)
            d.rejected++
            continue
        }
        if packetSize<20 || !isIPv4Packet(wire){
            wintunReleaseReceivePacket.Call(d.tun.session,packet)
            d.rejected++
            return 0,ErrInvalidBinding
        }
        if packetSize>uint32(len(dst)){
            wintunReleaseReceivePacket.Call(d.tun.session,packet)
            d.rejected++
            return 0,io.ErrShortBuffer
        }
        n:=copy(dst,wire)
        wintunReleaseReceivePacket.Call(d.tun.session,packet)
        d.received++
        return n,nil
    }
    // More than eight unrelated frames do not monopolize the caller.
    // A later explicit poll can still receive the queued real IPv4 packet.
    return 0,ErrN4NativeNoPacket
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
    n4OriginalRingOwners.Lock()
    claimed,exists:=n4OriginalRingOwners.held[d.tun]
    if !exists || claimed!=d.id {
        n4OriginalRingOwners.Unlock()
        return ErrN4NativeGuard
    }
    delete(n4OriginalRingOwners.held,d.tun)
    n4OriginalRingOwners.Unlock()
    d.stopped=true
    // No device close or OS routes are stolen here. The original product
    // Stop joins this lease before stopping Rust then WAL CAS and TUN.Close.
    return nil
}
var _ syscall.Errno = errorNoMoreItems

// Native Rust M3 transport is the sole current-generation owner of this
// exported nonblocking ring API. Rust AEAD authenticity is NOT established
// by these methods; the caller must first be the real original TLS owner
// that received the lease from N4PrepareRealWindowsProduct.
func(d *N4OriginalKernelPacketLease) ReceiveReadyIPv4(
 ctx context.Context,dst []byte,
)(int,error){return d.n4ReceiveReadyIPv4(ctx,dst)}
func(d *N4OriginalKernelPacketLease) WriteAuthenticatedIPv4(
 ctx context.Context,payload []byte,
)(int,error){return d.n4DeliverAuthenticatedIPv4(ctx,payload)}
