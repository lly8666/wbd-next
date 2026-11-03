package realityfront

import (
 "bytes"
 "context"
 "crypto/tls"
 "encoding/binary"
 "errors"
 "sync"
 "testing"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// The real FakeTCP original Go transport is captured at the packet-data
// boundary, not at an invented mock TLS handshake. This verifies TCP stream
// bytes, not a fixed IP segment count (segmentation is intentionally variable).
func TestPLAN028V4NoPreludeOriginalClientHelloFullCertificateAndSessionIDEpoch(t *testing.T) {
 key:=[]byte("0123456789abcdef0123456789abcdef")
 var previous []byte
 for lane:=uint8(1);lane<=4;lane++ {
  cert:=makeServerCert(t)
  assoc,peer:=newAssociationPeer(t)
  var mu sync.Mutex
  var observed []string
  var capture p2WireCapture
  peer.onClientPayload=func(s faketcp.Segment){mu.Lock();observed=append(observed,"client");mu.Unlock();capture.addClient(s)}
  peer.onServerPayload=func(s faketcp.Segment){mu.Lock();observed=append(observed,"server");mu.Unlock();capture.addServer(s)}
  epochStore,e:=NewV4EpochStore(4);if e!=nil{t.Fatal(e)}
  type result struct{err error}
  done:=make(chan result,1)
  go func(){
   _,se:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
    TLS:ServerConfig{ServerName:"target.test",RouteKey:key,TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
    ExpectedUsername:"alice",ExpectedPassword:"password-only-inside-TLS",
    ServerLimit:1400,
   },V4ServerOptions{DataPlaneReady:true,Epochs:epochStore})
   done<-result{se}
  }()
  _,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
   TLS:ClientConfig{ServerName:"target.test",RouteKey:key,RootCAs:v4TestRoots(cert),Timeout:3*time.Second},
   Username:"alice",Password:"password-only-inside-TLS",TunnelID:[]byte("same-install-001"),
   ClientLimit:1400,LaneID:lane,Policy:v4TestPolicy(4,CipherChaCha),
  },V4ClientOptions{DataPlaneReady:true})
  se:=<-done
  if ce!=nil||se.err!=nil{t.Fatalf("lane%d verified TLS/auth: client=%v server=%v",lane,ce,se.err)}
  cs,ss:=capture.snapshot()
  if len(cs)==0||len(ss)==0{t.Fatalf("lane%d no wire capture",lane)}
  cli:=assertHostedWireDirection(t,"client",cs)
  srv:=assertHostedWireDirection(t,"server",ss)
  assertTLSRecordStream(t,"client",cli)
  assertTLSRecordStream(t,"server",srv)
  if len(cli)<50||cli[0]!=22||cli[1]!=3||cli[5]!=1||bytes.HasPrefix(cli,[]byte("WB-R1")){
   t.Fatalf("lane%d first client payload is not a genuine TLS ClientHello",lane)
  }
  if len(srv)<6||srv[0]!=22||srv[1]!=3||srv[5]!=2{
   t.Fatalf("lane%d first server payload is not ServerHello",lane)
  }
  mu.Lock();first:=observed[0];mu.Unlock()
  if first!="client"{t.Fatalf("lane%d server sent payload before ClientHello",lane)}
  recordLen:=int(binary.BigEndian.Uint16(cli[3:5]))
  if recordLen<38||len(cli)<recordLen+5{t.Fatalf("lane%d malformed TLS record length %d",lane,recordLen)}
  // RFC8446 legacy_version(2), random(32), legacy_session_id length.
  base:=5+4+2
  var random [32]byte;copy(random[:],cli[base:base+32])
  sidOffset:=base+32
  if cli[sidOffset]!=32||sidOffset+1+32>len(cli){
   t.Fatalf("lane%d compatibility SessionID is not 32B",lane)
  }
  marker:=markerFor(key,"target.test",random)
  sid:=cli[sidOffset+1:sidOffset+33]
  if !bytes.Equal(sid,marker[:])||bytes.Equal(sid,previous){
   t.Fatalf("lane%d non-random/unrecognized SessionID",lane)
  }
  previous=append([]byte(nil),sid...)
  if bytes.Contains(cli,[]byte("password-only-inside-TLS"))||
     bytes.Contains(srv,[]byte("password-only-inside-TLS")){
   t.Fatalf("lane%d credential leaked before protected admission",lane)
  }
  // TestFirefox120PersonaKeepsPresetAndRouteMarker compares the same uTLS
  // preset's complete ordered extensions with unmodified Firefox120.
  t.Logf("PLAN028_STANDARD_TLS_WIRE lane=%d client_hello_record_bytes=%d server_first_record_bytes=%d session_id=32 source=real_faketcp",lane,recordLen+5,int(binary.BigEndian.Uint16(srv[3:5]))+5)
  peer.Close();assoc.Close()
 }
}

func TestPLAN028V4NoRouteKeyRejectsLocallyWithoutNetworkReadWrite(t *testing.T) {
 assoc,peer:=newAssociationPeer(t)
 defer assoc.Close();defer peer.Close()
 count:=0
 peer.onClientPayload=func(faketcp.Segment){count++}
 store,e:=NewV4EpochStore(2);if e!=nil{t.Fatal(e)}
 _,err:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
  TLS:ClientConfig{ServerName:"target.test",Timeout:time.Second},
  Username:"alice",Password:"pass",TunnelID:[]byte("same-install-001"),
  ClientLimit:1400,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
 },V4ClientOptions{DataPlaneReady:true})
 if !errors.Is(err,ErrAdmissionParams)||count!=0{t.Fatalf("missing key performed traffic: err=%v sends=%d",err,count)}
 _,err=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
  TLS:ServerConfig{ServerName:"target.test",Timeout:time.Second},
  ExpectedUsername:"alice",ExpectedPassword:"pass",ServerLimit:1400,
 },V4ServerOptions{DataPlaneReady:true,Epochs:store})
 if !errors.Is(err,ErrAdmissionParams){t.Fatalf("server accepted missing route-key: %v",err)}
}

func TestPLAN028V4WrongRouteKeyWrongCertAndWrongPasswordNoAdmission(t *testing.T) {
 goodKey:=[]byte("0123456789abcdef0123456789abcdef")
 wrongKey:=[]byte("abcdef0123456789abcdef0123456789")
 for _,tc:=range []struct{name string;wrongKey,wrongTrust,wrongPassword bool}{
  {"wrong_route_key",true,false,false},{"untrusted_server_certificate",false,true,false},{"wrong_protected_password",false,false,true},
 } {
  t.Run(tc.name,func(t *testing.T){
   cert:=makeServerCert(t)
   roots:=v4TestRoots(cert)
   if tc.wrongTrust{roots=v4TestRoots(makeServerCert(t))}
   assoc,peer:=newAssociationPeer(t)
   defer assoc.Close();defer peer.Close()
   store,e:=NewV4EpochStore(2);if e!=nil{t.Fatal(e)}
   called:=make(chan struct{},1)
   serverResult:=make(chan error,1)
   go func(){
    _,se:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
     TLS:ServerConfig{ServerName:"target.test",RouteKey:goodKey,TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:2*time.Second},
     ServerLimit:1400,
    },V4ServerOptions{DataPlaneReady:true,Epochs:store,
     Authenticate:func(user,password string)bool{select{case called<-struct{}{}:default:};return user=="alice"&&password=="correct"},
    })
    serverResult<-se
   }()
   key:=goodKey
   if tc.wrongKey{key=wrongKey}
   password:="correct";if tc.wrongPassword{password="incorrect"}
   _,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
    TLS:ClientConfig{ServerName:"target.test",RouteKey:key,RootCAs:roots,Timeout:2*time.Second},
    Username:"alice",Password:password,TunnelID:[]byte("same-install-001"),
    ClientLimit:1400,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
   },V4ClientOptions{DataPlaneReady:true})
   if ce==nil{t.Fatal("invalid route/certificate/password unexpectedly admitted")}
   <-serverResult
   calls:=len(called)
   if calls!=0 && !tc.wrongPassword{t.Fatal("password was disclosed to server before route/certificate validation")}
   if calls!=1 && tc.wrongPassword{t.Fatal("wrong protected password never reached authenticated TLS validation")}
  })
 }
}
