//go:build windows && wbd_v4_embedded_go
package windowsownerlease

// PLAN024: genuine original protected Go credential TLS, 2/4 independent
// authenticated Game lanes, native Rust GameAdapter AEAD+PN first delivery,
// M4-created signed Wintun OS UDP application and bounded Stop. A source
// record staged in Go is not a host WFP/route product Applied claim.
import(
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
func m0PLAN024WindowsRealGame(t *testing.T,n int){
 t.Helper()
 dll:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
 if dll==""{t.Fatal("original Go source-locked Rust owner DLL missing")}
 if !m0NativeWintunAvailable(t){t.Fatal("official signed Wintun required by real Game integration")}
 ctx,cancel:=context.WithTimeout(context.Background(),100*time.Second)
 defer cancel()
 routeKey:=[]byte("0123456789abcdef0123456789abcdef")
 clients:=make([]*faketcp.ClientAssociation,0,n)
 servers:=make([]*faketcp.ServerAssociation,0,n)
 routerDone:=make(chan struct{})
 defer close(routerDone)
 for i:=0;i<n;i++{
  flow:=faketcp.ClientFlow{
   LocalIP:[4]byte{10,98,0,2},PeerIP:[4]byte{10,98,0,1},
   LocalPort:uint16(42501+i),PeerPort:443,
  }
  toServer:=make(chan faketcp.Segment,4096)
  toClient:=make(chan faketcp.Segment,4096)
  emit:=func(ch chan<- faketcp.Segment)faketcp.SegmentEmitter{
   return func(seg faketcp.Segment)error{
    seg.Payload=append([]byte(nil),seg.Payload...)
    select{case ch<-seg:return nil
    default:return errors.New("bounded Game original Go TCP queue full")}
   }
  }
  client,e:=faketcp.NewClientAssociation(flow,uint32(123456+i),time.Second,emit(toServer))
  if e!=nil{t.Fatal(e)}
  defer client.Close()
  if e=client.Start(time.Now());e!=nil{t.Fatal(e)}
  syn:=<-toServer
  server,e:=faketcp.NewServerAssociation(syn,uint32(31337+i),time.Second,emit(toClient))
  if e!=nil{t.Fatal(e)}
  defer server.Close()
  synack,e:=server.SYNACKSegment()
  if e!=nil{t.Fatal(e)}
  if e=client.HandleSegment(synack,time.Now());e!=nil{t.Fatal(e)}
  ack:=<-toServer
  if _,e=server.HandleSegment(ack,time.Now());e!=nil{t.Fatal(e)}
  go func(){
   for{
    select{
    case <-routerDone:return
    case seg:=<-toServer:
     receipt,e:=server.HandleSegment(seg,time.Now())
     if e!=nil{return}
     if receipt.AckNeeded{_ = emit(toClient)(server.ACKSegment(receipt.Ack))}
    case seg:=<-toClient:
     if e:=client.HandleSegment(seg,time.Now());e!=nil{return}
    }
   }
  }()
  clients=append(clients,client)
  servers=append(servers,server)
 }
 epochs,e:=realityfront.NewV4EpochStore(16)
 if e!=nil{t.Fatal(e)}
 cert:=m0WinJoinCert(t)
 answer:=make(chan struct{
  group *realityfront.V4WindowsAuthenticatedGameServerGroup
  err error
 },1)
 go func(){
  server,err:=realityfront.V4WindowsEstablishOriginalGameServerGroup(
   ctx,dll,servers,realityfront.ServerAdmissionConfig{
    TLS:realityfront.ServerConfig{
     ServerName:"target.test",RouteKey:routeKey,
     TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},
     Timeout:8*time.Second,
    },
    ExpectedUsername:"protected-owner",ExpectedPassword:"secret",
    ServerLimit:1400,
   },epochs)
  answer<-struct{
   group *realityfront.V4WindowsAuthenticatedGameServerGroup
   err error
  }{server,err}
 }()
 policy,e:=realityfront.FixedPolicyForClient(n,0)
 if e!=nil{t.Fatal(e)}
 clientGroup,clientErr:=realityfront.V4WindowsEstablishOriginalGameClientGroup(
  ctx,dll,clients,realityfront.ClientAdmissionConfig{
   TLS:realityfront.ClientConfig{
    ServerName:"target.test",RouteKey:routeKey,Timeout:8*time.Second,
   },
   Username:"protected-owner",Password:"secret",
   TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,
   DesiredLanes:uint8(n),Policy:policy,
  })
 var answerValue struct{
  group *realityfront.V4WindowsAuthenticatedGameServerGroup
  err error
 }
 select{
 case answerValue=<-answer:
 case <-ctx.Done():t.Fatalf("original Go Game%d TLS group timeout: %v",n,ctx.Err())
 }
 if clientErr!=nil||answerValue.err!=nil||clientGroup==nil||answerValue.group==nil{
  t.Fatalf("Game%d real original-Go TLS→Rust group client=%v server=%v",
   n,clientErr,answerValue.err)
 }
 serverGroup:=answerValue.group
 tun,e:=windowsclient.OpenTUN(fmt.Sprintf("WBD-M0-GAME%d-%s",n,os.Getenv("GITHUB_RUN_ID")))
 if e!=nil{t.Fatalf("Game%d signed Wintun create: %v",n,e)}
 defer tun.Close()
 device:=CreatedWintun{TUN:tun}
 identity,e:=device.Identity(ctx,[16]byte{19},clientGroup.Epoch())
 if e!=nil{t.Fatal(e)}
 if e=clientGroup.BindAndJoinOriginalWintun(ctx,device,identity);e!=nil{
  t.Fatalf("Game%d original TLS Rust client 2/4 M4 native owner group: %v",n,e)
 }
 if e=serverGroup.BindAndJoinOriginalWintun(ctx,device,identity);e!=nil{
  t.Fatalf("Game%d original TLS Rust server 2/4 M4 native owner group: %v",n,e)
 }
 packet:=m0OriginalTLSRustAEADKernelUDP([]byte(fmt.Sprintf("game%d-real-original-Go-TLS",n)),41990)
 records,e:=clientGroup.StageGameRecords(ctx,packet)
 if e!=nil||len(records)!=n{t.Fatalf("Game%d native independent AEAD stage: %d %v",n,len(records),e)}
 // Native lane1 packet is deliberately NOT delivered; lane2 must reach
 // the original server's Rust first-delivery dedup after real OS kernel.
 lane2:=records[1]
 fromKernel:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,lane2.Wire)
 delivered,e:=serverGroup.OpenGameRecord(ctx,lane2.Lane,fromKernel)
 if e!=nil||string(delivered)!=string(packet){
  t.Fatalf("Game%d independent lane2 first-delivery no-HOL: %v %v",n,e,delivered)
 }
 if replay,err:=serverGroup.OpenGameRecord(ctx,lane2.Lane,fromKernel);err==nil{
  t.Fatalf("Game%d original M3 replay delivered %d bytes",n,len(replay))
 }
 reverse:=m0OriginalTLSRustAEADKernelUDP([]byte(fmt.Sprintf("game%d-native-reverse",n)),41991)
 backward,e:=serverGroup.StageGameRecords(ctx,reverse)
 if e!=nil||len(backward)!=n{t.Fatalf("Game%d original server reverse AEAD: %v",n,e)}
 lane:=backward[n-1]
 reverseFromKernel:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,lane.Wire)
 got,e:=clientGroup.OpenGameRecord(ctx,lane.Lane,reverseFromKernel)
 if e!=nil||string(got)!=string(reverse){
  t.Fatalf("Game%d original Go TLS Rust reverse first-delivery: %v",n,e)
 }
 stop,cancelStop:=context.WithTimeout(context.Background(),15*time.Second)
 defer cancelStop()
 if e=clientGroup.StopCryptoAfterDriverDrain(stop);e!=nil{t.Fatalf("Game%d client native Stop: %v",n,e)}
 if e=serverGroup.StopCryptoAfterDriverDrain(stop);e!=nil{t.Fatalf("Game%d server native Stop: %v",n,e)}
 if _,e=clientGroup.StageGameRecords(ctx,packet);e==nil{
  t.Fatalf("Game%d stale authenticated group accepted post Stop",n)
 }
 t.Logf("M0_PLAN024_ORIGINAL_GO_TLS_WINDOWS_GAME%d_NATIVE_RUST_M4_SIGNED_WINTUN_KERNEL_APP_LANE1_BLOCKED_FIRST_REVERSE_NO_HOL_STOP_PASS_SCOPED host_global_WFP_NOT_RUN=1",n)
}
func TestM0PLAN024WindowsRealOriginalGoGame2Game4SignedWintunFirstReverse(t *testing.T){
 for _,n:=range []int{2,4}{
  t.Run(fmt.Sprintf("game%d",n),func(t *testing.T){m0PLAN024WindowsRealGame(t,n)})
 }
}
