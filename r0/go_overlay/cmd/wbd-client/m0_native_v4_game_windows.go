//go:build windows && wbd_v4_embedded_go
package main

// Genuine per-lane original-Go FakeTCP credential/TLS bootstrap, then
// the proven Linux shared Rust GameAdapter and one native OS/WAL owner.
// PLAN029B Game2/Game4 share the original cold V4 Rust split owner,
// without adding a packet pump or modifying game FEC/AEAD/wire.
import(
 "context"
 "crypto/rand"
 "encoding/binary"
 "encoding/json"
 "errors"
 "fmt"
 "net/netip"
 "os"
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

func m0WindowsGameQualitySnapshot(grade uint8,data string){
 var snapshot struct{
  Tx uint64 `json:"tx_records"`
  Rx uint64 `json:"rx_first_delivered_ipv4"`
 }
 if json.Unmarshal([]byte(data),&snapshot)!=nil{return}
 if grade==0{
  m0WindowsPrintQualityV2("off","off",snapshot.Tx,snapshot.Rx)
 }else if grade<=7{
  profile:=m0WindowsQualityProfileName(int(grade)-1)
  m0WindowsPrintQualityV2("applied-"+profile,"negotiated-"+profile,
   snapshot.Tx,snapshot.Rx)
 }
}

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
// "all" and split-off do not allocate business Direct or Bypass OS
// destinations. DNS-only V4 remains active and owned even in these modes.
func m0GameBusinessSplit(o m0NativeV4Options) bool {
 return o.SplitEnable && o.RouteMode!="all"
}
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
 ctx context.Context,o m0NativeV4Options,localIP [4]byte,
 physicalMTU uint32,physicalIfIndex uint32,
 configure func(uint16,uint16)(faketcp.NpcapConfig,error),
 makePlan func(netip.Prefix)(windowsclient.NetworkPlan,error),
 pathChanged <-chan struct{},applied *bool,
)error{
 count:=2;if o.Mode==m0WinModeGame4{count=4}
 assocs:=make([]*faketcp.ClientAssociation,0,count)
 flows:=make([]faketcp.ClientFlow,0,count)
 cfgs:=make([]faketcp.NpcapConfig,0,count)
 var shared *faketcp.XdpEndpoint
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
  if shared!=nil{_ = shared.Close()}
  for _,assoc:=range assocs{assoc.Close()}
 }()
 for i:=0;i<count;i++{
  flow,err:=m0WindowsGameOriginalClientFlow(o,localIP,i)
  if err!=nil{return err}
  cfg,err:=configure(flow.LocalPort,flow.PeerPort)
  if err!=nil{return err}
  flows=append(flows,flow);cfgs=append(cfgs,cfg)
 }
 xdp,available,err:=faketcp.OpenXdpGameEndpoint(filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),physicalIfIndex,cfgs)
 if err!=nil{return err}
 if !available{return fmt.Errorf("WinXDP Game entry missing from wbd_engine.dll")}
 shared=xdp
 for i,flow:=range flows{
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
    _,e:=shared.WriteGameSegment(i,seg);return e
   })
  if err!=nil{return err}
  assocs=append(assocs,assoc)
 }
 // One handling function keeps original TLS detach/early semantics for both
 // cold carriers. Shared XDP dispatches directly; no lane mailbox or copy.
 handle:=func(index int,seg faketcp.Segment)error{
  a:=assocs[index]
  if a.State()==faketcp.ClientAssociationDetached{
   if handled,_:=a.RepeatGameColdFinalACK(&seg);handled{return nil}
   if len(seg.Payload)==0||seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{return nil}
   _=offerGameColdInbound(inbound,m0GameInbound{lane:index,segment:seg})
   return nil
  }
  err:=a.HandleSegment(seg,time.Now())
  if errors.Is(err,faketcp.ErrClientDetached){
   if handled,_:=a.RepeatGameColdFinalACK(&seg);handled{return nil}
   if len(seg.Payload)==0||seg.Flags&(faketcp.FlagFIN|faketcp.FlagRST)!=0{return nil}
   _=offerGameColdInbound(inbound,m0GameInbound{lane:index,segment:seg});return nil
  }
  if errors.Is(err,faketcp.ErrClientHandshake)&&a.State()==faketcp.ClientAssociationSYNSent{return nil}
  if err!=nil{a.Close()}
  return err
 }
 report:=func(err error){
  select{case <-handoff:return;default:}
  if ctx.Err()==nil{select{case failed<-err:default:}}
 }
 {
  readers.Add(1)
  go func(){
   defer readers.Done()
   for{
    index,seg,err:=shared.ReadGameSegmentUntil(handoff)
    if err!=nil{report(err);return}
    if err=handle(index,seg);err!=nil{report(err);return}
   }
  }()
 }
 for _,assoc:=range assocs{if err=assoc.Start(time.Now());err!=nil{return err}}
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
   return fmt.Errorf("original Game%d lanes TCP: %w",count,m0WindowsTagOriginalColdTransport(established.Err()))
  case res:=<-handshaked:
   if res.err!=nil{return fmt.Errorf("original Game%d lane%d TCP: %w",count,res.index+1,m0WindowsTagOriginalColdTransport(res.err))}
   remaining--
  case readErr:=<-failed:
   return fmt.Errorf("original Game%d NPF prehandoff: %w",count,readErr)
  case <-tick.C:
   now:=time.Now()
   for i,a:=range assocs{
    if _,err:=a.EmitRetransmitDue(now);err!=nil{
     return fmt.Errorf("original Game%d lane%d TCP retransmit: %w",count,i+1,m0WindowsTagOriginalColdTransport(err))
    }
   }
  }
 }
 policy,err:=realityfront.PolicyForClientWithInitialAndCipher(count,"fixed",4,4,20,o.RecordCipher)
 if err!=nil{return err}
 recordOffer,err:=m0WindowsV4ColdRecordOffer(
  filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),
  o.ConnectionMTU,physicalMTU,o.TunnelMTU,o.Mode,o.FEC2Mode=="fixed",
 )
 if err!=nil{return err}
 cfg:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{
   ServerName:o.ServerName,RouteKey:append([]byte(nil),o.RouteKey...),VerifyServer:o.TLSVerifyServer,RootCAs:o.TrustedServerRoots,Timeout:15*time.Second,
  },
  AutoLease:o.AutoLease,DesiredLanes:uint8(count),
  InstallationID:o.Installation[:],Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:recordOffer,Policy:policy,
 }
 fecMode:=uint8(0)
 if o.FEC2Mode=="fixed"{
  profile,e:=m0WindowsV4Profile(o.FEC2Profile)
  if e!=nil{return e}
  fecMode=uint8(profile)+1 // Linux GameFec=profile+1, TLS protected
 }
 paddingMode,paddingErr:=m0WindowsProtectedStartupPaddingValue(o.StartupPaddingMode)
 if paddingErr!=nil{return paddingErr}
 group,err:=realityfront.V4WindowsEstablishOriginalGameClientGroup(
  ctx,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),assocs,cfg,fecMode,paddingMode)
 if err!=nil{return m0WindowsTagOriginalColdTransport(err)}
 trustedLease,appliedCipher,selectionErr:=group.AuthenticatedNetworkSelection()
 if selectionErr!=nil||appliedCipher!=o.RecordCipher{
  return fmt.Errorf("%w: Game protected group network selection invalid: %v",windowsclient.ErrN4NativeGuard,selectionErr)
 }
 if o.AutoLease{
  assigned,parseErr:=netip.ParsePrefix(trustedLease)
  if parseErr!=nil||!assigned.IsValid()||!assigned.Addr().Is4()||
   assigned.Bits()!=32||assigned.Addr().IsUnspecified()||assigned.Addr().IsMulticast(){
   return fmt.Errorf("%w: Game server did not authenticate a usable auto IPv4 /32: %v",windowsclient.ErrN4NativeGuard,parseErr)
  }
  o.Lease4=assigned
 }else if trustedLease!=""&&trustedLease!=o.Lease4.String(){
  return fmt.Errorf("%w: Game protected manual /32 conflicts with configured Wintun",windowsclient.ErrN4NativeGuard)
 }
 fmt.Printf("WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION mode=%v auto_lease=%t lease=%s cipher=%d source=original_TLS_Rust_snapshot\n",
  o.Mode,o.AutoLease,o.Lease4,appliedCipher)
 fmt.Printf("WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes=%d fec=%d client_record_offer=%d requested_tun_mtu=%d\n",count,fecMode,cfg.ClientLimit,o.TunnelMTU)
 // Game2 and Game4 both use the SAME original cold CN/IP/DNS
 // snapshot as Normal. Even split-off/all retains one original Rust V4
 // DNS owner, with NO business Direct table/FakeIP writer.
 // No Go packet hot pump, separate Wintun, DNS fallback or Game FEC rewrite.
 // Game2/Game4 padding now uses the V5 authenticated cold selector and
 // original per-lane M1 AEAD, with the same bounded source flow policy.
 gameSplit,err:=m0Plan029TrialCold(o,netip.AddrFrom4(localIP),
   physicalIfIndex,o.Lease4.Addr(),o.TunnelMTU,group.Epoch())
 if err!=nil||gameSplit==nil{
  return fmt.Errorf("PLAN029B original Game%d V3 cold split: %w",
   count,errors.Join(err,windowsclient.ErrN4NativeGuard))
 }
 if gameSplit.TCPSynthetic4==[4]byte{}{
  return windowsclient.ErrN4NativeGuard
 }
 // All three route modes are admitted for Game2 and Game4.
 // In all/off synthetic is ONLY an owned DNS-TCP return listener;
 // ordinary CN uses real A and advanced CN alone gets FakeIP journal.
 synthetic:=netip.AddrFrom4(gameSplit.TCPSynthetic4)
 if gameSplit.RouteMode==0&&(len(gameSplit.Direct)!=0||
   len(gameSplit.CN)!=0||len(gameSplit.Domains)!=0||
   len(gameSplit.FakeJournalPath)!=0||gameSplit.PolicyFlags!=0){
  return fmt.Errorf("PLAN029B Game%d all/off allocated business Direct",count)
 }
 fmt.Printf("WBD_PLAN029B_GAME_V3_COLD_EFFECTIVE lanes=%d requested_route_mode=%s route_mode=%d requested_split=%t business_split=%t cn_domain_fakeip=%t direct_dns=%v tunnel_dns=%v cn_rows=%d domain_bytes=%d single_original_owner=1\n",
  count,o.RouteMode,gameSplit.RouteMode,o.SplitEnable,gameSplit.RouteMode!=0,
  gameSplit.PolicyFlags&1!=0,gameSplit.DirectDNS,gameSplit.TunnelDNS,
  len(gameSplit.CN),len(gameSplit.Domains))
 if count==4&&gameSplit.RouteMode==2&&gameSplit.PolicyFlags&1!=0{
  fmt.Printf("WBD_PLAN029_GAME4_CN_COLD_EFFECTIVE direct_dns=%v tunnel_dns=%v cn_rows=%d domains_bytes=%d fakeip=owned single_wintun=1\n",
   o.DirectDNS4,o.DNSServers4[0],len(gameSplit.CN),len(gameSplit.Domains))
 }
 fmt.Println("M0_GAME_COLD_STAGE WINTUN_OPEN_ENTER")
 tun,err:=windowsclient.OpenTUN(o.AdapterAlias)
 if err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE WINTUN_OPEN_DONE")
 // Never run TUN.Close in an unconditional defer: Rust's native Wintun
 // ring loan pins the original TUN active-call fence until full Join.
 // A failed OS WAL/Stop must return its actual error, not block in Close.
 fmt.Println("M0_GAME_COLD_STAGE PLAN_MAKE_ENTER")
 plan,err:=makePlan(o.Lease4)
 if err!=nil{return err}
 fmt.Println("M0_GAME_COLD_STAGE PLAN_MAKE_DONE")
 packet:=&m0WinRustGamePeer{
  group:group,first:group.FirstOriginalOwner(),tun:tun,
  xdp:shared,cfgs:cfgs,flows:flows,inbound:inbound,handoff:handoff,
  stopColdReaders:stopColdReaders,readers:&readers,errorSource:failed,
  pathMTU:o.ConnectionMTU, // NPF outer IPv4/TCP, never derived Wintun inner MTU
  disableOuterRepair:o.DisableOuterRepair,
  plan029Cold:gameSplit,
  errors:make(chan error,1),
 }
 fmt.Println("M0_GAME_COLD_STAGE PRODUCT_PREPARE_ENTER")
 var product *windowsownerlease.OriginalTLSNativeProductSession
 if synthetic.Is4(){
  product,err=windowsownerlease.PrepareOriginalTLSNativeGameProductWithSyntheticTCP(
   ctx,group,tun,plan,o.Installation,group.Epoch(),packet,synthetic)
 }else{
  product,err=windowsownerlease.PrepareOriginalTLSNativeGameProduct(
   ctx,group,tun,plan,o.Installation,group.Epoch(),packet)
 }
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
 if synthetic.Is4(){
  // Exactly one original Game2/4 Rust owner prepares its generation's
  // synthetic TCP listener AFTER OS Applied+MTU CAS and arms an exact
  // WAL-owned Defender Allow (DNS-only when all/off).
  port,tcpErr:=group.Plan029GamePrepareNativeTCPAfterOSApply(ctx)
  if tcpErr!=nil{return errors.Join(fmt.Errorf("Game%d DNS/Direct TCP PREPARE: %w",count,tcpErr),stop())}
  if tcpErr=product.Plan029ArmOwnedDirectTCP(ctx,port);tcpErr!=nil{
   return errors.Join(fmt.Errorf("Game%d DNS/Direct exact Defender Allow: %w",count,tcpErr),stop())
  }
  if tcpErr=group.Plan029GameEnableNativeTCPAfterDefender(ctx,port);tcpErr!=nil{
   return errors.Join(fmt.Errorf("Game%d DNS/Direct TCP ENABLE: %w",count,tcpErr),stop())
  }
  fmt.Printf("WBD_PLAN029B_GAME_NATIVE_DNS_TCP_ENABLED lanes=%d business_split=%t port=%d synthetic=%s owned_allow=1\n",count,gameSplit.RouteMode!=0,port,synthetic)
  if gameSplit.RouteMode==2&&gameSplit.PolicyFlags&1!=0{
   fmt.Printf("WBD_PLAN029_GAME4_CN_NATIVE_TCP_ENABLED port=%d synthetic=%s owned_allow=1\n",port,synthetic)
  }
 }
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=%d fec=%d tls=1 rust=1 native_os_wal=1\n",count,fecMode)
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 if applied!=nil{*applied=true}
 // Same diagnostic policy as Normal. Keep the GUI's light status
 // stream, but only emit heavy packet telemetry when explicitly requested.
 diagnostic:=os.Getenv("GITHUB_ACTIONS")=="true"||os.Getenv("WBD_NATIVE_TELEMETRY")=="1"
 interval:=2*time.Second
 if diagnostic{interval=time.Second}
 ticker:=time.NewTicker(interval);defer ticker.Stop()
 rotation,stopRotation:=m0WindowsArmRotation(o)
 defer stopRotation()
 var runtimeErr error
outer:
 for{
  select{
  case <-ctx.Done():break outer
  case <-rotation:
   if ctx.Err()==nil{runtimeErr=m0WindowsTimedRotationDue()}
   break outer
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
   snapshot:=packet.Stats()
   m0WindowsGameQualitySnapshot(fecMode,snapshot)
   if diagnostic{fmt.Println("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+snapshot)}
  }
 }
 stopErr:=stop()
 // A true dead verdict may authorize a new generation only after owned Stop.
 if stopErr!=nil{return fmt.Errorf("Game native owned Stop failed after %v: %w",runtimeErr,stopErr)}
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes=%d wal_restored=1 rust_stopped=1\n",count)
 return runtimeErr
}
