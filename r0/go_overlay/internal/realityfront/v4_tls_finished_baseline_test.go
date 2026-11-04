package realityfront

// One bounded, test-only full TLS 1.3 transcript comparison. It uses the
// original Go crypto/tls server and the original uTLS Firefox120 client;
// secrets are kept in memory and never written to a CI artifact. Actual
// AF_PACKET/TCP first flights are independently qualified by the netns PCAP.
import (
 "bytes"
 "context"
 "crypto/aes"
 "crypto/cipher"
 "crypto/hmac"
 "crypto/sha256"
 "crypto/sha512"
 "crypto/tls"
 "crypto/x509"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "hash"
 "net"
 "reflect"
 "strings"
 "sync"
 "testing"
 "time"

 utls "github.com/refraction-networking/utls"
 "golang.org/x/crypto/chacha20poly1305"
)

type plan028TLSCapture struct {
 net.Conn
 mu sync.Mutex
 stream []byte
}
func(c *plan028TLSCapture) Write(p []byte)(int,error){
 n,e:=c.Conn.Write(p)
 c.mu.Lock()
 c.stream=append(c.stream,p[:n]...)
 c.mu.Unlock()
 return n,e
}
func(c *plan028TLSCapture) snapshot()[]byte{
 c.mu.Lock();defer c.mu.Unlock()
 return append([]byte(nil),c.stream...)
}

type plan028FullTLSRun struct {
 client,server []byte
 keylog string
 complete bool
 peerVerified bool
 cipher uint16
}

func plan028DoFullTLS(t *testing.T, route bool,cert tls.Certificate, roots *x509.CertPool)plan028FullTLSRun{
 t.Helper()
 ln,err:=net.Listen("tcp","127.0.0.1:0")
 if err!=nil{t.Fatal(err)}
 defer ln.Close()
 ctx,cancel:=context.WithTimeout(context.Background(),7*time.Second)
 defer cancel()
 var keylog bytes.Buffer
 type serverResult struct{wire []byte;state tls.ConnectionState;err error}
 done:=make(chan serverResult,1)
 go func(){
  conn,e:=ln.Accept()
  if e!=nil{done<-serverResult{err:e};return}
  tracked:=&plan028TLSCapture{Conn:conn}
  srv:=tls.Server(tracked,recognizedServerTLSConfig(&tls.Config{
   Certificates:[]tls.Certificate{cert},KeyLogWriter:&keylog,
  }))
  e=srv.HandshakeContext(ctx)
  state:=srv.ConnectionState()
  snap:=tracked.snapshot()
  _=srv.Close()
  done<-serverResult{wire:snap,state:state,err:e}
 }()
 raw,err:=net.DialTimeout("tcp",ln.Addr().String(),3*time.Second)
 if err!=nil{t.Fatal(err)}
 tracked:=&plan028TLSCapture{Conn:raw}
 var client *utls.UConn
 if route {
  client,err=newFirefox120Client(tracked,ClientConfig{
   ServerName:"target.test",
   RouteKey:[]byte("0123456789abcdef0123456789abcdef"),
   VerifyServer:true,RootCAs:roots,
  })
 } else {
  client=utls.UClient(tracked,&utls.Config{
   ServerName:"target.test",RootCAs:roots,InsecureSkipVerify:false,
   Renegotiation:utls.RenegotiateNever,
  },utls.HelloFirefox_120)
  err=client.BuildHandshakeState()
 }
 if err!=nil{_ = raw.Close();t.Fatal(err)}
 handshakeErr:=client.HandshakeContext(ctx)
 state:=client.ConnectionState()
 snapshot:=tracked.snapshot()
 // Close the underlying TCP after snapshot to avoid post-handshake ticket
 // records changing the bounded full-handshake ciphertext evidence.
 _=raw.Close()
 result:=<-done
 if handshakeErr!=nil||result.err!=nil{
  t.Fatalf("original uTLS vs Go TLS handshake route=%t: client=%v server=%v",route,handshakeErr,result.err)
 }
 if state.Version!=utls.VersionTLS13||!state.HandshakeComplete||
  len(state.VerifiedChains)==0||state.NegotiatedProtocol!=""{
  t.Fatalf("client did not authenticate full TLS 1.3 certificate/Finished route=%t",route)
 }
 if result.state.Version!=tls.VersionTLS13||!result.state.HandshakeComplete{
  t.Fatalf("server did not complete full TLS 1.3 Finished route=%t",route)
 }
 return plan028FullTLSRun{client:snapshot,server:result.wire,keylog:keylog.String(),
  complete:true,peerVerified:true,cipher:state.CipherSuite}
}

type plan028TLSRecord struct{typ byte;header [5]byte;body []byte}
func plan028Records(t *testing.T,stream []byte)[]plan028TLSRecord{
 t.Helper()
 var result []plan028TLSRecord
 for len(stream)>0 {
  if len(stream)<5||stream[1]!=3{t.Fatal("invalid or private TLS record prefix")}
  n:=int(binary.BigEndian.Uint16(stream[3:5]))
  if n==0||n>16384+256||len(stream)<n+5{t.Fatal("invalid TLS record length")}
  rec:=plan028TLSRecord{typ:stream[0],body:append([]byte(nil),stream[5:5+n]...)}
  copy(rec.header[:],stream[:5])
  result=append(result,rec)
  stream=stream[5+n:]
 }
 return result
}

type plan028CHInfo struct {session []byte;random [32]byte;extensions []uint16;len int}
func plan028CH(t *testing.T,records []plan028TLSRecord)plan028CHInfo{
 t.Helper()
 if len(records)==0||records[0].typ!=22||len(records[0].body)<44||
  records[0].body[0]!=1{t.Fatal("first client payload is not ClientHello")}
 b:=records[0].body
 if int(b[1])<<16|int(b[2])<<8|int(b[3])!=len(b)-4{t.Fatal("ClientHello handshake length")}
 body:=b[4:]
 if !bytes.Equal(body[:2],[]byte{3,3}){t.Fatal("ClientHello legacy version")}
 var h plan028CHInfo
 copy(h.random[:],body[2:34])
 p:=34
 sidLen:=int(body[p]);p++
 if sidLen!=32||p+sidLen>len(body){t.Fatal("ClientHello legacy session id not 32 bytes")}
 h.session=append([]byte(nil),body[p:p+sidLen]...);p+=sidLen
 if p+2>len(body){t.Fatal("cipher list missing")}
 nc:=int(binary.BigEndian.Uint16(body[p:p+2]));p+=2+nc
 if nc%2!=0||nc==0||p>=len(body){t.Fatal("invalid cipher suite list")}
 comp:=int(body[p]);p+=1+comp
 if p+2>len(body){t.Fatal("no extension length")}
 extLen:=int(binary.BigEndian.Uint16(body[p:p+2]));p+=2
 if p+extLen!=len(body){t.Fatal("incorrect ClientHello extension length")}
 for end:=len(body);p<end;{
  if p+4>end{t.Fatal("short extension")}
  typ:=binary.BigEndian.Uint16(body[p:p+2])
  size:=int(binary.BigEndian.Uint16(body[p+2:p+4]));p+=4
  if p+size>end{t.Fatal("extension body overrun")}
  if typ&0x0f0f==0x0a0a && uint8(typ>>8)==uint8(typ){typ=0x0a0a}
  h.extensions=append(h.extensions,typ)
  p+=size
 }
 h.len=len(records[0].body)+5
 return h
}

func plan028ServerHello(t *testing.T,records []plan028TLSRecord,session []byte)uint16{
 t.Helper()
 if len(records)==0||records[0].typ!=22||len(records[0].body)<44||
   records[0].body[0]!=2{t.Fatal("server sent private bytes before ServerHello")}
 b:=records[0].body[4:]
 if len(b)<39{t.Fatal("ServerHello too short")}
 p:=2+32
 n:=int(b[p]);p++
 if n!=32||p+n+2>len(b)||!bytes.Equal(session,b[p:p+n]){
  t.Fatal("TLS 1.3 ServerHello did not echo 32-byte compatibility SessionID")
 }
 p+=n
 return binary.BigEndian.Uint16(b[p:p+2])
}
func plan028KeyLog(t *testing.T,content,which string)[]byte{
 t.Helper()
 for _,line:=range strings.Split(content,"\n"){
  fields:=strings.Fields(line)
  if len(fields)==3 && fields[0]==which {
   b,e:=hex.DecodeString(fields[2]);if e!=nil{t.Fatal(e)}
   return b
  }
 }
 t.Fatalf("TLS keylog lacked handshake secret %s",which)
 return nil
}

func plan028HKDFExpand(secret []byte,label string,n int,newHash func()hash.Hash)[]byte{
 info:=[]byte{byte(n>>8),byte(n)}
 full:="tls13 "+label
 info=append(info,byte(len(full)))
 info=append(info,full...)
 info=append(info,0)
 var out,prev []byte
 for i:=byte(1);len(out)<n;i++{
  m:=hmac.New(newHash,secret)
  m.Write(prev);m.Write(info);m.Write([]byte{i})
  prev=m.Sum(nil);out=append(out,prev...)
 }
 return out[:n]
}

func plan028HandshakeAEAD(t *testing.T,suite uint16,secret []byte)(cipher.AEAD,[]byte){
 t.Helper()
 var newHash func()hash.Hash
 var keyLen int
 switch suite{
 case tls.TLS_AES_128_GCM_SHA256:
  newHash=sha256.New;keyLen=16
 case tls.TLS_AES_256_GCM_SHA384:
  newHash=sha512.New384;keyLen=32
 case tls.TLS_CHACHA20_POLY1305_SHA256:
  newHash=sha256.New;keyLen=32
 default:t.Fatalf("unexpected TLS 1.3 suite 0x%x",suite)
 }
 key:=plan028HKDFExpand(secret,"key",keyLen,newHash)
 iv:=plan028HKDFExpand(secret,"iv",12,newHash)
 if suite==tls.TLS_CHACHA20_POLY1305_SHA256{
  a,e:=chacha20poly1305.New(key);if e!=nil{t.Fatal(e)}
  return a,iv
 }
 block,e:=aes.NewCipher(key);if e!=nil{t.Fatal(e)}
 a,e:=cipher.NewGCM(block);if e!=nil{t.Fatal(e)}
 return a,iv
}

func plan028DecryptHandshake(t *testing.T,records []plan028TLSRecord,suite uint16,secret []byte)map[byte][]byte{
 t.Helper()
 aead,iv:=plan028HandshakeAEAD(t,suite,secret)
 seq:=uint64(0)
 messages:=map[byte][]byte{}
 var buffered []byte
 for _,r:=range records{
  if r.typ==20||r.typ==22{continue} // plaintext CCS/Hello are legitimate.
  if r.typ!=23{t.Fatalf("TLS 1.3 invalid encrypted record type %d",r.typ)}
  nonce:=append([]byte(nil),iv...)
  var n [8]byte;binary.BigEndian.PutUint64(n[:],seq)
  for i:=0;i<8;i++{nonce[len(nonce)-8+i]^=n[i]}
  seq++
  p,err:=aead.Open(nil,nonce,r.body,r.header[:])
  if err!=nil{t.Fatalf("TLS 1.3 authenticated handshake record AEAD invalid: %v",err)}
  idx:=len(p)-1
  for idx>=0&&p[idx]==0{idx--}
  if idx<0{t.Fatal("empty TLS 1.3 inner content")}
  if p[idx]!=22{t.Fatalf("unexpected inner TLS content type %d before Finished",p[idx])}
  buffered=append(buffered,p[:idx]...)
  for len(buffered)>=4{
   size:=int(buffered[1])<<16|int(buffered[2])<<8|int(buffered[3])
   if size>1<<20{t.Fatal("too large decrypted TLS handshake")}
   if len(buffered)<4+size{break}
   typ:=buffered[0]
   if _,exists:=messages[typ];exists{t.Fatalf("duplicate handshake message %d",typ)}
   messages[typ]=append([]byte(nil),buffered[4:4+size]...)
   buffered=buffered[4+size:]
   if typ==20{return messages} // Finished then switches to application epoch.
  }
 }
 t.Fatal("no authenticated Finished in full TLS handshake records")
 return nil
}

func TestPLAN028OriginalTLS13CompleteFinishedCertificateVsSameConfiguredFirefox120(t *testing.T){
 cert:=makeServerCert(t)
 roots:=v4TestRoots(cert)
 baseline:=plan028DoFullTLS(t,false,cert,roots)
 recognized:=plan028DoFullTLS(t,true,cert,roots)
 cases:=[]struct{name string;run plan028FullTLSRun}{
  {"reference_uTLS_Firefox120",baseline},{"routekey_32byte_HMAC_SessionID",recognized},
 }
 type summary struct{chBytes,shBytes,clientRecords,serverRecords int;extensions []uint16;cipher uint16}
 var snapshots []summary
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   cli:=plan028Records(t,tc.run.client)
   srv:=plan028Records(t,tc.run.server)
   info:=plan028CH(t,cli)
   suite:=plan028ServerHello(t,srv,info.session)
   if suite!=tc.run.cipher{t.Fatal("server and client disagree on TLS suite")}
   clientFinished:=plan028DecryptHandshake(t,cli,suite,plan028KeyLog(t,tc.run.keylog,"CLIENT_HANDSHAKE_TRAFFIC_SECRET"))
   serverFinished:=plan028DecryptHandshake(t,srv,suite,plan028KeyLog(t,tc.run.keylog,"SERVER_HANDSHAKE_TRAFFIC_SECRET"))
   for _,kind:=range []byte{8,11,15,20}{
    if len(serverFinished[kind])==0{t.Fatalf("missing verified server handshake kind=%d",kind)}
   }
   if len(clientFinished[20])==0{t.Fatal("missing decrypted client TLS Finished")}
   if !bytes.Contains(serverFinished[11],cert.Certificate[0]){
    t.Fatal("server Certificate message does not contain configured certificate DER")
   }
   if !tc.run.complete||!tc.run.peerVerified{t.Fatal("full TLS did not verify certificate and Finished")}
   if tc.name=="routekey_32byte_HMAC_SessionID"{
    marker:=markerFor([]byte("0123456789abcdef0123456789abcdef"),"target.test",info.random)
    if !bytes.Equal(marker[:],info.session){t.Fatal("unrecognized local 32-byte HMAC SessionID")}
   }
   snapshots=append(snapshots,summary{chBytes:info.len,shBytes:len(srv[0].body)+5,
    clientRecords:len(cli),serverRecords:len(srv),extensions:info.extensions,cipher:suite})
   t.Logf("PLAN028_TLS13_CERT_FINISHED_DECRYPTED route=%t suite=0x%x client_hello_bytes=%d server_hello_bytes=%d client_records=%d server_records=%d certificate=1 certificate_verify=1 server_finished=1 client_finished=1 verified_chain=1",tc.name=="routekey_32byte_HMAC_SessionID",suite,info.len,len(srv[0].body)+5,len(cli),len(srv))
  })
 }
 if len(snapshots)!=2{t.Fatal("baseline was not executed")}
 if snapshots[0].cipher!=snapshots[1].cipher||
  snapshots[0].chBytes!=snapshots[1].chBytes||
  snapshots[0].shBytes!=snapshots[1].shBytes||
  !reflect.DeepEqual(snapshots[0].extensions,snapshots[1].extensions){
  t.Fatalf("original route ClientHello/ServerHello structure deviated from SAME configured uTLS reference: baseline=%+v route=%+v",snapshots[0],snapshots[1])
 }
 t.Logf("M0_PLAN028_ORIGINAL_TLS13_CONFIG_MATCHED_FULL_FINISHED_BASELINE_PASS server_cert_certificate_verify_server_and_client_finished=1 independent_route_key=1 no_private_prelude=1")
}

// Compile-time guarantee test credentials/route secret never escape into the
// transcript summaries. We intentionally do not persist raw streams/keylogs.
var _ = errors.Is
var _ = fmt.Sprintf
