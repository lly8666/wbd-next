//go:build windows && wbd_v4_embedded_go
package main

// PLAN026: Normal/off product peer. Original Go stays in TLS and OS setup;
// two Rust workers own every steady Wintun/NPF read, seal, open and send.
import (
 "context"
 "errors"
 "fmt"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
type m0WinRustNativePeer struct{
 owner *realityfront.V4WindowsAuthenticatedClientOwner
 endpoint *faketcp.NpcapEndpoint
 cfg faketcp.NpcapConfig
 flow faketcp.ClientFlow
 early <-chan faketcp.Segment
 handoff chan struct{}
 readers *sync.WaitGroup
 wintun *windowsclient.N4RustWintunLoan
 rx,tx *faketcp.NpcapNativeCaptureLease
 active bool
 last realityfront.V4WindowsNativeWorkerStatsV1
 effective realityfront.V4WindowsM2Effective
 fail chan error
}
func newM0WinRustNativePeer(owner *realityfront.V4WindowsAuthenticatedClientOwner,
 endpoint *faketcp.NpcapEndpoint,cfg faketcp.NpcapConfig,flow faketcp.ClientFlow,
 early <-chan faketcp.Segment,handoff chan struct{},readers *sync.WaitGroup,
)*m0WinRustNativePeer{
 return &m0WinRustNativePeer{owner:owner,endpoint:endpoint,cfg:cfg,
  flow:flow,early:early,handoff:handoff,readers:readers,fail:make(chan error,1)}
}
func(p *m0WinRustNativePeer) BindNativeRing(ctx context.Context,
 ring *windowsclient.N4OriginalKernelPacketLease,id windowsclient.N4UnifiedIdentity)(err error){
 if p.active{return windowsclient.ErrN4NativeGuard}
 // On any partial attach failure, finish Rust (if started) before releasing
 // the exact pcap/Wintun ownership. This is a cold failure path, not a
 // defensive per-packet abstraction or a legacy data-plane fallback.
 defer func(){
  if err==nil{return}
  stopped,cancel:=context.WithTimeout(context.Background(),15*time.Second)
  defer cancel()
  err=errors.Join(err,p.DrainPeerAndKernelLoans(stopped,p.owner,nil,id))
 }()
 if err=p.owner.ArmBoundOriginalM2(ctx);err!=nil{return err}
 sendSeq,recvSeq,err:=p.owner.OriginalVerifiedTCPBoundaries()
 if err!=nil{return err}
 maxIPv4,err:=p.owner.BoundOriginalIPv4Budget(ctx)
 if err!=nil||maxIPv4<20{return windowsclient.ErrN4NativeGuard}
 p.effective,err=p.owner.ReadBoundOriginalM2Effective(ctx)
 if err!=nil||p.effective.BusinessIPv4MTU!=uint32(maxIPv4){return windowsclient.ErrN4NativeGuard}
 // Reader sees the expected transfer close and exits without fatal error.
 close(p.handoff)
 p.rx,err=p.endpoint.TakeNativeCapture(p.cfg.Generation);if err!=nil{return err}
 p.readers.Wait()
 sender,err:=faketcp.OpenNpcapEndpoint(p.cfg);if err!=nil{return err}
 if err=sender.DisableReceiveForNativeTX();err!=nil{_ = sender.Close();return err}
 p.tx,err=sender.TakeNativeCapture(p.cfg.Generation)
 if err!=nil{_ = sender.Close();return err}
 rx,err:=p.rx.Native();if err!=nil{return err}
 tx,err:=p.tx.Native();if err!=nil{return err}
 p.wintun,err=ring.BorrowRustNativeRing(ctx);if err!=nil{return err}
 native,err:=p.wintun.Native();if err!=nil{return err}
 if native.WintunLUID!=id.WintunLUID||native.WintunIndex!=id.WintunIndex{
  return windowsclient.ErrN4NativeGuard
 }
 cfg:=realityfront.V4WindowsNativeIOV1{
  PathMTU:p.effective.PathMTU,
  InitialTXSeq:sendSeq,InitialRXSeq:recvSeq,
  LocalIP:p.flow.LocalIP,PeerIP:p.flow.PeerIP,
  LocalPort:p.flow.LocalPort,PeerPort:p.flow.PeerPort,
  SourceMAC:p.cfg.SourceMAC,NextHopMAC:p.cfg.NextHopMAC,
  RXCapture:rx.Handle,TXCapture:tx.Handle,
  WintunSession:native.Session,WintunReadEvent:native.ReadEvent,
  Npcap:realityfront.V4WindowsNpcapNativeFnsV1{
   NextEx:rx.Fns.NextEx,SendPacket:tx.Fns.SendPacket,
   GetEvent:rx.Fns.GetEvent,QueueAlloc:tx.Fns.QueueAlloc,
   QueueTransmit:tx.Fns.QueueTransmit,QueueDestroy:tx.Fns.QueueDestroy,
  },
  Wintun:realityfront.V4WindowsWintunNativeFnsV1{
   Receive:native.Fns.Receive,Release:native.Fns.Release,
   Allocate:native.Fns.Allocate,Send:native.Fns.Send,
  },
 }
 if err=p.owner.StartNativeIO(ctx,cfg);err!=nil{return err}
 p.active=true
 // At most the original Go 64-slot early buffer; Rust unique M3 opener
 // authenticates those bytes inside its RX worker before kernel delivery.
 for{
  select{
  case seg,ok:=<-p.early:
   if !ok{return nil}
   if len(seg.Payload)<51{continue}
   if err=p.owner.OfferNativeEarly(ctx,seg.Seq,seg.Payload);err!=nil{return err}
  default:return nil
  }
 }
}
func(p *m0WinRustNativePeer) VerifyPeerFirstAndReverse(ctx context.Context,
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity)error{
 if p.owner!=owner||!p.active{return windowsclient.ErrN4NativeGuard}
 timeout,cancel:=context.WithTimeout(ctx,20*time.Second);defer cancel()
 tick:=time.NewTicker(25*time.Millisecond);defer tick.Stop()
 for{
  state,err:=owner.NativeIOStats(timeout);if err!=nil{return err}
  p.last=state
  if state.WorkerError!=0{return fmt.Errorf("native Rust owner rc=%d",state.WorkerError)}
  if state.TXCopied>=2&&state.RXDelivered>=1&&state.TXAfterRX>=1{return nil}
  select{
  case <-timeout.Done():return fmt.Errorf("real Rust native first+reverse: %w %+v",timeout.Err(),state)
  case <-tick.C:
  }
 }
}
func(p *m0WinRustNativePeer) DrainPeerAndKernelLoans(ctx context.Context,
 owner *realityfront.V4WindowsAuthenticatedClientOwner,
 tun *windowsclient.TUN,id windowsclient.N4UnifiedIdentity)error{
 if p.owner!=owner{return windowsclient.ErrN4NativeGuard}
 if p.active{
  // A failed join is not a stop receipt. Never free native handles that a
  // Rust worker might still own.
  if err:=p.owner.JoinNativeIO(ctx);err!=nil{return err}
  p.active=false
 }
 var err error
 if p.wintun!=nil{err=errors.Join(err,p.wintun.ReleaseAfterRustJoin());p.wintun=nil}
 if p.rx!=nil{err=errors.Join(err,p.rx.CloseAfterRustJoin());p.rx=nil}
 if p.tx!=nil{err=errors.Join(err,p.tx.CloseAfterRustJoin());p.tx=nil}
 return err
}
func(p *m0WinRustNativePeer) RefreshEffective(ctx context.Context)error{
 s,err:=p.owner.NativeIOStats(ctx);if err!=nil{return err}
 if s.WorkerError!=0{return fmt.Errorf("Rust native worker rc=%d",s.WorkerError)}
 p.last=s
 p.effective,err=p.owner.ReadBoundOriginalM2Effective(ctx)
 return err
}
func(p *m0WinRustNativePeer) Stats()m0NativeV4PacketStats{
 return m0NativeV4PacketStats{Mode:m0WinModeNormal,TxPackets:p.last.TXCopied,
  RxFirstDelivered:p.last.RXDelivered,RejectedAuth:p.last.Rejected,
  EffectiveM2:p.effective}
}
func(p *m0WinRustNativePeer) Errors()<-chan error{return p.fail}
func(p *m0WinRustNativePeer) RequestAutoStartProfile(
 profile realityfront.FecV2Profile,
)(realityfront.FecV2State,error){
 return realityfront.FecV2State{},windowsclient.ErrN4NativeGuard
}
