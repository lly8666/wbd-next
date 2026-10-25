package main

import (
 "bytes"
 "crypto/sha256"
 "testing"
)

// An intentionally TEST-ONLY retransmission cost comparison. The host's
// actual kernel TCP retransmission behavior must never be disabled.
// Each "connection cycle" has 99 app ciphertext full IPv4 packets and one
// protected initial ClientHello-size IPv4 packet, optionally + TWO deliberately
// repeated ClientHello packets (one early and one after stable stage).
func flowCaseBenchmark(b *testing.B, manualRepeats bool) {
 coder,e:=newCoder();if e!=nil{b.Fatal(e)}
 // Real test ClientHello size was 517 bytes in the prior OpenSSL MemoryBIO
 // corpus; AES-GCM CPU/padding cost is length-dependent, not bytes-dependent.
 helloBytes:=make([]byte,517)
 copy(helloBytes[:5],[]byte{22,3,1,2,0})
 copy(helloBytes[45:],[]byte(innerPublicSNI))
 handshake:=packet(mainPort,1000,6,0x18,helloBytes)
 assertHS:=Spec{Label:"synthetic_handshake",Port:mainPort,Seq:1000,Proto:6,
  Flags:0x18,Boundary:true,TrustedApp:false,Inner:handshake}
 fast:=boundaryTestSpec(false,true,1345,0x18,6)
 if gate(assertHS,true,22000,11000)||!gate(fast,true,22000,11000){
  b.Fatal("refuse to benchmark broken test gate")
 }
 stableBytes:=len(fast.Inner)*99
 b.SetBytes(int64(stableBytes+len(handshake)))
 b.ReportAllocs()
 b.ResetTimer()
 for i:=0;i<b.N;i++ {
  n:=uint64(i)*104+1
  testAes:=func(){
   pad:=choosePadding(assertHS)
   w,_:=coder.seal(handshake,0,n,pad);n++
   decoded,_,observedPad,err:=coder.open(w,0)
   if err!=nil||len(decoded)!=len(handshake)||observedPad!=pad{
    b.Fatal("auth record roundtrip",err)
   }
  }
  testAes() // One original ClientHello always stays AES.
  if manualRepeats {testAes()} // Artificial early handshake re-send.
  for j:=0;j<99;j++{
   w,_:=coder.seal(fast.Inner,1,n,0);n++
   decoded,_,observedPad,err:=coder.open(w,1)
   if err!=nil||observedPad!=0||len(decoded)!=len(fast.Inner){b.Fatal("fast roundtrip",err)}
  }
  if manualRepeats {testAes()} // Artificial late old-sequence resend, AES.
 }
}
func BenchmarkFlowWith2SyntheticHandshakeResends(b *testing.B){
 flowCaseBenchmark(b,true)
}
func BenchmarkFlowNoSyntheticHandshakeResends(b *testing.B){
 flowCaseBenchmark(b,false)
}
func TestModeFieldAgainstTrustedReceiverExpectation(t *testing.T){
 coder,e:=newCoder();if e!=nil{t.Fatal(e)}
 original:=boundaryTestSpec(false,true,1345,0x18,6)
 aes,_:=coder.seal(original.Inner,0,9,0)
 fast,_:=coder.seal(original.Inner,1,10,0)
 if aes[5]!=0||fast[5]!=1 {t.Fatal("explicit mode byte incorrect")}
 if _,_,_,e=coder.open(aes,0);e!=nil{t.Fatal(e)}
 if _,_,_,e=coder.open(fast,1);e!=nil{t.Fatal(e)}
 altered:=append([]byte{},aes...)
 altered[5]=1
 if _,_,_,e=coder.open(altered,0);e==nil{t.Fatal("forged AES->XOR admission accepted")}
 altered=append([]byte{},fast...)
 altered[5]=0
 if _,_,_,e=coder.open(altered,1);e==nil{t.Fatal("forged XOR->AES admission accepted")}
 altered=append([]byte{},aes...)
 altered[5]=2
 if _,_,_,e=coder.open(altered,0);e==nil{t.Fatal("unknown mode accepted")}
 altered=append([]byte{},aes...)
 altered[6]^=1 // AES public PN is part of authenticated AAD and nonce.
 if _,_,_,e=coder.open(altered,0);e==nil{t.Fatal("modified PN authenticated")}
 altered=append([]byte{},aes...)
 altered[len(altered)-1]^=1 // Ciphertext/tag modification must fail.
 if _,_,_,e=coder.open(altered,0);e==nil{t.Fatal("modified ciphertext/tag authenticated")}
 // Deliberately document that PN-XOR is not cryptographic authentication:
 // public decoder can always invert it, even after arbitrary rewrapping.
 recovered,_,_,e:=coder.open(fast,1)
 if e!=nil||!bytes.Equal(recovered,original.Inner){t.Fatal("XOR not recovered")}
 h:=sha256.Sum256(recovered)
 if h!=sha256.Sum256(original.Inner){t.Fatal("XOR recovered mismatch")}
}
func TestFlowStartGuardEvenAfterClock(t *testing.T){
 s:=boundaryTestSpec(false,true,1345,0x18,6)
 if gate(s,false,21000,11000){t.Fatal("elapsed time must NOT replace TLS Finished verification")}
 if gate(s,true,10999,11000){t.Fatal("fast before random deadline")}
 if !gate(s,true,21000,11000){t.Fatal("normal fast after deadline")}
 s.Seq=1000
 if gate(s,true,21000,11000){t.Fatal("expired clock leaked original handshake seq")}
}
