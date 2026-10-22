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
 m0V4TxPendingMax=256
)
type m0NativeV4Outbound struct {
 seq uint32
 wire []byte // immutable Rust FrozenRecord ciphertext, reused byte-exact on retry
 sentAt time.Time
 lastSent time.Time
 retries uint32
}
type m0NativeV4Peer struct {
 mu sync.Mutex
 owner *realityfront.V4WindowsAuthenticatedClientOwner
 mode m0WindowsV4Mode
 blockID uint64 // 1-based original TLS authenticated per-direction FEC2 source
 endpoint *faketcp.NpcapEndpoint
 flow faketcp.ClientFlow
 inbound <-chan faketcp.Segment
 ring *windowsclient.N4OriginalKernelPacketLease
 identity windowsclient.N4UnifiedIdentity
 sendNext,recvNext,peerAck uint32
 rx *m0V4RxWindow
 scratch []byte // one retained true kernel ring copy buffer for all pulses
 maxIPv4 int
 pending []m0NativeV4Outbound
 sent,opened,sentAfterOpen,retries,duplicates,rejected,oversize uint64
 pendingCount int
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
  owner:owner,mode:mode,blockID:1,
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
 p.ring=ring;p.identity=id;p.sendNext=send;p.recvNext=recv
 p.peerAck=send
 p.rx=newM0V4RxWindow(recv)
 p.maxIPv4=maxIPv4
 p.scratch=make([]byte,maxIPv4+31)
 return nil
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
 p.pendingCount=len(p.pending)
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
func(p *m0NativeV4Peer) transmitOne(ctx context.Context)(bool,error){
 if p.stopped(){return false,context.Canceled}
 if len(p.pending)>=m0V4TxPendingMax{return false,nil}
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
 if p.mode==m0WinModeNormal {
  ciphertext,seq,_,err=p.owner.SealBoundOriginalNormalOff(ctx,p.scratch[:n])
 }else{
  if n>p.maxIPv4||p.blockID==0||p.blockID==^uint64(0){
   p.mu.Lock();p.oversize++;p.mu.Unlock()
   return true,nil
  }
  // Source payload includes the canonical 10-byte FEC2 block/index header;
  // Rust M1/M3 and RS16 decoder own all authenticated first deliveries.
  // A missing M2 Applied revision MUST still deny mode activation via the
  // actual public mode capability; this source path cannot fake parity.
  ciphertext,seq,_,err=p.owner.SealBoundOriginalFEC2Source(
   ctx,p.blockID,0,p.scratch[:n])
 }
 if err!=nil{return false,err} // exact generation/cipher failure: Stop

 if seq!=p.sendNext{return false,windowsclient.ErrN4NativeGuard}
 if err=p.sendCarrier(seq,p.recvNext,ciphertext);err!=nil{return false,err}
 p.pending=append(p.pending,m0NativeV4Outbound{
  // SealBound returns a fresh exact immutable Rust C-ABI record buffer.
  // Retain it for byte-identical TCP retry instead of copying ciphertext twice.
  seq:seq,wire:ciphertext,
  sentAt:time.Now(),lastSent:time.Now(),
 })
 p.sendNext=seq+uint32(len(ciphertext))
 if p.mode!=m0WinModeNormal{p.blockID++}
 p.mu.Lock()
 p.sent++
 if p.opened>0{p.sentAfterOpen++}
 p.pendingCount=len(p.pending)
 if len(p.pending)>0{p.oldestUnackedAt=p.pending[0].sentAt}
 p.mu.Unlock()
 return true,nil
}
func(p *m0NativeV4Peer) receiveOne(ctx context.Context,seg faketcp.Segment)error{
 if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
  return windowsclient.ErrN4NativeGuard
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
 if rangeErr!=nil{
  p.mu.Lock();p.rejected++;p.mu.Unlock()
  // A far-ahead/corrupt TCP sequence is not a valid ACK and cannot
  // terminate the healthy later-lane/original owner connection.
  return nil
 }
 if !ok{
  p.mu.Lock();p.duplicates++;p.mu.Unlock()
  return nil
 }
 // Native Rust authenticates each record and handles dedup/RS16 first
 // delivery. A single repair ciphertext may release several IPv4 packets;
 // commit cumulative TCP carrier receipt only after ALL Wintun copies.
 var frames [][]byte
 if p.mode==m0WinModeNormal{
  plain,openErr:=p.owner.OpenBoundOriginalNormalOff(ctx,seg.Seq,seg.Payload)
  if openErr!=nil{
   p.mu.Lock();p.rejected++;p.mu.Unlock()
   return nil
  }
  frames=[][]byte{plain}
 }else{
  delivered,openErr:=p.owner.OpenBoundOriginalFEC2(ctx,seg.Seq,seg.Payload)
  if openErr!=nil{
   p.mu.Lock();p.rejected++;p.mu.Unlock()
   return nil
  }
  frames=make([][]byte,0,len(delivered))
  for _,frame:=range delivered{frames=append(frames,frame.IPv4)}
 }
 for _,plain:=range frames{
  if len(plain)<20||len(plain)>p.maxIPv4{return windowsclient.ErrN4NativeGuard}
  copied,copyErr:=p.ring.WriteAuthenticatedIPv4(ctx,plain)
  if copyErr!=nil||copied!=len(plain){
   return errors.Join(windowsclient.ErrN4NativeGuard,copyErr)
  }
 }
 ack,err:=p.rx.Copied(seg.Seq,len(seg.Payload))
 if err!=nil{return err}
 p.recvNext=ack
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
// Bounded fair drain. A continuously busy Wintun cannot starve peer RX,
// and a busy peer cannot starve native kernel output. No fixed 4ms per packet.
func(p *m0NativeV4Peer) pulse(ctx context.Context)(int,error){
 if p==nil||p.ring==nil||p.rx==nil{return 0,windowsclient.ErrN4NativeGuard}
 start:=time.Now()
 done:=0
 for done<m0V4BatchPackets&&time.Since(start)<m0V4BatchCPU{
  if err:=ctx.Err();err!=nil{return done,err}
  if p.stopped(){return done,context.Canceled}
  changed:=false
  // Direction alternates every attempted slot, rather than giving
  // a permanently full receive ring exclusive ownership of the worker.
  if done%2==0 {
   select{
   case seg,ok:=<-p.inbound:
    if !ok{return done,windowsclient.ErrN4NativeGuard}
    if err:=p.receiveOne(ctx,seg);err!=nil{return done,err}
    done++;changed=true
   default:
   }
  }
  if done<m0V4BatchPackets{
   tx,err:=p.transmitOne(ctx)
   if err!=nil{return done,err}
   if tx{done++;changed=true}
  }
  if done<m0V4BatchPackets{
   select{
   case seg,ok:=<-p.inbound:
    if !ok{return done,windowsclient.ErrN4NativeGuard}
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
  retried,err:=p.retryOne(time.Now())
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
   return fmt.Errorf("native V4 actual kernel first+reverse app not observed: %w",err)
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
   if !ok{return windowsclient.ErrN4NativeGuard}
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
    if !ok{select{case p.failure<-windowsclient.ErrN4NativeGuard:default:};return}
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
 return ctx.Err()
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
 TxPackets uint64 `json:"tx_records"`
 RxFirstDelivered uint64 `json:"rx_first_delivered_ipv4"`
 RetxRecords uint64 `json:"frozen_ciphertext_retransmits"`
 DuplicateCarrier uint64 `json:"duplicate_tcp_carriers"`
 RejectedAuth uint64 `json:"rejected_or_invalid_carriers"`
 ExplicitOversize uint64 `json:"oversize_rejects"`
 PendingRecords int `json:"unacked_carrier_records"`
 OldestPendingMS int64 `json:"oldest_unacked_carrier_ms"`
 MaxInterdeliveryMS int64 `json:"max_observed_interdelivery_ms"`
}
func(p *m0NativeV4Peer) Stats()m0NativeV4PacketStats{
 if p==nil{return m0NativeV4PacketStats{}}
 p.mu.Lock()
 defer p.mu.Unlock()
 now:=time.Now()
 var age int64
 if !p.oldestUnackedAt.IsZero(){age=now.Sub(p.oldestUnackedAt).Milliseconds()}
 return m0NativeV4PacketStats{
  Mode:p.mode,TxPackets:p.sent,RxFirstDelivered:p.opened,
  RetxRecords:p.retries,DuplicateCarrier:p.duplicates,RejectedAuth:p.rejected,
  ExplicitOversize:p.oversize,PendingRecords:p.pendingCount,
  OldestPendingMS:age,MaxInterdeliveryMS:p.maxRXInterdeliveryMs,
 }
}
