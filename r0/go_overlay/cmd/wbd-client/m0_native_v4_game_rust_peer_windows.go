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
 xdp *faketcp.XdpEndpoint
 cfgs []faketcp.NpcapConfig
 xdpMoved bool
 flows []faketcp.ClientFlow
 inbound <-chan m0GameInbound
 handoff chan struct{}
 stopColdReaders func()
 readers *sync.WaitGroup
 errorSource <-chan error
 loan *windowsclient.N4RustWintunLoan
 identity windowsclient.N4UnifiedIdentity
 maxIPv4 int
 pathMTU uint32
 disableOuterRepair bool
 plan029Cold *realityfront.V4WindowsColdSplitConfig // synchronous cold only; no hot Go callback
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
  p.live||p.moved||(len(p.flows)!=2&&len(p.flows)!=4)||
  p.xdp==nil||p.handoff==nil||p.stopColdReaders==nil||p.readers==nil{
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
 fmt.Println("M0_GAME_COLD_STAGE BIND_RING_ENTER")
 created:=windowsownerlease.CreatedWintun{TUN:p.tun}
 deviceID,err:=created.Identity(ctx,id.Installation,id.Generation)
 if err!=nil{return err}
 if err=p.group.BindAndJoinOriginalWintun(ctx,created,deviceID);err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE WINTUN_RUST_BOUND")
 max,err:=p.group.EffectiveGamePayloadMTU()
 if err!=nil||max<20{return windowsclient.ErrN4NativeGuard}
 boundaries,err:=p.group.OriginalGameTCPBoundaries()
 if err!=nil||len(boundaries)!=len(p.flows){return windowsclient.ErrN4NativeGuard}
 cfgs:=p.cfgs
 // Stop ALL post-TLS Go NPF readers and join them before moving ANY native
 // pcap_t. Their already-read bounded ciphertext is offered to Rust M3
 // for normal authenticated opening and never written into Wintun by Go.
 fmt.Println("M0_GAME_COLD_STAGE NPF_READER_JOIN_ENTER")
 p.stopColdReaders();p.moved=true
 p.readers.Wait()
 fmt.Println("M0_GAME_COLD_STAGE NPF_READER_JOIN_DONE")
 // Readers have joined, so the next native live pcap_next_ex MUST NOT
 // inherit an unconsumed pcap_breakloop (-2) from the old Go handoff.
 select{case e:=<-p.errorSource:return fmt.Errorf("original Game capture handoff: %w",e)
 default:}
 handles,e:=p.xdp.TakeNative(cfgs[0].Generation);if e!=nil{return e}
 p.xdpMoved=true
 fmt.Println("M0_GAME_COLD_STAGE NPF_CAPTURE_MOVED")
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
   RXCapture:handles[0],TXCapture:handles[1],
   WintunSession:native.Session,WintunReadEvent:native.ReadEvent,
   Wintun:realityfront.V4WindowsWintunNativeFnsV1{
    Receive:native.Fns.Receive,Release:native.Fns.Release,
    Allocate:native.Fns.Allocate,Send:native.Fns.Send,
   },
  },
 }
 // Per-lane original-Go TCP boundaries stay separate, never overwritten
 // by group ACK; each true copied game record advances only its NPF lane.
 for i:=1;i<len(p.flows);i++{
  v:=&cfg.Extra[i-1]
  v.InitialTXSeq=boundaries[i][0];v.InitialRXSeq=boundaries[i][1]
  v.LocalPort=p.flows[i].LocalPort;v.PeerPort=p.flows[i].PeerPort
  v.RXCapture=handles[0];v.TXCapture=handles[1]
 }
 if p.disableOuterRepair{cfg.DisableOuterRepair=1}
 fmt.Println("M0_GAME_COLD_STAGE RUST_GAME_START_ENTER")
 if p.plan029Cold!=nil{
  if err=p.group.StartNativeGameIOWithColdSplit(ctx,cfg,*p.plan029Cold);err!=nil{return err}
 }else if err=p.group.StartNativeGameIO(ctx,cfg);err!=nil{return err}
 p.live=true;p.identity=id;p.maxIPv4=max
 enabled,readErr:=p.group.NativeGameOuterRepairEffective(ctx)
 if readErr!=nil||((enabled==0)!=p.disableOuterRepair){
  return fmt.Errorf("native original Game outer-repair effective mismatch: %w",errors.Join(readErr,windowsclient.ErrN4NativeGuard))
 }
 fmt.Printf("WBD_WINDOWS_GAME_OUTER_REPAIR_EFFECTIVE enabled=%d source=rust_game_outer\n",enabled)
 fmt.Println("M0_GAME_COLD_STAGE RUST_GAME_START_DONE")
 for{
  select{
  case rec:=<-p.inbound:
   if rec.lane<0||rec.lane>=len(p.flows){return windowsclient.ErrN4NativeGuard}
   // A late pure cold TCP control is not an authenticated native failure.
   if len(rec.segment.Payload)==0||rec.segment.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{continue}
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
 // H2223 Game2/4 parity: this is a local authenticated activation
 // verdict, not a synthetic minimum-traffic generator. Normal already
 // uses the identical worker verdict. The group and native capture/Wintun
 // loans were bound in BindNativeRing; the product controller performs
 // real OS/WAL Apply and independent LiveReceipt/MTU readbacks before
 // publishing WBD_WINDOWS_CLIENT_READY. Empty idle traffic is valid.
 // Keep all counters truthful for independent application E2E checks.
 if err:=ctx.Err();err!=nil{return err}
 v,e:=p.group.NativeGameIOStats(ctx)
 if e!=nil{return e}
 p.last=v
 if e=m0WindowsRustNativeStartupVerdict(v);e!=nil{return e}
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_STARTUP_READY lanes=%d workers=%d tx_copied=%d rx_delivered=%d tx_after_rx=%d application_reverse_required=0\n",
  len(p.flows),v.Workers,v.TXCopied,v.RXDelivered,v.TXAfterRX)
 return nil
}
func(p *m0WinRustGamePeer) DrainPeerAndKernelLoans(
 ctx context.Context,first *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity,
)error{
 if p==nil||p.first!=first||p.tun!=tun{return windowsclient.ErrN4NativeGuard}
 if p.live{
  if err:=p.group.JoinNativeGameIO(ctx);err!=nil{
   fmt.Printf("M0_PLAN027_GAME_STOP_RESULT stage=native_worker_join result=FAIL error=%v\n",err)
   return err
  }
  p.live=false
  fmt.Println("M0_PLAN027_GAME_STOP_RESULT stage=native_worker_join result=PASS")
 }
 var err error
 if p.loan!=nil{err=errors.Join(err,p.loan.ReleaseAfterRustJoin());p.loan=nil}
 if p.xdpMoved{err=errors.Join(err,p.xdp.CloseAfterRustJoin());p.xdpMoved=false}
 return err
}
func(p *m0WinRustGamePeer) HealthError(ctx context.Context)error{
 if p==nil||!p.live{return windowsclient.ErrN4NativeGuard}
 s,e:=p.group.NativeGameIOStats(ctx)
 if e!=nil{return e}
 p.last=s
 if s.WorkerError!=0{return m0WindowsRustNativeWorkerError(s.WorkerError)}
 mtu,e:=p.group.RefreshGamePayloadMTU(ctx)
 if e!=nil{return e}
 if mtu!=p.maxIPv4{return fmt.Errorf("Game Rust native effective MTU changed from %d to %d: require new authenticated native attach",p.maxIPv4,mtu)}
 enabled,readErr:=p.group.NativeGameOuterRepairEffective(ctx)
 if readErr!=nil||((enabled==0)!=p.disableOuterRepair){
  return fmt.Errorf("Game original outer repair mode drift: %w",errors.Join(readErr,windowsclient.ErrN4NativeGuard))
 }
 return nil
}
func(p *m0WinRustGamePeer) Stats()string{
 s:=map[string]any{
  "mode":fmt.Sprintf("game%d",len(p.flows)),
  "native_rust_workers":2,
  "tx_records":p.last.TXCopied,"rx_first_delivered_ipv4":p.last.RXDelivered,
  "tx_after_reverse":p.last.TXAfterRX,"rejected_auth":p.last.Rejected,
  "effective_payload_mtu":p.maxIPv4,
  "rust_worker_error":p.last.WorkerError,
 }
 b,_:=json.Marshal(s);return string(b)
}
func(p *m0WinRustGamePeer) Errors()<-chan error{return p.errors}
