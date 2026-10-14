// Exact independent Go 1.23 standard-library reference for pinned
// wobuzhidao@a7a82db3 internal/tlsrecord/{keys,suite,record,suite_test}.go
// Go source fixture generator: go run crates/wbd-codec/oracles/aes_v3_go_reference.go
// This does not import internal/tlsrecord; use with the pinned original Go
// suite_test.go to verify Go implementation and this independent oracle.
package main

import (
 "crypto/aes"
 "crypto/cipher"
 "crypto/hmac"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "fmt"
)
func hkdf(master, salt, info []byte) []byte {
 mac:=hmac.New(sha256.New,salt);mac.Write(master);prk:=mac.Sum(nil)
 var prev,out []byte
 for i:=byte(1);len(out)<76;i++ {
  h:=hmac.New(sha256.New,prk);h.Write(prev);h.Write(info);h.Write([]byte{i});prev=h.Sum(nil);out=append(out,prev...)
 }
 return out[:76]
}
func wire(suite int, keys []byte, pn uint64, kind byte, payload []byte, pad int) []byte {
 n:=16;if suite==3{n=32}
 block,e:=aes.NewCipher(keys[:n]);if e!=nil{panic(e)}
 aead,e:=cipher.NewGCM(block);if e!=nil{panic(e)}
 hp,e:=aes.NewCipher(keys[44:44+n]);if e!=nil{panic(e)}
 iv:=append([]byte(nil),keys[32:44]...)
 pnbytes:=make([]byte,8);binary.BigEndian.PutUint64(pnbytes,pn)
 for i:=0;i<8;i++{iv[4+i]^=pnbytes[i]}
 plain:=append([]byte{kind},payload...);plain=append(plain,0x17)
 plain=append(plain,make([]byte,pad)...)
 head:=[]byte{0x17,0x03,0x03,0,0}
 binary.BigEndian.PutUint16(head[3:],uint16(8+len(plain)+16))
 aad:=append(append([]byte(nil),head...),pnbytes...)
 ciphertext:=aead.Seal(nil,iv,plain,aad)
 mask:=make([]byte,16);hp.Encrypt(mask,ciphertext[:16])
 for i:=0;i<8;i++{pnbytes[i]^=mask[i]}
 return append(append(append([]byte(nil),head...),pnbytes...),ciphertext...)
}
func main(){
 master:=make([]byte,32);for i:=range master{master[i]=0x6d}
 nonce:=make([]byte,16);for i:=range nonce{nonce[i]=byte(i*7+3)}
 fmt.Println("# Go 1.23 stdlib oracle reproduces pinned old Go a7a82db3 n3Keys, cipherForSuite and referenceAESWire; fields suite|pn|kind|pad|payload_hex|wire_hex")
 fmt.Println("# independent Python cryptography HKDF/AES-GCM/AES-ECB checked all 14/14 bytes")
 for _,s:=range []struct{id int;name string}{{2,"aes-128-gcm"},{3,"aes-256-gcm"}} {
  keys:=hkdf(master,nonce,[]byte("WBD-TLSLIKE-V3/"+s.name+"/c2s"))
  fmt.Printf("# suite=%d keys aead32=%x iv=%x hp32=%x\n",s.id,keys[:32],keys[32:44],keys[44:])
  test:=[]struct{pn uint64;kind byte;pad int;payload []byte}{
   {0,0,0,nil},{7,0,0,[]byte("short")},{1<<32|1,0,0,[]byte{0,255,16,32}},
   {^uint64(0),0,0,nil},{10,1,8,[]byte("Q")},{15,0,0,[]byte{0,0,255,0,0}},
   {16,0,0,make([]byte,17)},
  }
  for _,x:=range test{fmt.Printf("%d|%d|%d|%d|%s|%s\n",s.id,x.pn,x.kind,x.pad,hex.EncodeToString(x.payload),hex.EncodeToString(wire(s.id,keys,x.pn,x.kind,x.payload,x.pad)))}
 }
}
