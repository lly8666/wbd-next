//go:build windows

package faketcp

// PLAN026: cold-only handoff of the ORIGINAL authenticated Npcap capture.
// All data-plane pcap_next_ex/pcap_sendpacket calls after the handoff belong
// exclusively to the Rust native owner. This code never parses a business
// packet and never creates a background reader.
import (
    "fmt"
    "unsafe"
    "sync"
    "syscall"
)

// The three pointers have the same order and pointer width as Rust's
// wbd_platform::windows_native_io::NpcapFns. They are native wpcap.dll C
// function addresses, not Go callbacks and not Go-managed heap pointers.
type NpcapNativeFnsV1 struct {
    NextEx     uintptr
    SendPacket uintptr
    GetEvent   uintptr
    QueueAlloc uintptr
    QueueTransmit uintptr
    QueueDestroy uintptr
}

// A borrowed pcap_t / wpcap DLL is valid until CloseAfterRustJoin.
// Captured frames already placed in the caller's pre-handoff channel MUST be
// transferred/drained separately after the old Go reader has exited; this
// method neither discards those frames nor reopens an overlapping RX handle.
type NpcapNativeCaptureV1 struct {
    Handle     uintptr
    Fns        NpcapNativeFnsV1
    Event      uintptr
    Generation uint64
    Flow       NpcapFlow
}

func npcapOptionalProcAddr(p *syscall.Proc) uintptr {
    if p==nil{return 0}
    return p.Addr()
}

type NpcapNativeCaptureLease struct {
    mu        sync.Mutex
    handle    uintptr
    dll       *syscall.DLL
    closeProc *syscall.Proc
    event     uintptr
    fns       NpcapNativeFnsV1
    generation uint64
    flow      NpcapFlow
    closed    bool
}

// DisableReceiveForNativeTX installs an always-false BPF on the dedicated
// TX pcap_t. Otherwise a second open_live would also capture every incoming
// lane frame and waste kernel CPU / fill an unread NPF ring. It is still
// the SAME interface and uses pcap_sendpacket/sendqueue normally.
func(e *NpcapEndpoint) DisableReceiveForNativeTX()error{
 if e==nil||e.gate==nil||e.handle==0{return ErrNpcapClosed}
 if err:=e.gate.begin(e.cfg.Generation);err!=nil{return err}
 defer e.gate.end()
 compile,err:=e.dll.FindProc("pcap_compile");if err!=nil{return err}
 set,err:=e.dll.FindProc("pcap_setfilter");if err!=nil{return err}
 free,err:=e.dll.FindProc("pcap_freecode");if err!=nil{return err}
 expression,err:=syscall.BytePtrFromString("ip and ip[0] = 0")
 if err!=nil{return err}
 var prog pcapBPFProgram
 if rc,_,_:=compile.Call(e.handle,uintptr(unsafe.Pointer(&prog)),
    uintptr(unsafe.Pointer(expression)),1,pcapNetmaskUnknown);int32(rc)!=0{
  return fmt.Errorf("Npcap TX-only filter compile: %s",pcapError(e.getErr,e.handle))
 }
 defer free.Call(uintptr(unsafe.Pointer(&prog)))
 if rc,_,_:=set.Call(e.handle,uintptr(unsafe.Pointer(&prog)));int32(rc)!=0{
  return fmt.Errorf("Npcap TX-only filter apply: %s",pcapError(e.getErr,e.handle))
 }
 return nil
}

// This is a cold read-only clone of the already-verified original Npcap
// lane configuration. Needed to open one TX-only capture after the Go
// readers have joined. It never reopens a second receive path.
func(e *NpcapEndpoint) NativeCaptureConfig()(NpcapConfig,error){
 if e==nil||e.gate==nil||e.handle==0||e.cfg.Generation==0{
  return NpcapConfig{},ErrNpcapClosed
 }
 return e.cfg,nil
}

// TakeNativeCapture permanently disables Go NpcapEndpoint packet calls. It
// keeps the exact original pcap_t and DLL loaded for Rust's two-worker engine;
// no old Go caller can accidentally close the transferred handle.
//
// IMPORTANT: the original reader must be allowed to return from its existing
// pcap_next_ex call. The original live endpoint has a 50ms read timeout;
// breakloop is requested, then the actual active-call gate is joined. Caller
// must still synchronize its own reader goroutine and drain bounded early
// ingress before publishing the Rust RX route.
//
// An unsupported pcap_getevent is rejected before freezing the Go endpoint.
// After the freeze, all failures are scoped fatal to THIS candidate and must
// be closed with the returned lease after Rust Stop.
func (e *NpcapEndpoint) TakeNativeCapture(generation uint64) (*NpcapNativeCaptureLease, error) {
    if e == nil || e.gate == nil || e.dll == nil || e.handle == 0 {
        return nil, ErrNpcapClosed
    }
    if generation == 0 || e.cfg.Generation != generation {
        return nil, ErrNpcapStaleGeneration
    }
    getEvent, err := e.dll.FindProc("pcap_getevent")
    if err != nil {
        return nil, fmt.Errorf("%w: pcap_getevent: %v", ErrNpcapUnsupported, err)
    }
    if !e.gate.close() {
        return nil, ErrNpcapClosed
    }
    if e.breakLoop != nil {
        e.breakLoop.Call(e.handle)
    }
    // No new Go read/write may start after gate.close. In-flight uses finish
    // before e.handle and DLL function pointers are moved to the Rust lease.
    e.gate.wait()
    e.sendMu.Lock()
    defer e.sendMu.Unlock()
    if e.sendQueue != 0 {
        e.queueDestroy.Call(e.sendQueue)
        e.sendQueue = 0
    }
    event, _, _ := getEvent.Call(e.handle)
    lease := &NpcapNativeCaptureLease{
        handle:e.handle, dll:e.dll, closeProc:e.closeProc,
        event:event, generation:generation, flow:e.cfg.Flow,
        fns:NpcapNativeFnsV1{
            NextEx:e.nextEx.Addr(),
            SendPacket:e.sendPacket.Addr(),
            GetEvent:getEvent.Addr(),
            QueueAlloc:npcapOptionalProcAddr(e.queueAlloc),
            QueueTransmit:npcapOptionalProcAddr(e.queueTransmit),
            QueueDestroy:npcapOptionalProcAddr(e.queueDestroy),
        },
    }
    // e.Close() is now safely inert; only CloseAfterRustJoin can close pcap_t
    // and unload its module. All low-level calls belong exclusively to Rust.
    e.handle = 0
    e.dll = nil
    e.nextEx = nil
    e.sendPacket = nil
    e.closeProc = nil
    return lease,nil
}

// Native returns only the raw SAME-process driver values. This is not a
// TLS identity/OS Applied authorization: the true scoped Rust V4 owner must
// additionally verify the protected admission epoch and Wintun reservation.
func(l *NpcapNativeCaptureLease) Native()(NpcapNativeCaptureV1,error){
    if l==nil{return NpcapNativeCaptureV1{},ErrNpcapClosed}
    l.mu.Lock();defer l.mu.Unlock()
    if l.closed||l.handle==0||l.dll==nil{return NpcapNativeCaptureV1{},ErrNpcapClosed}
    if l.event==0{return NpcapNativeCaptureV1{},ErrNpcapUnsupported}
    return NpcapNativeCaptureV1{
        Handle:l.handle,Fns:l.fns,Event:l.event,
        Generation:l.generation,Flow:l.flow,
    },nil
}

// Must be invoked only AFTER Rust has joined every reader/worker touching
// this pcap_t and every borrowed pcap buffer has been released. No default
// finalizer or Go defer on the old endpoint may close it earlier.
func(l *NpcapNativeCaptureLease) CloseAfterRustJoin()error{
    if l==nil{return nil}
    l.mu.Lock();defer l.mu.Unlock()
    if l.closed{return nil}
    l.closed=true
    if l.handle!=0{
        l.closeProc.Call(l.handle)
        l.handle=0
    }
    if l.dll!=nil{
        err:=l.dll.Release()
        l.dll=nil
        return err
    }
    return nil
}
