// Minimal lab: independent implicit record counter, no WBD protected PN.
// Non-TLS-23 or retransmitted 23 => AES-128-GCM; original trusted 23 => copy.
// TLS-like 5-byte header, 2-byte trailing mode-family marker, then rolling
// XOR on final 8 BITS (one byte). Also contrast xor final 8 BYTES.
// Not actual TLS 1.3, not a TLS classifier, not production, not secure fast path.
package tailmarker

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "errors"
 "crypto/subtle"
 "encoding/binary"
 "math/bits"
 "testing"
)
const nPayload=1345
const batchSize=100
type variant int
const(
 hybrid99NoXOR variant=iota
 hybrid99Tail1
 hybrid99Tail8
 hybrid95Tail1
 hybrid80Tail1
 allAESTail1
 oldFullXOR
)
type tailMask int
const(
 maskNone tailMask=iota
 maskOneByte
 maskEightBytes
)
type coder struct {
 aead cipher.AEAD
 iv [12]byte
 nonceBuf [12]byte
 aadBuf [15]byte
 // Independent old XOR baseline scratch, NOT a WBD production record.
 oldKey [16]byte
 oldBlock cipher.Block
 oldAESBlock [16]byte
 oldXORMask [1600]byte
}
func newCoder()*coder{
 key:=[16]byte{3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18}
 hk:=[16]byte{0xc3,0x10,0x0c,0x3a,0x50,0xe2,0x81,0x49,0x76,0xbb,0x21,0x39,0x77,0x00,0xdd,0xa3}
 b,e:=aes.NewCipher(key[:]);if e!=nil{panic(e)}
 hp,e:=aes.NewCipher(hk[:]);if e!=nil{panic(e)}
 a,e:=cipher.NewGCM(b);if e!=nil{panic(e)}
 return &coder{aead:a,iv:[12]byte{1,2,3,4,0,0,0,0,0,0,0,0},oldBlock:hp}
}
func (c *coder) nonce(seq uint64)[]byte{
 copy(c.nonceBuf[:],c.iv[:])
 for i:=0;i<8;i++{c.nonceBuf[4+i]^=byte(seq>>(56-8*i))}
 return c.nonceBuf[:]
}
func marker(seq uint64, fallbackAES bool)uint16{
 v:=uint16(seq*137+59)
 if fallbackAES{return 0xf000 | (v&0x0fff)}
 return v%0xf000 // Most codepoints given to genuine pre-existing TLS 23.
}
func maskRolling(w []byte,seq uint64,mode tailMask){
 n:=0
 switch mode {case maskNone:return;case maskOneByte:n=1;case maskEightBytes:n=8;default:panic("mask")}
 if len(w)<n{panic("short tail")}
 // One independent implicit per-record counter, never WBD's protected PN.
 k:=bits.RotateLeft64(seq*0x9e3779b97f4a7c15 ^ 0x6c616e5f6e6f7365,17)
 for i:=0;i<n;i++{w[len(w)-1-i]^=byte(k>>(i*8))}
}
func (c *coder) makeAAD(header []byte,m uint16,seq uint64)[]byte{
 copy(c.aadBuf[:5],header[:5])
 binary.BigEndian.PutUint16(c.aadBuf[5:7],m)
 binary.BigEndian.PutUint64(c.aadBuf[7:15],seq)
 return c.aadBuf[:]
}
func isAESFallback(inner []byte,retrans bool)bool{
 // IMPORTANT: this merely checks the caller's synthetic "trusted" label.
 // Byte 0x17 is NOT proof TLS 1.3 Finished, authentication, or app data.
 return retrans || len(inner)==0 || inner[0]!=0x17
}
func (c *coder) seal(w,inner []byte,retrans bool,seq uint64,roll tailMask,forceAES bool)[]byte{
 fallback:=forceAES||isAESFallback(inner,retrans)
 bodylen:=len(inner)
 if fallback{bodylen+=c.aead.Overhead()}
 total:=5+bodylen+2
 if len(w)<total{panic("small seal buffer")}
 out:=w[:total]
 out[0]=0x17;out[1]=3;out[2]=3
 binary.BigEndian.PutUint16(out[3:5],uint16(total-5))
 m:=marker(seq,fallback)
 if fallback {
  c.aead.Seal(out[5:5],c.nonce(seq),inner,c.makeAAD(out[:5],m,seq))
 }else{
  copy(out[5:5+len(inner)],inner)
 }
 binary.BigEndian.PutUint16(out[total-2:],m)
 maskRolling(out,seq,roll)
 return out
}
func (c *coder) open(w,out []byte,seq uint64,roll tailMask)(bool,[]byte,error){
 if len(w)<7||w[0]!=0x17||w[1]!=3||w[2]!=3||
  int(binary.BigEndian.Uint16(w[3:5]))!=len(w)-5{return false,nil,errors.New("bad TLS-like outer header")}
 // Undo only tail XOR, on a reusable scratch copy so caller wire is unchanged.
 // Bench output buffer must be >= total for this variant.
 copy(out,w)
 b:=out[:len(w)]
 maskRolling(b,seq,roll)
 m:=binary.BigEndian.Uint16(b[len(b)-2:])
 fallback:=m>=0xf000
 // Counter-synchronized marker validation, NOT cryptographic authenticity.
 // Network loss/reordering and outer TCP retrans must NOT desynchronize it.
 if m!=marker(seq,fallback){return fallback,nil,errors.New("counter/marker mismatch")}
 payload:=b[5:len(b)-2]
 if fallback{
  p,e:=c.aead.Open(b[5:5],c.nonce(seq),payload,c.makeAAD(b[:5],m,seq))
  if e!=nil{return fallback,nil,e}
  return fallback,p,nil
 }
 return fallback,payload,nil
}
func tlsFixture()[]byte{
 p:=make([]byte,nPayload)
 p[0]=0x17;p[1]=3;p[2]=3
 binary.BigEndian.PutUint16(p[3:5],uint16(len(p)-5))
 for i:=5;i<len(p);i++{p[i]=byte((i*47+i/13)%256)}
 return p
}
func otherFixture()[]byte{
 p:=tlsFixture()
 p[0]=0x16 // authenticated? no; intentionally fallback.
 return p
}
// Exact same sizes and pointer lifetimes, verify retransmitted TLS23 AES.
func pick(i,fastPct int,tls23,other []byte)([]byte,bool,bool){
 if i<fastPct{return tls23,false,false}
 if (i-fastPct)%2==0{return other,false,true}
 return tls23,true,true
}
func TestTailMarkerModesRoundtrip(t *testing.T){
 c:=newCoder()
 tls23,other:=tlsFixture(),otherFixture()
 for _,roll:=range []tailMask{maskNone,maskOneByte,maskEightBytes}{
  for _,fastPct:=range []int{0,80,95,99,100}{
   var wire [1600]byte
   var output [1600]byte
   for i:=0;i<1000;i++{
    inner,retrans,wantAES:=pick(i%100,fastPct,tls23,other)
    seq:=uint64(i+1)
    enc:=c.seal(wire[:],inner,retrans,seq,roll,false)
    gotAES,got,e:=c.open(enc,output[:],seq,roll)
    if e!=nil||gotAES!=wantAES||!bytes.Equal(got,inner){
     t.Fatalf("roll=%d fast%%=%d seq=%d gotAES=%v wantAES=%v err=%v",roll,fastPct,seq,gotAES,wantAES,e)
    }
    if enc[0]!=0x17||enc[1]!=3||enc[2]!=3{t.Fatal("outer malformed")}
    if len(enc)!=1352+map[bool]int{true:16,false:0}[wantAES]{t.Fatal("overhead wrong")}
   }
  }
 }
}
func TestTrailerFingerprintAndUnauthenticatedFast(t *testing.T){
 c:=newCoder()
 tls23:=tlsFixture()
 var wire [1600]byte
 var out [1600]byte
 w:=c.seal(wire[:],tls23,false,18,maskOneByte,false)
 // Original TLS-like 23 header appears AGAIN at offset five in clear:
 if !bytes.Equal(w[:5],[]byte{0x17,3,3,5,67}){t.Fatalf("unexpected outer header %x",w[:5])}
 if !bytes.Equal(w[5:8],[]byte{0x17,3,3}){t.Fatal("missing visible nested TLS signature")}
 if w[len(w)-2]>=0xf0{t.Fatal("fast high marker leaked the wrong range")}
 // Fast mode has no MAC: changing ordinary payload is accepted.
 flip:=append([]byte(nil),w...)
 flip[24]^=1
 aes,p,e:=c.open(flip,out[:],18,maskOneByte)
 if e!=nil||aes||bytes.Equal(p,tls23){t.Fatal("fast mode unexpectedly authenticated")}
 // The test-only deterministic marker allows a single-byte mode downgrade
 // to be rejected, but remains publicly computable, not authentication.
 other:=otherFixture()
 wa:=c.seal(wire[:],other,false,19,maskOneByte,false)
 tampered:=append([]byte(nil),wa...)
 tampered[len(tampered)-2]=0x20 // clear high-byte mode downgrade
 aes,p,e=c.open(tampered,out[:],19,maskOneByte)
 if e==nil{t.Fatal("AES downgrade should fail marker consistency")}
 _=aes;_=p
 // Reordering different sequence counters loses implicit rolling state.
 _,_,e=c.open(w,out[:],20,maskOneByte)
 if e==nil{t.Fatal("implicit counter mismatch should be rejected")}
}
func (c *coder) sealOldFullXOR(w,inner []byte,seq uint64)[]byte{
 n:=5+8+len(inner)
 b:=w[:n];b[0]=0x17;b[1]=3;b[2]=3
 binary.BigEndian.PutUint16(b[3:5],uint16(n-5))
 copy(b[13:],inner)
 key:=bits.RotateLeft64(seq,17)^uint64(0x6c616e5f6e6f7365)
 binary.LittleEndian.PutUint64(c.oldXORMask[:8],key)
 filled:=8
 for filled<len(inner){filled+=copy(c.oldXORMask[filled:len(inner)],c.oldXORMask[:filled])}
 subtle.XORBytes(b[13:],b[13:],c.oldXORMask[:len(inner)])
 c.oldBlock.Encrypt(c.oldAESBlock[:],b[13:29])
 binary.BigEndian.PutUint64(b[5:13],(seq|(uint64(1)<<63))^binary.BigEndian.Uint64(c.oldAESBlock[:8]))
 return b
}
func (c *coder) openOldFullXOR(w,out []byte,seq uint64)[]byte{
 c.oldBlock.Encrypt(c.oldAESBlock[:],w[13:29])
 tagged:=binary.BigEndian.Uint64(w[5:13])^binary.BigEndian.Uint64(c.oldAESBlock[:8])
 if tagged!=(seq|(uint64(1)<<63)){panic("old benchmark PN mismatch")}
 copy(out,w[13:])
 subtle.XORBytes(out[:len(w)-13],out[:len(w)-13],c.oldXORMask[:len(w)-13])
 return out[:len(w)-13]
}
var benchSink uint64
func bench(b *testing.B,v variant){
 c:=newCoder()
 tls23:=tlsFixture()
 other:=otherFixture()
 wires:=make([][]byte,batchSize)
 outputs:=make([][]byte,batchSize)
 for i:=range wires{wires[i]=make([]byte,1600);outputs[i]=make([]byte,1600)}
 fastPct:=99
 roll:=maskOneByte
 forceAES:=false
 switch v{
 case hybrid99NoXOR:roll=maskNone
 case hybrid99Tail1:
 case hybrid99Tail8:roll=maskEightBytes
 case hybrid95Tail1:fastPct=95
 case hybrid80Tail1:fastPct=80
 case allAESTail1:forceAES=true
 case oldFullXOR:
 default:panic("mode")
 }
 b.SetBytes(nPayload*batchSize);b.ReportAllocs();b.ResetTimer()
 var s uint64
 for j:=0;j<b.N;j++{
  for i:=0;i<batchSize;i++{
   seq:=uint64(j*batchSize+i+1)
   orig,retrans,wantFallback:=pick(i,fastPct,tls23,other)
   if v==oldFullXOR{
    w:=c.sealOldFullXOR(wires[i],orig,seq)
    p:=c.openOldFullXOR(w,outputs[i],seq)
    if len(p)!=len(orig){b.Fatal("old length")}
    s+=uint64(p[10])+seq
    continue
   }
   if forceAES{wantFallback=true}
   w:=c.seal(wires[i],orig,retrans,seq,roll,forceAES)
   isAES,p,e:=c.open(w,outputs[i],seq,roll)
   if e!=nil||isAES!=wantFallback||len(p)!=len(orig){b.Fatalf("open failed %v",e)}
   s+=uint64(p[10])+seq
  }
 }
 benchSink=s
}
func BenchmarkHybrid99NoTailXOR(b *testing.B){bench(b,hybrid99NoXOR)}
func BenchmarkHybrid99Last8Bits(b *testing.B){bench(b,hybrid99Tail1)}
func BenchmarkHybrid99Last8Bytes(b *testing.B){bench(b,hybrid99Tail8)}
func BenchmarkHybrid95Last8Bits(b *testing.B){bench(b,hybrid95Tail1)}
func BenchmarkHybrid80Last8Bits(b *testing.B){bench(b,hybrid80Tail1)}
func BenchmarkAlwaysAESLast8Bits(b *testing.B){bench(b,allAESTail1)}
func BenchmarkPreviousOptimizedFullXOR(b *testing.B){bench(b,oldFullXOR)}
