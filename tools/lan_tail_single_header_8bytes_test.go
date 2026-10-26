// One-header correction: genuine TLS23 keeps its ORIGINAL 5B header, plus
// trailer 2B within a modified outer length. It is restored before delivering
// to inner TLS. Non23/retrans23 gets AES128-GCM and newly emitted 5B 23 header.
// Final 8 BYTES of the entire resulting record get per-counter rolling XOR.
// Minimal CPU benchmark only, NOT standards-compliant TLS, not WBD production.
package tailone

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "crypto/subtle"
 "encoding/binary"
 "errors"
 "math/bits"
 "testing"
)

const recordBytes=1345
const batchCount=100
const markerLen=2
type tailStyle uint8
const(
 tailNone tailStyle=iota
 tailLast1
 tailLast8Loop
 tailLast8Word
)
type benchCase uint8
const(
 one99Word benchCase=iota
 one99ByteLoop
 one99NoXOR
 one99Last1
 one95Word
 one80Word
 oneAllAESWord
 oldDoubleHeader99Word
 oldFullXOR
)
type session struct{
 aead cipher.AEAD
 iv [12]byte
 nonceBuf [12]byte
 aadBuf [15]byte
 oldHP cipher.Block
 oldBlock [16]byte
 oldMask [1600]byte
}
func newSession()*session{
 key:=[16]byte{3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18}
 hpKey:=[16]byte{0xc3,0x10,0x0c,0x3a,0x50,0xe2,0x81,0x49,0x76,0xbb,0x21,0x39,0x77,0x00,0xdd,0xa3}
 b,e:=aes.NewCipher(key[:]);if e!=nil{panic(e)}
 hp,e:=aes.NewCipher(hpKey[:]);if e!=nil{panic(e)}
 g,e:=cipher.NewGCM(b);if e!=nil{panic(e)}
 return &session{aead:g,oldHP:hp,iv:[12]byte{1,2,3,4,0,0,0,0,0,0,0,0}}
}
func (s *session) nonce(counter uint64)[]byte{
 copy(s.nonceBuf[:],s.iv[:])
 for i:=0;i<8;i++{s.nonceBuf[4+i]^=byte(counter>>(56-8*i))}
 return s.nonceBuf[:]
}
func marker(counter uint64,aesFallback bool)uint16{
 v:=uint16(counter*137+59)
 if aesFallback {return 0xf000|(v&0x0fff)}
 return v%0xf000
}
func tailWord(counter uint64)uint64{
 return bits.RotateLeft64(counter*0x9e3779b97f4a7c15^0x6c616e5f6e6f7365,17)
}
func rollTail(buf []byte,counter uint64,style tailStyle){
 if style==tailNone{return}
 word:=tailWord(counter)
 switch style{
 case tailLast1:
  buf[len(buf)-1]^=byte(word)
 case tailLast8Loop:
  for j:=0;j<8;j++{buf[len(buf)-1-j]^=byte(word>>(8*j))}
 case tailLast8Word:
  b:=buf[len(buf)-8:]
  binary.LittleEndian.PutUint64(b,binary.LittleEndian.Uint64(b)^bits.ReverseBytes64(word))
 default:panic("invalid tail style")
 }
}
func (s *session) aad(head []byte,m uint16,counter uint64)[]byte{
 copy(s.aadBuf[:5],head[:5])
 binary.BigEndian.PutUint16(s.aadBuf[5:7],m)
 binary.BigEndian.PutUint64(s.aadBuf[7:15],counter)
 return s.aadBuf[:]
}
func genuineTLSRecord(data []byte)bool{
 return len(data)>=5 && data[0]==0x17 && data[1]==3 && data[2]==3 &&
  int(binary.BigEndian.Uint16(data[3:5]))==len(data)-5
}
func (s *session) seal(w,inner []byte,retrans,verified bool,counter uint64,tail tailStyle,doubleHeader,forceAES bool)[]byte{
 fast:=verified && !retrans && genuineTLSRecord(inner) && !forceAES
 total:=len(inner)+markerLen
 if !fast {total+=5+s.aead.Overhead()}
 if fast && doubleHeader {total+=5}
 if total>len(w){panic("small output")}
 out:=w[:total]
 mark:=marker(counter,!fast)
 if fast{
  if doubleHeader{
   out[0]=0x17;out[1]=3;out[2]=3
   binary.BigEndian.PutUint16(out[3:5],uint16(total-5))
   copy(out[5:total-2],inner)
  }else{
   // Exactly ONE actual original TLS header, NOT a new outer header.
   copy(out[:len(inner)],inner)
   // Custom envelope's +2B trailer must be counted to parse one record.
   // Before giving to inner TLS, remove trailer and restore length.
   binary.BigEndian.PutUint16(out[3:5],uint16(total-5))
  }
 }else{
  out[0]=0x17;out[1]=3;out[2]=3
  binary.BigEndian.PutUint16(out[3:5],uint16(total-5))
  s.aead.Seal(out[5:5],s.nonce(counter),inner,s.aad(out[:5],mark,counter))
 }
 binary.BigEndian.PutUint16(out[total-2:],mark)
 rollTail(out,counter,tail)
 return out
}
func (s *session) open(w,scratch []byte,counter uint64,tail tailStyle,doubleHeader bool)(bool,[]byte,error){
 if len(w)<8||len(scratch)<len(w)||
  w[0]!=0x17||w[1]!=3||w[2]!=3||
  int(binary.BigEndian.Uint16(w[3:5]))!=len(w)-5{
  return false,nil,errors.New("invalid single TLS-like record")
 }
 b:=scratch[:len(w)]
 copy(b,w)
 rollTail(b,counter,tail)
 m:=binary.BigEndian.Uint16(b[len(b)-2:])
 aesFallback:=m>=0xf000
 if m!=marker(counter,aesFallback){
  return false,nil,errors.New("implicit counter mismatch")
 }
 if aesFallback{
  text,e:=s.aead.Open(b[5:5],s.nonce(counter),b[5:len(b)-2],s.aad(b[:5],m,counter))
  if e!=nil{return true,nil,e}
  return true,text,nil
 }
 if doubleHeader{
  plain:=b[5:len(b)-2]
  if !genuineTLSRecord(plain){return false,nil,errors.New("bad nested original TLS record")}
  return false,plain,nil
 }
 plain:=b[:len(b)-2]
 if len(plain)<5{return false,nil,errors.New("fast frame short")}
 binary.BigEndian.PutUint16(plain[3:5],uint16(len(plain)-5))
 if !genuineTLSRecord(plain){return false,nil,errors.New("bad recovered TLS record")}
 return false,plain,nil
}
func innerTLSFixture()*tlsFixture{
 key:=[16]byte{0x31,0x44,0x53,0x67,0x81,0xa2,0xb3,0xc4,0xd5,0xe6,0xf7,0x08,0x19,0x2a,0x3b,0x4c}
 block,_:=aes.NewCipher(key[:])
 g,_:=cipher.NewGCM(block)
 var nonce [12]byte
 nonce[11]=1
 p:=make([]byte,recordBytes-5-16)
 for i:=range p{p[i]=byte((i*47+i/13)%256)}
 full:=make([]byte,recordBytes)
 full[0]=0x17;full[1]=3;full[2]=3
 binary.BigEndian.PutUint16(full[3:5],uint16(recordBytes-5))
 g.Seal(full[5:5],nonce[:],p,full[:5])
 return &tlsFixture{record:full,original:p,aead:g,nonce:nonce}
}
type tlsFixture struct{
 record []byte
 original []byte
 aead cipher.AEAD
 nonce [12]byte
}
func (f *tlsFixture) decrypt(rec []byte)([]byte,error){
 if !genuineTLSRecord(rec){return nil,errors.New("bad outer TLS length")}
 return f.aead.Open(nil,f.nonce[:],rec[5:],rec[:5])
}
func otherFixture(original []byte)[]byte{
 p:=append([]byte(nil),original...)
 p[0]=0x16
 return p
}
func inputFor(i,fastPercent int,tlsRec,other []byte)([]byte,bool,bool){
 if i<fastPercent {return tlsRec,false,false}
 if (i-fastPercent)%2==0{return other,false,true}
 return tlsRec,true,true
}
func (s *session) oldSeal(w,inner []byte,seq uint64)[]byte{
 n:=5+8+len(inner)
 b:=w[:n];b[0]=0x17;b[1]=3;b[2]=3
 binary.BigEndian.PutUint16(b[3:5],uint16(n-5))
 copy(b[13:],inner)
 k:=bits.RotateLeft64(seq,17)^uint64(0x6c616e5f6e6f7365)
 binary.LittleEndian.PutUint64(s.oldMask[:8],k)
 filled:=8
 for filled<len(inner){filled+=copy(s.oldMask[filled:len(inner)],s.oldMask[:filled])}
 subtle.XORBytes(b[13:],b[13:],s.oldMask[:len(inner)])
 s.oldHP.Encrypt(s.oldBlock[:],b[13:29])
 binary.BigEndian.PutUint64(b[5:13],(seq|(uint64(1)<<63))^binary.BigEndian.Uint64(s.oldBlock[:8]))
 return b
}
func (s *session) oldOpen(w,out []byte,seq uint64)[]byte{
 s.oldHP.Encrypt(s.oldBlock[:],w[13:29])
 tagged:=binary.BigEndian.Uint64(w[5:13])^binary.BigEndian.Uint64(s.oldBlock[:8])
 if tagged!=(seq|(uint64(1)<<63)){panic("old PN mismatch")}
 copy(out,w[13:])
 subtle.XORBytes(out[:len(w)-13],out[:len(w)-13],s.oldMask[:len(w)-13])
 return out[:len(w)-13]
}
func TestTrueInnerTLSAEADRoundtripSingleHeader(t *testing.T){
 f:=innerTLSFixture()
 orig,e:=f.decrypt(f.record)
 if e!=nil||!bytes.Equal(orig,f.original){t.Fatal("real AES-GCM TLS-style AEAD fixture invalid")}
 var w [1600]byte
 var out [1600]byte
 c:=newSession()
 for _,roll:=range []tailStyle{tailNone,tailLast1,tailLast8Loop,tailLast8Word}{
  for _,dbl:=range []bool{false,true}{
   for _,seq:=range []uint64{0,1,42,0x100000001}{
    rec:=c.seal(w[:],f.record,false,true,seq,roll,dbl,false)
    want:=recordBytes+2
    if dbl{want+=5}
    if len(rec)!=want{t.Fatalf("record has duplicated header? got=%d want=%d",len(rec),want)}
    if !dbl&&(!bytes.Equal(rec[:3],f.record[:3])||binary.BigEndian.Uint16(rec[3:5])!=uint16(recordBytes-5+2)){
     t.Fatal("single header not from original TLS")
    }
    mode,got,err:=c.open(rec,out[:],seq,roll,dbl)
    if err!=nil||mode||!bytes.Equal(got,f.record){t.Fatalf("open mode=%v double=%v seq=%d: %v",roll,dbl,seq,err)}
    plaintext,e:=f.decrypt(got)
    if e!=nil||!bytes.Equal(plaintext,f.original){t.Fatal("the original real TLS AEAD tag must remain valid after inverse transform")}
   }
  }
 }
}
func TestNon23AndRetrans23UseAESAndRestoreBytes(t *testing.T){
 f:=innerTLSFixture()
 other:=otherFixture(f.record)
 c:=newSession()
 var w,out [1600]byte
 for _,roll:=range []tailStyle{tailNone,tailLast1,tailLast8Loop,tailLast8Word}{
  for _,fast:=range []int{0,80,95,99,100}{
   for i:=0;i<1000;i++{
    data,retrans,wantAES:=inputFor(i%100,fast,f.record,other)
    seq:=uint64(i+1001)
    enc:=c.seal(w[:],data,retrans,true,seq,roll,false,false)
    gotAES,got,err:=c.open(enc,out[:],seq,roll,false)
    if err!=nil||gotAES!=wantAES||!bytes.Equal(got,data){
     t.Fatalf("fastpct=%d seq=%d roll=%d err=%v",fast,seq,roll,err)
    }
    want:=recordBytes+2
    if wantAES{want+=5+16}
    if len(enc)!=want{t.Fatal("incorrect record wire overhead")}
   }
  }
 }
}
func TestMarkerMutationAndTLSHeaderCaveat(t *testing.T){
 f:=innerTLSFixture()
 c:=newSession()
 var w,out [1600]byte
 seq:=uint64(19)
 fast:=c.seal(w[:],f.record,false,true,seq,tailLast8Word,false,false)
 if bytes.Equal(fast[5:8],[]byte{0x17,3,3}){t.Fatal("cannot have visible duplicated TLS header at offset 5")}
 // The original TLS recipient cannot accept the modified length and tail:
 if _,err:=f.decrypt(fast);err==nil{t.Fatal("unprocessed transport wrapping is NOT genuine TLS")}
 tampered:=append([]byte(nil),fast...)
 tampered[111]^=0x40
 aes,got,err:=c.open(tampered,out[:],seq,tailLast8Word,false)
 if err!=nil||aes||bytes.Equal(got,f.record){t.Fatal("fast mode is NOT authenticated; test must show tamper accepted")}
 // Falling back AES does provide genuine AEAD integrity on unchanged mode.
 fallback:=c.seal(w[:],otherFixture(f.record),false,true,seq,tailLast8Word,false,false)
 tampered=append([]byte(nil),fallback...)
 tampered[110]^=0x80
 _,_,err=c.open(tampered,out[:],seq,tailLast8Word,false)
 if err==nil{t.Fatal("AES body tamper must reject")}
}
var benchSink uint64
func benchmark(b *testing.B,v benchCase){
 c:=newSession();f:=innerTLSFixture();other:=otherFixture(f.record)
 wire:=make([][]byte,batchCount)
 out:=make([][]byte,batchCount)
 for i:=range wire{wire[i]=make([]byte,1600);out[i]=make([]byte,1600)}
 pct:=99;style:=tailLast8Word;double:=false;forceAES:=false
 switch v{
 case one99Word:
 case one99ByteLoop:style=tailLast8Loop
 case one99NoXOR:style=tailNone
 case one99Last1:style=tailLast1
 case one95Word:pct=95
 case one80Word:pct=80
 case oneAllAESWord:forceAES=true
 case oldDoubleHeader99Word:double=true
 case oldFullXOR:
 default:panic("bad bench case")
 }
 b.SetBytes(int64(recordBytes*batchCount))
 b.ReportAllocs();b.ResetTimer()
 var acc uint64
 for rep:=0;rep<b.N;rep++{
  for i:=0;i<batchCount;i++{
   seq:=uint64(rep*batchCount+i+1)
   data,retrans,wasAES:=inputFor(i,pct,f.record,other)
   if v==oldFullXOR{
    rec:=c.oldSeal(wire[i],data,seq)
    got:=c.oldOpen(rec,out[i],seq)
    if len(got)!=len(data){b.Fatal("old full XOR result")}
    acc+=uint64(got[10])^seq
    continue
   }
   rec:=c.seal(wire[i],data,retrans,true,seq,style,double,forceAES)
   isAES,got,err:=c.open(rec,out[i],seq,style,double)
   if err!=nil||len(got)!=len(data)||isAES!=(wasAES||forceAES){b.Fatalf("decode %v",err)}
   acc+=uint64(got[10])^seq
  }
 }
 benchSink=acc
}
func BenchmarkSingleHeader99Tail8Word(b *testing.B){benchmark(b,one99Word)}
func BenchmarkSingleHeader99Tail8ByteLoop(b *testing.B){benchmark(b,one99ByteLoop)}
func BenchmarkSingleHeader99NoTail(b *testing.B){benchmark(b,one99NoXOR)}
func BenchmarkSingleHeader99Tail1(b *testing.B){benchmark(b,one99Last1)}
func BenchmarkSingleHeader95Tail8Word(b *testing.B){benchmark(b,one95Word)}
func BenchmarkSingleHeader80Tail8Word(b *testing.B){benchmark(b,one80Word)}
func BenchmarkSingleHeaderAllAESTail8Word(b *testing.B){benchmark(b,oneAllAESWord)}
func BenchmarkOldDoubleHeader99Tail8Word(b *testing.B){benchmark(b,oldDoubleHeader99Word)}
func BenchmarkOldFullXOR(b *testing.B){benchmark(b,oldFullXOR)}
