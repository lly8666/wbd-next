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
func b91NewPair(parent context.Context,flow faketcp.ClientFlow,ordinal int)(*b91Pair,error){
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
 p.server,e=faketcp.NewServerAssociation(syn,uint32(500000+ordinal*10000),time.Second,emit(s2c))
 if e!=nil{return fail(e)}
 synack,e:=p.server.SYNACKSegment();if e!=nil{return fail(e)}
 if e=p.client.HandleSegment(synack,time.Now());e!=nil{return fail(e)}
 select{case ack:=<-c2s:if _,e=p.server.HandleSegment(ack,time.Now());e!=nil{return fail(e)}
 case <-ctx.Done():return fail(ctx.Err())}
 if e=p.client.WaitEstablished(ctx);e!=nil{return fail(e)}
 p.wg.Add(2)
 go func(){defer p.wg.Done();for{select{
 case seg:=<-c2s:_,_=p.server.HandleSegment(seg,time.Now())
 case <-ctx.Done():return
 }}}()
 go func(){defer p.wg.Done();for{select{
 case seg:=<-s2c:_=p.client.HandleSegment(seg,time.Now())
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
func B91RunNativeCI(ctx context.Context,local,peer netip.Addr,normal V4LinuxClientProductConfig,game V4AndroidGameConfig,mode string,recordLimit uint16,
 route func(string)(func()error,error),send func()error)(ret error){
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
  p,e:=b91NewPair(ctx,flow,i);if e!=nil{return e}
  pairs=append(pairs,p);assocs=append(assocs,p.client)
  p.wg.Add(1)
  go func(p *b91Pair){
   defer p.wg.Done()
   _,e:=EstablishServerV4(ctx,p.server,ServerAdmissionConfig{
    TLS:ServerConfig{ServerName:"target.test",RouteKey:routeKey,TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:15*time.Second},
    ExpectedUsername:"b91-ci",ExpectedPassword:"b91-fixture",ServerLimit:recordLimit,
    AllocateLease:func(req AdmissionRequest)(string,error){return V4AllocateAutomaticLease(leases,req)},
   },V4ServerOptions{DataPlaneReady:true,Epochs:store,perClientMixedMode:true})
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
  }
  tx=func()(uint64,error){v,e:=p.OriginalLoopPulse();return v.BusinessRawCopied,e}
 }else{
  p,e:=NewV4AndroidGameProduct(game);if e!=nil{return e}
  lease,e=p.ConnectAuthenticatedGame(ctx,assocs,cfg);if e!=nil{return e}
  closeProduct=p.Close
  defer func(){stop:=closeProduct();ret=errors.Join(ret,stop);if stop==nil{fmt.Println("B91_NATIVE_STOP_PASS",mode)}}()
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
 before,e:=tx();if e!=nil{return e}
 if e=send();e!=nil{return e}
 if e=b91WaitTX(ctx,tx,before);e!=nil{return e}
 fmt.Println("B91_NATIVE_APP_TX_PASS",mode,"remote_m4_NOT_PROVEN")
 return nil
}
