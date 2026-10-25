// Standalone (NOT PRODUCT) mixed AEAD/full fallback + public-PN-XOR wire lab.
// Genuine mutually authenticated TLS1.3 handshake on outer loopback TCP first,
// then deliberate raw TCP TLS-looking records. Those records are NOT RFC TLS.
// Fallback uses real Go AES-128-GCM AEAD; NOT the WBD Rust AEAD wire format.
// Trusted labels and classifier proof are test-only, not a live TLS DPI oracle.
package main

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math/big"
 "math/bits"
 "net"
 "os"
 "strconv"
 "time"
)

const innerPublicSNI="private.inner-wbd.example"
const mainPort uint16=50101
const safeBoundary uint32=18000
const pathMTU=1500
const underlayOverhead=40
const maxWireRecord=pathMTU-underlayOverhead
const labAeadOverhead=31
const delayMinMs=11000
const delayRangeMs=10001
type Spec struct{
 Label string
 Port uint16
 Seq uint32
 Proto byte
 Flags byte
 TrustedApp bool
 Boundary bool
 Stage string
 Inner []byte
}
type Receipt struct{
 Label string `json:"label"`
 PN uint64 `json:"pn"`
 Mode string `json:"mode"`
 WireBytes int `json:"wire_bytes"`
 InnerBytes int `json:"inner_bytes"`
 PlainSha256 string `json:"inner_sha256"`
 PaddingBytes int
 LifecycleBoundary bool
 Stage string
 ElapsedFromLastServerFlightMs int64
 PadSha256 string
}
type Manifest struct{
 Scope string `json:"scope"`
 InnerTLS13Genuine bool `json:"inner_tls13_genuine"`
 OuterMutualTLS13Genuine bool `json:"outer_mutual_tls13_genuine"`
 FinalServerHelloSeen bool `json:"final_server_hello_seen"`
 RealProductionClassifier bool `json:"real_production_classifier"`
 RealWbdAeadWire bool `json:"real_wbd_aead_wire"`
 AESFallbackTamperRejected bool `json:"aes_fallback_tamper_rejected"`
 PlaintextRoundtripAll bool `json:"plaintext_roundtrip_all"`
 ModeDowngradeRejectedInTestOracle bool `json:"mode_downgrade_rejected_in_test_oracle"`
 Records []Receipt `json:"records"`
 ChosenHoldMs int64
 ObservedFastElapsedMs int64
 MtuBytes int
 OuterIPTCPOverhead int
 PaddedRecords int
 UnpaddedRecords int
 PaddingBytesTotal int
 MTUMaxRecordObserved int
 LargeNoRoomFallback int
}

func fail(err error){if err!=nil{panic(err)}}
func packet(port uint16,seq uint32,proto byte,flags byte,data []byte)[]byte{
 n:=40+len(data);if n>1345{panic("excessive owned inner payload")}
 p:=make([]byte,n);p[0]=0x45;p[2]=byte(n>>8);p[3]=byte(n)
 p[6]=0x40;p[8]=64;p[9]=proto
 copy(p[12:20],[]byte{10,11,12,13,10,21,22,23})
 binary.BigEndian.PutUint16(p[20:22],port);binary.BigEndian.PutUint16(p[22:24],443)
 binary.BigEndian.PutUint32(p[24:28],seq)
 p[32]=0x50;p[33]=flags
 copy(p[40:],data)
 return p
}
func tlsRecordHeader(data []byte)bool{
 return len(data)>=5 && bytes.Equal(data[:3],[]byte{0x17,0x03,0x03})
}
// Trusted label is provided by the test harness, not derivable from visible
// TLS1.3 0x17; boundary check prevents old-range retransmit fast-path.
func gate(s Spec, verifiedServerHello bool, elapsedMs, holdMs int64)bool{
 if elapsedMs<holdMs{return false}
 if !verifiedServerHello||!s.TrustedApp||s.Port!=mainPort||s.Proto!=6||
    s.Seq<safeBoundary||len(s.Inner)<40+64||s.Flags&0x07!=0{return false}
 return tlsRecordHeader(s.Inner[40:])
}
func maskPnRepeat(b []byte,pn uint64){
 k:=bits.RotateLeft64(pn,17)^uint64(0x6c616e5f6e6f7365)
 i:=0
 for ;i+8<=len(b);i+=8{
  binary.LittleEndian.PutUint64(b[i:i+8],binary.LittleEndian.Uint64(b[i:i+8])^k)
 }
 for j:=0;i+j<len(b);j++{b[i+j]^=byte(k>>(8*j))}
}
type Coder struct{aead cipher.AEAD;iv [12]byte}
func newCoder()(Coder,error){
 var k [16]byte;var iv [12]byte
 if _,e:=rand.Read(k[:]);e!=nil{return Coder{},e}
 if _,e:=rand.Read(iv[:]);e!=nil{return Coder{},e}
 block,e:=aes.NewCipher(k[:]);if e!=nil{return Coder{},e}
 g,e:=cipher.NewGCM(block);if e!=nil{return Coder{},e}
 return Coder{g,iv},nil
}
func (c Coder)nonce(pn uint64)[]byte{
 n:=c.iv
 b:=make([]byte,8);binary.BigEndian.PutUint64(b,pn)
 for i:=0;i<8;i++{n[4+i]^=b[i]}
 return n[:]
}
// 5 header | 1 explicit LAB-ONLY mode byte | 8 clear PN |
// AES: encrypted(kind=0 | inner_ipv4) | 16B tag -> inner+31B
// XOR: masked(kind=0 | inner_ipv4) -> inner+15B.
// Mode is unauthenticated for XOR; authenticated in AES AAD. A real receiver
// needs secure capability/mode admission; this fixture assumes oracle identity.
// Authenticated original IPv4 bytes plus optional trailing random filler.
// Original IPv4 TotalLength stays intact; receiver trims after AES verifies.
// This LAB custom format is not the production WBD Rust wire protocol.
func (c Coder)seal(p []byte,mode byte,pn uint64,padLen int)([]byte,[]byte){
 if padLen<0||padLen>maxWireRecord-len(p)-labAeadOverhead{panic("MTU pad budget exceeded")}
 if mode==1&&padLen!=0{panic("fast path must not pad")}
 n:=len(p);used:=n+labAeadOverhead+padLen
 if mode==1{used=n+15}
 if used>maxWireRecord{panic("outer record exceeds MTU")}
 w:=make([]byte,used);copy(w[:3],[]byte{0x17,0x03,0x03})
 binary.BigEndian.PutUint16(w[3:5],uint16(used-5))
 w[5]=mode;binary.BigEndian.PutUint64(w[6:14],pn)
 body:=make([]byte,1+n+padLen);body[0]=0;copy(body[1:],p)
 var pad []byte
 if padLen>0{pad=body[1+n:];if _,e:=rand.Read(pad);e!=nil{panic(e)}}
 if mode==0{
  v:=c.aead.Seal(w[14:14],c.nonce(pn),body,w[:14])
  if len(v)!=used-14{panic("AEAD length mismatch")}
 }else if mode==1{copy(w[14:],body);maskPnRepeat(w[14:],pn)
 }else{panic("bad mode")}
 return w,pad
}
func (c Coder)open(w []byte,expectedMode byte)([]byte,uint64,int,error){
 if len(w)<15||!bytes.Equal(w[:3],[]byte{0x17,0x03,0x03})||
   int(binary.BigEndian.Uint16(w[3:5]))+5!=len(w)||len(w)>maxWireRecord{
  return nil,0,0,errors.New("bad outer framing or MTU")
 }
 if w[5]!=expectedMode{return nil,0,0,errors.New("test oracle mode mismatch")}
 pn:=binary.BigEndian.Uint64(w[6:14])
 var plain []byte
 if expectedMode==0{
  if len(w)<labAeadOverhead+40{return nil,0,0,errors.New("short AEAD")}
  v,e:=c.aead.Open(nil,c.nonce(pn),w[14:],w[:14])
  if e!=nil{return nil,0,0,fmt.Errorf("AEAD auth failure: %w",e)}
  plain=v
 }else if expectedMode==1{
  plain=append([]byte{},w[14:]...);maskPnRepeat(plain,pn)
 }else{return nil,0,0,errors.New("bad mode")}
 if len(plain)<41||plain[0]!=0||plain[1]>>4!=4{return nil,0,0,errors.New("invalid IPv4")}
 declared:=int(binary.BigEndian.Uint16(plain[3:5]))
 if declared<40||declared>len(plain)-1{return nil,0,0,errors.New("original IPv4 total length invalid")}
 padLen:=len(plain)-1-declared
 if expectedMode==1&&padLen!=0{return nil,0,0,errors.New("XOR must not pad")}
 return plain[1:1+declared],pn,padLen,nil
}
func randomHoldMs()int64{
 var b [4]byte;if _,e:=rand.Read(b[:]);e!=nil{panic(e)}
 return delayMinMs+int64(binary.BigEndian.Uint32(b[:])%delayRangeMs)
}
func choosePadding(s Spec)int{
 if !s.Boundary{return 0}
 room:=maxWireRecord-len(s.Inner)-labAeadOverhead
 if room<=0{return 0}
 var b [2]byte;if _,e:=rand.Read(b[:]);e!=nil{panic(e)}
 min:=16;if room<min{min=1}
 return min+int(binary.BigEndian.Uint16(b[:]))%(room-min+1)
}
func testCert()(tls.Certificate,*x509.CertPool,error){
 pub,priv,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{return tls.Certificate{},nil,e}
 now:=time.Now()
 t:=&x509.Certificate{SerialNumber:big.NewInt(1),
  Subject:pkix.Name{CommonName:"localhost"},
  NotBefore:now.Add(-time.Hour),NotAfter:now.Add(time.Hour),
  KeyUsage:x509.KeyUsageDigitalSignature|x509.KeyUsageCertSign,
  ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth,x509.ExtKeyUsageServerAuth},
  BasicConstraintsValid:true,IsCA:true,DNSNames:[]string{"localhost"}}
 der,e:=x509.CreateCertificate(rand.Reader,t,t,pub,priv)
 if e!=nil{return tls.Certificate{},nil,e}
 cert,e:=x509.ParseCertificate(der);if e!=nil{return tls.Certificate{},nil,e}
 pool:=x509.NewCertPool();pool.AddCert(cert)
 return tls.Certificate{Certificate:[][]byte{der},PrivateKey:priv,Leaf:cert},pool,nil
}
func readCorpus(root string)([]byte,[]byte,[]byte){
 ch,e:=os.ReadFile(root+"/client_hello.bin");fail(e)
 sf,e:=os.ReadFile(root+"/server_flight.bin");fail(e)
 app,e:=os.ReadFile(root+"/encrypted_app.bin");fail(e)
 if len(ch)<50||ch[0]!=22||!bytes.Contains(ch,[]byte(innerPublicSNI))||
   len(sf)<50||sf[0]!=22||sf[5]!=2||len(app)<1305||
   !bytes.Equal(app[:3],[]byte{23,3,3}){panic("not genuine inner TLS1.3 corpus")}
 // RFC8446 HelloRetryRequest fixed ServerHello.random. Do not advance gate on HRR.
 hrr:=[]byte{0xcf,0x21,0xad,0x74,0xe5,0x9a,0x61,0x11,0xbe,0x1d,0x8c,0x02,
 0x1e,0x65,0xb8,0x91,0xc2,0xa2,0x11,0x16,0x7a,0xbb,0x8c,0x5e,0x07,0x9e,
 0x09,0xe2,0xc8,0xa8,0x33,0x9c}
 if len(sf)<43||bytes.Equal(sf[11:43],hrr){panic("inner server flight not final ServerHello")}
 return ch,sf,app
}
func specs(ch,sf,app []byte)[]Spec{
 build:=func(label,stage string,boundary bool,port uint16,seq uint32,proto,flags byte,data []byte,trust bool)Spec{
  return Spec{Label:label,Stage:stage,Boundary:boundary,Port:port,
   Seq:seq,Proto:proto,Flags:flags,TrustedApp:trust,
   Inner:packet(port,seq,proto,flags,data)}
 }
 var ss []Spec
 add:=func(label,stage string,boundary bool,port uint16,seq uint32,proto,flags byte,data []byte,trust bool){
  ss=append(ss,build(label,stage,boundary,port,seq,proto,flags,data,trust))
 }
 add("TCP_SYN_start_PAD","early",true,mainPort,0,6,0x02,nil,false)
 add("TCP_SYNACK_start_PAD","early",true,443,0,6,0x12,nil,false)
 add("genuine_clienthello_start_PAD","early",true,mainPort,1000,6,0x18,ch,false)
 add("genuine_clienthello_retransmit_start_PAD","early",true,mainPort,1000,6,0x18,ch,false)
 for i,start:=0,0;start<len(sf);i,start=i+1,start+1000{
  stop:=start+1000;if stop>len(sf){stop=len(sf)}
  add(fmt.Sprintf("genuine_serverflight_chunk%d_start_PAD",i),"early",true,
   443,2000+uint32(start),6,0x18,sf[start:stop],false)
 }
 add("QUIC_Initial_start_PAD","early",true,40001,4000,17,0,
  []byte{0xc3,0,0,0,1,0x21,0x55,0x01,0,0,0,0,0,0,1},false)
 add("TLS13_early_app_before_hold_no_PAD_AES","early",false,mainPort,20000,6,0x18,app[:1305],true)
 add("HTTP_middle_no_PAD_AES","early",false,51001,25000,6,0x18,[]byte("GET /index HTTP/1.1"),false)
 add("TCP_ACK_middle_no_PAD_AES","early",false,mainPort,25000,6,0x10,nil,false)
 add("UDP_middle_no_PAD_AES","early",false,53001,6000,17,0,[]byte{1,2,3,4,5},false)
 add("unknown_TLS13_middle_no_PAD_AES","early",false,50204,6000,6,0x18,app[:1305],false)
 // Exactly MTU (no padding capacity); do not fragment or exceed MTU.
 add("TCP_end_exact_MTU_zero_pad_AES","late",true,mainPort,31000,6,0x11,
  app[:maxWireRecord-labAeadOverhead-40],false)
 add("TLS13_app_fast_after_hold_XOR","late",false,mainPort,20000,6,0x18,app[:1305],true)
 add("TLS13_fast_same_app_new_PN_XOR","late",false,mainPort,20000,6,0x18,app[:1305],true)
 add("TLS13_app_fast_small_XOR","late",false,mainPort,26000,6,0x18,app[:290],true)
 add("TLS13_app_fast_later_XOR","late",false,mainPort,28000,6,0x18,app[:1305],true)
 add("genuine_clienthello_oldseq_late_PAD_AES","late",true,mainPort,1000,6,0x18,ch,false)
 add("TLS13_protected_edge_identical_cipher_PAD_AES","late",true,mainPort,20000,6,0x18,app[:1305],false)
 add("TCP_FIN_end_PAD_AES","late",true,mainPort,32000,6,0x11,nil,false)
 add("TCP_RST_end_PAD_AES","late",true,mainPort,33000,6,0x14,nil,false)
 add("QUIC_CONNECTION_CLOSE_end_PAD_AES","late",true,40001,5000,17,0,
  []byte{0x43,0,0,0,0,0,1,0x1c},false)
 add("TCP_normal_middle_AFTER_HOLD_no_PAD_AES","late",false,51001,35000,6,0x18,
  []byte("ordinary unchanged application data"),false)
 add("TCP_ACK_after_hold_no_PAD_AES","late",false,mainPort,35000,6,0x10,nil,false)
 add("UDP_normal_after_hold_no_PAD_AES","late",false,53001,6000,17,0,[]byte{1,2,3},false)
 add("TLS12_like_unknown_after_hold_no_PAD_AES","late",false,50203,6000,6,0x18,
  []byte{23,3,3,0,4,1,2,3,4},false)
 add("TLS13_app_fast_end_XOR","late",false,mainPort,39000,6,0x18,app[:1305],true)
 return ss
}
func run(port int,root,manifestPath string)error{
 ch,sf,app:=readCorpus(root)
 var sample []byte
 sample=append(sample,[]byte("test")...)
 maskPnRepeat(sample,7);maskPnRepeat(sample,7)
 if string(sample)!="test"{return errors.New("mask roundtrip fail")}
 specs:=specs(ch,sf,app)
 // Gate is not enabled until the genuine inner final ServerHello is present
 // in a verified local TLS transcript. This is only a test-controlled gate.
 verified:=len(sf)>=43 && sf[5]==2
 if !verified{return errors.New("final serverhello not seen")}
 c,e:=newCoder();if e!=nil{return e}
 recs:=make([][]byte,0,len(specs))
 manifest:=Manifest{Scope:"GENUINE_OUTER_MUTUAL_TLS13_THEN_TEST_ONLY_MIXED_AESGCM_OR_PUBLIC_PN_XOR",
  InnerTLS13Genuine:true,OuterMutualTLS13Genuine:true,FinalServerHelloSeen:true,
  RealProductionClassifier:false,RealWbdAeadWire:false,PlaintextRoundtripAll:true,
  ModeDowngradeRejectedInTestOracle:true,Records:make([]Receipt,0,len(specs))}
 aesCount,xorCount:=0,0
 for i,s:=range specs{
  mode:=byte(0);if gate(s,verified){mode=1;xorCount++}else{aesCount++}
  w:=c.seal(s.Inner,mode,uint64(i))
  got,pn,e:=c.open(w,mode)
  if e!=nil||pn!=uint64(i)||!bytes.Equal(got,s.Inner){return fmt.Errorf("local exact mixed roundtrip failed %s: %v",s.Label,e)}
  if mode==0{
   tampered:=append([]byte{},w...)
   tampered[len(tampered)-1]^=1
   if _,_,e=c.open(tampered,0);e==nil{return errors.New("AEAD tamper not rejected")}
   wrong:=append([]byte{},w...);wrong[5]=1
   if _,_,e=c.open(wrong,0);e==nil{return errors.New("lab oracle mode downgrade accepted")}
  }
  h:=sha256.Sum256(s.Inner)
  name:="aes128_gcm_full";if mode==1{name="public_pn_xor_fast"}
  manifest.Records=append(manifest.Records,Receipt{s.Label,uint64(i),name,len(w),len(s.Inner),hex.EncodeToString(h[:])})
  recs=append(recs,w)
 }
 manifest.AESFallbackTamperRejected=true
 if aesCount<10||xorCount<3{return fmt.Errorf("incorrect split aes=%d xor=%d",aesCount,xorCount)}
 parsed,e:=json.MarshalIndent(manifest,"","  ");if e!=nil{return e}
 if e=os.WriteFile(manifestPath,append(parsed,byte(10)),0600);e!=nil{return e}
 cert,pool,e:=testCert();if e!=nil{return e}
 listener,e:=net.Listen("tcp",net.JoinHostPort("127.0.0.1",strconv.Itoa(port)))
 if e!=nil{return e}
 defer listener.Close()
 addr:=listener.Addr().String()
 srv:=&tls.Config{MinVersion:tls.VersionTLS13,MaxVersion:tls.VersionTLS13,
  Certificates:[]tls.Certificate{cert},ClientAuth:tls.RequireAndVerifyClientCert,
  ClientCAs:pool,SessionTicketsDisabled:true}
 cli:=&tls.Config{MinVersion:tls.VersionTLS13,MaxVersion:tls.VersionTLS13,
  ServerName:"localhost",RootCAs:pool,Certificates:[]tls.Certificate{cert},
  SessionTicketsDisabled:true}
 serverResult:=make(chan error,1)
 go func(){
  raw,err:=listener.Accept();if err!=nil{serverResult<-err;return}
  defer raw.Close()
  raw.SetDeadline(time.Now().Add(18*time.Second))
  sc:=tls.Server(raw,srv)
  if e:=sc.Handshake();e!=nil{serverResult<-e;return}
  var ready [7]byte
  if _,e:=io.ReadFull(sc,ready[:]);e!=nil{serverResult<-e;return}
  if string(ready[:])!="C_READY"{serverResult<-errors.New("missing encrypted bootstrap barrier");return}
  if _,e:=sc.Write([]byte("S_READY"));e!=nil{serverResult<-e;return}
  direct:=sc.NetConn()
  for i,s:=range specs{
   var h [5]byte
   if _,e:=io.ReadFull(direct,h[:]);e!=nil{serverResult<-e;return}
   n:=int(binary.BigEndian.Uint16(h[3:5]))
   if n<=0||n>1500||!bytes.Equal(h[:3],[]byte{0x17,0x03,0x03}){
    serverResult<-errors.New("bad post-handshake raw outer frame");return
   }
   w:=make([]byte,n+5);copy(w[:5],h[:])
   if _,e:=io.ReadFull(direct,w[5:]);e!=nil{serverResult<-e;return}
   expectedMode:=byte(0);if gate(s,verified){expectedMode=1}
   decoded,pn,e:=c.open(w,expectedMode)
   if e!=nil||pn!=uint64(i)||!bytes.Equal(decoded,s.Inner){
    serverResult<-fmt.Errorf("on-wire server decrypt failed %s: %v",s.Label,e);return
   }
  }
  serverResult<-nil
 }()
 raw,e:=net.DialTimeout("tcp",addr,5*time.Second);if e!=nil{return e}
 defer raw.Close()
 raw.SetDeadline(time.Now().Add(18*time.Second))
 tc:=tls.Client(raw,cli)
 if e=tc.Handshake();e!=nil{return e}
 if tc.ConnectionState().Version!=tls.VersionTLS13{return errors.New("wrong TLS version")}
 if _,e=tc.Write([]byte("C_READY"));e!=nil{return e}
 var ack [7]byte;if _,e=io.ReadFull(tc,ack[:]);e!=nil{return e}
 if string(ack[:])!="S_READY"{return errors.New("missing server TLS barrier")}
 direct:=tc.NetConn()
 for _,w:=range recs{
  if _,e=direct.Write(w);e!=nil{return e}
  time.Sleep(17*time.Millisecond)
 }
 if e=<-serverResult;e!=nil{return e}
 receipt,e:=json.Marshal(map[string]interface{}{
  "outer_mutual_tls13":true,"inner_tls13_corpus":true,
  "records":len(recs),"fallback_aes":aesCount,"fast_pn_xor":xorCount,
  "all_exact_roundtrip":true,"fallback_tamper_rejected":true,
  "scope":"LAB_ONLY_NO_REAL_CLASSIFIER_OR_WBD_AEAD_WIRE",
 })
 if e!=nil{return e}
 fmt.Println(string(receipt))
 return nil
}
func main(){
 if len(os.Args)!=4{panic("usage: mixed_tcp PORT inner_tls_corpus_dir owned_manifest.json")}
 port,e:=strconv.Atoi(os.Args[1]);fail(e)
 fail(run(port,os.Args[2],os.Args[3]))
}
