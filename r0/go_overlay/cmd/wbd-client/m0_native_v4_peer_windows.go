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
 if owner==nil||endpoint==nil||inbound==nil{return nil,windowsclient.ErrN4NativeGuard}
 if err:=flow.Validate();err!=nil{return nil,err}
 return &m0NativeV4Peer{
  owner:owner,endpoint:endpoint,flow:flow,inbound:inbound,
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
 ciphertext,seq,_,err:=p.owner.SealBoundOriginalNormalOff(ctx,p.scratch[:n])
 if err!=nil{return false,err} // identity/cipher/replay failure: stop this owner
 if seq!=p.sendNext{return false,windowsclient.ErrN4NativeGuard}
 if err=p.sendCarrier(seq,p.recvNext,ciphertext);err!=nil{return false,err}
 p.pending=append(p.pending,m0NativeV4Outbound{
  seq:seq,wire:append([]byte(nil),ciphertext...),
  sentAt:time.Now(),lastSent:time.Now(),
 })
 p.sendNext=seq+uint32(len(ciphertext))
 p.mu.Lock();p.sent++;if p.opened>0{p.sentAfterOpen++};p.mu.Unlock()
 return true,nil
}
func(p *m0NativeV4Peer) receiveOne(ctx context.Context,seg faketcp.Segment)error{
 if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
  return windowsclient.ErrN4NativeGuard
 }
 p.observePeerACK(seg.Ack)
 if len(seg.Payload)==0{return nil}
 if len(seg.Payload)<51||len(seg.Payload)>p.maxIPv4+31{
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
 plain,err:=p.owner.OpenBoundOriginalNormalOff(ctx,seg.Seq,seg.Payload)
 if err!=nil{
  // Rust M3 owns real AEAD/PN replay rejection, never expose failed
  // plaintext. Drop this invalid record but keep healthy lanes alive.
  p.mu.Lock();p.rejected++;p.mu.Unlock()
  return nil
 }
 if len(plain)<20||len(plain)>p.maxIPv4{return windowsclient.ErrN4NativeGuard}
 copied,err:=p.ring.WriteAuthenticatedIPv4(ctx,plain)
 if err!=nil||copied!=len(plain){
  return errors.Join(windowsclient.ErrN4NativeGuard,err)
 }
 ack,err:=p.rx.Copied(seg.Seq,len(seg.Payload))
 if err!=nil{return err}
 p.recvNext=ack
 p.mu.Lock();p.opened++;p.mu.Unlock()
 // Critical: ACK is the *highest contiguous* Rust-authenticated and
 // Wintun-copied TCP interval. Delivered future packet cannot ACK a gap.
 return p.sendACK()
}
func(p *m0NativeV4Peer) retryOne(now time.Time)(bool,error){
 if len(p.pending)==0||p.stopped(){return false,nil}
 for i:=range p.pending{
  pending:=&p.pending[i]
  if now.Sub(pending.lastSent)<m0V4RetxAfter||pending.retries>=8{continue}
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
 if done==0{
  retried,err:=p.retryOne(time.Now())
  if err!=nil{return 0,err}
  if retried{return 1,nil}
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
 p.mu.Unlock()
 return ctx.Err()
}
func(p *m0NativeV4Peer) Errors()<-chan error{
 if p==nil{return nil}
 return p.failure
}
