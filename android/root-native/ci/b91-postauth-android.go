//go:build android && cgo && wbd_v4_embedded_go && wbd_android_specialty_test

// CI-only in-process cold transport between the two ORIGINAL associations.
// No synthetic SYNACK, guessed handoff sequence, fake lease or M4 data peer.
package realityfront

import (
 "bytes"
 "context"
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "errors"
 "fmt"
 "math/big"
 "net/netip"
 "sync"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
)
func b91Cert()(tls.Certificate,*x509.CertPool,error){
 key,e:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);if e!=nil{return tls.Certificate{},nil,e}
 now:=time.Now()
 cert:=&x509.Certificate{SerialNumber:big.NewInt(1),Subject:pkix.Name{CommonName:"target.test"},
  DNSNames:[]string{"target.test"},NotBefore:now.Add(-time.Hour),NotAfter:now.Add(time.Hour),
  KeyUsage:x509.KeyUsageDigitalSignature|x509.KeyUsageCertSign,ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
  BasicConstraintsValid:true,IsCA:true}
 raw,e:=x509.CreateCertificate(rand.Reader,cert,cert,&key.PublicKey,key);if e!=nil{return tls.Certificate{},nil,e}
 leaf,e:=x509.ParseCertificate(raw);if e!=nil{return tls.Certificate{},nil,e}
 roots:=x509.NewCertPool();roots.AddCert(leaf)
 return tls.Certificate{Certificate:[][]byte{raw},PrivateKey:key},roots,nil
}
type b91Pair struct{
 client *faketcp.ClientAssociation
 server *faketcp.ServerAssociation
 result chan error
 cancel context.CancelFunc
 wg sync.WaitGroup
}
func b91NewPair(parent context.Context,flow faketcp.ClientFlow,ordinal int,peerMSS uint16)(*b91Pair,error){
 ctx,cancel:=context.WithCancel(parent)
 p:=&b91Pair{cancel:cancel,result:make(chan error,1)}
 c2s:=make(chan faketcp.Segment,256);s2c:=make(chan faketcp.Segment,256)
 emit:=func(ch chan faketcp.Segment)faketcp.SegmentEmitter{
  return func(seg faketcp.Segment)error{
   seg.Payload=bytes.Clone(seg.Payload)
   select{case ch<-seg:return nil;case <-ctx.Done():return ctx.Err()}
  }
 }
 fail:=func(e error)(*b91Pair,error){p.close();return nil,e}
 var e error
 p.client,e=faketcp.NewClientAssociation(flow,uint32(100000+ordinal*10000),time.Second,emit(c2s))
 if e!=nil{return fail(e)}
 if e=p.client.Start(time.Now());e!=nil{return fail(e)}
 var syn faketcp.Segment
 select{case syn=<-c2s:case <-ctx.Done():return fail(ctx.Err())}
 localMSS:=faketcp.PublicV4AdvertisedMSS()
 if peerMSS!=0{if e=faketcp.SetPublicV4AdvertisedMSS(peerMSS);e!=nil{return fail(e)}}
 p.server,e=faketcp.NewServerAssociation(syn,uint32(500000+ordinal*10000),time.Second,emit(s2c))
 restore:=faketcp.SetPublicV4AdvertisedMSS(localMSS)
 if e!=nil||restore!=nil{return fail(errors.Join(e,restore))}
 synack,e:=p.server.SYNACKSegment();if e!=nil{return fail(e)}
 if e=p.client.HandleSegment(synack,time.Now());e!=nil{return fail(e)}
 select{case ack:=<-c2s:if _,e=p.server.HandleSegment(ack,time.Now());e!=nil{return fail(e)}
 case <-ctx.Done():return fail(ctx.Err())}
 if e=p.client.WaitEstablished(ctx);e!=nil{return fail(e)}
 p.wg.Add(2)
 go func(){defer p.wg.Done();for{select{
 case seg:=<-c2s:
  result,e:=p.server.HandleSegment(seg,time.Now())
  if e!=nil{fmt.Println("B94_COLD_SERVER_SEGMENT",e);continue}
  // The original server reader owns this explicit ACK dispatch. Without
  // it BootstrapStream.Write waits forever for its final cumulative ACK.
  if result.AckNeeded{if e=emit(s2c)(p.server.ACKSegment(result.Ack));e!=nil{return}}
 case <-ctx.Done():return
 }}}()
 go func(){defer p.wg.Done();for{select{
 case seg:=<-s2c:if e:=p.client.HandleSegment(seg,time.Now());e!=nil&&!errors.Is(e,faketcp.ErrClientDetached){fmt.Println("B94_COLD_CLIENT_SEGMENT",e)}
 case <-ctx.Done():return
 }}}()
 return p,nil
}
func(p *b91Pair)close(){
 p.cancel()
 if p.client!=nil{p.client.Close()}
 if p.server!=nil{p.server.Close()}
 p.wg.Wait()
}
func b91WaitTX(ctx context.Context,read func()(uint64,error),before uint64)error{
 deadline:=time.Now().Add(4*time.Second)
 for time.Now().Before(deadline){
  n,e:=read();if e!=nil{return e};if n>before{return nil}
  select{case <-ctx.Done():return ctx.Err();case <-time.After(40*time.Millisecond):}
 }
 return fmt.Errorf("original Android native TX did not increase")
}
func B91RunNativeCI(ctx context.Context,local,peer netip.Addr,normal V4LinuxClientProductConfig,game V4AndroidGameConfig,mode string,recordLimit,serverLimit uint16,boundary bool,peerMSSes []uint16,
 route func(string)(func()error,error),send func(string)error)(ret error){
 cert,roots,e:=b91Cert();if e!=nil{return e}
 routeKey:=[]byte("0123456789abcdef0123456789abcdef")
 store,e:=NewV4EpochStore(8);if e!=nil{return e}
 leases,e:=logicaltunnel.NewLeaseRegistry(netip.MustParsePrefix("198.19.0.0/24"),32);if e!=nil{return e}
 var install logicaltunnel.InstallationID;install[0]=91
 tunnel:=logicaltunnel.DerivedTunnelID("b91-ci",install)
 n:=int(game.Lanes);if n==0{n=1}
 policyMode:="off";parity:=0
 if n>1||normal.FECMode==FecV2Fixed{policyMode="fixed";parity=4}
 if n==1&&normal.FECMode==FecV2Auto{policyMode="auto"}
 policy,e:=PolicyForClientWithInitialAndCipher(n,policyMode,parity,4,20,CipherChaCha);if e!=nil{return e}
 pairs:=make([]*b91Pair,0,n);assocs:=make([]*faketcp.ClientAssociation,0,n)
 defer func(){for _,p:=range pairs{p.close()}}()
 for i:=0;i<n;i++{
  flow:=faketcp.ClientFlow{LocalIP:local.As4(),PeerIP:peer.As4(),LocalPort:uint16(46100+i),PeerPort:443}
  peerMSS:=uint16(0);if len(peerMSSes)==n{peerMSS=peerMSSes[i]}
  p,e:=b91NewPair(ctx,flow,i,peerMSS);if e!=nil{return e}
  pairs=append(pairs,p);assocs=append(assocs,p.client)
  p.wg.Add(1)
  go func(p *b91Pair){
   defer p.wg.Done()
   _,e:=EstablishServerV4(ctx,p.server,ServerAdmissionConfig{
    TLS:ServerConfig{ServerName:"target.test",RouteKey:routeKey,TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:15*time.Second},
    ExpectedUsername:"b91-ci",ExpectedPassword:"b91-fixture",ServerLimit:serverLimit,
    AllocateLease:func(req AdmissionRequest)(string,error){return V4AllocateAutomaticLease(leases,req)},
   },V4ServerOptions{DataPlaneReady:true,Epochs:store,perClientMixedMode:true})
   if e!=nil{fmt.Println("B94_ORIGINAL_SERVER_ADMISSION_FAIL",e)}else{fmt.Println("B94_ORIGINAL_SERVER_ADMISSION_PASS")}
   p.result<-e
  }(p)
 }
 fmt.Println("B91_ORIGINAL_ASSOCIATIONS_ESTABLISHED",mode,n,"cold_transport=in_process")
 cfg:=ClientAdmissionConfig{TLS:ClientConfig{ServerName:"target.test",RouteKey:routeKey,VerifyServer:true,RootCAs:roots,Timeout:15*time.Second},
  Username:"b91-ci",Password:"b91-fixture",TunnelID:tunnel.Bytes(),AutoLease:true,InstallationID:append([]byte(nil),install[:]...),
  ClientLimit:recordLimit,DesiredLanes:uint8(n),LaneID:1,Policy:policy}
 var lease string
 var closeProduct func()error
 var tx func()(uint64,error)
 var fecCounters func()([9]uint64,error)
 var pulse func()(V4PublicLoopPulse,error)
 if n==1{
  p,e:=NewV4LinuxClientProduct(normal);if e!=nil{return e}
  s,e:=p.ConnectAuthenticatedPeer(ctx,assocs[0],cfg);if e!=nil{return e}
  closeProduct=p.Close
  defer func(){stop:=closeProduct();ret=errors.Join(ret,stop);if stop==nil{fmt.Println("B91_NATIVE_STOP_PASS",mode)}}()
  lease,e=s.AuthenticatedLeaseIPv4();if e!=nil{return e}
  if normal.FECMode!=FecV2Off{
   f,e:=p.OriginalFECReadback()
   if e!=nil||f.RequestedRevision!=1||f.AppliedRevision!=0||!f.Pending{return fmt.Errorf("original FEC pending: %+v %v",f,e)}
   fmt.Println("B91_NATIVE_FEC_PENDING_PASS",mode,f.Profile,f.RequestedRevision)
   // Existing Android read-only ABI. No production diagnostic or packet hook.
   fecCounters=func()([9]uint64,error){
    p.mu.Lock();defer p.mu.Unlock()
    return p.owner.originalAndroidFixedM4Counters()
   }
  }
  pulse=p.OriginalLoopPulse
  tx=func()(uint64,error){v,e:=p.OriginalLoopPulse();return v.BusinessRawCopied,e}
 }else{
  p,e:=NewV4AndroidGameProduct(game);if e!=nil{return e}
  lease,e=p.ConnectAuthenticatedGame(ctx,assocs,cfg);if e!=nil{return e}
  closeProduct=p.Close
  defer func(){stop:=closeProduct();ret=errors.Join(ret,stop);if stop==nil{fmt.Println("B91_NATIVE_STOP_PASS",mode)}}()
  if len(peerMSSes)==n{
   // Inspect the actual original TLS session snapshots, not a duplicate
   // predicted budget or a counter from the test transport.
   want:=recordLimit
   for _,mss:=range peerMSSes{if mss<want{want=mss}}
   for i,s:=range p.sessions{
    cold,e:=s.ColdSnapshot();if e!=nil{return e}
    cl,sl:=cold.RecordLimits()
    if cl!=want||sl!=serverLimit{return fmt.Errorf("lane %d authenticated cap client=%d server=%d expected=%d/%d",i+1,cl,sl,want,serverLimit)}
    fmt.Printf("B101_GAME_AUTH_RECORD_PASS lane=%d client=%d server=%d\n",i+1,cl,sl)
   }
  }
  lanes,ready,e:=p.OriginalNativeState()
  if e!=nil||!ready||lanes!=uint32(n){return fmt.Errorf("real Game native group state %d %t %v",lanes,ready,e)}
  if game.GameFecEnabled{if _,e=p.OriginalGameFecCounters();e!=nil{return e}}
  tx=func()(uint64,error){v,e:=p.OriginalM4Counters();return v.RawCopied,e}
 }
 for _,p:=range pairs{select{case e:=<-p.result:if e!=nil{return fmt.Errorf("original server TLS/lease: %w",e)}
 case <-ctx.Done():return ctx.Err()}}
 if lease==""{return ErrAdmissionParams}
 fmt.Println("B91_NATIVE_M4_STARTED",mode,"lanes",n,"actual_fixture_tls_lease",lease)
 undo,e:=route(lease);if e!=nil{return e};if undo==nil{return ErrAdmissionUnsupported}
 defer func(){e:=undo();ret=errors.Join(ret,e);if e==nil{fmt.Println("B91_NATIVE_UID_STOP_PASS",mode)}}()
 var probeErr error
 if boundary{
  for _,probe:=range []string{"mtu-minus","mtu-edge"}{
   before,e:=tx();if e!=nil{return e}
   var fecBefore [9]uint64
   if fecCounters!=nil{fecBefore,e=fecCounters();if e!=nil{return e}}
   if e=send(probe);e!=nil{return e}
   deadline:=time.Now().Add(6*time.Second)
   copied:=false
   for time.Now().Before(deadline){
    after,e:=tx();if e!=nil{return e}
    copied=after>=before+4
    if fecCounters!=nil{
     f,e:=fecCounters();if e!=nil{return e}
     copied=copied&&f[0]>=fecBefore[0]+4&&f[1]>fecBefore[1]&&f[7]==0&&f[8]==0
    }
    if copied{fmt.Println("B98_MTU_BOUNDARY_TX_PASS",mode,probe,"four_datagrams");break}
    select{case <-ctx.Done():return ctx.Err();case <-time.After(50*time.Millisecond):}
   }
   if !copied{return fmt.Errorf("MTU boundary original native TX incomplete mode=%s probe=%s",mode,probe)}
  }
  if e=send("mtu-over");e!=nil{return e}
  fmt.Println("B98_MTU_DF_OVERSIZE_REJECT_PASS",mode)
  return nil
 }
 for _,probe:=range []string{"1","send4"}{
  before,e:=tx();if e!=nil{return e}
  if e=send(probe);e!=nil{fmt.Println("B95_NATIVE_SOCKET_SEND_FAIL",mode,probe,e);probeErr=errors.Join(probeErr,e);continue}
  if e=b91WaitTX(ctx,tx,before);e!=nil{
   fmt.Println("B95_NATIVE_SOCKET_TX_FAIL",mode,probe,e)
   if pulse!=nil{v,err:=pulse();fmt.Printf("B97_NATIVE_PULSE mode=%s tun=%d rejected=%d raw=%d txerr=%d tx=%d udp=%d err=%v\n",mode,v.TunIPv4Admitted,v.TunIPv4Rejected,v.BusinessRawCopied,v.TxErrors,v.TxRecords,v.TunUDPSeen,err)}
   if fecCounters!=nil{v,err:=fecCounters();fmt.Println("B97_FEC_COUNTERS_FAIL",mode,v,err)}
   probeErr=errors.Join(probeErr,e);continue
  }
  fmt.Println("B95_NATIVE_SOCKET_TX_PASS",mode,probe)
 }
 if fecCounters!=nil{
  before,e:=fecCounters();if e!=nil{return errors.Join(probeErr,e)}
  e=send("burst4")
  if e!=nil{probeErr=errors.Join(probeErr,e)}else{
   deadline:=time.Now().Add(6*time.Second)
   var after [9]uint64
   for time.Now().Before(deadline){
    after,e=fecCounters();if e!=nil{return errors.Join(probeErr,e)}
    if after[0]>=before[0]+32&&after[1]>before[1]{break}
    select{case <-ctx.Done():return errors.Join(probeErr,ctx.Err());case <-time.After(50*time.Millisecond):}
   }
   fmt.Printf("B97_FEC_BURST_COUNTERS mode=%s source_before=%d source_after=%d parity_before=%d parity_after=%d mature=%d applied=%d\n",mode,before[0],after[0],before[1],after[1],after[7],after[8])
   if after[0]>=before[0]+32&&after[1]>before[1]&&after[7]==0&&after[8]==0{
    fmt.Println("B97_FEC_SOURCE_PARITY_PASS",mode,"remote_m2_NOT_PROVEN")
   }else{probeErr=errors.Join(probeErr,fmt.Errorf("FEC source/parity burst or pending evidence incomplete"))}
  }
 }
 if probeErr!=nil{return probeErr}
 fmt.Println("B91_NATIVE_APP_TX_PASS",mode,"remote_m4_NOT_PROVEN")
 return nil
}
