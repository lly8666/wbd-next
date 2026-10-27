//go:build windows && wbd_v4_embedded_go
package main

// Actual original-Go Windows Game2/4 NPF↔signed Wintun loop. All
// logical IDs, FEC2 coding, parity deadlines, AEAD, PN and dedup come
// from the SAME Rust GameAdapter proven on Linux. No second Go FEC,
// loss estimator or Go retransmission controller is created here.
import (
 "context"
 "errors"
 "fmt"
 "encoding/json"
 "runtime"
 "sync"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
)
type m0GameInbound struct{lane int;segment faketcp.Segment}
type m0GameLane struct {
 endpoint *faketcp.NpcapEndpoint
 flow faketcp.ClientFlow
 tx,ack uint32
 rx *m0V4RxWindow
 failed bool
 sent uint64
}
type m0NativeV4GamePeer struct {
 group *realityfront.V4WindowsAuthenticatedGameGroup
 first *realityfront.V4WindowsAuthenticatedClientOwner
 tun *windowsclient.TUN
 fec bool
 lanes []m0GameLane
 inbound <-chan m0GameInbound
 ring *windowsclient.N4OriginalKernelPacketLease
 identity windowsclient.N4UnifiedIdentity
 scratch []byte
 maxIPv4 int
 stop,done chan struct{}
 cancel context.CancelFunc
 running,stopping bool
 errors chan error
 mu sync.Mutex
 sent,opened,after uint64
 laneFailed uint64
}
func(p *m0NativeV4GamePeer) BindNativeRing(
 ctx context.Context,ring *windowsclient.N4OriginalKernelPacketLease,
 id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||ring==nil||p.group==nil||p.tun==nil{return windowsclient.ErrN4NativeGuard}
 native:=windowsownerlease.CreatedWintun{TUN:p.tun}
 deviceID,err:=native.Identity(ctx,id.Installation,id.Generation)
 if err!=nil{return err}
 if err=p.group.BindAndJoinOriginalWintun(ctx,native,deviceID);err!=nil{return err}
 mtu,err:=p.group.EffectiveGamePayloadMTU()
 if err!=nil||mtu<20{return windowsclient.ErrN4NativeGuard}
 boundaries,err:=p.group.OriginalGameTCPBoundaries()
 if err!=nil||len(boundaries)!=len(p.lanes){return windowsclient.ErrN4NativeGuard}
 p.mu.Lock();defer p.mu.Unlock()
 if p.ring!=nil{return windowsclient.ErrN4NativeGuard}
 p.ring=ring;p.identity=id;p.maxIPv4=mtu;p.scratch=make([]byte,mtu)
 for i,v:=range boundaries{
  p.lanes[i].tx=v[0];p.lanes[i].ack=v[1]
  p.lanes[i].rx=newM0V4RxWindow(v[1])
 }
 return nil
}
func(p *m0NativeV4GamePeer) carrier(i int,seq,ack uint32,wire []byte)error{
 l:=&p.lanes[i]
 _,err:=l.endpoint.WriteSegment(1,faketcp.Segment{
  SrcIP:l.flow.LocalIP,DstIP:l.flow.PeerIP,
  SrcPort:l.flow.LocalPort,DstPort:l.flow.PeerPort,
  Seq:seq,Ack:ack,Flags:faketcp.FlagACK|faketcp.FlagPSH,
  Window:65535,Payload:wire,
 })
 return err
}
func(p *m0NativeV4GamePeer) acknowledge(i int)error{
 l:=&p.lanes[i]
 _,err:=l.endpoint.WriteSegment(1,faketcp.Segment{
  SrcIP:l.flow.LocalIP,DstIP:l.flow.PeerIP,
  SrcPort:l.flow.LocalPort,DstPort:l.flow.PeerPort,
  Seq:l.tx,Ack:l.ack,Flags:faketcp.FlagACK,Window:65535,
 })
 return err
}
// One lane's real NPF error or authenticated FIN/RST must not hold the
// healthy siblings hostage. Exact Rust staged tickets are always settled,
// including failed copies; no fabricated per-lane kernel credit.
func(p *m0NativeV4GamePeer) retireLane(i int,cause error)error{
 if p.lanes[i].failed{return nil}
 p.lanes[i].failed=true
 p.mu.Lock();p.laneFailed++;p.mu.Unlock()
 for j:=range p.lanes{if !p.lanes[j].failed{return nil}}
 return fmt.Errorf("%w: all original Game lanes unavailable after lane%d: %v",
  windowsclient.ErrN4NativeGuard,i+1,cause)
}
func(p *m0NativeV4GamePeer) send(ctx context.Context,rec realityfront.V4WindowsGameRecord)error{
 if rec.Lane==0||int(rec.Lane)>len(p.lanes){return windowsclient.ErrN4NativeGuard}
 i:=int(rec.Lane)-1;l:=&p.lanes[i]
 var sentErr error
 if !l.failed{sentErr=p.carrier(i,l.tx,l.ack,rec.Wire)}
 // Off and fixed FEC both settle exact Rust staged M4 tickets.
 // A previously dead lane reports NotSent, never another successful copy.
 if e:=p.group.ReportGameFecNpcapCopy(ctx,rec,!l.failed&&sentErr==nil);e!=nil{
  return errors.Join(sentErr,e)
 }
 if l.failed{return nil}
 if sentErr!=nil{return p.retireLane(i,sentErr)}
 l.tx+=uint32(len(rec.Wire));l.sent++
 p.mu.Lock();p.sent++;if p.opened>0{p.after++};p.mu.Unlock()
 return nil
}
func(p *m0NativeV4GamePeer) transmit(ctx context.Context)(bool,error){
 n,err:=p.ring.ReceiveReadyIPv4(ctx,p.scratch)
 if errors.Is(err,windowsclient.ErrN4NativeNoPacket){return false,nil}
 if err!=nil{return false,err}
 if n<20||n>p.maxIPv4{return false,windowsclient.ErrN4NativeGuard}
 records,err:=p.group.StageGameRecords(ctx,p.scratch[:n])
 if err!=nil{return false,err}
 if len(records)>len(p.lanes){return false,windowsclient.ErrN4NativeGuard}
 // Zero/partial immediate records are legitimate scheduled Game4
 // replicas; the same Rust owner emits remaining due copies on poll.
 for _,rec:=range records{
  if err=p.send(ctx,rec);err!=nil{return false,err}
 }
 return true,nil
}
func(p *m0NativeV4GamePeer) receive(ctx context.Context,in m0GameInbound)error{
 if in.lane<0||in.lane>=len(p.lanes){return windowsclient.ErrN4NativeGuard}
 l:=&p.lanes[in.lane];seg:=in.segment
 if seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
  return p.retireLane(in.lane,fmt.Errorf("real Game%d lane%d FIN/RST",
   len(p.lanes),in.lane+1))
 }
 if l.failed||len(seg.Payload)==0{return nil}
 ok,e:=l.rx.Check(seg.Seq,len(seg.Payload))
 independent:=e!=nil&&l.rx.IndependentAEADCandidate(seg.Seq,len(seg.Payload))
 if !ok&&!independent{return nil}
 var frames [][]byte
 var pending bool
 if p.fec{
  frames,pending,e=p.group.OpenGameFecBatch(ctx,uint32(in.lane+1),seg.Payload)
 }else{
  var ipv4 []byte
  ipv4,e=p.group.OpenGameRecord(ctx,uint32(in.lane+1),seg.Payload)
  if len(ipv4)>0{frames=[][]byte{ipv4}}
 }
 if e!=nil{return nil} // Rust AEAD/PN/auth rejection, never OS copy
 copiedPrefix:=uint32(0)
 for _,ipv4:=range frames{
  n,e:=p.ring.WriteAuthenticatedIPv4(ctx,ipv4)
  if e!=nil||n!=len(ipv4){break}
  copiedPrefix++
 }
 if pending{
  // One authenticated symbol can emit multiple recovered IPv4 packets.
  // Report only the TRUE successful Wintun prefix, not a false all/none
  // claim after earlier writes already reached the native kernel.
  if e:=p.group.CompleteGameFecBatch(ctx,uint32(in.lane+1),copiedPrefix);e!=nil{return e}
 }
 p.mu.Lock();p.opened+=uint64(copiedPrefix);p.mu.Unlock()
 if copiedPrefix!=uint32(len(frames)){return windowsclient.ErrN4NativeGuard}
 if independent{
  l.ack=l.rx.Ack()
 }else{
  ack,e:=l.rx.Copied(seg.Seq,len(seg.Payload))
  if e!=nil{return e}
  l.ack=ack
 }
 l.rx.NoteAuthenticated(seg.Seq,len(seg.Payload))
 if err:=p.acknowledge(in.lane);err!=nil{
  return p.retireLane(in.lane,err)
 }
 return nil
}
func(p *m0NativeV4GamePeer) pulse(ctx context.Context)(int,error){
 if p==nil||p.ring==nil{return 0,windowsclient.ErrN4NativeGuard}
 done:=0;start:=time.Now()
 for done<m0V4BatchPackets&&time.Since(start)<m0V4BatchCPU{
  if err:=ctx.Err();err!=nil{return done,err}
  select{
  case in,ok:=<-p.inbound:
   if !ok{return done,windowsclient.ErrN4NativeGuard}
   if err:=p.receive(ctx,in);err!=nil{return done,err}
   done++
  default:
  }
  sent,err:=p.transmit(ctx)
  if err!=nil{return done,err}
  if sent{done++;continue}
  break
 }
 // Rust Game4 may delay its remaining copies even in off mode.
 // The one existing due ABI also polls shared GameFecTx parity, with
 // original M4 kernel I/O completion for every per-lane staged ticket.
 due,err:=p.group.DueGameFecParity(ctx,16)
 if err!=nil{return done,err}
 for _,rec:=range due{
  if err=p.send(ctx,rec);err!=nil{return done,err}
  done++
 }
 return done,nil
}
func(p *m0NativeV4GamePeer) VerifyPeerFirstAndReverse(
 ctx context.Context,first *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.first!=first||p.tun!=tun||p.identity!=id||p.ring==nil{
  return windowsclient.ErrN4NativeGuard
 }
 probe,cancel:=context.WithTimeout(ctx,25*time.Second)
 defer cancel()
 tick:=time.NewTicker(m0V4IdlePoll);defer tick.Stop()
 for{
  done,err:=p.pulse(probe)
  if err!=nil{return err}
  p.mu.Lock()
  ready:=p.sent>=uint64(2*len(p.lanes))&&p.opened>=1&&
   p.after>=uint64(len(p.lanes))
  for i:=range p.lanes{
   ready=ready&&!p.lanes[i].failed&&p.lanes[i].sent>=2
  }
  p.mu.Unlock()
  if ready{break}
  if done>0{runtime.Gosched();continue}
  select{
  case <-probe.Done():return fmt.Errorf("Game%d native first/reverse not delivered: %w",len(p.lanes),probe.Err())
  case in,ok:=<-p.inbound:
   if !ok{return windowsclient.ErrN4NativeGuard}
   if err=p.receive(probe,in);err!=nil{return err}
  case <-tick.C:
  }
 }
 background,stop:=context.WithCancel(context.Background())
 p.mu.Lock();p.running=true;p.cancel=stop;p.mu.Unlock()
 go func(){
  defer close(p.done);defer stop()
  timer:=time.NewTicker(m0V4IdlePoll);defer timer.Stop()
  for{
   done,err:=p.pulse(background)
   if err!=nil{
    if background.Err()==nil{select{case p.errors<-err:default:}}
    return
   }
   if done>0{runtime.Gosched();continue}
   select{
   case <-background.Done():return
   case <-p.stop:return
   case in,ok:=<-p.inbound:
    if !ok{select{case p.errors<-windowsclient.ErrN4NativeGuard:default:};return}
    if e:=p.receive(background,in);e!=nil{select{case p.errors<-e:default:};return}
   case <-timer.C:
   }
  }
 }()
 return nil
}
func(p *m0NativeV4GamePeer) DrainPeerAndKernelLoans(
 ctx context.Context,first *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.first!=first||p.tun!=tun||p.identity!=id{return windowsclient.ErrN4NativeGuard}
 p.mu.Lock()
 running:=p.running
 if !p.stopping{
  p.stopping=true;close(p.stop)
  if p.cancel!=nil{p.cancel()}
 }
 p.mu.Unlock()
 if running{
  select{case <-p.done:case <-ctx.Done():return ctx.Err()}
 }
 return ctx.Err()
}
func(p *m0NativeV4GamePeer) Errors()<-chan error{return p.errors}
func(p *m0NativeV4GamePeer) Stats()string{
 p.mu.Lock();defer p.mu.Unlock()
 s,_:=json.Marshal(map[string]any{
  "mode":fmt.Sprintf("game%d",len(p.lanes)),
  "tx_records":p.sent,"rx_first_delivered_ipv4":p.opened,
  "failed_lanes":p.laneFailed,"effective_payload_mtu":p.maxIPv4,
 })
 return string(s)
}
