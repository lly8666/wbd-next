// Isolated LAB ONLY: plain 0/1+PN vs encrypted 1-bit mode inside existing 8B PN.
//
// This test benchmarks only the real sender/receiver cryptographic framing
// change on the same machine and exact 1345B inner payload mix. No production
// WBD wire change, no connection classification or mode authorization here.
package main

import (
 "bytes"
 "crypto/aes"
 "crypto/cipher"
 "encoding/binary"
 "errors"
 "fmt"
 "math/bits"
 "testing"
)

const (
 innerPacketLen=1345
 wireMax=1500
 modeAes byte=0
 modeXor byte=1
 pnMask uint64=(uint64(1)<<63)-1
)
var sinkByte byte
var sinkNum uint64

type labCoder struct {
 aead cipher.AEAD
 hp cipher.Block
 iv [12]byte
 // Per-lane reusable scratch. A normal WBD owner processes each direction
 // serially; no shared/global mutable state. Zero per-record HP allocations.
 hpBlock [16]byte
 aadScratch [14]byte
 nonceScratch [12]byte
}
func newLabCoder() labCoder {
 // Repeatable independent lab keys; NOT production key derivation.
 k:=[16]byte{0x11,0x54,0xae,0x90,0xdd,0x32,0xc8,0xaf,0x18,0x06,0x32,0xdd,0x42,0x3a,0x11,0xe9}
 hk:=[16]byte{0xc3,0x10,0x0c,0x3a,0x50,0xe2,0x81,0x49,0x76,0xbb,0x21,0x39,0x77,0x00,0xdd,0xa3}
 block,_:=aes.NewCipher(k[:])
 hp,_:=aes.NewCipher(hk[:])
 aead,_:=cipher.NewGCM(block)
 return labCoder{aead:aead,hp:hp,iv:[12]byte{9,2,21,4,5,1,0,0,0,0,0,0}}
}
func (c *labCoder) nonce(pn uint64)[]byte {
 copy(c.nonceScratch[:],c.iv[:])
 for i:=0;i<8;i++{c.nonceScratch[4+i]^=byte(pn>>(56-8*i))}
 return c.nonceScratch[:]
}
func xorBody(x []byte,pn uint64) {
 mask:=bits.RotateLeft64(pn,17)^uint64(0x6c616e5f6e6f7365)
 var i int
 for ;i+8<=len(x);i+=8{
  binary.LittleEndian.PutUint64(x[i:i+8],
   binary.LittleEndian.Uint64(x[i:i+8])^mask)
 }
 for j:=0;i+j<len(x);j++ {x[i+j]^=byte(mask>>(8*j))}
}
func (c *labCoder) headerMask(sample []byte)uint64 {
 c.hp.Encrypt(c.hpBlock[:],sample[:16])
 return binary.BigEndian.Uint64(c.hpBlock[:8])
}
func (c *labCoder) seal(slot,plain []byte,pn uint64,mode byte,hidden bool) []byte{
 if pn>pnMask||mode>modeXor{panic("invalid lab PN/mode")}
 header:=14
 if hidden{header=13}
 need:=header+len(plain)
 if mode==modeAes{need+=16}
 if need>len(slot)||need>wireMax{panic("record exceeds test MTU")}
 w:=slot[:need]
 w[0]=0x17;w[1]=3;w[2]=3
 binary.BigEndian.PutUint16(w[3:5],uint16(need-5))
 if hidden {
  // Low 63 bits = monotonically allocated packet number; top bit = mode.
  // Mask from first 16 bytes of *already produced* ciphertext or XOR body.
  raw:=(uint64(mode)<<63)|pn
  binary.BigEndian.PutUint64(w[5:13],raw)
  if mode==modeAes{
   c.aead.Seal(w[13:13],c.nonce(pn),plain,w[:13])
  } else{
   copy(w[13:],plain)
   xorBody(w[13:],pn)
  }
  protected:=raw^c.headerMask(w[13:])
  binary.BigEndian.PutUint64(w[5:13],protected)
 }else{
  w[5]=mode
  binary.BigEndian.PutUint64(w[6:14],pn)
  if mode==modeAes {
   c.aead.Seal(w[14:14],c.nonce(pn),plain,w[:14])
  }else{
   copy(w[14:],plain)
   xorBody(w[14:],pn)
  }
 }
 return w
}
func (c *labCoder) open(w,dst []byte,hidden bool)(byte,uint64,[]byte,error){
 h:=14
 if hidden{h=13}
 if len(w)<h+41 || w[0]!=0x17||w[1]!=3||w[2]!=3||
  len(w)>wireMax||int(binary.BigEndian.Uint16(w[3:5]))!=len(w)-5{
  return 0,0,nil,errors.New("invalid outer record")
 }
 var pn uint64
 var mode byte
 aad:=c.aadScratch[:]
 if hidden{
  if len(w)<h+16{return 0,0,nil,errors.New("short HP sample")}
  mask:=c.headerMask(w[13:])
  tagged:=binary.BigEndian.Uint64(w[5:13])^mask
  mode=byte(tagged>>63);pn=tagged&pnMask
  copy(aad[:5],w[:5])
  binary.BigEndian.PutUint64(aad[5:13],tagged)
 }else{
  mode=w[5]
  pn=binary.BigEndian.Uint64(w[6:14])
  copy(aad[:14],w[:14])
 }
 if mode==modeAes{
  aa:=aad[:14];if hidden{aa=aad[:13]}
  plain,e:=c.aead.Open(dst[:0],c.nonce(pn),w[h:],aa)
  if e!=nil{return mode,pn,nil,e}
  return mode,pn,plain,nil
 }
 if mode!=modeXor{return mode,pn,nil,errors.New("unknown mode")}
 n:=len(w)-h
 if n>cap(dst){return mode,pn,nil,errors.New("decoder buffer")}
 buf:=dst[:n]
 copy(buf,w[h:])
 xorBody(buf,pn)
 return mode,pn,buf,nil
}
func packetFixture() []byte {
 // IPv4/TCP header and genuine-sized opaque TLS1.3 ciphertext fixture.
 // AAD and XOR sampling costs depend on bytes and size, not plaintext origin.
 v:=make([]byte,innerPacketLen+1)
 v[0]=0 // original lab "kind" byte
 v[1]=0x45
 binary.BigEndian.PutUint16(v[3:5],innerPacketLen)
 v[10]=6
 binary.BigEndian.PutUint16(v[21:23],50101)
 binary.BigEndian.PutUint16(v[23:25],443)
 v[33]=0x50;v[34]=0x18
 v[41]=0x17;v[42]=3;v[43]=3
 binary.BigEndian.PutUint16(v[44:46],uint16(innerPacketLen-45))
 for i:=46;i<len(v);i++{v[i]=byte((i*93+i/7)%256)}
 return v
}
func TestMaskedModeBothDirections(t *testing.T){
 c:=newLabCoder()
 p:=packetFixture()
 for _,hidden:=range []bool{false,true}{
  for _,mode:=range []byte{modeAes,modeXor}{
   for _,pn:=range []uint64{0,1,42,0x100000001,pnMask}{
    w:=c.seal(make([]byte,1600),p,pn,mode,hidden)
    gotMode,gotPn,got,e:=c.open(w,make([]byte,1600),hidden)
    if e!=nil||gotMode!=mode||gotPn!=pn||!bytes.Equal(got,p){
     t.Fatalf("hidden=%v mode=%d pn=%d got=%d/%d err=%v",hidden,mode,pn,gotMode,gotPn,e)
    }
    if w[0]!=23||w[1]!=3||w[2]!=3{t.Fatal("bad TLS-like header")}
    if hidden {
     if len(w)!=(13+len(p)+map[byte]int{0:16,1:0}[mode]){
      t.Fatal("unexpected hidden record length")
     }
     raw:=(uint64(mode)<<63)|pn
     if binary.BigEndian.Uint64(w[5:13])==raw{t.Fatal("mode + PN appeared plaintext")}
    }else if w[5]!=mode{t.Fatal("original mode byte changed")}
   }
  }
 }
}
func TestMaskedModeAesTamperAndXorIsUnauthenticated(t *testing.T){
 c:=newLabCoder();p:=packetFixture()
 aesW:=c.seal(make([]byte,1600),p,41,modeAes,true)
 flip:=append([]byte(nil),aesW...)
 flip[5]^=0x01 // changes protected PN but not mode
 _,_,_,e:=c.open(flip,make([]byte,1600),true)
 if e==nil{t.Fatal("AES modified protected PN should reject")}
 flip=append([]byte(nil),aesW...)
 flip[len(flip)-1]^=0x01
 _,_,_,e=c.open(flip,make([]byte,1600),true)
 if e==nil{t.Fatal("AES modified authentication tag should reject")}
 xW:=c.seal(make([]byte,1600),p,42,modeXor,true)
 flip=append([]byte(nil),xW...)
 flip[80]^=0x01
 gotMode,_,got,e:=c.open(flip,make([]byte,1600),true)
 if e!=nil||gotMode!=modeXor||bytes.Equal(got,p){
  t.Fatal("XOR malleability test unexpectedly rejected or lost its mutation")
 }
 // Critical: even a secret header protection key is NOT integrity of XOR.
 // The test above proves header masking alone cannot authenticate payload.
}
func TestSingleCipherBlockMaskAndNoPlainMode(t *testing.T){
 c:=newLabCoder();p:=packetFixture()
 for n:=0;n<1000;n++{
  mode:=modeXor
  if n%100==0{mode=modeAes}
  w:=c.seal(make([]byte,1600),p,uint64(n),mode,true)
  m,pn,p2,e:=c.open(w,make([]byte,1600),true)
  if e!=nil||m!=mode||pn!=uint64(n)||len(p2)!=len(p){
   t.Fatalf("mixed record failed i=%d %s",n,fmt.Sprint(e))
  }
 }
}
func benchMix(b *testing.B,hidden bool,fastPercent int) {
 c:=newLabCoder();p:=packetFixture()
 wires:=make([][]byte,100)
 outs:=make([][]byte,100)
 for i:=range wires {
  wires[i]=make([]byte,1600)
  outs[i]=make([]byte,1600)
 }
 b.SetBytes(int64(100*innerPacketLen))
 b.ReportAllocs()
 b.ResetTimer()
 var sink uint64
 for cycle:=0;cycle<b.N;cycle++ {
  for i:=0;i<100;i++{
   mode:=modeAes
   if i<fastPercent{mode=modeXor}
   pn:=uint64(cycle*100+i)
   w:=c.seal(wires[i],p,pn,mode,hidden)
   gotMode,gotPn,got,e:=c.open(w,outs[i],hidden)
   if e!=nil||gotMode!=mode||gotPn!=pn||len(got)!=len(p){b.Fatalf("bad A/B loop %v",e)}
   sink+=uint64(got[41])^uint64(gotPn)
  }
 }
 sinkNum=sink
}
func BenchmarkPlainModeMixed99(b *testing.B){benchMix(b,false,99)}
func BenchmarkHiddenPNModeMixed99(b *testing.B){benchMix(b,true,99)}
func BenchmarkPlainModeAllAES(b *testing.B){benchMix(b,false,0)}
func BenchmarkHiddenPNModeAllAES(b *testing.B){benchMix(b,true,0)}
func BenchmarkPlainModeAllXOR(b *testing.B){benchMix(b,false,100)}
func BenchmarkHiddenPNModeAllXOR(b *testing.B){benchMix(b,true,100)}
func benchParse(b *testing.B,hidden bool){
 c:=newLabCoder();p:=packetFixture()
 wire:=c.seal(make([]byte,1600),p,123456,modeXor,hidden)
 b.ReportAllocs()
 b.ResetTimer()
 var sink uint64
 for i:=0;i<b.N;i++{
  if hidden{
   tagged:=binary.BigEndian.Uint64(wire[5:13])^c.headerMask(wire[13:])
   sink+=tagged
  }else{
   sink+=uint64(wire[5])+binary.BigEndian.Uint64(wire[6:14])
  }
 }
 sinkNum=sink
}
func BenchmarkReadPlainModeOnly(b *testing.B){benchParse(b,false)}
func BenchmarkReadHiddenModeOnly(b *testing.B){benchParse(b,true)}
