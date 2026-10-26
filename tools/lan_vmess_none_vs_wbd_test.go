// Self-contained VMess (V2Fly) no-payload-encryption vs WBD PN-XOR microbenchmark.
// Reference: v2fly/v2ray-core master proxy/vmess/encoding/auth.go (SHAKE128
// 16B IV size XOR) and outbound/outbound.go (NONE stream: chunk+mask, zero:
// raw stream). VMess TCP NONE does NOT encrypt or XOR the payload and does
// NOT use global padding in ChunkStreamWriter. Initialization/header/auth is
// intentionally EXCLUDED from this *steady-state per-chunk* comparison.
//
// WBD reference: experiment/lan-hp-mode-cost/tools/lan_hp_mode_cost_test.go.
// WBD fast mode is public PN XOR on original inner data, optionally with AES128
// protected PN+mode. No production code is changed.
package vmessbench

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "crypto/sha3"
 "encoding/binary"
 "math/bits"
 "testing"
)

const (
 payloadN=1345
 batchN=100
 tlsOuterType=0x17
)
var benchHash uint64
var vmessIV=[16]byte{0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}
var hpKey=[16]byte{0xc3,0x10,0x0c,0x3a,0x50,0xe2,0x81,0x49,0x76,0xbb,0x21,0x39,0x77,0x00,0xdd,0xa3}

type style int
const (
 vmessZero style=iota
 vmessNonePlainLength
 vmessNoneSHAKE
 wbdClearPNXOR
 wbdHiddenPNXOR
)
func (s style) label()string{
 switch s{
 case vmessZero:return "VMessZeroRaw"
 case vmessNonePlainLength:return "VMessNonePlainLength"
 case vmessNoneSHAKE:return "VMessNoneSHAKE128"
 case wbdClearPNXOR:return "WBDClearPNXOR"
 case wbdHiddenPNXOR:return "WBDHiddenPNXOR"
 }
 return "unknown"
}
type codec struct {
 style style
 e,d *sha3.SHAKE
 hp cipher.Block
 hpBlock [16]byte
 tmpMask [2]byte
}
func newCodec(s style)*codec{
 c:=&codec{style:s}
 if s==vmessNoneSHAKE{
  c.e=sha3.NewSHAKE128();c.d=sha3.NewSHAKE128()
  _,_=c.e.Write(vmessIV[:]);_,_=c.d.Write(vmessIV[:])
 }
 if s==wbdHiddenPNXOR{
  var e error
  c.hp,e=aes.NewCipher(hpKey[:]);if e!=nil{panic(e)}
 }
 return c
}
func (c *codec) mask(b []byte)uint64{
 c.hp.Encrypt(c.hpBlock[:],b[:16])
 return binary.BigEndian.Uint64(c.hpBlock[:8])
}
func maskPNBody(dst []byte,pn uint64){
 k:=bits.RotateLeft64(pn,17)^uint64(0x6c616e5f6e6f7365)
 i:=0
 for ;i+8<=len(dst);i+=8{
  v:=binary.LittleEndian.Uint64(dst[i:i+8])
  binary.LittleEndian.PutUint64(dst[i:i+8],v^k)
 }
 for j:=0;i+j<len(dst);j++{dst[i+j]^=byte(k>>(8*j))}
}
func (c *codec) seal(w,original []byte,pn uint64)(int){
 n:=len(original)
 switch c.style{
 case vmessZero:
  copy(w,original);return n
 case vmessNonePlainLength:
  binary.BigEndian.PutUint16(w[:2],uint16(n))
  copy(w[2:],original)
  return n+2
 case vmessNoneSHAKE:
  _,_=c.e.Read(c.tmpMask[:])
  masked:=uint16(n)^binary.BigEndian.Uint16(c.tmpMask[:])
  binary.BigEndian.PutUint16(w[:2],masked)
  copy(w[2:],original)
  return n+2
 case wbdClearPNXOR,wbdHiddenPNXOR:
  head:=14
  if c.style==wbdHiddenPNXOR{head=13}
  total:=head+1+n
  w[0]=tlsOuterType;w[1]=3;w[2]=3
  binary.BigEndian.PutUint16(w[3:5],uint16(total-5))
  w[head]=0
  copy(w[head+1:total],original)
  maskPNBody(w[head:total],pn)
  if c.style==wbdClearPNXOR{
   w[5]=1
   binary.BigEndian.PutUint64(w[6:14],pn)
  }else{
   const pnMax=(uint64(1)<<63)-1
   if pn>pnMax{panic("63bit WBD PN exhausted")}
   tagged:=(uint64(1)<<63)|pn
   binary.BigEndian.PutUint64(w[5:13],tagged^c.mask(w[13:total]))
  }
  return total
 }
 panic("unknown style")
}
func (c *codec) open(w,out []byte,pnExpected uint64)(int,bool){
 switch c.style{
 case vmessZero:
  if len(out)<len(w){return 0,false}
  return copy(out,w),true
 case vmessNonePlainLength:
  if len(w)<2{return 0,false}
  n:=int(binary.BigEndian.Uint16(w[:2]))
  if n>len(out)||n+2!=len(w){return 0,false}
  return copy(out,w[2:]),true
 case vmessNoneSHAKE:
  if len(w)<2{return 0,false}
  _,_=c.d.Read(c.tmpMask[:])
  n:=int(binary.BigEndian.Uint16(w[:2])^binary.BigEndian.Uint16(c.tmpMask[:]))
  if n>len(out)||n+2!=len(w){return 0,false}
  return copy(out,w[2:]),true
 case wbdClearPNXOR,wbdHiddenPNXOR:
  head:=14
  if c.style==wbdHiddenPNXOR{head=13}
  if len(w)<head+17||w[0]!=tlsOuterType||w[1]!=3||w[2]!=3||
   int(binary.BigEndian.Uint16(w[3:5]))!=len(w)-5{return 0,false}
  var pn uint64
  if c.style==wbdClearPNXOR{
   if w[5]!=1{return 0,false}
   pn=binary.BigEndian.Uint64(w[6:14])
  }else{
   tagged:=binary.BigEndian.Uint64(w[5:13])^c.mask(w[13:])
   if tagged>>63!=1{return 0,false}
   pn=tagged&((uint64(1)<<63)-1)
  }
  if pn!=pnExpected{return 0,false}
  n:=len(w)-head
  if n!=payloadN+1||n>len(out)+1{return 0,false}
  // Decode into reusable owned scratch that includes 1B original "kind".
  copy(out[:n],w[head:])
  maskPNBody(out[:n],pn)
  if out[0]!=0{return 0,false}
  return n-1,true
 }
 return 0,false
}
func input()[]byte{
 p:=make([]byte,payloadN)
 p[0]=0x45
 binary.BigEndian.PutUint16(p[2:4],uint16(payloadN))
 p[8]=64;p[9]=6
 binary.BigEndian.PutUint16(p[20:22],50101)
 binary.BigEndian.PutUint16(p[22:24],443)
 p[32]=0x50;p[33]=0x18
 // An inner TLS1.3 ciphertext-looking application record starts at offset 40.
 p[40]=0x17;p[41]=3;p[42]=3
 binary.BigEndian.PutUint16(p[43:45],uint16(payloadN-45))
 for i:=45;i<len(p);i++{p[i]=byte((i*37+i/13)%256)}
 return p
}
func TestVMessCorrectSHAKE128Vector(t *testing.T){
 c:=newCodec(vmessNoneSHAKE)
 expected:=[]byte{0x98,0x48,0x19,0x46,0xde,0x85}
 for i:=0;i<3;i++{
  var b [2]byte
  _,_=c.e.Read(b[:])
  if !bytes.Equal(b[:],expected[2*i:2*i+2]){
   t.Fatalf("SHAKE128 V2Fly size mask mismatch i=%d got=%x expected=%x",i,b,expected[2*i:2*i+2])
  }
 }
}
func TestRoundtripAndPlaintextExposure(t *testing.T){
 p:=input()
 for _,s:=range []style{vmessZero,vmessNonePlainLength,vmessNoneSHAKE,wbdClearPNXOR,wbdHiddenPNXOR}{
  c:=newCodec(s)
  for i:=0;i<1000;i++{
   wire:=make([]byte,1600)
   output:=make([]byte,1600)
   pn:=uint64(i+1)
   n:=c.seal(wire,p,pn)
   got,ok:=c.open(wire[:n],output,pn)
   if !ok{t.Fatalf("decode failure mode=%s seq=%d",s.label(),i)}
   payload:=output[:got]
   if s==wbdClearPNXOR||s==wbdHiddenPNXOR{payload=output[1:1+got]}
   if !bytes.Equal(payload,p){t.Fatalf("plain mismatch style=%s seq=%d",s.label(),i)}
   if s<=vmessNoneSHAKE{
    if !bytes.Contains(wire[:n],p[:64]){t.Fatalf("VMess None/Zero altered unencrypted payload style=%s",s.label())}
   }else{
    if bytes.Contains(wire[:n],p[:64]){t.Fatalf("XOR incorrectly transmitted raw inner TCP/IP header style=%s",s.label())}
   }
  }
 }
}
func BenchmarkVMessZero(b *testing.B){bench(b,vmessZero)}
func BenchmarkVMessNonePlainLength(b *testing.B){bench(b,vmessNonePlainLength)}
func BenchmarkVMessNoneSHAKE128(b *testing.B){bench(b,vmessNoneSHAKE)}
func BenchmarkWBDClearPNXOR(b *testing.B){bench(b,wbdClearPNXOR)}
func BenchmarkWBDHiddenPNXOR(b *testing.B){bench(b,wbdHiddenPNXOR)}
func bench(b *testing.B,kind style){
 c:=newCodec(kind)
 p:=input()
 w:=make([][]byte,batchN);out:=make([][]byte,batchN)
 for i:=range w{
  w[i]=make([]byte,1600);out[i]=make([]byte,1600)
 }
 b.SetBytes(payloadN*batchN)
 b.ReportAllocs()
 b.ResetTimer()
 var nsum uint64
 for run:=0;run<b.N;run++{
  for i:=0;i<batchN;i++{
   pn:=uint64(run*batchN+i+1)
   n:=c.seal(w[i],p,pn)
   m,ok:=c.open(w[i][:n],out[i],pn)
   if !ok||m!=payloadN{b.Fatalf("decode fail mode=%s",kind.label())}
   nsum+=uint64(m)+uint64(n)+uint64(out[i][1])
  }
 }
 benchHash=nsum
}
