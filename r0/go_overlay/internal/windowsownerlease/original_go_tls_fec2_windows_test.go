//go:build windows && wbd_v4_embedded_go
package windowsownerlease

// PLAN024: actual original Go protected credential FakeTCP/TLS feature7
// -> native Rust M3 FEC source authenticated sender/receiver
// -> M4-created signed Wintun kernel -> real Windows UDP application.
// No M2 SetTxFec verified Applied ACK or host-global OS grant is implied.
import (
 "context"
 "crypto/tls"
 "errors"
 "fmt"
 "os"
 "testing"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
func m0PLAN024WindowsRealOriginalGoFEC2(t *testing.T,mode string,port uint16){
 t.Helper()
 dll:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
 if dll==""{t.Fatal("source-locked Windows native Rust DLL missing")}
 if !m0NativeWintunAvailable(t){t.Fatal("official signed Wintun unavailable for positive original FEC2 test")}
 ctx,cancel:=context.WithTimeout(context.Background(),55*time.Second)
 defer cancel()
 routeKey:=[]byte("0123456789abcdef0123456789abcdef")
 flow:=faketcp.ClientFlow{LocalIP:[4]byte{10,88,0,2},
  PeerIP:[4]byte{10,88,0,1},LocalPort:port,PeerPort:443}
 toServer:=make(chan faketcp.Segment,4096)
 toClient:=make(chan faketcp.Segment,4096)
 emit:=func(ch chan<- faketcp.Segment)faketcp.SegmentEmitter{
  return func(seg faketcp.Segment)error{
   seg.Payload=append([]byte(nil),seg.Payload...)
   select{case ch<-seg:return nil
   default:return errors.New("bounded protected TCP segment queue full")}
  }
 }
 client,e:=faketcp.NewClientAssociation(flow,123456,time.Second,emit(toServer))
 if e!=nil{t.Fatal(e)}
 defer client.Close()
 if e=client.Start(time.Now());e!=nil{t.Fatal(e)}
 syn:=<-toServer
 server,e:=faketcp.NewServerAssociation(syn,31337,time.Second,emit(toClient))
 if e!=nil{t.Fatal(e)}
 defer server.Close()
 synack,e:=server.SYNACKSegment()
 if e!=nil{t.Fatal(e)}
 if e=client.HandleSegment(synack,time.Now());e!=nil{t.Fatal(e)}
 ack:=<-toServer
 if _,e=server.HandleSegment(ack,time.Now());e!=nil{t.Fatal(e)}
 routerDone:=make(chan struct{})
 defer close(routerDone)
 routerErr:=make(chan error,1)
 sendErr:=func(err error){if err!=nil{select{case routerErr<-err:default:}}}
 go func(){
  for{
   select{
   case <-routerDone:return
   case seg:=<-toServer:
    got,err:=server.HandleSegment(seg,time.Now())
    if err!=nil{sendErr(err);return}
    if got.AckNeeded{sendErr(emit(toClient)(server.ACKSegment(got.Ack)))}
   case seg:=<-toClient:
    if err:=client.HandleSegment(seg,time.Now());err!=nil{sendErr(err);return}
   }
  }
 }()
 store,e:=realityfront.NewV4EpochStore(1)
 if e!=nil{t.Fatal(e)}
 policy,e:=realityfront.PolicyForClientWithInitialAndCipher(
  1,mode,4,0,20,realityfront.CipherChaCha)
 if e!=nil{t.Fatalf("original Go policy=%s: %v",mode,e)}
 type response struct{
  session *realityfront.V4ServerSession
  owner *realityfront.V4WindowsAuthenticatedServerOwner
  err error
 }
 answer:=make(chan response,1)
 go func(){
  owner,session,err:=realityfront.V4WindowsEstablishOriginalFEC2ServerOwner(
   ctx,dll,server,realityfront.ServerAdmissionConfig{
    TLS:realityfront.ServerConfig{
     ServerName:"target.test",RouteKey:routeKey,
     TLSConfig:&tls.Config{Certificates:[]tls.Certificate{m0WinJoinCert(t)}},
     Timeout:6*time.Second,
    },
    ExpectedUsername:"protected-owner",ExpectedPassword:"secret",
    ServerLimit:1400,
   },realityfront.V4ServerOptions{DataPlaneReady:true,Epochs:store})
  answer<-response{session:session,owner:owner,err:err}
 }()
 owner,session,clientErr:=realityfront.V4WindowsEstablishOriginalFEC2ClientOwner(
  ctx,dll,client,realityfront.ClientAdmissionConfig{
   TLS:realityfront.ClientConfig{ServerName:"target.test",
    RouteKey:routeKey,Timeout:6*time.Second},
   Username:"protected-owner",Password:"secret",
   TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,
   LaneID:1,DesiredLanes:1,Policy:policy,
  })
 var peer response
 select{
 case peer=<-answer:
 case <-ctx.Done():t.Fatalf("original TLS native FEC %s peer timeout: %v",mode,ctx.Err())
 }
 if clientErr!=nil||peer.err!=nil||owner==nil||session==nil||
    peer.owner==nil||peer.session==nil{
  var linkErr error
  select{case linkErr=<-routerErr:default:}
  t.Fatalf("original Go TLS FEC2 %s owner client=%v server=%v fakeTCP=%v",
   mode,clientErr,peer.err,linkErr)
 }
 if session.Epoch==[16]byte{}||session.Epoch!=peer.session.Epoch{
  t.Fatal("original Go TLS FEC2 epoch mismatch")
 }
 tun,e:=windowsclient.OpenTUN(fmt.Sprintf("WBD-M0-FEC2-%s-%s",mode,os.Getenv("GITHUB_RUN_ID")))
 if e!=nil{t.Fatalf("created signed Wintun for true FEC2: %v",e)}
 defer tun.Close()
 device:=CreatedWintun{TUN:tun}
 identity,e:=device.Identity(ctx,[16]byte{17},session.Epoch)
 if e!=nil{t.Fatalf("real device identity: %v",e)}
 if e:=owner.BindOriginalM4NativeDevice(ctx,device,identity);e!=nil{
  t.Fatalf("FEC2 client original TLS->Rust real Wintun hold: %v",e)
 }
 if e:=peer.owner.BindOriginalM4NativeDevice(ctx,device,identity);e!=nil{
  t.Fatalf("FEC2 server original TLS->Rust real Wintun hold: %v",e)
 }
 outbound:=m0OriginalTLSRustAEADKernelUDP([]byte("original-FEC2-"+mode),41090)
 wire,seq,pn,e:=owner.SealBoundOriginalFEC2Source(ctx,1,0,outbound)
 if e!=nil||pn!=0||len(wire)==0{
  t.Fatalf("original feature7 Rust source AEAD mode %s pn%d: %v",mode,pn,e)
 }
 fromKernel:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,wire)
 delivered,e:=peer.owner.OpenBoundOriginalFEC2(ctx,seq,fromKernel)
 if e!=nil||len(delivered)!=1||string(delivered[0].IPv4)!=string(outbound)||
  delivered[0].Recovered{
  t.Fatalf("same-original-credential Rust FEC2 first delivery %s: %+v %v",mode,delivered,e)
 }
 if replay,err:=peer.owner.OpenBoundOriginalFEC2(ctx,seq,fromKernel);err==nil{
  t.Fatalf("original FEC2 %s duplicate PN delivered %d frames",mode,len(replay))
 }
 reverse:=m0OriginalTLSRustAEADKernelUDP([]byte("real-reverse-FEC2-"+mode),41091)
 reverseWire,reverseSeq,_,e:=peer.owner.SealBoundOriginalFEC2Source(ctx,2,0,reverse)
 if e!=nil{t.Fatalf("original server FEC2 seal %s: %v",mode,e)}
 reverseFromKernel:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,reverseWire)
 recv,e:=owner.OpenBoundOriginalFEC2(ctx,reverseSeq,reverseFromKernel)
 if e!=nil||len(recv)!=1||string(recv[0].IPv4)!=string(reverse){
  t.Fatalf("client original Go TLS Rust FEC2 reverse %s: %+v %v",mode,recv,e)
 }
 stopCtx,stopCancel:=context.WithTimeout(context.Background(),12*time.Second)
 defer stopCancel()
 if e:=owner.StopScopedOwner(stopCtx);e!=nil{t.Fatalf("client FEC2 native Stop %s: %v",mode,e)}
 if e:=peer.owner.StopScopedOwner(stopCtx);e!=nil{t.Fatalf("server FEC2 native Stop %s: %v",mode,e)}
 if _,_,_,e:=owner.SealBoundOriginalFEC2Source(ctx,3,0,outbound);e==nil{
  t.Fatalf("FEC2 after Stop accepted source %s",mode)
 }
 t.Logf("M0_PLAN024_ORIGINAL_GO_TLS_WINDOWS_FEC2_%s_RUST_M3_SIGNED_WINTUN_KERNEL_UDP_APP_FIRST_REVERSE_PASS_SCOPED m2_applied=NOT_RUN host_wfp=NOT_RUN",mode)
}
func TestM0PLAN024WindowsRealOriginalGoFEC2FixedAutoSignedWintunFirstReverse(t *testing.T){
 for i,mode:=range []string{"fixed","auto"}{
  t.Run(mode,func(t *testing.T){
   m0PLAN024WindowsRealOriginalGoFEC2(t,mode,uint16(41801+i))
  })
 }
}
