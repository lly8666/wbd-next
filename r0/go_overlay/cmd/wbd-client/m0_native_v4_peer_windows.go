//go:build windows && wbd_v4_embedded_go
package main

// Real original-Go post-credential-TLS Windows Rust M3 peer packet pump.
// The M4-created, generation-pinned native Wintun kernel ring owns all
// ingress/egress. Only independently authenticated Rust records reach it.
import (
 "context"
 "errors"
 "fmt"
 "runtime"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
const (
 m0V4BatchPackets=32
 m0V4BatchCPU=2*time.Millisecond
 m0V4IdlePoll=time.Millisecond
 m0V4RetxAfter=750*time.Millisecond
 m0V4TxPendingMax=256 // non-Normal legacy carrier path only
 m0V4M2ShadowCredit=1536 // Rust original Normal M1 arena2048, 10Mbps/RTT600ms bounded
)
type m0NativeV4Outbound struct {
 seq uint32
 wire []byte // immutable Rust FrozenRecord ciphertext, reused byte-exact on retry
 sentAt time.Time
 lastSent time.Time
 retries uint32
}
// Source-locked low-memory audit: only immutable metadata from Rust M3,
// not ciphertext, IV, key, payload, tunnel addresses or application bytes.
// Data writer serializes producer/feedback/parity within the same pulse.
type m0V4TXEvent struct {
 Kind string
 Seq uint32
 Expected uint32
 PN uint64
 Bytes uint32
 AgeMS int64
 Status string
}
const m0V4TXAuditSlots=64
type m0NativeV4Peer struct {
 mu sync.Mutex
 owner *realityfront.V4WindowsAuthenticatedClientOwner
 mode m0WindowsV4Mode
 initialProfile realityfront.FecV2Profile
 autoStartProfile realityfront.FecV2Profile
 autoPolicy realityfront.FecV2AutoPolicy
 autoController *realityfront.V4WindowsOriginalFEC2AutoController
 endpoint *faketcp.NpcapEndpoint
 flow faketcp.ClientFlow
 inbound <-chan faketcp.Segment
 ring *windowsclient.N4OriginalKernelPacketLease
 identity windowsclient.N4UnifiedIdentity
 sendNext,recvNext,peerAck uint32
 auditStarted time.Time
 auditCursor uint64
 auditEvents [m0V4TXAuditSlots]m0V4TXEvent
 rx *m0V4RxWindow
 scratch []byte // one retained true kernel ring copy buffer for all pulses
 maxIPv4 int
 pending []m0NativeV4Outbound
 // One original-NPF copied-prefix completion batch. The same Rust PN/SEQ
 // remains pending/frozen until a bounded synchronous batch report after I/O.
 m2Results [m0V4BatchPackets]realityfront.V4WindowsM2FirstsendResult
 m2ResultsCount int
 sourceBatchCounts [5]uint64 // truthful 1..4 ready originals, not target fill rate
 sourceBatchStageFailures uint64
 maxM2CompletionBatch uint32
 // Fixed capacity, reused every fair TX turn. Go does not allocate a
 // fresh ciphertext slice or make four separate Rust FFI transitions.
 sourceInputs [realityfront.V4WindowsOriginalSourceBatchMax]realityfront.V4WindowsOriginalSourceInput
 sourceOutputs [realityfront.V4WindowsOriginalSourceBatchMax]realityfront.V4WindowsOriginalSourceOutput
 sent,opened,sentAfterOpen,retries,duplicates,rejected,oversize,feedbackSent uint64
 pendingCount int
 effective realityfront.V4WindowsM2Effective
 fixedApplied bool
 lastFixedRead time.Time
 oldestUnackedAt time.Time
 lastRXAt time.Time
 maxRXInterdeliveryMs int64
 running,stopping bool
 stop,done chan struct{}
 workerCancel context.CancelFunc
 failure chan error
}
func newM0NativeV4Peer(
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 endpoint *faketcp.NpcapEndpoint,flow faketcp.ClientFlow,
 inbound <-chan faketcp.Segment,
)(*m0NativeV4Peer,error){
 return newM0NativeV4PeerForMode(owner,endpoint,flow,inbound,m0WinModeNormal)
}
// The production TCP carrier and native Wintun worker are identical for
// Normal and authenticated feature7 FEC2. Game requires 2/4 independent
// original FakeTCP/TLS lanes and must NOT silently use one-lane fallback.
func newM0NativeV4PeerForMode(
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 endpoint *faketcp.NpcapEndpoint,flow faketcp.ClientFlow,
 inbound <-chan faketcp.Segment,mode m0WindowsV4Mode,
)(*m0NativeV4Peer,error){
 if owner==nil||endpoint==nil||inbound==nil{return nil,windowsclient.ErrN4NativeGuard}
 if mode!=m0WinModeNormal&&mode!=m0WinModeFixed&&mode!=m0WinModeAuto{
  return nil,windowsclient.ErrN4NativeGuard
 }
 if err:=flow.Validate();err!=nil{return nil,err}
 return &m0NativeV4Peer{
  owner:owner,mode:mode,initialProfile:realityfront.FecV2Maximum,
  endpoint:endpoint,flow:flow,inbound:inbound,
  stop:make(chan struct{}),done:make(chan struct{}),
  failure:make(chan error,1),
  pending:make([]m0NativeV4Outbound,0,m0V4TxPendingMax),
 },nil
}
func(p *m0NativeV4Peer) BindNativeRing(
 ctx context.Context,ring *windowsclient.N4OriginalKernelPacketLease,
 id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||ctx==nil||ring==nil||id.Installation==[16]byte{}||
  id.Generation==[16]byte{}||id.WintunLUID==0||id.WintunIndex==0{
  return windowsclient.ErrN4NativeGuard
 }
 if err:=ctx.Err();err!=nil{return err}
 send,recv,err:=p.owner.OriginalVerifiedTCPBoundaries()
 if err!=nil{return err}
 maxIPv4,err:=p.owner.BoundOriginalIPv4Budget(ctx)
 if err!=nil||maxIPv4<20||maxIPv4>2048{return windowsclient.ErrN4NativeGuard}
 if _,err=ring.Counts();err!=nil{return err}
 p.mu.Lock();defer p.mu.Unlock()
 if p.ring!=nil||p.stopping||send==0||recv==0{
  return windowsclient.ErrN4NativeGuard
 }
 // Register the single Rust M2 recovery direction ONLY when the live
 // original Go credential TLS and the same M4-created Wintun are bound.
 // Do not arm parallel FEC2 until its genuine public M2 mode is approved.
 if p.mode==m0WinModeNormal||p.mode==m0WinModeFixed||p.mode==m0WinModeAuto{
  if err:=p.owner.ArmBoundOriginalM2(ctx);err!=nil{return err}
  actual,readErr:=p.owner.ReadBoundOriginalM2Effective(ctx)
  if readErr!=nil||actual.BusinessIPv4MTU!=uint32(maxIPv4){
   return fmt.Errorf("%w: original M2 effective Rust/FEC MTU readback mismatch go=%d rust=%d: %v",
    windowsclient.ErrN4NativeGuard,maxIPv4,actual.BusinessIPv4MTU,readErr)
  }
  p.effective=actual
  if p.mode==m0WinModeFixed||p.mode==m0WinModeAuto{
   if err:=p.owner.SelectBoundOriginalFEC2Initial(ctx,p.initialProfile);err!=nil{
    return err
   }
  }
  if p.mode==m0WinModeAuto {
   ctl,err:=realityfront.NewV4WindowsOriginalFEC2AutoController(
    p.owner,p.autoPolicy,p.autoStartProfile)
   if err!=nil{return err}
   if err=ctl.Start();err!=nil{return err}
   p.autoController=ctl
  }
 }
 p.ring=ring;p.identity=id;p.sendNext=send;p.recvNext=recv
 p.auditStarted=time.Now()
 p.peerAck=send
 p.rx=newM0V4RxWindow(recv)
 p.maxIPv4=maxIPv4
 p.scratch=make([]byte,maxIPv4+31)
 return nil
}
// These ring writes occur only in the single native pulse send-owner.
// Separate counter snapshots use p.mu, without storing any sensitive wire.
func(p *m0NativeV4Peer) noteTX(kind string,seq,expected uint32,pn uint64,n int,status string){
 if p==nil{return}
 p.mu.Lock();defer p.mu.Unlock()
 ms:=int64(0)
 if !p.auditStarted.IsZero(){ms=time.Since(p.auditStarted).Milliseconds()}
 p.auditEvents[p.auditCursor%m0V4TXAuditSlots]=m0V4TXEvent{
  Kind:kind,Seq:seq,Expected:expected,PN:pn,Bytes:uint32(n),AgeMS:ms,Status:status,
 }
 p.auditCursor++
}
func(p *m0NativeV4Peer) txTrace()string{
 p.mu.Lock();defer p.mu.Unlock()
 limit:=p.auditCursor
 if limit>m0V4TXAuditSlots{limit=m0V4TXAuditSlots}
 var out string
 for i:=uint64(0);i<limit;i++{
  idx:=(p.auditCursor-limit+i)%m0V4TXAuditSlots
  e:=p.auditEvents[idx]
  out+=fmt.Sprintf(" [%dms %s seq=%d exp=%d pn=%d bytes=%d stage=%s]",
   e.AgeMS,e.Kind,e.Seq,e.Expected,e.PN,e.Bytes,e.Status)
 }
 return out
}
func(p *m0NativeV4Peer) stopped()bool{
 select{case <-p.stop:return true;default:return false}
}
// Only real peer TCP cumulative acknowledgement may release an immutable
// ciphertext carrier. It is not a fictitious M2 Applied or app-delivery ACK.
func(p *m0NativeV4Peer) observePeerACK(ack uint32){
 if int32(ack-p.peerAck)<0||int32(p.sendNext-ack)<0{return}
 if int32(ack-p.peerAck)>0{p.peerAck=ack}
 taken:=0
 for taken<len(p.pending){
  row:=p.pending[taken]
  end:=row.seq+uint32(len(row.wire))
  if int32(ack-end)<0{break}
  p.pending[taken].wire=nil
  taken++
 }
 if taken>0{
  copy(p.pending,p.pending[taken:])
  for i:=len(p.pending)-taken;i<len(p.pending);i++{p.pending[i]=m0NativeV4Outbound{}}
  p.pending=p.pending[:len(p.pending)-taken]
 }
 p.mu.Lock()
 if p.mode!=m0WinModeNormal{p.pendingCount=len(p.pending)}
 if len(p.pending)>0{p.oldestUnackedAt=p.pending[0].sentAt
 }else{p.oldestUnackedAt=time.Time{}}
 p.mu.Unlock()
}
func(p *m0NativeV4Peer) sendCarrier(seq,ack uint32,wire []byte)error{
 _,err:=p.endpoint.WriteSegment(1,faketcp.Segment{
  SrcIP:p.flow.LocalIP,DstIP:p.flow.PeerIP,
  SrcPort:p.flow.LocalPort,DstPort:p.flow.PeerPort,
  Seq:seq,Ack:ack,Flags:faketcp.FlagACK|faketcp.FlagPSH,
  Window:65535,Payload:wire,
 })
 return err
}
func(p *m0NativeV4Peer) sendACK()error{
 _,err:=p.endpoint.WriteSegment(1,faketcp.Segment{
  SrcIP:p.flow.LocalIP,DstIP:p.flow.PeerIP,
  SrcPort:p.flow.LocalPort,DstPort:p.flow.PeerPort,
  Seq:p.sendNext,Ack:p.recvNext,Flags:faketcp.FlagACK,Window:65535,
 })
 return err
}
// Read up to four ALREADY-ready native Wintun frames with zero batching
// wait, seal all in the one original Rust M1/FixedStream owner, then send
// each fully authenticated packet through its original pcap endpoint.
// Stop is the ONLY recovery from a post-seal error or partial driver copy.
func(p *m0NativeV4Peer) transmitReadySourceBatch(
 ctx context.Context,limit int,
)(int,error){
 if p==nil||p.ring==nil||p.owner==nil||p.stopped(){
  return 0,windowsclient.ErrN4NativeGuard
 }
 if limit<=0||limit>realityfront.V4WindowsOriginalSourceBatchMax{
  return 0,windowsclient.ErrN4NativeGuard
 }
 ready,dropped:=0,0
 for slot:=0;slot<limit;slot++{
  n,err:=p.ring.ReceiveReadyIPv4(ctx,p.scratch)
  if errors.Is(err,windowsclient.ErrN4NativeNoPacket){break}
  if err!=nil{
   if errors.Is(err,context.Canceled){return dropped,err}
   if n==0{
    p.mu.Lock();p.rejected++;p.mu.Unlock()
    dropped++;continue
   }
   return dropped,err
  }
  if n<20||n>p.maxIPv4||n>2048{
   p.mu.Lock();p.oversize++;p.mu.Unlock()
   dropped++;continue
  }
  in:=&p.sourceInputs[ready]
  in.Length=uint32(n)
  in.Reserved=0
  copy(in.IPv4[:n],p.scratch[:n])
  ready++
 }
 if ready==0{return dropped,nil}
 count,err:=p.owner.SealBoundOriginalSourceBatch(
  ctx,p.sourceInputs[:ready],p.sourceOutputs[:ready])
 p.mu.Lock()
 p.sourceBatchCounts[ready]++
 if err!=nil||count!=uint32(ready){p.sourceBatchStageFailures++}
 p.mu.Unlock()
 if err!=nil||count!=uint32(ready){
  // Already allocated nonces/serials in Rust, if any, cannot be replayed
  // or bridged by Go. A hard owner stop protects the entire generation.
  return dropped,fmt.Errorf("%w: original M1 source stage batch produced=%d ready=%d: %v",
   windowsclient.ErrN4NativeGuard,count,ready,err)
 }
 for i:=0;i<ready;i++{
  row:=&p.sourceOutputs[i]
  n:=int(row.Used)
  if n<=31||n>len(row.Wire)||row.Seq!=p.sendNext{
   p.noteTX("source-batch",row.Seq,p.sendNext,row.PN,n,"SEQ_OR_LENGTH_MISMATCH")
   return dropped+i,fmt.Errorf(
    "%w: original source stage batch contiguous TX expected=%d got=%d used=%d; recent=%s",
    windowsclient.ErrN4NativeGuard,p.sendNext,row.Seq,n,p.txTrace())
  }
  wire:=row.Wire[:n]
  sentErr:=p.sendCarrier(row.Seq,p.recvNext,wire)
  if sentErr==nil{
   p.noteTX("source-batch",row.Seq,p.sendNext,row.PN,n,"NPF_COPIED")
  }else{
   p.noteTX("source-batch",row.Seq,p.sendNext,row.PN,n,"NPF_UNCERTAIN")
  }
  if p.m2ResultsCount>=m0V4BatchPackets{
   return dropped+i,fmt.Errorf(
    "%w: original NPF M2 completion buffer full",
    windowsclient.ErrN4NativeGuard)
  }
  outcome:=uint32(1)
  if sentErr!=nil{outcome=2} // Uncertain, no fresh F credit
  p.m2Results[p.m2ResultsCount]=realityfront.V4WindowsM2FirstsendResult{
   PN:row.PN,Seq:row.Seq,WireLen:uint32(n),Outcome:outcome,
  }
  p.m2ResultsCount++
  if sentErr!=nil{return dropped+i,sentErr}
  p.sendNext=row.Seq+uint32(n)
  p.mu.Lock()
  p.sent++
  if p.opened>0{p.sentAfterOpen++}
  p.mu.Unlock()
 }
 return dropped+ready,nil
}
func(p *m0NativeV4Peer) transmitOne(ctx context.Context)(bool,error){
 if p.stopped(){return false,context.Canceled}
 // Original M2 shadow stores OPTIONAL frozen repair candidates. Its
 // occupancy never waits on peer ACK to permit new Wintun DATA. The Rust
 // owner still makes an honest, bounded choice about repair retention.
 if p.mode!=m0WinModeNormal&&p.mode!=m0WinModeFixed&&p.mode!=m0WinModeAuto &&
    len(p.pending)>=m0V4TxPendingMax{return false,nil}
 n,err:=p.ring.ReceiveReadyIPv4(ctx,p.scratch)
 if errors.Is(err,windowsclient.ErrN4NativeNoPacket){return false,nil}
 if err!=nil{
  if errors.Is(err,context.Canceled){return false,err}
  // A malformed/oversize real kernel frame is an explicit failed copy,
  // never a truncated success and never a global connection kill.
  if n==0{p.mu.Lock();p.rejected++;p.mu.Unlock();return true,nil}
  return false,err
 }
 if n<20||n>p.maxIPv4{
  p.mu.Lock();p.oversize++;p.mu.Unlock();return true,nil
 }
 var ciphertext []byte
 var seq uint32
 var pn uint64
 if p.mode==m0WinModeNormal {
  ciphertext,seq,pn,err=p.owner.SealBoundOriginalNormalOff(ctx,p.scratch[:n])
 }else{
  // Both Fixed and Auto reuse exactly Linux's shared FixedStream,
  // immutable M1/RS16 block/index and deferred parity owner. Auto
  // starts Strong=5 at revision1 and later follows only authenticated
  // shared-controller revisions; never one Go block per packet.
  ciphertext,seq,pn,err=p.owner.SealBoundOriginalFixedSource(ctx,p.scratch[:n])
 }
 if err!=nil{return false,fmt.Errorf("M0 native original M3 seal mode=%s: %w",p.mode,err)} // original fail-closed Stop

 if seq!=p.sendNext{
  p.noteTX("source",seq,p.sendNext,pn,len(ciphertext),"SEQ_MISMATCH")
  return false,fmt.Errorf("%w: native source TX sequence mismatch expected=%d got=%d; recent=%s",
   windowsclient.ErrN4NativeGuard,p.sendNext,seq,p.txTrace())
 }
 err=p.sendCarrier(seq,p.recvNext,ciphertext)
 if err==nil{p.noteTX("source",seq,p.sendNext,pn,len(ciphertext),"NPF_COPIED")
 }else{p.noteTX("source",seq,p.sendNext,pn,len(ciphertext),"NPF_ERROR")}
 if p.mode==m0WinModeNormal||p.mode==m0WinModeFixed||p.mode==m0WinModeAuto{
  // A valid original NPF pcap_sendpacket return is the ONLY new M2
  // data firstsend event. Negative error is NOT peer receipt or a
  // definite acknowledgement; a failed callback fences this owner.
  if p.m2ResultsCount>=m0V4BatchPackets{
   return false,fmt.Errorf("%w: native firstsend completion descriptors exhausted",windowsclient.ErrN4NativeGuard)
  }
  outcome:=uint32(1)
  if err!=nil{
   // An NPF syscall error is not positive proof that the driver did not
   // attempt a copy. It consumes this PN as Uncertain with no F credit.
   outcome=2
  }
  p.m2Results[p.m2ResultsCount]=realityfront.V4WindowsM2FirstsendResult{
   PN:pn,Seq:seq,WireLen:uint32(len(ciphertext)),Outcome:outcome,
  }
  p.m2ResultsCount++
 }
 if err!=nil{return false,err}
 if p.mode!=m0WinModeNormal&&p.mode!=m0WinModeFixed&&p.mode!=m0WinModeAuto{
  p.pending=append(p.pending,m0NativeV4Outbound{
   // Non-Normal remains unqualified and never substitutes TCP retry for M2.
   seq:seq,wire:ciphertext,sentAt:time.Now(),lastSent:time.Now(),
  })
 }
 p.sendNext=seq+uint32(len(ciphertext))
 p.mu.Lock()
 p.sent++
 if p.opened>0{p.sentAfterOpen++}
 if p.mode!=m0WinModeNormal&&p.mode!=m0WinModeFixed&&p.mode!=m0WinModeAuto{
  p.pendingCount=len(p.pending)
  if len(p.pending)>0{p.oldestUnackedAt=p.pending[0].sentAt}
 }
 p.mu.Unlock()
 return true,nil
}
func(p *m0NativeV4Peer) receiveOne(ctx context.Context,seg faketcp.Segment)error{
 if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
  return fmt.Errorf("%w: native peer TCP carrier FIN/RST flags=%d",windowsclient.ErrN4NativeGuard,seg.Flags)
 }
 p.observePeerACK(seg.Ack)
 if len(seg.Payload)==0{return nil}
 maxWire:=p.maxIPv4+31
 if p.mode!=m0WinModeNormal{maxWire+=14}
 if len(seg.Payload)<51||len(seg.Payload)>maxWire{
  p.mu.Lock();p.oversize++;p.mu.Unlock()
  return nil
 }
 ok,rangeErr:=p.rx.Check(seg.Seq,len(seg.Payload))
 independent:=false
 if rangeErr!=nil{
  // Presentation TCP bitmap remains fixed 256 entries / 128KiB. After
  // true Rust M2 arming, a later record can be AEAD/PN-authenticated
  // despite an old cumulative ACK hole, WITHOUT granting a fake ACK.
  independent=(p.mode==m0WinModeNormal||p.mode==m0WinModeFixed||p.mode==m0WinModeAuto) &&
   p.rx.IndependentAEADCandidate(seg.Seq,len(seg.Payload))
  if !independent{
   p.mu.Lock();p.rejected++;p.mu.Unlock()
   return nil
  }
 }
 if !ok&&!independent{
  p.mu.Lock();p.duplicates++;p.mu.Unlock()
  return nil
 }
 // Native Rust authenticates each record and handles dedup/RS16 first
 // delivery. A single repair ciphertext may release several IPv4 packets;
 // commit cumulative TCP carrier receipt only after ALL Wintun copies.
 var frames [][]byte
 if p.mode==m0WinModeNormal{
  plain,kind,_,openErr:=p.owner.OpenBoundOriginalNormalOrKind1(ctx,seg.Seq,seg.Payload)
  if openErr!=nil{
   // Rust owner/arena/state faults must not masquerade as arbitrary
   // untrusted-wire authentication rejects. Only rc=INVALID retains
   // the existing packet rejection; all other statuses Stop this owner.
   if realityfront.V4WindowsNativeOwnerFatal(openErr){
    return fmt.Errorf("%w: original Normal M1/M3 open owner failure: %w",
     windowsclient.ErrN4NativeGuard,openErr)
   }
   p.mu.Lock();p.rejected++;p.mu.Unlock()
   return nil
  }
  if kind==1 {
   frames=[][]byte{plain}
  }else if kind==2 {
   // Rust M3 alone authenticated this UNIQUE reverse kind1, then the
   // exact scoped GLOBAL M2 ReceiptState retired any genuinely sent PN.
   // It must not enter Wintun or impersonate an ordinary TCP ACK.
   frames=nil
   count,countErr:=p.owner.BoundOriginalM2Outstanding(ctx)
   if countErr!=nil{return fmt.Errorf("M0 original M2 authenticated receipt outstanding query: %w",countErr)}
   p.mu.Lock();p.pendingCount=int(count);p.mu.Unlock()
  }else{return fmt.Errorf("%w: native Rust M3 authenticated record kind=%d",windowsclient.ErrN4NativeGuard,kind)}
 }else{
  delivered,openErr:=p.owner.OpenBoundOriginalFEC2(ctx,seg.Seq,seg.Payload)
  if openErr!=nil{
   if realityfront.V4WindowsNativeOwnerFatal(openErr){
    return fmt.Errorf("%w: original FEC2 M1/M3 open owner failure: %w",
     windowsclient.ErrN4NativeGuard,openErr)
   }
   p.mu.Lock()
   p.rejected++
   first:=p.rejected==1
   p.mu.Unlock()
   // One exact original Rust/Go native error per generation, not
   // packet logging or another decoder. The prior whole-mode real NPF
   // run had >500 failed reverse FEC2 opens but the caller discarded
   // the actual rejection status, hiding the first cause.
   if first{
    fmt.Printf("WBD_WINDOWS_FEC2_FIRST_NATIVE_OPEN_REJECTION mode=%s seq=%d wire_bytes=%d error=%v\n",
     p.mode,seg.Seq,len(seg.Payload),openErr)
   }
   return nil
  }
  frames=make([][]byte,0,len(delivered))
  for _,frame:=range delivered{frames=append(frames,frame.IPv4)}
 }
 for _,plain:=range frames{
  if len(plain)<20||len(plain)>p.maxIPv4{return fmt.Errorf("%w: native M4 authenticated IPv4 len=%d max=%d",windowsclient.ErrN4NativeGuard,len(plain),p.maxIPv4)}
  copied,copyErr:=p.ring.WriteAuthenticatedIPv4(ctx,plain)
  if copyErr!=nil||copied!=len(plain){
   return errors.Join(fmt.Errorf("%w: native M4 Wintun write len=%d copied=%d",windowsclient.ErrN4NativeGuard,len(plain),copied),copyErr)
  }
 }
 if independent{
  // Only original Rust AEAD+unique PN allowed this forward delivery.
  // Keep original Go cumulative ACK exactly at the verified gap.
  p.recvNext=p.rx.Ack()
 }else{
  ack,ackErr:=p.rx.Copied(seg.Seq,len(seg.Payload))
  if ackErr!=nil{return ackErr}
  p.recvNext=ack
 }
 if p.mode==m0WinModeNormal||p.mode==m0WinModeFixed||p.mode==m0WinModeAuto{
  // This is AFTER the real Rust M3 unique opener and successful owned
  // Wintun copies (or authenticated kind1 handling), never raw TCP seq.
  p.rx.NoteAuthenticated(seg.Seq,len(seg.Payload))
 }
 p.mu.Lock()
 if len(frames)>0{
  now:=time.Now()
  if !p.lastRXAt.IsZero(){
   gap:=now.Sub(p.lastRXAt).Milliseconds()
   if gap>p.maxRXInterdeliveryMs{p.maxRXInterdeliveryMs=gap}
  }
  p.lastRXAt=now
 }
 p.opened+=uint64(len(frames))
 p.mu.Unlock()
 // Critical: ACK is the *highest contiguous* Rust-authenticated and
 // Wintun-copied TCP interval. Delivered future packet cannot ACK a gap.
 return p.sendACK()
}

// A real S2C M3 unique DATA PN creates a bounded reverse kind1 draft in
// the SAME original Rust authenticated owner. Exactly one original M1
// ciphertext/seq is copied through NPF; no TCP-ACK-derived M2 receipt.
func(p *m0NativeV4Peer) rustFeedbackOne(ctx context.Context)(bool,error){
 if (p.mode!=m0WinModeNormal&&p.mode!=m0WinModeFixed&&p.mode!=m0WinModeAuto)||p.stopped(){return false,nil}
 wire,seq,pn,err:=p.owner.NextBoundOriginalM2Feedback(ctx,p.maxIPv4+31)
 if err!=nil{return false,fmt.Errorf("M0 original M2 reverse-kind1 feedback draft: %w",err)}
 if len(wire)==0{return false,nil}
 if seq!=p.sendNext{
  p.noteTX("control",seq,p.sendNext,pn,len(wire),"SEQ_MISMATCH")
  settle:=p.owner.CompleteBoundOriginalM2Feedback(ctx,pn,false)
  return false,errors.Join(
   fmt.Errorf("%w: original M2 control TX sequence mismatch expected=%d got=%d; recent=%s",windowsclient.ErrN4NativeGuard,p.sendNext,seq,p.txTrace()),settle)
 }
 sentErr:=p.sendCarrier(seq,p.recvNext,wire)
 if sentErr==nil{p.noteTX("control",seq,p.sendNext,pn,len(wire),"NPF_COPIED")
 }else{p.noteTX("control",seq,p.sendNext,pn,len(wire),"NPF_ERROR")}
 settleErr:=p.owner.CompleteBoundOriginalM2Feedback(ctx,pn,sentErr==nil)
 if sentErr!=nil||settleErr!=nil{
  return false,fmt.Errorf("M0 original M2 reverse-kind1 feedback complete: %w",errors.Join(sentErr,settleErr))
 }
 p.sendNext=seq+uint32(len(wire))
 p.mu.Lock();p.feedbackSent++;p.mu.Unlock()
 return true,nil
}
// Normal/off retries are *only* originally frozen Rust M2 candidates,
// after process-global receipt/repair byte budget admission. Go copies
// ciphertext byte-exact through the same original Npcap endpoint; no new
// PN, seal call, or independent 750ms/8 retries can reach the Normal worker.
func(p *m0NativeV4Peer) rustRepairOne(ctx context.Context)(bool,error){
 if p.mode!=m0WinModeNormal&&p.mode!=m0WinModeFixed&&p.mode!=m0WinModeAuto{return false,nil}
 if p.stopped(){return false,nil}
 cap:=p.maxIPv4+31
 if p.mode!=m0WinModeNormal{cap+=14}
 wire,seq,pn,err:=p.owner.NextBoundOriginalM2Repair(ctx,cap)
 if err!=nil{return false,fmt.Errorf("M0 original M2 immutable repair candidate: %w",err)}
 if len(wire)==0{return false,nil}
 sentErr:=p.sendCarrier(seq,p.recvNext,wire)
 count,settleErr:=p.owner.CompleteBoundOriginalM2Repair(ctx,pn,sentErr==nil)
 if settleErr!=nil{return false,fmt.Errorf("M0 original M2 immutable repair completion: %w",errors.Join(windowsclient.ErrN4NativeGuard,sentErr,settleErr))}
 p.mu.Lock()
 p.pendingCount=int(count)
 if sentErr==nil{p.retries++}
 p.mu.Unlock()
 if sentErr!=nil{return false,sentErr}
 return true,nil
}

func(p *m0NativeV4Peer) rustFixedParityOne(ctx context.Context)(bool,error){
 if p.mode==m0WinModeNormal||p.stopped(){return false,nil}
 rows,err:=p.owner.NextBoundOriginalFixedParity(ctx)
 if err!=nil{return false,err}
 if len(rows)==0{return false,nil}
 copied:=uint32(0)
 for _,row:=range rows{
  if row.Seq!=p.sendNext{
   p.noteTX("parity",row.Seq,p.sendNext,row.PN,len(row.Wire),"SEQ_MISMATCH")
   _=p.owner.CompleteBoundOriginalFixedParity(ctx,copied,uint32(len(rows))-copied,0)
   return false,fmt.Errorf("%w: W168 Fixed parity TX sequence mismatch expected=%d got=%d",
    windowsclient.ErrN4NativeGuard,p.sendNext,row.Seq) // trace kept for first caller failure
  }
  if err=p.sendCarrier(row.Seq,p.recvNext,row.Wire);err!=nil{
   p.noteTX("parity",row.Seq,p.sendNext,row.PN,len(row.Wire),"NPF_ERROR")
   _=p.owner.CompleteBoundOriginalFixedParity(ctx,copied,uint32(len(rows))-copied,0)
   return false,err
  }
  p.noteTX("parity",row.Seq,p.sendNext,row.PN,len(row.Wire),"NPF_COPIED")
  p.sendNext=row.Seq+uint32(len(row.Wire))
  copied++
 }
 if err=p.owner.CompleteBoundOriginalFixedParity(ctx,copied,0,0);err!=nil{return false,err}
 return true,nil
}
func(p *m0NativeV4Peer) retryOne(now time.Time)(bool,error){
 if len(p.pending)==0||p.stopped(){return false,nil}
 for i:=range p.pending{
  pending:=&p.pending[i]
  if now.Sub(pending.lastSent)<m0V4RetxAfter{continue}
  if pending.retries>=8{
   // No silent permanent head-of-line stall. This specific original
   // carrier exhausted its finite immutable-ciphertext retry budget;
   // it is not an invented Go M2/FEC applied or packet acknowledgment.
   return false,fmt.Errorf("%w: exact original TCP carrier retry exhausted",windowsclient.ErrN4NativeGuard)
  }
  // Fixed ciphertext and original sequence; NEVER reseal or spend a PN.
  if err:=p.sendCarrier(pending.seq,p.recvNext,pending.wire);err!=nil{return false,err}
  pending.lastSent=now;pending.retries++
  p.mu.Lock();p.retries++;p.mu.Unlock()
  return true,nil
 }
 return false,nil
}
// A copied NPF prefix is settled exactly once. Errors fence this owner:
// do not re-report any descriptor after a partial or invalid Rust callback.
func(p *m0NativeV4Peer) flushOriginalFirstsend(ctx context.Context)error{
 if p==nil{return windowsclient.ErrN4NativeGuard}
 n:=p.m2ResultsCount
 if n==0{return nil}
 if n>m0V4BatchPackets{return windowsclient.ErrN4NativeGuard}
 settled,outstanding,e:=p.owner.ReportOriginalM2NpcapFirstsendBatch(
  ctx,p.m2Results[:n])
 // Regardless of the returned code, this batch cannot be tried again:
 // after NPF completion a Rust partial internal failure requires Stop.
 for i:=0;i<n;i++{p.m2Results[i]=realityfront.V4WindowsM2FirstsendResult{}}
 p.m2ResultsCount=0
 p.mu.Lock()
 if uint32(n)>p.maxM2CompletionBatch{p.maxM2CompletionBatch=uint32(n)}
 p.mu.Unlock()
 if e!=nil||settled!=uint32(n){
  return fmt.Errorf("%w: actual original NPF M2 batch completed=%d expected=%d: %v",
   windowsclient.ErrN4NativeGuard,settled,n,e)
 }
 p.mu.Lock();p.pendingCount=int(outstanding);p.mu.Unlock()
 return nil
}
// Bounded fair drain. A continuously busy Wintun cannot starve peer RX,
// and a busy peer cannot starve native kernel output. No fixed 4ms per packet.
func(p *m0NativeV4Peer) pulse(ctx context.Context)(done int,err error){
 if p==nil||p.ring==nil||p.rx==nil{return 0,windowsclient.ErrN4NativeGuard}
 // If cancellation or a kernel error stops this round after real NPF
 // copies, finish their truthful Rust PN outcomes while the original M4
 // session is still borrowed. Stop must join this pulse first.
 defer func(){
  if p.m2ResultsCount==0{return}
  flushCtx:=ctx
  if ctx.Err()!=nil{
   var cancel context.CancelFunc
   flushCtx,cancel=context.WithTimeout(context.Background(),2*time.Second)
   defer cancel()
  }
  if flushErr:=p.flushOriginalFirstsend(flushCtx);flushErr!=nil{
   err=errors.Join(err,flushErr)
  }
 }()
 start:=time.Now()
 done=0
 for done<m0V4BatchPackets&&time.Since(start)<m0V4BatchCPU{
  if err:=ctx.Err();err!=nil{return done,err}
  if p.stopped(){return done,context.Canceled}
  changed:=false
  // Direction alternates every attempted slot, rather than giving
  // a permanently full receive ring exclusive ownership of the worker.
  if done%2==0 {
   select{
   case seg,ok:=<-p.inbound:
    if !ok{return done,fmt.Errorf("%w: original NPF peer ingress queue closed during pulse",windowsclient.ErrN4NativeGuard)}
    if err:=p.receiveOne(ctx,seg);err!=nil{return done,err}
    done++;changed=true
   default:
   }
  }
  if done<m0V4BatchPackets&&time.Since(start)<m0V4BatchCPU{
   // One original Rust entry-lock + DLL FFI for <=4 ALREADY-ready
   // Wintun sources. Never wait to fill; finish and credit every real
   // NPF copied prefix before accepting reverse peer receipts.
   batch:=m0V4BatchPackets-done
   if batch>realityfront.V4WindowsOriginalSourceBatchMax{
    batch=realityfront.V4WindowsOriginalSourceBatchMax
   }
   txCount,txErr:=p.transmitReadySourceBatch(ctx,batch)
   if txErr!=nil{return done,txErr}
   done+=txCount
   if txCount>0{changed=true}
  }
  // An authenticated reverse kind1 may arrive next. Settle the genuine
  // NPF copied prefix into Rust M2 BEFORE it can receive a peer receipt.
  if flushErr:=p.flushOriginalFirstsend(ctx);flushErr!=nil{return done,flushErr}
  if done<m0V4BatchPackets{
   select{
   case seg,ok:=<-p.inbound:
    if !ok{return done,fmt.Errorf("%w: original NPF peer ingress queue closed during pulse",windowsclient.ErrN4NativeGuard)}
    if err:=p.receiveOne(ctx,seg);err!=nil{return done,err}
    done++;changed=true
   default:
   }
  }
  if !changed{break}
 }
 // One bounded retransmission opportunity EACH fair drain round, even
 // under continuously busy TX/RX. The prior idle-only retry starved all
 // missing carrier segments at 10Mbps and under constant peer traffic.
 if ctx.Err()==nil&&!p.stopped(){
  var retried bool
  var err error
  if p.mode==m0WinModeNormal||p.mode==m0WinModeFixed||p.mode==m0WinModeAuto{
   // Feedback is deadline-driven and never waits for a Go TCP presentation ACK.
   acknowledged,feedbackErr:=p.rustFeedbackOne(ctx)
   if feedbackErr!=nil{return done,feedbackErr}
   if acknowledged{done++}
   retried,err=p.rustRepairOne(ctx)
   if p.mode!=m0WinModeNormal && err==nil{
    sent,parityErr:=p.rustFixedParityOne(ctx)
    if parityErr!=nil{return done,parityErr}
    if sent{done++}
    // Each fair pulse already processes at most 32 packets/2ms.
    // At 45k source PPS this 2ms bounded maturity turn supplies up to
    // 128k expiries/s without starving fresh or holding one unbounded lock.
    if time.Since(p.lastFixedRead)>=2*time.Millisecond{
     p.lastFixedRead=time.Now()
     state,readErr:=p.owner.ReadBoundOriginalFixedMature(ctx)
     if readErr!=nil{return done,readErr}
     p.mu.Lock()
     prior:=p.fixedApplied
     p.fixedApplied=state.Applied==1
     p.mu.Unlock()
     if state.Applied==1&&!prior{
      // Mode-specific single original-M2 maturity: no inherited Auto
      // revision success and no fake public native product Applied.
      fmt.Printf("WBD_WINDOWS_FEC2_M2_MATURE_SCOPED mode=%s source=%d parity=%d reverse=%d positive2s=%d covered2s=%d\n",
       p.mode,state.CopiedSource,state.CopiedParity,state.ReverseReports,state.Positive2s,state.Covered2s)
     }
    }
   }
  }else{
   retried,err=p.retryOne(time.Now())
  }
  if err!=nil{return done,err}
  if retried{done++}
 }
 return done,nil
}
func(p *m0NativeV4Peer) VerifyPeerFirstAndReverse(
 ctx context.Context,owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||ctx==nil||owner!=p.owner||tun==nil{return windowsclient.ErrN4NativeGuard}
 p.mu.Lock()
 valid:=p.ring!=nil&&p.identity==id&&!p.running&&!p.stopping
 p.mu.Unlock()
 if !valid{return windowsclient.ErrN4NativeGuard}
 timeout,cancel:=context.WithTimeout(ctx,20*time.Second)
 defer cancel()
 idle:=time.NewTicker(m0V4IdlePoll);defer idle.Stop()
 for {
  if err:=timeout.Err();err!=nil{
   // SOURCE-locked real Windows Wintun/NPF outcome, not a Go/TCP/FEC
   // simulated receipt. Needed to distinguish unreceived reverse FEC
   // from M3 rejection, native TUN write, or missing first/reverse TX.
   stats:=p.Stats()
   ring,ringErr:=p.ring.Counts()
   p.mu.Lock()
   sentAfterOpen:=p.sentAfterOpen
   txNext,rxNext:=p.sendNext,p.recvNext
   p.mu.Unlock()
   return fmt.Errorf("native V4 actual kernel first+reverse app not observed: %w mode=%s sent_after_open=%d original_tx_next=%d original_rx_next=%d native=%+v ring=%+v ring_error=%v",
    err,p.mode,sentAfterOpen,txNext,rxNext,stats,ring,ringErr)
  }
  work,err:=p.pulse(timeout)
  if err!=nil{return err}
  p.mu.Lock();ready:=p.sent>=2&&p.opened>=1&&p.sentAfterOpen>=1;p.mu.Unlock()
  if ready{break}
  if work>0{runtime.Gosched();continue}
  select{
  case <-timeout.Done():return timeout.Err()
  case <-p.stop:return context.Canceled
  case seg,ok:=<-p.inbound:
   if !ok{return fmt.Errorf("%w: original NPF peer ingress queue closed during first-reverse",windowsclient.ErrN4NativeGuard)}
   if err:=p.receiveOne(timeout,seg);err!=nil{return err}
  case <-idle.C:
  }
 }
 workerCtx,workerCancel:=context.WithCancel(context.Background())
 p.mu.Lock();p.running=true;p.workerCancel=workerCancel;p.mu.Unlock()
 go func(){
  defer close(p.done);defer workerCancel()
  ticker:=time.NewTicker(m0V4IdlePoll);defer ticker.Stop()
  for {
   work,err:=p.pulse(workerCtx)
   if err!=nil{
    if workerCtx.Err()==nil&&!p.stopped(){
     select{case p.failure<-err:default:}
    }
    return
   }
   if work>0{runtime.Gosched();continue}
   select{
   case <-workerCtx.Done():return
   case <-p.stop:return
   case seg,ok:=<-p.inbound:
    if !ok{select{case p.failure<-fmt.Errorf("%w: original NPF peer ingress queue closed after Ready",windowsclient.ErrN4NativeGuard):default:};return}
    if err:=p.receiveOne(workerCtx,seg);err!=nil{
     if workerCtx.Err()==nil{select{case p.failure<-err:default:}}
     return
    }
   case <-ticker.C:
   }
  }
 }()
 return nil
}
func(p *m0NativeV4Peer) DrainPeerAndKernelLoans(
 ctx context.Context,owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||ctx==nil||owner!=p.owner||tun==nil{return windowsclient.ErrN4NativeGuard}
 p.mu.Lock()
 if p.ring==nil||p.identity!=id{p.mu.Unlock();return windowsclient.ErrN4NativeGuard}
 running:=p.running
 if !p.stopping{
  p.stopping=true;close(p.stop)
  if p.workerCancel!=nil{p.workerCancel()}
 }
 p.mu.Unlock()
 if running{
  select{case <-p.done:case <-ctx.Done():return ctx.Err()}
 }
 p.mu.Lock()
 for i:=range p.pending{p.pending[i]=m0NativeV4Outbound{}}
 p.pending=p.pending[:0]
 p.pendingCount=0
 p.oldestUnackedAt=time.Time{}
 p.mu.Unlock()
 // Join SAME Linux controller before dropping original Rust generation,
 // Wintun kernel ring or native OS/WAL; no late Auto revision writes.
 if p.autoController!=nil{p.autoController.Stop()}
 return ctx.Err()
}
func(p *m0NativeV4Peer) RequestAutoStartProfile(
 profile realityfront.FecV2Profile,
)(realityfront.FecV2State,error){
 if p==nil||p.mode!=m0WinModeAuto||p.autoController==nil||p.stopped(){
  return realityfront.FecV2State{},windowsclient.ErrN4NativeGuard
 }
 return p.autoController.RequestOperatorStartProfile(profile)
}
// Exact owner readback uses one tiny Rust FFI per product telemetry second,
// never per fresh DATA. A failure is returned to the owning run loop.
func(p *m0NativeV4Peer) RefreshEffective(ctx context.Context)error{
 if p==nil||p.owner==nil{return windowsclient.ErrN4NativeGuard}
 actual,err:=p.owner.ReadBoundOriginalM2Effective(ctx)
 if err!=nil{return err}
 p.mu.Lock()
 p.effective=actual
 p.mu.Unlock()
 return nil
}
func(p *m0NativeV4Peer) Errors()<-chan error{
 if p==nil{return nil}
 return p.failure
}

// m0NativeV4PacketStats is a non-secret per-owner bounded producer snapshot,
// NOT a Windows OS/WFP Applied receipt and NOT a proof of end-to-end goodput.
// Host CPU/RSS, RTT and queue-drop counters must come from the isolated
// performance harness (the internal Go heap is not Windows process RSS).
type m0NativeV4PacketStats struct{
 Mode m0WindowsV4Mode `json:"mode"`
 // Exact LOCAL NPF pre-auth drop: not WAN loss or authenticated delivery.
 NPFIngressLocalDrops uint64 `json:"npcap_ingress_local_drops"`
 TxPackets uint64 `json:"tx_records"`
 RxFirstDelivered uint64 `json:"rx_first_delivered_ipv4"`
 RetxRecords uint64 `json:"frozen_ciphertext_retransmits"`
 AuthenticatedM2FeedbackSent uint64 `json:"original_authenticated_m2_reverse_controls_sent"`
 DuplicateCarrier uint64 `json:"duplicate_tcp_carriers"`
 RejectedAuth uint64 `json:"rejected_or_invalid_carriers"`
 ExplicitOversize uint64 `json:"oversize_rejects"`
 PendingRecords int `json:"pending_original_rust_frozen_or_unacked_legacy_carrier_records"`
 EffectiveM2 realityfront.V4WindowsM2Effective `json:"actual_rust_m2_effective"`
 AutoRequestedRevision uint64 `json:"auto_requested_revision,omitempty"`
 AutoAppliedRevision uint64 `json:"auto_applied_revision,omitempty"`
 AutoDesiredProfile realityfront.FecV2Profile `json:"auto_requested_profile,omitempty"`
 AutoPending bool `json:"auto_revision_pending,omitempty"`
 AutoPolicyError string `json:"auto_policy_error,omitempty"`
 OldestPendingMS int64 `json:"oldest_unacked_carrier_ms"`
 MaxInterdeliveryMS int64 `json:"max_observed_interdelivery_ms"`
 SourceBatchCounts [5]uint64 `json:"original_source_batch_counts_0_to_4"`
 SourceBatchStageFailures uint64 `json:"original_source_stage_failures"`
 MaxM2CompletionBatch uint32 `json:"original_m2_firstsend_batch_peak"`
 // Only Go runtime memory fields; Rust DLL/OS allocations are in
 // the separate process WorkingSet/PrivateBytes sampler.
 GoHeapAllocBytes uint64 `json:"go_runtime_heap_alloc_bytes_1hz,omitempty"`
 GoHeapObjects uint64 `json:"go_runtime_heap_objects_1hz,omitempty"`
 GoMallocsTotal uint64 `json:"go_runtime_mallocs_total_1hz,omitempty"`
 GoNumGC uint32 `json:"go_runtime_num_gc_1hz,omitempty"`
}
func(p *m0NativeV4Peer) Stats()m0NativeV4PacketStats{
 if p==nil{return m0NativeV4PacketStats{}}
 p.mu.Lock()
 defer p.mu.Unlock()
 now:=time.Now()
 var age int64
 if !p.oldestUnackedAt.IsZero(){age=now.Sub(p.oldestUnackedAt).Milliseconds()}
 snapshot:=m0NativeV4PacketStats{
  Mode:p.mode,TxPackets:p.sent,RxFirstDelivered:p.opened,
  RetxRecords:p.retries,AuthenticatedM2FeedbackSent:p.feedbackSent,
  DuplicateCarrier:p.duplicates,RejectedAuth:p.rejected,
  ExplicitOversize:p.oversize,PendingRecords:p.pendingCount,
  EffectiveM2:p.effective,
  OldestPendingMS:age,MaxInterdeliveryMS:p.maxRXInterdeliveryMs,
  SourceBatchCounts:p.sourceBatchCounts,
  SourceBatchStageFailures:p.sourceBatchStageFailures,
  MaxM2CompletionBatch:p.maxM2CompletionBatch,
 }
 if p.autoController!=nil{
  state,err:=p.autoController.Snapshot()
  snapshot.AutoRequestedRevision=state.RequestedRevision
  snapshot.AutoAppliedRevision=state.AppliedRevision
  snapshot.AutoDesiredProfile=state.Desired
  snapshot.AutoPending=state.RequestedRevision!=state.AppliedRevision
  if err!=nil{snapshot.AutoPolicyError=err.Error()}
 }
 return snapshot
}
