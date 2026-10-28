//go:build windows && wbd_v4_embedded_go
package realityfront

// M0-facing typed Windows client credential TLS -> authentic M1/M3 Rust
// ProtectedScopedOwner -> SAME-process M4-created Wintun Hold lifetime API.
// It intentionally has NO product Connected/WFP/route/DNS grant. The M4
// product owns its separate native OS transaction and all network cleanup.
import (
    "context"
    "errors"
    "fmt"
    "runtime"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4WindowsScopedOwnerReadback struct {
    Generation uint32
    ServerSide bool
    OwnerActive bool
    DeviceBound bool
    DeviceQuiesced bool
    ProductApplied bool
}
type V4WindowsAuthenticatedClientOwner struct{
    bridge *v4WindowsNativeOwnerBridge
    device *v4WindowsRealDeviceLease
}
// Only the original FakeTCP + credential protected TLS handshake can create
// the private bridge token: no struct with caller supplied cold/WBGH fields.
func V4WindowsEstablishOriginalClientOwner(
    ctx context.Context,library string,assoc *faketcp.ClientAssociation,
    cfg ClientAdmissionConfig,
)(*V4WindowsAuthenticatedClientOwner,*V4ClientSession,error){
    if ctx==nil||assoc==nil{return nil,nil,ErrAdmissionParams}
    native,err:=newV4WindowsPrivateOwnerBridge(library)
    if err!=nil{return nil,nil,err}
    result,err:=native.connectVerifiedClient(ctx,assoc,cfg)
    if err!=nil{return nil,nil,err}
    state,err:=native.state()
    if err!=nil||state.phase!=2||state.applied!=0||
        state.generation==0||state.server!=0{return nil,nil,errV4WindowsOwner}
    return &V4WindowsAuthenticatedClientOwner{bridge:native},result,nil
}
// BindOriginalM4NativeDevice requires the actual external native M4 holder;
// a token may never be rebound to another OS adapter or newer TLS epoch.
// A successful device binding remains scoped, not a product Apply signal.
func(s *V4WindowsAuthenticatedClientOwner) BindOriginalM4NativeDevice(
    ctx context.Context,device V4WindowsCurrentNativeDevice,
    id V4WindowsNativeDeviceIdentity,
)error{
    if s==nil||s.bridge==nil||s.device!=nil{return errV4WindowsOwner}
    held,err:=s.bridge.holdOriginalCreatedWintun(ctx,device,id)
    if held!=nil{s.device=held}
    return err
}
func(s *V4WindowsAuthenticatedClientOwner) OriginalOwnerReadback()(V4WindowsScopedOwnerReadback,error){
    var out V4WindowsScopedOwnerReadback
    if s==nil||s.bridge==nil{return out,errV4WindowsOwner}
    state,err:=s.bridge.state()
    if err!=nil{return out,err}
    dev,err:=s.bridge.realNativeDeviceState()
    if err!=nil{return out,err}
    if dev.Applied!=0{return out,errV4WindowsOwner}
    return V4WindowsScopedOwnerReadback{
        Generation:state.generation,ServerSide:false,OwnerActive:state.phase==2,
        DeviceBound:dev.Bound==1,DeviceQuiesced:dev.Quiesced==1,
        ProductApplied:false,
    },nil
}

// B2 zero-wait bounded original Wintun ready-prefix SOURCE stage ABI.
// The caller owns both buffers for one fair 2ms native turn; neither
// a staged Go array nor Rust AEAD seal means a native NPF kernel copy.
type V4WindowsOriginalSourceInput struct{
 Length,Reserved uint32
 IPv4 [2048]byte
}
type V4WindowsOriginalSourceOutput struct{
 Used,Seq uint32
 PN uint64
 Wire [2048]byte
}
const V4WindowsOriginalSourceBatchMax=4
func(s *V4WindowsAuthenticatedClientOwner) SealBoundOriginalSourceBatch(
 ctx context.Context,inputs []V4WindowsOriginalSourceInput,
 outputs []V4WindowsOriginalSourceOutput,
)(uint32,error){
 if ctx==nil||s==nil||s.bridge==nil||s.device==nil||
    s.bridge.stageSourceBatchProc==nil{
    return 0,fmt.Errorf("%w: SOURCE_BATCH_OWNER_UNBOUND",errV4WindowsOwner)
 }
 if len(inputs)==0||len(inputs)>V4WindowsOriginalSourceBatchMax||
    len(outputs)!=len(inputs)||
    unsafe.Sizeof(V4WindowsOriginalSourceInput{})!=2056||
    unsafe.Sizeof(V4WindowsOriginalSourceOutput{})!=2064{
    return 0,fmt.Errorf("%w: SOURCE_BATCH_LAYOUT input=%d output=%d",
     errV4WindowsOwner,len(inputs),len(outputs))
 }
 if err:=ctx.Err();err!=nil{return 0,err}
 maxIPv4:=s.device.maxIPv4
 for i:=range inputs{
  n:=inputs[i].Length
  if inputs[i].Reserved!=0||n<20||n>2048||
     int(n)>maxIPv4||inputs[i].IPv4[0]>>4!=4||
     inputs[i].IPv4[0]&15<5||
     int(inputs[i].IPv4[0]&15)*4>int(n){
    return 0,fmt.Errorf("%w: SOURCE_BATCH_BAD_IPV4 row=%d n=%d max=%d version=%d ihl=%d reserved=%d",
      errV4WindowsOwner,i,n,maxIPv4,inputs[i].IPv4[0]>>4,inputs[i].IPv4[0]&15,inputs[i].Reserved)
  }
 }
 release,err:=s.device.borrowHot(ctx)
 if err!=nil{return 0,errors.Join(errV4WindowsOwner,err)}
 defer release()
 var produced uint32
 err=winOwnerCall(s.bridge.stageSourceBatchProc,
  uintptr(s.bridge.handle),uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&inputs[0])),uintptr(len(inputs)),
  uintptr(unsafe.Pointer(&outputs[0])),uintptr(len(outputs)),
  uintptr(unsafe.Pointer(&produced)))
 runtime.KeepAlive(inputs);runtime.KeepAlive(outputs)
 runtime.KeepAlive(s.bridge.epoch)
 if produced>uint32(len(inputs)){
  return 0,fmt.Errorf("%w: SOURCE_BATCH_OUTPUT_OVERFLOW produced=%d requested=%d",
    errV4WindowsOwner,produced,len(inputs))
 }
 // Any partial native error after a seal may have burned original M1
 // PN/SEQ. Return the truthful prefix but do not submit it as a second
 // attempt; the enclosing original Go owner must Stop.
 if err!=nil{
  return produced,fmt.Errorf("SOURCE_BATCH_RUST_ABI produced=%d requested=%d: %w",
   produced,len(inputs),errors.Join(errV4WindowsOwner,err))
 }
 if produced!=uint32(len(inputs)){
  return produced,fmt.Errorf("%w: SOURCE_BATCH_PARTIAL_SUCCESS produced=%d requested=%d",
   errV4WindowsOwner,produced,len(inputs))
 }
 for i:=range outputs{
  n:=outputs[i].Used
  if n<=31||n>2048{
   return produced,fmt.Errorf("%w: SOURCE_BATCH_BAD_OUTPUT row=%d used=%d",
    errV4WindowsOwner,i,n)
  }
 }
 return produced,nil
}
// SealBoundOriginalNormalOff is callable only AFTER original-Go verified
// credential TLS, successful Rust commit and the same live M4-created native
// Wintun Hold. It asks the SAME Rust M1 owner for a single immutable M3 AEAD
// record. This makes NO assertion that any OS UDP packet was sent yet.
func (s *V4WindowsAuthenticatedClientOwner) SealBoundOriginalNormalOff(
    ctx context.Context,ipv4 []byte,
)([]byte,uint32,uint64,error){
    if ctx==nil||s==nil||s.bridge==nil||s.device==nil||
        s.bridge.sealNormalProc==nil||len(ipv4)<20||len(ipv4)>s.device.maxIPv4||
        ipv4[0]>>4!=4{
        return nil,0,0,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,0,0,err}
    borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return nil,0,0,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
    // Current M4 borrowHot above guards original TLS/generation and Stop.
    // Rust v3_ready under this same seal call independently asserts
    // ACTIVE, authentic epoch, LUID and interface index.
    // 31 is the original M3 fixed on-wire record overhead. The v3 Rust
    // authority also computes its own conservative 576B budget and rejects
    // oversize data before consuming a PN.
    wire:=make([]byte,len(ipv4)+31)
    var used uintptr
    var seq uint32
    var pn uint64
    err:=winOwnerCall(s.bridge.sealNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&used)),
        uintptr(unsafe.Pointer(&seq)),uintptr(unsafe.Pointer(&pn)),
    )
    runtime.KeepAlive(ipv4)
    runtime.KeepAlive(wire)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used!=uintptr(len(wire)){
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    return wire,seq,pn,nil
}

// OpenBoundOriginalNormalOff authenticates a peer's M3 record using the
// ORIGINAL Go credential-TLS-derived Rust owner AND the very same live
// process-created Wintun generation. It neither accepts unauthenticated
// IPv4 from a kernel socket nor itself grants WFP/route OS Applied.
// A failed Rust AEAD / PN / replay result NEVER yields any plaintext.
func(s *V4WindowsAuthenticatedClientOwner) OpenBoundOriginalNormalOff(
    ctx context.Context,seq uint32,wire []byte,
)([]byte,error){
    if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
        s.bridge.openNormalProc==nil||len(wire)<51||len(wire)>s.device.maxIPv4+31{
        return nil,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return nil,err}
    borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return nil,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
    state,err:=s.OriginalOwnerReadback()
    if err!=nil||!state.OwnerActive||!state.DeviceBound||
        state.DeviceQuiesced||state.ProductApplied||state.ServerSide{
        return nil,errV4WindowsOwner
    }
    plain:=make([]byte,len(wire))
    var used uintptr
    err=winOwnerCall(s.bridge.openNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&plain[0])),uintptr(len(plain)),
        uintptr(unsafe.Pointer(&used)),
    )
    runtime.KeepAlive(wire)
    runtime.KeepAlive(plain)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used<20||used>uintptr(len(plain)){
        // Return NO data on any Rust error, including incomplete or
        // non-single IPv4 records. Rust owns replay and authentication.
        return nil,errors.Join(errV4WindowsOwner,err)
    }
    if plain[0]>>4!=4 || plain[0]&0xf<5 ||
        int(plain[0]&0xf)*4>int(used){
        return nil,errV4WindowsOwner
    }
    return plain[:used],nil
}




// BoundOriginalM2Outstanding is a read-only count of original Rust-owned
// FrozenRecord shadows, not a TCP ACK or an application-delivery claim.
func(s *V4WindowsAuthenticatedClientOwner) BoundOriginalM2Outstanding(
    ctx context.Context,
)(uint32,error){
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.queryM2Proc==nil{return 0,errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return 0,err}
    var count uint32
    err:=winOwnerCall(s.bridge.queryM2Proc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&count)))
    runtime.KeepAlive(s.bridge.epoch)
    return count,err
}

// NextBoundOriginalM2Repair asks the SAME original Rust M2 ReceiptState to
// schedule at most one previously frozen ciphertext under the GLOBAL repair
// byte quota. This returns no new AEAD PN; call completion synchronously after
// the true original Npcap frame send attempt.
func(s *V4WindowsAuthenticatedClientOwner) NextBoundOriginalM2Repair(
    ctx context.Context,maxWire int,
)([]byte,uint32,uint64,error){
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.prepareRepairProc==nil||maxWire<51||maxWire>2048{
        return nil,0,0,fmt.Errorf("%w: original M2 frozen repair preflight cap=%d (owner=%t device=%t proc=%t)",
            errV4WindowsOwner,maxWire,s!=nil&&s.bridge!=nil,
            s!=nil&&s.device!=nil,s!=nil&&s.bridge!=nil&&s.bridge.prepareRepairProc!=nil)
    }
    if err:=ctx.Err();err!=nil{return nil,0,0,err}
    borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return nil,0,0,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
    wire:=make([]byte,maxWire)
    var used uintptr
    var seq uint32
    var pn uint64
    err:=winOwnerCall(s.bridge.prepareRepairProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&used)),uintptr(unsafe.Pointer(&seq)),
        uintptr(unsafe.Pointer(&pn)))
    runtime.KeepAlive(wire)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used>uintptr(len(wire)) {
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    if used==0{return nil,0,0,nil}
    if used<51{return nil,0,0,fmt.Errorf(
        "%w: original M2 repair C-ABI returned short authentic ciphertext used=%d cap=%d",
        errV4WindowsOwner,used,maxWire)}
    return wire[:used],seq,pn,nil
}
func(s *V4WindowsAuthenticatedClientOwner) CompleteBoundOriginalM2Repair(
    ctx context.Context,pn uint64,npcapSent bool,
)(uint32,error){
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.finishRepairProc==nil{return 0,errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return 0,err}
    var sent uintptr
    if npcapSent{sent=1}
    var count uint32
    err:=winOwnerCall(s.bridge.finishRepairProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(pn),sent,uintptr(unsafe.Pointer(&count)))
    runtime.KeepAlive(s.bridge.epoch)
    return count,err
}

// ArmBoundOriginalM2 verifies the current M4 Wintun OS generation and then
// asks the SAME original post-credential-TLS Rust owner to bind its M2
// FrozenRecord/receipt route; this is never a public OS Applied grant.
func(s *V4WindowsAuthenticatedClientOwner) ArmBoundOriginalM2(ctx context.Context)error{
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.armM2Proc==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil {
        return errors.Join(errV4WindowsOwner,err)
    }
    state,err:=s.OriginalOwnerReadback()
    if err!=nil||!state.OwnerActive||!state.DeviceBound||
        state.DeviceQuiesced||state.ProductApplied{return errV4WindowsOwner}
    err=winOwnerCall(s.bridge.armM2Proc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex))
    runtime.KeepAlive(s.bridge.epoch)
    return err
}
// Only call after the EXACT original Npcap synchronous sendpacket syscall:
// sent=true means the native NPF accepted a frame, NOT the peer applied it.
// Retains and moves the SAME M1 frozen AEAD PN/SEQ on the Rust side. The
// CPU-side Go ciphertext is NEVER the authoritative M2 shadow.
func(s *V4WindowsAuthenticatedClientOwner) ReportOriginalM2NpcapFirstsend(
    ctx context.Context,pn uint64,seq uint32,wireLen int,sent bool,
)(uint32,error){
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.reportM2Proc==nil||wireLen<31||wireLen>2048 {
        return 0,errV4WindowsOwner
    }
    if err:=ctx.Err();err!=nil{return 0,err}
    borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return 0,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
    var yes uintptr
    if sent{yes=1}
    var outstanding uint32
    err:=winOwnerCall(s.bridge.reportM2Proc,
        uintptr(s.bridge.handle),uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
        uintptr(pn),uintptr(seq),uintptr(wireLen),yes,
        uintptr(unsafe.Pointer(&outstanding)))
    runtime.KeepAlive(s.bridge.epoch)
    return outstanding,err
}

// Typed unchanged Rust M1 PN/SEQ and real NPF syscall completions.
// One batch is bounded by the same 32-record/2ms owner fair turn;
// staged bytes in Go are never equivalent to native copied/p2p delivery.
type V4WindowsM2FirstsendResult struct {
 PN uint64
 Seq,WireLen,Outcome,Reserved uint32
}
const V4WindowsM2FirstsendBatchMax=32
// Pure metadata preflight: original NPF first-send has already happened, so
// refusal must say whether the caller presented noncontiguous/duplicate
// records or Rust refused the exact original frozen PN. Never log ciphertext.
func validateOriginalM2FirstsendBatch(rows []V4WindowsM2FirstsendResult)error{
 if len(rows)==0||len(rows)>V4WindowsM2FirstsendBatchMax{
  return fmt.Errorf("%w: M2_BATCH_BAD_COUNT count=%d",errV4WindowsOwner,len(rows))
 }
 var next uint32
 for i,row:=range rows{
  if row.Reserved!=0||row.Outcome>2||row.WireLen<31||row.WireLen>2048{
   return fmt.Errorf("%w: M2_BATCH_BAD_DESCRIPTOR row=%d len=%d outcome=%d reserved=%d",
    errV4WindowsOwner,i,row.WireLen,row.Outcome,row.Reserved)
  }
  if i>0&&row.Seq!=next{
   return fmt.Errorf("%w: M2_BATCH_NONCONTIGUOUS row=%d expected_seq=%d got_seq=%d",
    errV4WindowsOwner,i,next,row.Seq)
  }
  for j:=0;j<i;j++{
   if rows[j].PN==row.PN{
    return fmt.Errorf("%w: M2_BATCH_DUPLICATE_PN row=%d earlier=%d",
     errV4WindowsOwner,i,j)
   }
  }
  next=row.Seq+row.WireLen // uint32 TCP wrap remains valid
 }
 return nil
}
func(s *V4WindowsAuthenticatedClientOwner) ReportOriginalM2NpcapFirstsendBatch(
 ctx context.Context,rows []V4WindowsM2FirstsendResult,
)(uint32,uint32,error){
 if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
  s.bridge.reportM2BatchProc==nil{
  return 0,0,fmt.Errorf("%w: M2_BATCH_OWNER_UNBOUND",errV4WindowsOwner)
 }
 if unsafe.Sizeof(V4WindowsM2FirstsendResult{})!=24{
  return 0,0,fmt.Errorf("%w: M2_BATCH_ABI_LAYOUT",errV4WindowsOwner)
 }
 if err:=ctx.Err();err!=nil{return 0,0,err}
 if err:=validateOriginalM2FirstsendBatch(rows);err!=nil{return 0,0,err}
 release,err:=s.device.borrowHot(ctx)
 if err!=nil{return 0,0,errors.Join(errV4WindowsOwner,err)}
 defer release()
 var settled,outstanding uint32
 err=winOwnerCall(s.bridge.reportM2BatchProc,
  uintptr(s.bridge.handle),uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&rows[0])),uintptr(len(rows)),
  uintptr(unsafe.Pointer(&settled)),uintptr(unsafe.Pointer(&outstanding)))
 runtime.KeepAlive(rows);runtime.KeepAlive(s.bridge.epoch)
 if err!=nil{return settled,outstanding,err}
 if settled!=uint32(len(rows)){
  return settled,outstanding,fmt.Errorf("%w: M2_BATCH_NATIVE_INCOMPLETE settled=%d expected=%d",
   errV4WindowsOwner,settled,len(rows))
 }
 return settled,outstanding,nil
}

// One canonical kind1 from original Rust M3-unique reverse DATA PNs,
// sealed with the SAME TLS-bound M1 PN/sequence and exact live Wintun Hold.
// Empty output is a legitimate bounded feedback scheduler idle turn.
func(s *V4WindowsAuthenticatedClientOwner) NextBoundOriginalM2Feedback(
 ctx context.Context,capacity int,
)([]byte,uint32,uint64,error){
 if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
  s.bridge.feedbackDueProc==nil||capacity<128||capacity>2048||
  capacity>s.device.maxIPv4+31{
   return nil,0,0,fmt.Errorf("%w: bounded reverse M2 due stage=preflight cap=%d max=%d",errV4WindowsOwner,capacity,s.device.maxIPv4+31)
  }
 if err:=ctx.Err();err!=nil{return nil,0,0,err}
 borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return nil,0,0,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
 // Original protected M4 lease is borrowed through the FFI and Rust
 // feedback_due again checks epoch/LUID/index/phase under Entry lock.
 // Avoid the redundant two status FFIs on each due scheduler turn.
  output:=make([]byte,capacity)
 var used uintptr
 var seq uint32
 var pn uint64
 err:=winOwnerCall(s.bridge.feedbackDueProc,
  uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&output[0])),uintptr(capacity),
  uintptr(unsafe.Pointer(&used)),uintptr(unsafe.Pointer(&seq)),
  uintptr(unsafe.Pointer(&pn)))
 runtime.KeepAlive(output);runtime.KeepAlive(s.bridge.epoch)
 if err!=nil{return nil,0,0,fmt.Errorf("%w: bounded reverse M2 due stage=native_abi %v",errV4WindowsOwner,err)}
 if used>uintptr(capacity){return nil,0,0,fmt.Errorf("%w: bounded reverse M2 due stage=length used=%d cap=%d",errV4WindowsOwner,used,capacity)}
 if used==0{return nil,0,0,nil}
 if used<51{return nil,0,0,errV4WindowsOwner}
 return output[:used],seq,pn,nil
}
// Confirm only whether Npcap accepted the original Rust M1 control bytes.
// False is NotSent, never M2 acknowledgment or success from TCP presentation.
func(s *V4WindowsAuthenticatedClientOwner) CompleteBoundOriginalM2Feedback(
 ctx context.Context,pn uint64,npcapSent bool,
)error{
 if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
  s.bridge.feedbackResultProc==nil{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
 var copied uintptr
 if npcapSent{copied=1}
 err:=winOwnerCall(s.bridge.feedbackResultProc,
  uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(pn),copied)
 runtime.KeepAlive(s.bridge.epoch)
 return err
}
// Rust has already authenticated this record and its unique PN before
// returning OK. Malformed authenticated *DATA* is a per-record discard, not
// proof that the authenticated owner/OS generation is corrupt. An unexpected
// returned kind, by contrast, is an owner ABI contract failure: Stop.
// The error carries only a bounded validation stage and lengths, no wire.
func normalOpenVerifiedKind1(kind uint32,used uintptr,plain []byte)error{
 if kind!=1{
  return fmt.Errorf("%w: NORMAL_OPEN_UNEXPECTED_KIND kind=%d used=%d",
   errV4WindowsOwner,kind,used)
 }
 if used<20||used>uintptr(len(plain)){
  if used>uintptr(len(plain)){
   return fmt.Errorf("%w: NORMAL_OPEN_OUTPUT_OVERFLOW used=%d cap=%d",
    errV4WindowsOwner,used,len(plain))
  }
  return fmt.Errorf("%w: NORMAL_OPEN_AUTHENTICATED_IPV4_SHORT used=%d",
   &v4WindowsNativeABIError{Code:1},used)
 }
 version,ihl:=plain[0]>>4,plain[0]&15
 if version!=4||ihl<5||int(ihl)*4>int(used){
  return fmt.Errorf("%w: NORMAL_OPEN_AUTHENTICATED_IPV4_HEADER used=%d version=%d ihl=%d",
   &v4WindowsNativeABIError{Code:1},used,version,ihl)
 }
 return nil
}

// OpenBoundOriginalNormalOrKind1 calls the ONE original Rust M1/M3 AEAD+PN
// opener and returns verified kind=1 IPv4 or kind=2 canonical staged M2
// receipt. The latter has NO Wintun packet and is NOT an M2 ACK/repair
// until the same Rust owner scopes it to a frozen, definitely-sent shadow.
// Go's carrier TCP ACK remains presentation-only.
func(s *V4WindowsAuthenticatedClientOwner) OpenBoundOriginalNormalOrKind1(
    ctx context.Context,seq uint32,wire []byte,
)([]byte,uint32,uint64,error){
    if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
        s.bridge.openKind1Proc==nil{
        return nil,0,0,fmt.Errorf("%w: NORMAL_OPEN_OWNER_UNBOUND",errV4WindowsOwner)
    }
    if len(wire)<51||len(wire)>s.device.maxIPv4+31{
        return nil,0,0,fmt.Errorf("%w: NORMAL_OPEN_WIRE_BUDGET wire=%d max=%d",
            errV4WindowsOwner,len(wire),s.device.maxIPv4+31)
    }
    if err:=ctx.Err();err!=nil{return nil,0,0,err}
    borrowRelease,borrowErr:=s.device.borrowHot(ctx)
 if borrowErr!=nil{return nil,0,0,errors.Join(errV4WindowsOwner,borrowErr)}
 defer borrowRelease()
    // Same M4 protected hot borrow + Rust v3_ready/AEAD/unique-PN:
    // no need to fetch two more mutable status snapshots per packet.
        plaintext:=make([]byte,len(wire))
    var used uintptr
    var kind uint32
    var pn uint64
    err:=winOwnerCall(s.bridge.openKind1Proc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&plaintext[0])),uintptr(len(plaintext)),
        uintptr(unsafe.Pointer(&used)),
        uintptr(unsafe.Pointer(&kind)),
        uintptr(unsafe.Pointer(&pn)),
    )
    runtime.KeepAlive(wire)
    runtime.KeepAlive(plaintext)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil {
        // The original Rust rc stays wrapped for Fatal() classification.
        return nil,0,0,fmt.Errorf("NORMAL_OPEN_RUST_ABI seq=%d wire=%d: %w",
            seq,len(wire),errors.Join(errV4WindowsOwner,err))
    }
    if used>uintptr(len(plaintext)){
        return nil,0,0,fmt.Errorf("%w: NORMAL_OPEN_OUTPUT_OVERFLOW used=%d cap=%d",
            errV4WindowsOwner,used,len(plaintext))
    }
    if kind==2 && used==0{
        return nil,kind,pn,nil // Rust retains decoded, authenticated kind1
    }
    if verifyErr:=normalOpenVerifiedKind1(kind,used,plaintext);verifyErr!=nil{
        return nil,0,0,verifyErr
    }
    return plaintext[:used],kind,pn,nil
}

// This only stops Rust M1/M3 after an M4-held CURRENT created Wintun has
// separately quiesced (or without any device binding at all). It cannot be
// promoted to V4OriginalOwnerStopper's "OwnerAndDriversDrained" product
// completion, because real WFP/routes and their WAL are M4's responsibility.
func(s *V4WindowsAuthenticatedClientOwner) StopScopedOwner(ctx context.Context)error{
    if s==nil||s.bridge==nil||ctx==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if s.device!=nil{
        if err:=s.device.quiesceAndStopRustOnly(ctx);err!=nil{return err}
        return nil
    }
    return s.bridge.stopRustOwnerOnly()
}
func(s *V4WindowsAuthenticatedClientOwner) StopAndReleaseOriginalOwner()(
    V4OwnerStopCompletion,error,
){
    // Explicit rejection prevents M4 network cleanup being ordered after
    // merely an M0 Rust crypto owner without real native M4 kernel drivers
    // and CAS-proven OS WFP/route ownership.
    return V4OwnerStopCompletion{},errors.Join(errV4WindowsOwner,ErrAdmissionUnsupported)
}


// Authenticated SERVER half of the same original-Go FakeTCP credential TLS
// callback and native Windows Rust M1/M3 owner; used for real peer receive.
// It cannot be fabricated with caller-supplied cold material or exported
// command-line parameters and does not authorize the host WFP product.
type V4WindowsAuthenticatedServerOwner struct{
    bridge *v4WindowsNativeOwnerBridge
    device *v4WindowsRealDeviceLease
}
func V4WindowsEstablishOriginalServerOwner(
    ctx context.Context,library string,assoc *faketcp.ServerAssociation,
    cfg ServerAdmissionConfig,options V4ServerOptions,
)(*V4WindowsAuthenticatedServerOwner,*V4ServerSession,error){
    if ctx==nil||assoc==nil{return nil,nil,errV4WindowsOwner}
    owner,err:=newV4WindowsPrivateOwnerBridge(library)
    if err!=nil{return nil,nil,err}
    if options.ownerBridge!=nil{return nil,nil,errV4WindowsOwner}
    options.ownerBridge=owner
    session,err:=EstablishServerV4(ctx,assoc,cfg,options)
    if err!=nil{return nil,nil,err}
    st,err:=owner.state()
    if err!=nil||st.phase!=2||st.server!=1||st.applied!=0||
        st.generation==0||!owner.committed{return nil,nil,errV4WindowsOwner}
    return &V4WindowsAuthenticatedServerOwner{bridge:owner},session,nil
}
func(s *V4WindowsAuthenticatedServerOwner) BindOriginalM4NativeDevice(
    ctx context.Context,device V4WindowsCurrentNativeDevice,
    id V4WindowsNativeDeviceIdentity,
)error{
    if s==nil||s.bridge==nil||s.device!=nil{return errV4WindowsOwner}
    hold,err:=s.bridge.holdOriginalCreatedWintun(ctx,device,id)
    if hold!=nil{s.device=hold}
    return err
}
func(s *V4WindowsAuthenticatedServerOwner) checkedBound(
    ctx context.Context,
)error{
    if s==nil||ctx==nil||s.bridge==nil||s.device==nil||
        s.bridge.handle==0{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
        return errors.Join(errV4WindowsOwner,err)
    }
    st,err:=s.bridge.state()
    if err!=nil||st.phase!=2||st.server!=1||st.applied!=0||
        st.generation==0{return errV4WindowsOwner}
    dev,err:=s.bridge.realNativeDeviceState()
    if err!=nil||dev.Bound!=1||dev.Quiesced!=0||dev.Applied!=0||
        dev.IfIndex!=s.device.identity.InterfaceIndex||
        dev.LUID!=s.device.identity.LUID{
        return errV4WindowsOwner
    }
    return nil
}
// Actual original TLS-derived SERVER M3 authenticated decrypt, receiving
// only the exact native kernel UDP application's wire record. The C ABI
// consumes replay/PN and never returns failed AEAD plaintext.
func(s *V4WindowsAuthenticatedServerOwner) OpenBoundOriginalNormalOff(
    ctx context.Context,seq uint32,wire []byte,
)([]byte,error){
    if s==nil||s.device==nil||len(wire)<51||len(wire)>s.device.maxIPv4+31{return nil,errV4WindowsOwner}
    if err:=s.checkedBound(ctx);err!=nil{return nil,err}
    plain:=make([]byte,len(wire))
    var used uintptr
    err:=winOwnerCall(s.bridge.openNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(seq),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&plain[0])),uintptr(len(plain)),
        uintptr(unsafe.Pointer(&used)))
    runtime.KeepAlive(wire)
    runtime.KeepAlive(plain)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used<20||used>uintptr(len(plain)){
        return nil,errors.Join(errV4WindowsOwner,err)
    }
    if plain[0]>>4!=4||plain[0]&15<5||
        int(plain[0]&15)*4>int(used){
        return nil,errV4WindowsOwner
    }
    return plain[:used],nil
}
// True original TLS-derived SERVER M1 immutable outbound AEAD record,
// using the same bounded 576-byte native normal/off Rust budget as client.
func(s *V4WindowsAuthenticatedServerOwner) SealBoundOriginalNormalOff(
    ctx context.Context,ipv4 []byte,
)([]byte,uint32,uint64,error){
    if s==nil||s.device==nil||len(ipv4)<20||len(ipv4)>s.device.maxIPv4||ipv4[0]>>4!=4{
        return nil,0,0,errV4WindowsOwner
    }
    if err:=s.checkedBound(ctx);err!=nil{return nil,0,0,err}
    wire:=make([]byte,len(ipv4)+31)
    var used uintptr
    var seq uint32
    var pn uint64
    err:=winOwnerCall(s.bridge.sealNormalProc,
        uintptr(s.bridge.handle),
        uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
        uintptr(s.device.identity.LUID),
        uintptr(s.device.identity.InterfaceIndex),
        uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
        uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
        uintptr(unsafe.Pointer(&used)),
        uintptr(unsafe.Pointer(&seq)),uintptr(unsafe.Pointer(&pn)))
    runtime.KeepAlive(ipv4);runtime.KeepAlive(wire)
    runtime.KeepAlive(s.bridge.epoch)
    if err!=nil||used!=uintptr(len(wire)){
        return nil,0,0,errors.Join(errV4WindowsOwner,err)
    }
    return wire,seq,pn,nil
}
func(s *V4WindowsAuthenticatedServerOwner) StopScopedOwner(ctx context.Context)error{
    if s==nil||ctx==nil||s.bridge==nil{return errV4WindowsOwner}
    if err:=ctx.Err();err!=nil{return err}
    if s.device!=nil{return s.device.quiesceAndStopRustOnly(ctx)}
    return s.bridge.stopRustOwnerOnly()
}

// OriginalVerifiedTCPBoundaries exposes ONLY original FakeTCP Detach's
// authenticated TCP seq/ACK starting fence for the packet transport.
// It is not a cold key, a Rust handle or an OS network authorization.
func(s *V4WindowsAuthenticatedClientOwner) OriginalVerifiedTCPBoundaries()(
 sendNext,receiveNext uint32,err error,
){
 if s==nil||s.bridge==nil||s.device==nil||!s.bridge.committed||
  s.bridge.stopped||s.bridge.tcpSendNext==0||
  s.bridge.tcpRecvNext==0{
  return 0,0,errV4WindowsOwner
 }
 state,e:=s.OriginalOwnerReadback()
 if e!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied{
  return 0,0,errV4WindowsOwner
 }
 return s.bridge.tcpSendNext,s.bridge.tcpRecvNext,nil
}

// BoundOriginalIPv4Budget comes only from the original TLS Rust owner after
// M4-verified native Wintun Hold and one Win32 real interface MTU readback.
// A stale, quiesced or stopped generation MUST NOT use this cached ceiling.
func(s *V4WindowsAuthenticatedClientOwner) BoundOriginalIPv4Budget(
 ctx context.Context,
)(int,error){
 if ctx==nil||s==nil||s.device==nil||s.bridge==nil||
  s.device.maxIPv4<20{return 0,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return 0,err}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
  return 0,err
 }
 state,err:=s.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied{
  return 0,errV4WindowsOwner
 }
 return s.device.maxIPv4,nil
}
