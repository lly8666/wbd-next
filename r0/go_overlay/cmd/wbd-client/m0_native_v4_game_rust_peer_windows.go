//go:build windows && wbd_v4_embedded_go
package main

// Original Game2/4 TLS authentication remains Go cold-control only;
// all steady lane Npcap + single Wintun GameAdapter traffic moves to
// exactly two Rust workers. No packet pump, fallback or new FEC codec.
import(
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
)
type m0WinRustGamePeer struct{
 group *realityfront.V4WindowsAuthenticatedGameGroup
 first *realityfront.V4WindowsAuthenticatedClientOwner
 tun *windowsclient.TUN
 endpoints []*faketcp.NpcapEndpoint
 flows []faketcp.ClientFlow
 inbound <-chan m0GameInbound
 handoff chan struct{}
 readers *sync.WaitGroup
 errorSource <-chan error
 loan *windowsclient.N4RustWintunLoan
 captures []*faketcp.NpcapNativeCaptureLease
 senders []*faketcp.NpcapNativeCaptureLease
 identity windowsclient.N4UnifiedIdentity
 maxIPv4 int
 pathMTU uint32
 live bool
 moved bool
 last realityfront.V4WindowsNativeWorkerStatsV1
 errors chan error
}
func(p *m0WinRustGamePeer) BindNativeRing(ctx context.Context,
 ring *windowsclient.N4OriginalKernelPacketLease,
 id windowsclient.N4UnifiedIdentity,
)(err error){
 if p==nil||ring==nil||p.group==nil||p.first==nil||p.tun==nil||
  p.live||p.moved||(len(p.endpoints)!=2&&len(p.endpoints)!=4)||
  len(p.flows)!=len(p.endpoints)||p.handoff==nil||p.readers==nil{
  return windowsclient.ErrN4NativeGuard
 }
 // Any partial cold capture handoff must first Join Rust if Start succeeded,
 // then close the exact formerly-Go owned native kernel leases.
 defer func(){
  if err==nil{return}
  stop,cancel:=context.WithTimeout(context.Background(),15*time.Second)
  defer cancel()
  err=errors.Join(err,p.DrainPeerAndKernelLoans(stop,p.first,p.tun,id))
 }()
 created:=windowsownerlease.CreatedWintun{TUN:p.tun}
 deviceID,err:=created.Identity(ctx,id.Installation,id.Generation)
 if err!=nil{return err}
 if err=p.group.BindAndJoinOriginalWintun(ctx,created,deviceID);err!=nil{return err}
 max,err:=p.group.EffectiveGamePayloadMTU()
 if err!=nil||max<20{return windowsclient.ErrN4NativeGuard}
 boundaries,err:=p.group.OriginalGameTCPBoundaries()
 if err!=nil||len(boundaries)!=len(p.endpoints){return windowsclient.ErrN4NativeGuard}
 cfgs:=make([]faketcp.NpcapConfig,len(p.endpoints))
 for i,endpoint:=range p.endpoints{
  cfgs[i],err=endpoint.NativeCaptureConfig()
  if err!=nil{return err}
 }
 // Stop ALL post-TLS Go NPF readers and join them before moving ANY native
 // pcap_t. Their already-read bounded ciphertext is offered to Rust M3
 // for normal authenticated opening and never written into Wintun by Go.
 close(p.handoff);p.moved=true
 p.readers.Wait()
 select{case e:=<-p.errorSource:return fmt.Errorf("original Game capture handoff: %w",e)
 default:}
 nativeRX:=make([]faketcp.NpcapNativeCaptureV1,len(cfgs))
 nativeTX:=make([]faketcp.NpcapNativeCaptureV1,len(cfgs))
 for i,endpoint:=range p.endpoints{
  loan,e:=endpoint.TakeNativeCapture(cfgs[i].Generation)
  if e!=nil{return e}
  p.captures=append(p.captures,loan)
  nativeRX[i],err=loan.Native();if err!=nil{return err}
  tx,e:=faketcp.OpenNpcapEndpoint(cfgs[i])
  if e!=nil{return e}
  if e=tx.DisableReceiveForNativeTX();e!=nil{_ =tx.Close();return e}
  send,e:=tx.TakeNativeCapture(cfgs[i].Generation)
  if e!=nil{_ =tx.Close();return e}
  p.senders=append(p.senders,send)
  nativeTX[i],err=send.Native();if err!=nil{return err}
 }
 p.loan,err=ring.BorrowRustNativeRing(ctx)
 if err!=nil{return err}
 native,err:=p.loan.Native()
 if err!=nil||native.WintunLUID!=id.WintunLUID||
  native.WintunIndex!=id.WintunIndex{return windowsclient.ErrN4NativeGuard}
 first:=p.flows[0]
 cfg:=realityfront.V4WindowsGameNativeIOV3{
  First:realityfront.V4WindowsNativeIOV1{
   PathMTU:p.pathMTU,
   InitialTXSeq:boundaries[0][0],InitialRXSeq:boundaries[0][1],
   LocalIP:first.LocalIP,PeerIP:first.PeerIP,
   LocalPort:first.LocalPort,PeerPort:first.PeerPort,
   SourceMAC:cfgs[0].SourceMAC,NextHopMAC:cfgs[0].NextHopMAC,
   RXCapture:nativeRX[0].Handle,TXCapture:nativeTX[0].Handle,
   WintunSession:native.Session,WintunReadEvent:native.ReadEvent,
   Npcap:realityfront.V4WindowsNpcapNativeFnsV1{
    NextEx:nativeRX[0].Fns.NextEx,SendPacket:nativeTX[0].Fns.SendPacket,
    GetEvent:nativeRX[0].Fns.GetEvent,QueueAlloc:nativeTX[0].Fns.QueueAlloc,
    QueueTransmit:nativeTX[0].Fns.QueueTransmit,
    QueueDestroy:nativeTX[0].Fns.QueueDestroy,
   },
   Wintun:realityfront.V4WindowsWintunNativeFnsV1{
    Receive:native.Fns.Receive,Release:native.Fns.Release,
    Allocate:native.Fns.Allocate,Send:native.Fns.Send,
   },
  },
 }
 // Per-lane original-Go TCP boundaries stay separate, never overwritten
 // by group ACK; each true copied game record advances only its NPF lane.
 for i:=1;i<len(p.endpoints);i++{
  v:=&cfg.Extra[i-1]
  v.InitialTXSeq=boundaries[i][0];v.InitialRXSeq=boundaries[i][1]
  v.LocalPort=p.flows[i].LocalPort;v.PeerPort=p.flows[i].PeerPort
  v.RXCapture=nativeRX[i].Handle;v.TXCapture=nativeTX[i].Handle
  v.Npcap=realityfront.V4WindowsNpcapNativeFnsV1{
   NextEx:nativeRX[i].Fns.NextEx,SendPacket:nativeTX[i].Fns.SendPacket,
   GetEvent:nativeRX[i].Fns.GetEvent,QueueAlloc:nativeTX[i].Fns.QueueAlloc,
   QueueTransmit:nativeTX[i].Fns.QueueTransmit,
   QueueDestroy:nativeTX[i].Fns.QueueDestroy,
  }
 }
 if err=p.group.StartNativeGameIO(ctx,cfg);err!=nil{return err}
 p.live=true;p.identity=id;p.maxIPv4=max
 for{
  select{
  case rec:=<-p.inbound:
   if rec.lane<0||rec.lane>=len(p.endpoints){return windowsclient.ErrN4NativeGuard}
   if rec.segment.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{
    return fmt.Errorf("real Game peer FIN/RST lane%d",rec.lane+1)
   }
   if len(rec.segment.Payload)==0{continue}
   if err=p.group.OfferNativeGameEarly(ctx,uint32(rec.lane+1),
       rec.segment.Seq,rec.segment.Payload);err!=nil{return err}
  default:return nil
  }
 }
}
func(p *m0WinRustGamePeer) VerifyPeerFirstAndReverse(
 ctx context.Context,first *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.first!=first||p.tun!=tun||p.identity!=id||!p.live{
  return windowsclient.ErrN4NativeGuard
 }
 probe,cancel:=context.WithTimeout(ctx,25*time.Second);defer cancel()
 ticker:=time.NewTicker(25*time.Millisecond);defer ticker.Stop()
 for{
  v,e:=p.group.NativeGameIOStats(probe)
  if e!=nil{return e}
  p.last=v
  if v.WorkerError!=0{return fmt.Errorf("Game native Rust worker rc=%d",v.WorkerError)}
  if v.TXCopied>=uint64(2*len(p.endpoints))&&v.RXDelivered>=1&&
    v.TXAfterRX>=uint64(len(p.endpoints)){return nil}
  select{
  case <-probe.Done():return fmt.Errorf("real Game Rust first+reverse: %w stats=%+v",probe.Err(),v)
  case <-ticker.C:
  }
 }
}
func(p *m0WinRustGamePeer) DrainPeerAndKernelLoans(
 ctx context.Context,first *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.first!=first||p.tun!=tun{return windowsclient.ErrN4NativeGuard}
 if p.live{
  if err:=p.group.JoinNativeGameIO(ctx);err!=nil{return err}
  p.live=false
 }
 var err error
 if p.loan!=nil{err=errors.Join(err,p.loan.ReleaseAfterRustJoin());p.loan=nil}
 for _,l:=range p.captures{err=errors.Join(err,l.CloseAfterRustJoin())}
 for _,l:=range p.senders{err=errors.Join(err,l.CloseAfterRustJoin())}
 p.captures=nil;p.senders=nil
 return err
}
func(p *m0WinRustGamePeer) HealthError(ctx context.Context)error{
 if p==nil||!p.live{return windowsclient.ErrN4NativeGuard}
 s,e:=p.group.NativeGameIOStats(ctx)
 if e!=nil{return e}
 p.last=s
 if s.WorkerError!=0{return fmt.Errorf("Game native Rust worker rc=%d",s.WorkerError)}
 mtu,e:=p.group.RefreshGamePayloadMTU(ctx)
 if e!=nil{return e}
 if mtu!=p.maxIPv4{return fmt.Errorf("Game Rust native effective MTU changed from %d to %d: require new authenticated native attach",p.maxIPv4,mtu)}
 return nil
}
func(p *m0WinRustGamePeer) Stats()string{
 s:=map[string]any{
  "mode":fmt.Sprintf("game%d",len(p.endpoints)),
  "native_rust_workers":2,
  "tx_records":p.last.TXCopied,"rx_first_delivered_ipv4":p.last.RXDelivered,
  "tx_after_reverse":p.last.TXAfterRX,"rejected_auth":p.last.Rejected,
  "effective_payload_mtu":p.maxIPv4,
  "rust_worker_error":p.last.WorkerError,
 }
 b,_:=json.Marshal(s);return string(b)
}
func(p *m0WinRustGamePeer) Errors()<-chan error{return p.errors}
