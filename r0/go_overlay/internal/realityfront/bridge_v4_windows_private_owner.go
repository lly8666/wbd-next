//go:build windows && wbd_v4_embedded_go

// M0 shared Windows-only private original Go post-credential-TLS callback.
// This file is OPT-IN and cannot be reached from config/CLI unauthenticated
// bytes. A Rust owner-phase receipt is NOT a Windows native WFP/TUN lease or
// product Connected/Applied state. M4 owns separate guarded network entry.
package realityfront

import (
    "context"
    "errors"
    "fmt"
    "path/filepath"
    "runtime"
    "syscall"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

var errV4WindowsOwner=errors.New("original-Go private Windows Rust owner refused")
type v4WindowsNativeOwnerBridge struct {
    dll *syscall.DLL
    prepareProc,stageProc,commitProc,abortProc,stateProc,stopProc,releaseProc *syscall.Proc
    bindWintunProc,quiesceWintunProc,deviceStateProc *syscall.Proc
    sealNormalProc,openNormalProc,openKind1Proc,armM2Proc,reportM2Proc,prepareRepairProc,finishRepairProc,queryM2Proc,feedbackDueProc,feedbackResultProc *syscall.Proc
    handle uint64
    epoch [16]byte
    serverSide bool
    // Frozen original-Go FakeTCP Detach receive/send NEXT boundaries.
    // Only the verified credential TLS callback can populate these.
    tcpRecvNext,tcpSendNext uint32
    committed,stopped bool
}
func newV4WindowsPrivateOwnerBridge(absoluteLibrary string)(*v4WindowsNativeOwnerBridge,error){
    if !filepath.IsAbs(absoluteLibrary)||filepath.Ext(absoluteLibrary)!=".dll" {
        return nil,errV4WindowsOwner
    }
    dll,err:=syscall.LoadDLL(absoluteLibrary)
    if err!=nil{return nil,fmt.Errorf("%w: load actual native Rust DLL: %v",errV4WindowsOwner,err)}
    // Exact source-locked binary owner is supplied by the *same process*.
    // This function does not establish trust in a caller-supplied DLL path.
    find:=func(name string)(*syscall.Proc,error){return dll.FindProc(name)}
    b:=&v4WindowsNativeOwnerBridge{dll:dll}
    names:=[]struct{name string;out **syscall.Proc}{
        {"wbd_m0_win_owner_v1_prepare",&b.prepareProc},
        {"wbd_m0_win_owner_v1_stage",&b.stageProc},
        {"wbd_m0_win_owner_v1_commit",&b.commitProc},
        {"wbd_m0_win_owner_v1_abort",&b.abortProc},
        {"wbd_m0_win_owner_v1_state",&b.stateProc},
        {"wbd_m0_win_owner_v1_stop",&b.stopProc},
        {"wbd_m0_win_owner_v1_release",&b.releaseProc},
        {"wbd_m0_win_owner_v2_bind_wintun",&b.bindWintunProc},
        {"wbd_m0_win_owner_v2_quiesce_wintun",&b.quiesceWintunProc},
        {"wbd_m0_win_owner_v2_device_state",&b.deviceStateProc},
        {"wbd_m0_win_owner_v3_seal_normal_off",&b.sealNormalProc},
        {"wbd_m0_win_owner_v3_open_normal_off",&b.openNormalProc},
        {"wbd_m0_win_owner_v5_open_data_or_kind1",&b.openKind1Proc},
        {"wbd_m0_win_owner_v6_arm_original_m2",&b.armM2Proc},
        {"wbd_m0_win_owner_v6_report_npcap_firstsend",&b.reportM2Proc},
        {"wbd_m0_win_owner_v6_next_frozen_repair",&b.prepareRepairProc},
        {"wbd_m0_win_owner_v6_finish_frozen_repair",&b.finishRepairProc},
        {"wbd_m0_win_owner_v6_m2_outstanding",&b.queryM2Proc},
        {"wbd_m0_win_owner_v7_reverse_m2_feedback_due",&b.feedbackDueProc},
        {"wbd_m0_win_owner_v7_reverse_m2_feedback_result",&b.feedbackResultProc},
    }
    for _,entry:=range names{
        p,e:=find(entry.name)
        if e!=nil{_ = dll.Release();return nil,fmt.Errorf("%w: missing Rust ABI %s",errV4WindowsOwner,entry.name)}
        *entry.out=p
    }
    return b,nil
}
func winOwnerCall(proc *syscall.Proc,args ...uintptr)error{
    if proc==nil{return errV4WindowsOwner}
    status,_,_:=proc.Call(args...)
    if status!=0{return fmt.Errorf("%w: C ABI rc=%d",errV4WindowsOwner,status)}
    return nil
}
func (b *v4WindowsNativeOwnerBridge) prepare(
    snapshot V4ColdSessionSnapshot,rxBoundary uint32,peer v4PeerTransport,
)(v4PreparedOwner,error){
    if b==nil||b.dll==nil||b.handle!=0||b.committed||b.stopped||
        !snapshot.server||snapshot.epoch==[16]byte{}{
        return nil,errV4WindowsOwner
    }
    cold,err:=snapshot.MarshalColdBundle()
    if err!=nil{return nil,err}
    handoff,err:=v4PrivateHandoffFromVerifiedSession(rxBoundary,peer,snapshot)
    if err!=nil{return nil,err}
    var h uint64
    err=winOwnerCall(b.prepareProc,uintptr(unsafe.Pointer(&cold[0])),uintptr(len(cold)),
        uintptr(unsafe.Pointer(&handoff[0])),uintptr(len(handoff)),1,
        uintptr(unsafe.Pointer(&h)))
    runtime.KeepAlive(cold);runtime.KeepAlive(handoff)
    if err!=nil||h==0{return nil,errV4WindowsOwner}
    b.handle=h;b.epoch=snapshot.epoch;b.serverSide=true
    return &v4WindowsNativeOwnerPrepared{owner:b},nil
}
// ConnectVerifiedClient is the sole client-side original-Go V4 protected TLS
// path into the same M1/M3 Windows Rust owner. The original FakeTCP Client
// Association (not a bare net.Conn or forged WBGH) supplies Detach's actual
// two sequence limits. This is a private opt-in control seam, NOT Windows
// kernel/WFP activation. A bad/unsupported policy never touches the DLL.
func (b *v4WindowsNativeOwnerBridge) connectVerifiedClient(
    ctx context.Context, assoc *faketcp.ClientAssociation, cfg ClientAdmissionConfig,
)(*V4ClientSession,error){
    if b==nil||b.dll==nil||b.handle!=0||b.committed||b.stopped||
        ctx==nil||assoc==nil||assoc.BootstrapConn()==nil{
        return nil,errV4WindowsOwner
    }
    if cfg.Policy.Transport!=TransportNormal||cfg.Policy.FECMode!=FECOff||
        cfg.Policy.DesiredLanes!=1||cfg.DesiredLanes!=1{
        return nil,ErrAdmissionUnsupported
    }
    session,err:=EstablishClientV4(ctx,assoc.BootstrapConn(),cfg,
        V4ClientOptions{DataPlaneReady:true})
    if err!=nil{return nil,err}
    // No access to Rust owner on a rejected/modified post-TLS snapshot.
    if _,err=session.ColdSnapshot();err!=nil{return nil,err}
    handoff,err:=assoc.Detach()
    if err!=nil{return nil,err}
    if err=b.prepareAuthenticatedClient(session,handoff,assoc.Flow());err!=nil{
        return nil,fmt.Errorf("%w: real original-Go client Detach/Rust owner: %v",
            errV4WindowsOwner,err)
    }
    return session,nil
}
func (b *v4WindowsNativeOwnerBridge) prepareAuthenticatedClient(
    session *V4ClientSession,handoff faketcp.ClientHandoff,flow faketcp.ClientFlow,
)error{
    if b==nil||b.dll==nil||b.handle!=0||b.committed||b.stopped||
        session==nil{return errV4WindowsOwner}
    if err:=flow.Validate();err!=nil{return errV4WindowsOwner}
    cold,err:=session.ColdSnapshot()
    if err!=nil||cold.ServerSide(){return errV4WindowsOwner}
    snapshot,err:=cold.MarshalColdBundle()
    if err!=nil{return err}
    peer:=v4PeerTransport{
        mss:handoff.Peer.MSS,advertised:handoff.Peer.AdvertisedMSS,
        flow:faketcp.ServerFlow{
            ClientIP:flow.LocalIP,ServerIP:flow.PeerIP,
            ClientPort:flow.LocalPort,ServerPort:flow.PeerPort,
        },
    }
    command,err:=v4PrivateHandoffFromVerifiedClientSession(
        handoff.ReceiveNext,peer,cold)
    if err!=nil{return err}
    var handle uint64
    err=winOwnerCall(b.prepareProc,uintptr(unsafe.Pointer(&snapshot[0])),
        uintptr(len(snapshot)),uintptr(unsafe.Pointer(&command[0])),
        uintptr(len(command)),0,uintptr(unsafe.Pointer(&handle)))
    runtime.KeepAlive(snapshot);runtime.KeepAlive(command)
    if err!=nil||handle==0{return errV4WindowsOwner}
    b.handle=handle
    // Do not claim active on original Go Detach until Rust's exact
    // SendNext committal. A failed Commit discards ONLY this PREPARED
    // generation and never calls Stop on an uncommitted owner.
    if err=winOwnerCall(b.commitProc,uintptr(handle),0,0,
        uintptr(handoff.SendNext));err!=nil{
        if winOwnerCall(b.abortProc,uintptr(handle))==nil{
            b.handle=0
        }
        return err
    }
    b.tcpRecvNext=handoff.ReceiveNext
    b.tcpSendNext=handoff.SendNext
    b.epoch=cold.Epoch()
    b.serverSide=false
    b.committed=true
    return nil
}
type v4WindowsNativeOwnerPrepared struct {
    owner *v4WindowsNativeOwnerBridge
    done bool
}
func (p *v4WindowsNativeOwnerPrepared) commit(
    early []faketcp.TransitionPacket,exactTXBoundary uint32,
)error{
    if p==nil||p.done||p.owner==nil||p.owner.handle==0{return errV4WindowsOwner}
    if len(early)>32{return errV4WindowsOwner}
    b:=p.owner
    total:=0
    for _,chunk:=range early{
        n:=len(chunk.Payload)
        if n==0||n>2048||total+n>65535{return errV4WindowsOwner}
        err:=winOwnerCall(b.stageProc,uintptr(b.handle),uintptr(chunk.Seq),
            uintptr(unsafe.Pointer(&chunk.Payload[0])),uintptr(n))
        runtime.KeepAlive(chunk.Payload)
        if err!=nil{return err}
        total+=n
    }
    if err:=winOwnerCall(b.commitProc,uintptr(b.handle),
        uintptr(len(early)),uintptr(total),uintptr(exactTXBoundary));err!=nil{
        return err
    }
    b.committed=true;p.done=true
    return nil
}
func (p *v4WindowsNativeOwnerPrepared) abort(){
    if p==nil||p.done||p.owner==nil{return}
    p.done=true
    b:=p.owner
    if b.handle==0||b.committed{return}
    // Only an uncommitted original protected TLS candidate may be released
    // here. Post-Commit requires true terminal Stop, never a raw delete.
    if winOwnerCall(b.abortProc,uintptr(b.handle))==nil{
        b.handle=0;b.epoch=[16]byte{}
    }
}
type v4WindowsOwnerState struct {
    version,structSize,generation,phase,server,applied,loansDrained,reserved uint32
}
func (b *v4WindowsNativeOwnerBridge) state()(v4WindowsOwnerState,error){
    var v v4WindowsOwnerState
    if b==nil||b.handle==0{return v,errV4WindowsOwner}
    if err:=winOwnerCall(b.stateProc,uintptr(b.handle),
        uintptr(unsafe.Pointer(&v)),uintptr(unsafe.Sizeof(v)));err!=nil{return v,err}
    expectedRole:=uint32(0)
    if b.serverSide{expectedRole=1}
    if v.version!=1||v.structSize!=uint32(unsafe.Sizeof(v))||v.generation!=uint32(b.handle>>32)||
        v.server!=expectedRole||v.applied!=0||v.reserved!=0{return v,errV4WindowsOwner}
    return v,nil
}
// Explicit narrow component Stop. Deliberately does NOT implement the
// V4OriginalOwnerStopper product interface: no Windows M4 driver or WFP
// native route was acquired by this bridge; no product cleanup is certified.
func (b *v4WindowsNativeOwnerBridge) stopRustOwnerOnly()error{
    if b==nil{return errV4WindowsOwner}
    if b.stopped&&b.handle==0{return nil}
    if !b.committed||b.handle==0{return errV4WindowsOwner}
    if err:=winOwnerCall(b.stopProc,uintptr(b.handle));err!=nil{return err}
    state,err:=b.state()
    if err!=nil||state.phase!=3||state.loansDrained!=1{return errV4WindowsOwner}
    if err=winOwnerCall(b.releaseProc,uintptr(b.handle));err!=nil{return err}
    b.handle=0;b.committed=false;b.stopped=true;return nil
}
