// Isolated steady-state research, NOT production. Same TLS-like WBD fast
// record, protected mode+PN and 1345B IPv4/TCP/TLS13-looking fixture.
// FullUnroll4 and FullSubtleXOR MUST match FullBaseline bit for bit.
// Prefix variants alter the public-wire bytes and leave tail plaintext.
//
// Important: public PN-XOR offers NO cryptographic confidentiality or MAC,
// and prefix mode is only a cost illustration, not safe TLS classification.
package pnxoropt

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "crypto/subtle"
 "encoding/binary"
 "math/bits"
 "testing"
)

const bodySize=1345
const perCycle=100
type variant uint8
const (
 fullBaseline variant=iota
 fullUnroll4
 fullSubtleXOR
 prefix64
 prefix128
 prefix256
)
type coder struct {
 hp cipher.Block
 block [16]byte
 maskScratch [1600]byte
 v variant
}
func makeCoder(v variant)*coder{
 k:=[16]byte{0xc3,0x10,0x0c,0x3a,0x50,0xe2,0x81,0x49,0x76,0xbb,0x21,0x39,0x77,0x00,0xdd,0xa3}
 hp,e:=aes.NewCipher(k[:]);if e!=nil{panic(e)}
 return &coder{hp:hp,v:v}
}
func repeatedKey(pn uint64)uint64{
 return bits.RotateLeft64(pn,17)^uint64(0x6c616e5f6e6f7365)
}
func xorBaseline(dst []byte,pn uint64){
 k:=repeatedKey(pn)
 i:=0
 for ;i+8<=len(dst);i+=8{
  binary.LittleEndian.PutUint64(dst[i:i+8],binary.LittleEndian.Uint64(dst[i:i+8])^k)
 }
 for j:=0;i<len(dst);i,j=i+1,j+1{dst[i]^=byte(k>>(8*j))}
}
func xorUnroll(dst []byte,pn uint64){
 k:=repeatedKey(pn)
 i:=0
 for ;i+32<=len(dst);i+=32{
  binary.LittleEndian.PutUint64(dst[i:i+8],binary.LittleEndian.Uint64(dst[i:i+8])^k)
  binary.LittleEndian.PutUint64(dst[i+8:i+16],binary.LittleEndian.Uint64(dst[i+8:i+16])^k)
  binary.LittleEndian.PutUint64(dst[i+16:i+24],binary.LittleEndian.Uint64(dst[i+16:i+24])^k)
  binary.LittleEndian.PutUint64(dst[i+24:i+32],binary.LittleEndian.Uint64(dst[i+24:i+32])^k)
 }
 for ;i+8<=len(dst);i+=8{
  binary.LittleEndian.PutUint64(dst[i:i+8],binary.LittleEndian.Uint64(dst[i:i+8])^k)
 }
 for j:=0;i<len(dst);i,j=i+1,j+1{dst[i]^=byte(k>>(8*j))}
}
func (c *coder) xorSubtle(dst []byte,pn uint64){
 k:=repeatedKey(pn)
 binary.LittleEndian.PutUint64(c.maskScratch[:8],k)
 filled:=8
 for filled<len(dst){
  filled+=copy(c.maskScratch[filled:len(dst)],c.maskScratch[:filled])
 }
 subtle.XORBytes(dst,dst,c.maskScratch[:len(dst)])
}
func (c *coder) mask(dst []byte,pn uint64){
 switch c.v {
 case fullBaseline:xorBaseline(dst,pn)
 case fullUnroll4:xorUnroll(dst,pn)
 case fullSubtleXOR:c.xorSubtle(dst,pn)
 case prefix64: if len(dst)>64{dst=dst[:64]};xorBaseline(dst,pn)
 case prefix128:if len(dst)>128{dst=dst[:128]};xorBaseline(dst,pn)
 case prefix256:if len(dst)>256{dst=dst[:256]};xorBaseline(dst,pn)
 default:panic("bad variant")
 }
}
func (c *coder) hpMask(sample []byte)uint64{
 c.hp.Encrypt(c.block[:],sample[:16])
 return binary.BigEndian.Uint64(c.block[:8])
}
func (c *coder) seal(buf,original []byte,pn uint64)[]byte{
 if pn>=(uint64(1)<<63){panic("PN exhausted")}
 used:=14+len(original)
 if len(buf)<used{panic("small record")}
 w:=buf[:used]
 w[0]=0x17;w[1]=3;w[2]=3
 binary.BigEndian.PutUint16(w[3:5],uint16(used-5))
 w[13]=0 // historical 1B kind inside public-XOR body
 copy(w[14:],original)
 c.mask(w[13:],pn)
 tagged:=(uint64(1)<<63)|pn
 binary.BigEndian.PutUint64(w[5:13],tagged^c.hpMask(w[13:]))
 return w
}
func (c *coder) open(w,out []byte)(uint64,[]byte,bool){
 if len(w)<13+17||w[0]!=0x17||w[1]!=3||w[2]!=3 ||
  int(binary.BigEndian.Uint16(w[3:5]))!=len(w)-5 || len(out)<len(w)-13 {
  return 0,nil,false
 }
 tagged:=binary.BigEndian.Uint64(w[5:13])^c.hpMask(w[13:])
 if tagged>>63!=1{return 0,nil,false}
 pn:=tagged&((uint64(1)<<63)-1)
 n:=copy(out,w[13:])
 c.mask(out[:n],pn)
 if out[0]!=0{return 0,nil,false}
 return pn,out[1:n],true
}
func packet()[]byte{
 p:=make([]byte,bodySize)
 p[0]=0x45;binary.BigEndian.PutUint16(p[2:4],bodySize)
 p[8]=64;p[9]=6
 binary.BigEndian.PutUint16(p[20:22],50101)
 binary.BigEndian.PutUint16(p[22:24],443)
 p[32]=0x50;p[33]=0x18
 p[40]=0x17;p[41]=3;p[42]=3
 binary.BigEndian.PutUint16(p[43:45],bodySize-45)
 for i:=45;i<len(p);i++{p[i]=byte((i*37+i/13)%256)}
 return p
}
func TestFullVariantsIdenticalWire(t *testing.T){
 p:=packet()
 for _,pn:=range []uint64{0,1,7,42,0x100000001,(1<<63)-1}{
  b:=makeCoder(fullBaseline).seal(make([]byte,1600),p,pn)
  for _,v:=range []variant{fullUnroll4,fullSubtleXOR}{
   c:=makeCoder(v)
   w:=c.seal(make([]byte,1600),p,pn)
   if !bytes.Equal(b,w){t.Fatalf("full XOR bytes DIFFER mode=%d pn=%d",v,pn)}
   n,got,ok:=c.open(w,make([]byte,1600))
   if !ok||n!=pn||!bytes.Equal(got,p){t.Fatalf("full roundtrip mode=%d pn=%d",v,pn)}
  }
 }
}
func TestAllVariantsRoundtripAndPrefixPlaintextExposure(t *testing.T){
 p:=packet()
 for v:=fullBaseline;v<=prefix256;v++{
  c:=makeCoder(v)
  for i:=0;i<1000;i++{
   pn:=uint64(i+1)
   w:=c.seal(make([]byte,1600),p,pn)
   parsed,data,ok:=c.open(w,make([]byte,1600))
   if !ok||parsed!=pn||!bytes.Equal(data,p){t.Fatalf("roundtrip variant=%d pn=%d",v,pn)}
   if w[0]!=0x17||w[1]!=3||w[2]!=3{t.Fatalf("not TLS-like")}
   if v>=prefix64{
    prefix:=64
    if v==prefix128{prefix=128}
    if v==prefix256{prefix=256}
    if !bytes.Equal(w[13+prefix:],p[prefix-1:]) {
     t.Fatalf("prefix mode should expose unchanged tail; mode=%d",v)
    }
   }
  }
 }
}
func BenchmarkFullBaseline(b *testing.B){bench(b,fullBaseline)}
func BenchmarkFullUnroll4(b *testing.B){bench(b,fullUnroll4)}
func BenchmarkFullSubtleXOR(b *testing.B){bench(b,fullSubtleXOR)}
func BenchmarkPrefix64(b *testing.B){bench(b,prefix64)}
func BenchmarkPrefix128(b *testing.B){bench(b,prefix128)}
func BenchmarkPrefix256(b *testing.B){bench(b,prefix256)}
var benchSink uint64
func bench(b *testing.B,v variant){
 c:=makeCoder(v);p:=packet()
 wires:=make([][]byte,perCycle)
 outputs:=make([][]byte,perCycle)
 for i:=range wires{
  wires[i]=make([]byte,1600)
  outputs[i]=make([]byte,1600)
 }
 b.ReportAllocs();b.SetBytes(bodySize*perCycle);b.ResetTimer()
 var result uint64
 for cycle:=0;cycle<b.N;cycle++{
  for i:=0;i<perCycle;i++{
   pn:=uint64(cycle*perCycle+i+1)
   w:=c.seal(wires[i],p,pn)
   recovered,original,ok:=c.open(w,outputs[i])
   if !ok||recovered!=pn||len(original)!=len(p){b.Fatal("open mismatch")}
   result+=uint64(original[4])^recovered
  }
 }
 benchSink=result
}
