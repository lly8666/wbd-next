//go:build windows && wbd_v4_embedded_go
package main

// Public original-Go credential TLS verified Rust M3 packet pump.
// ONLY the exclusive pinned N4OriginalKernelPacketLease may supply real
// Windows Wintun ingress/egress. No canned packet or mock owner.
import(
 "context"
 "errors"
 "fmt"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)

type m0NativeV4Peer struct {
 mu sync.Mutex
 owner *realityfront.V4WindowsAuthenticatedClientOwner
 endpoint *faketcp.NpcapEndpoint
 flow faketcp.ClientFlow
 inbound <-chan faketcp.Segment
 ring *windowsclient.N4OriginalKernelPacketLease
 identity windowsclient.N4UnifiedIdentity
 sendNext,recvNext uint32
 sent,opened,sentAfterOpen uint64
 running,stopping bool
 stop,done chan struct{}
 failure chan error
}
func newM0NativeV4Peer(
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 endpoint *faketcp.NpcapEndpoint,flow faketcp.ClientFlow,
 inbound <-chan faketcp.Segment,
)(*m0NativeV4Peer,error){
 if owner==nil||endpoint==nil||inbound==nil{return nil,windowsclient.ErrN4NativeGuard}
 if err:=flow.Validate();err!=nil{return nil,err}
 return &m0NativeV4Peer{owner:owner,endpoint:endpoint,flow:flow,
  inbound:inbound,stop:make(chan struct{}),done:make(chan struct{}),
  failure:make(chan error,1)},nil
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
 if _,err=ring.Counts();err!=nil{return err}
 p.mu.Lock();defer p.mu.Unlock()
 if p.ring!=nil||p.stopping||send==0||recv==0{
  return windowsclient.ErrN4NativeGuard
 }
 p.ring=ring;p.identity=id;p.sendNext=send;p.recvNext=recv
 return nil
}
func(p *m0NativeV4Peer) pulse(ctx context.Context)error{
 if err:=ctx.Err();err!=nil{return err}
 p.mu.Lock();defer p.mu.Unlock()
 if p.stopping||p.ring==nil{return windowsclient.ErrN4NativeGuard}
 // Nonblocking signed native Wintun ring polling: no indefinite goroutine
 // read that would prevent Stop from draining kernel loans.
 buf:=make([]byte,65535)
 n,e:=p.ring.ReceiveReadyIPv4(ctx,buf)
 if e!=nil && !errors.Is(e,windowsclient.ErrN4NativeNoPacket){return e}
 if e==nil{
  if n<20||n>512{return windowsclient.ErrN4NativeGuard}
  ciphertext,seq,_,sealErr:=p.owner.SealBoundOriginalNormalOff(ctx,buf[:n])
  if sealErr!=nil{return sealErr}
  _,sealErr=p.endpoint.WriteSegment(1,faketcp.Segment{
   SrcIP:p.flow.LocalIP,DstIP:p.flow.PeerIP,
   SrcPort:p.flow.LocalPort,DstPort:p.flow.PeerPort,
   Seq:seq,Ack:p.recvNext,Flags:faketcp.FlagACK|faketcp.FlagPSH,
   Window:65535,Payload:ciphertext,
  })
  if sealErr!=nil{return sealErr}
  p.sendNext=seq+uint32(len(ciphertext))
  p.sent++
  if p.opened>0{p.sentAfterOpen++}
 }
 select{
 case seg:=<-p.inbound:
  if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{return windowsclient.ErrN4NativeGuard}
  if len(seg.Payload)==0{return nil}
  if seg.Seq!=p.recvNext||len(seg.Payload)<51||len(seg.Payload)>543{
   return windowsclient.ErrN4NativeGuard
  }
  plain,openErr:=p.owner.OpenBoundOriginalNormalOff(ctx,seg.Seq,seg.Payload)
  if openErr!=nil{return openErr}
  copied,openErr:=p.ring.WriteAuthenticatedIPv4(ctx,plain)
  if openErr!=nil||copied!=len(plain){
   return errors.Join(windowsclient.ErrN4NativeGuard,openErr)
  }
  p.recvNext+=uint32(len(seg.Payload))
  p.opened++
  // ACK only after exact M3 authentication AND native Wintun send.
  _,openErr=p.endpoint.WriteSegment(1,faketcp.Segment{
   SrcIP:p.flow.LocalIP,DstIP:p.flow.PeerIP,
   SrcPort:p.flow.LocalPort,DstPort:p.flow.PeerPort,
   Seq:p.sendNext,Ack:p.recvNext,Flags:faketcp.FlagACK,Window:65535,
  })
  return openErr
 default:return nil
 }
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
 // Only native kernel-originated app data, then real Rust-M3-authenticated
 // peer response, then OS app reply in that order will prove first/reverse.
 timeout,cancel:=context.WithTimeout(ctx,20*time.Second)
 defer cancel()
 tick:=time.NewTicker(4*time.Millisecond);defer tick.Stop()
 for{
  if err:=timeout.Err();err!=nil{return fmt.Errorf("native V4 peer/app first-and-reverse not observed: %w",err)}
  if err:=p.pulse(timeout);err!=nil{return err}
  p.mu.Lock();ok:=p.sent>=2&&p.opened>=1&&p.sentAfterOpen>=1;p.mu.Unlock()
  if ok{break}
  select{case <-timeout.Done():return timeout.Err();case <-tick.C:}
 }
 p.mu.Lock();p.running=true;p.mu.Unlock()
 go func(){
  defer close(p.done)
  ticker:=time.NewTicker(4*time.Millisecond);defer ticker.Stop()
  for{
   select{
   case <-p.stop:return
   case <-ticker.C:
    work,c:=context.WithTimeout(context.Background(),2*time.Second)
    err:=p.pulse(work);c()
    if err!=nil{select{case p.failure<-err:default:};return}
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
 if !p.stopping{p.stopping=true;close(p.stop)}
 p.mu.Unlock()
 if running{
  select{case <-p.done:case <-ctx.Done():return ctx.Err()}
 }
 return ctx.Err()
}
func(p *m0NativeV4Peer) Errors()<-chan error{
 if p==nil{return nil}
 return p.failure
}
