//go:build windows && wbd_v4_embedded_go
package main

// Genuine per-lane original-Go FakeTCP credential/TLS bootstrap, then
// the proven Linux shared Rust GameAdapter and one native OS/WAL owner.
import(
 "context"
 "crypto/rand"
 "encoding/binary"
 "errors"
 "fmt"
 "path/filepath"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
)
// A user/parent Stop (or old generation canceled for a path change) can
// race the same second as the 1Hz M4 MTU/Health ticker. A canceled OS
// LiveReceipt returns (0,context.Canceled), not a real native MTU drift.
// Keep the original 1Hz fail-closed check when the owner remains live.
func m0WindowsGameRuntimeMTUDrift(ctx context.Context,expected,actual uint32,readErr error)error{
 if ctx.Err()!=nil{return nil}
 if readErr==nil&&actual==expected{return nil}
 return fmt.Errorf("Game original M4 OS MTU drift/invalid WAL expected=%d actual=%d: %w",
  expected,actual,errors.Join(windowsclient.ErrN4NativeGuard,readErr))
}
// Already-detached Game M3 ciphertext is an optional finite cold backlog.
// Its overflow must NEVER kill a Go reader still needed by other genuine
// per-lane TLS handshakes. Drop just this early record and keep servicing
// the original NPF socket until Rust owns it; no hot Go pump is introduced.
func offerGameColdInbound(inbound chan<- m0GameInbound,record m0GameInbound)bool{
 select{
 case inbound<-record:return true
 default:return false
 }
}

// All Game lanes retain one authenticated server listener port.
// Source ports distinguish exact original FakeTCP 5-tuples; incrementing the
// destination (443+i) breaks the single-port server before any real TLS.
func m0WindowsGameOriginalClientFlow(
 o m0NativeV4Options,localIP [4]byte,lane int,
)(faketcp.ClientFlow,error){
 src:=int(o.SourcePort)+lane
 if lane<0||lane>=4||o.ServerPort==0||src<=0||src>65535||!o.ServerIP.Is4(){
  return faketcp.ClientFlow{},windowsclient.ErrN4NativeGuard
 }
 return faketcp.ClientFlow{
  LocalIP:localIP,PeerIP:o.ServerIP.As4(),
  LocalPort:uint16(src),PeerPort:o.ServerPort,
 },nil
}

func runM0NativeV4WindowsGame(
 ctx context.Context,o m0NativeV4Options,localIP [4]byte,physical uint32,
 open func(uint16,uint16)(*faketcp.NpcapEndpoint,error),
 makePlan func()(windowsclient.NetworkPlan,error),
 pathChanged <-chan struct{},
)error{
 count:=2;if o.Mode==m0WinModeGame4{count=4}
 assocs:=make([]*faketcp.ClientAssociation,0,count)
 endpoints:=make([]*faketcp.NpcapEndpoint,0,count)
 flows:=make([]faketcp.ClientFlow,0,count)
 // Native M3 authenticates the finite real pre-handoff NPF backlog.
 inbound:=make(chan m0GameInbound,256)
 handoff:=make(chan struct{})
 // On failed TLS/Apply, close the cold read signal before joining NPF
 // readers. Successful Rust handoff shares the same idempotent close.
 stopColdReaders:=sync.OnceFunc(func(){close(handoff)})
 failed:=make(chan error,count+1)
 var readers sync.WaitGroup
 defer func(){
  fmt.Println("M0_GAME_COLD_STAGE DEFER_NPF_JOIN_ENTER")
  stopColdReaders()
  readers.Wait()
  fmt.Println("M0_GAME_COLD_STAGE DEFER_NPF_JOIN_DONE")
  for _,ep:=range endpoints{_ = ep.Close()}
  for _,assoc:=range assocs{assoc.Close()}
 }()
 for i:=0;i<count;i++{
  flow,err:=m0WindowsGameOriginalClientFlow(o,localIP,i)
  if err!=nil{return err}
  // Each Npcap receive filter and the SYN emitter now target this exact
  // independent client source port AND the same remote server 443.
  ep,err:=open(flow.LocalPort,flow.PeerPort)
  if err!=nil{return err}
  endpoints=append(endpoints,ep)
  var seed [4]byte
  if _,err=rand.Read(seed[:]);err!=nil{return err}
  assoc,err:=faketcp.NewClientAssociation(flow,binary.BigEndian.Uint32(seed[:]),
   time.Second,func(seg faketcp.Segment)error{
    if seg.Flags&faketcp.FlagSYN!=0{
     wire:=faketcp.MarshalSegment(seg,1,faketcp.PacketPersonaWindows11)
     decoded,decodeErr:=faketcp.ParseIPv4TCP(wire)
     if decodeErr!=nil||!decoded.MSSSet||decoded.MSS!=faketcp.PublicV4AdvertisedMSS(){return windowsclient.ErrN4NativeGuard}
     fmt.Printf("WBD_WINDOWS_GAME_ACTUAL_SYN_MSS_V1 side=client lane=%d local_advertised_mss=%d tcp_option_bytes=%x\n",
      i,decoded.MSS,wire[40:44])
    }
    _,e:=ep.WriteSegment(1,seg);return e
   })
  if err!=nil{return err}
  assocs=append(assocs,assoc)
  flows=append(flows,flow)
  readers.Add(1)
  go func(index int,endpoint *faketcp.NpcapEndpoint,a *faketcp.ClientAssociation){
   defer readers.Done()
   for{
    select{case <-handoff:return;default:}
    seg,_,err:=endpoint.ReadSegmentUntil(1,handoff)
    if err!=nil{
     select{case <-handoff:return;default:}
     if ctx.Err()==nil{select{case failed<-err:default:}}
     return
    }
    if a.State()==faketcp.ClientAssociationDetached{
     _=offerGameColdInbound(inbound,m0GameInbound{lane:index,segment:seg})
    }else if err=a.HandleSegment(seg,time.Now());err!=nil{
     if ctx.Err()==nil{select{case failed<-err:default:}}
     return
    }
   }
  }(i,ep,assoc)
  if err=assoc.Start(time.Now());err!=nil{return err}
 }
 // Start all independent original FakeTCP SYNs before waiting for any
 // particular lane. Under real 15–30% loss, serial 20s lane waits could
 // burn the entire Windows public Ready deadline without ever attempting
 // later Game4 TLS lanes; no new protocol, OS worker or hot Go pump.
 established,cancel:=context.WithTimeout(ctx,20*time.Second)
 defer cancel()
 type laneReady struct{index int;err error}
 handshaked:=make(chan laneReady,count)
 for i,a:=range assocs{
  go func(i int,a *faketcp.ClientAssociation){
   handshaked<-laneReady{index:i,err:a.WaitEstablished(established)}
  }(i,a)
 }
 tick:=time.NewTicker(100*time.Millisecond)
 defer tick.Stop()
 for remaining:=count;remaining>0;{
  select{
  case <-established.Done():
   return fmt.Errorf("original Game%d lanes TCP: %w",count,established.Err())
  case res:=<-handshaked:
   if res.err!=nil{return fmt.Errorf("original Game%d lane%d TCP: %w",count,res.index+1,res.err)}
   remaining--
  case readErr:=<-failed:
   return fmt.Errorf("original Game%d NPF prehandoff: %w",count,readErr)
  case <-tick.C:
   now:=time.Now()
   for i,a:=range assocs{
    if _,err:=a.EmitRetransmitDue(now);err!=nil{
     return fmt.Errorf("original Game%d lane%d TCP retransmit: %w",count,i+1,err)
    }
   }
  }
 }
 policy,err:=realityfront.FixedPolicyForClient(count,4)
 if err!=nil{return err}
 recordOffer,err:=m0WindowsV4ColdRecordOffer(
  filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),
  o.ConnectionMTU,physical,o.TunnelMTU,o.Mode,o.FEC2Mode=="fixed",
 )
 if err!=nil{return err}
 cfg:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{
   ServerName:o.ServerName,RouteKey:append([]byte(nil),o.RouteKey...),VerifyServer:true,RootCAs:o.TrustedServerRoots,Timeout:15*time.Second,
  },
  AutoLease:false,DesiredLanes:uint8(count),
  InstallationID:o.Installation[:],Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:recordOffer,Policy:policy,
 }
 fecMode:=uint8(0)
 if o.FEC2Mode=="fixed"{
  profile,e:=m0WindowsV4Profile(o.FEC2Profile)
  if e!=nil{return e}
  fecMode=uint8(profile)+1 // Linux GameFec=profile+1, TLS protected
 }
 group,err:=realityfront.V4WindowsEstablishOriginalGameClientGroup(
  ctx,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),assocs,cfg,fecMode)
 if err!=nil{return err}
 fmt.Printf("WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes=%d fec=%d client_record_offer=%d requested_tun_mtu=%d\n",count,fecMode,cfg.ClientLimit,o.TunnelMTU)
 fmt.Println("M0_GAME_COLD_STAGE WINTUN_OPEN_ENTER")
 tun,err:=windowsclient.OpenTUN(o.AdapterAlias)
 if err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE WINTUN_OPEN_DONE")
 // Never run TUN.Close in an unconditional defer: Rust's native Wintun
 // ring loan pins the original TUN active-call fence until full Join.
 // A failed OS WAL/Stop must return its actual error, not block in Close.
 fmt.Println("M0_GAME_COLD_STAGE PLAN_MAKE_ENTER")
 plan,err:=makePlan()
 if err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE PLAN_MAKE_DONE")
 packet:=&m0WinRustGamePeer{
  group:group,first:group.FirstOriginalOwner(),tun:tun,
  endpoints:endpoints,flows:flows,inbound:inbound,handoff:handoff,
  stopColdReaders:stopColdReaders,readers:&readers,errorSource:failed,
  pathMTU:o.ConnectionMTU, // NPF outer IPv4/TCP, never derived Wintun inner MTU
  disableOuterRepair:o.DisableOuterRepair,
  errors:make(chan error,1),
 }
 fmt.Println("M0_GAME_COLD_STAGE PRODUCT_PREPARE_ENTER")
 product,err:=windowsownerlease.PrepareOriginalTLSNativeGameProduct(
  ctx,group,tun,plan,o.Installation,group.Epoch(),packet)
 if err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE PRODUCT_PREPARE_DONE")
 stop:=func()error{
  done,cancel:=context.WithTimeout(context.Background(),60*time.Second)
  defer cancel()
  e:=product.Stop(done)
  if e!=nil{
   fmt.Printf("M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=FAIL error=%v native_joined=%t wintun_close=RETAINED\n",e,!packet.live)
   return e
  }
  // Full owned Rust Join, WFP/routes/MTU/DNS WAL recovery and kernel
  // lease release are positively verified BEFORE Wintun Close.
  if e=tun.Close();e!=nil{
   fmt.Printf("M0_PLAN027_GAME_STOP_RESULT stage=wintun_close result=FAIL error=%v\n",e)
   return e
  }
  fmt.Println("M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=PASS wintun_closed=1")
  return nil
 }
 fmt.Println("M0_GAME_COLD_STAGE OS_APPLY_ENTER")
 receipt,err:=product.Apply(ctx)
 if err!=nil{return errors.Join(err,stop())}
 fmt.Println("M0_GAME_COLD_STAGE OS_APPLY_DONE")
 if !receipt.AllNativeOSApplied{return errors.Join(windowsclient.ErrN4NativeGuard,stop())}
 fmt.Println("M0_GAME_COLD_STAGE LIVE_RECEIPT_ENTER")
 live,err:=product.LiveReceipt(ctx)
 if err==nil{fmt.Println("M0_GAME_COLD_STAGE LIVE_RECEIPT_DONE")}
 if err!=nil||!live.AllNativeOSApplied{
  return errors.Join(err,windowsclient.ErrN4NativeGuard,stop())
 }
 // Distinct Game cold path: generation-scoped numeric Wintun MTU CAS
 // MUST pass before READY. No extra OS writes or hot-packet calculation.
 actualInner,err:=product.RuntimeMTU(ctx)
 if err!=nil||actualInner!=o.TunnelMTU{
  return errors.Join(fmt.Errorf("Game owned Wintun OS MTU not applied planned=%d inspected=%d: %w",
   o.TunnelMTU,actualInner,windowsclient.ErrN4NativeGuard),err,stop())
 }
 fmt.Printf("WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=%d applied=%d outer_config=%d\n",
  o.TunnelMTU,actualInner,o.ConnectionMTU)
 select{
 case <-pathChanged:return errors.Join(errM0WindowsPhysicalPathChanged,stop())
 default:
 }
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=%d fec=%d tls=1 rust=1 native_os_wal=1\n",count,fecMode)
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 ticker:=time.NewTicker(time.Second);defer ticker.Stop()
 var runtimeErr error
outer:
 for{
  select{
  case <-ctx.Done():break outer
  case <-pathChanged:
   runtimeErr=errM0WindowsPhysicalPathChanged
   break outer
  case runtimeErr=<-packet.Errors():break outer
  case runtimeErr=<-failed:break outer
  case <-ticker.C:
   if ctx.Err()!=nil{break outer}
   if stateErr:=packet.HealthError(ctx);stateErr!=nil{
    if ctx.Err()!=nil{break outer}
    runtimeErr=fmt.Errorf("real Game Rust native driver/MTU failure: %w",stateErr)
    break outer
   }
   currentMTU,mtuErr:=product.RuntimeMTU(ctx)
   if ctx.Err()!=nil{break outer}
   if drift:=m0WindowsGameRuntimeMTUDrift(ctx,o.TunnelMTU,currentMTU,mtuErr);drift!=nil{
    runtimeErr=drift
    break outer
   }
   fmt.Println("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+packet.Stats())
  }
 }
 stopErr:=stop()
 if stopErr!=nil{return errors.Join(runtimeErr,stopErr)}
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes=%d wal_restored=1 rust_stopped=1\n",count)
 return runtimeErr
}
