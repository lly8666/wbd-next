package main

import (
 "bytes"
 "crypto/sha256"
 "testing"
)

func boundaryTestSpec(boundary,trust bool,n int,flags byte,proto byte)Spec{
 p:=make([]byte,n);p[0]=0x45;p[2]=byte(n>>8);p[3]=byte(n)
 p[9]=proto
 p[20]=0xc3;p[21]=0xb5 // src port 50101
 p[22]=1;p[23]=0xbb // dest 443
 p[24]=0;p[25]=0;p[26]=0x4e;p[27]=0x20 // seq 20000
 p[32]=0x50;p[33]=flags
 if n>=45{copy(p[40:],[]byte{23,3,3,0,255})}
 return Spec{Port:mainPort,Seq:20000,Proto:proto,Flags:flags,
  Boundary:boundary,TrustedApp:trust,Stage:"late",Inner:p}
}
func TestRandomHoldAndSequence(t *testing.T){
 seen:=map[int64]bool{}
 for i:=0;i<800;i++{
  n:=randomHoldMs()
  if n<11000||n>21000{t.Fatalf("invalid random delay %d",n)}
  seen[n]=true
 }
 if len(seen)<750{t.Fatalf("weak random delay diversity %d",len(seen))}
 s:=boundaryTestSpec(false,true,1345,0x18,6)
 if gate(s,true,10999,11000){t.Fatal("fast admitted before hold")}
 if !gate(s,true,11000,11000){t.Fatal("fast excluded after hold")}
 s.Seq=1000
 if gate(s,true,21001,11000){t.Fatal("old handshake retransmit leaked after hold")}
 s.Seq=20000;s.TrustedApp=false
 if gate(s,true,21001,11000){t.Fatal("unknown flow leaked")}
 s.TrustedApp=true;s.Flags=0x11
 if gate(s,true,21001,11000){t.Fatal("FIN wrongly XOR")}
}
func TestPaddingOnlyLifecycleAndMTU(t *testing.T){
 coder,e:=newCoder();if e!=nil{t.Fatal(e)}
 for _,n:=range []int{40,52,360,1000,1345,1389}{
  for _,boundary:=range []bool{false,true}{
   s:=boundaryTestSpec(boundary,false,n,0x11,6)
   for trial:=0;trial<8;trial++{
    pad:=choosePadding(s)
    if !boundary&&pad!=0{t.Fatal("steady/unknown payload padded")}
    if boundary&&n<1389&&pad<=0{t.Fatal("lifecycle missed padding")}
    if pad>256{t.Fatal("random padding exceeded resource budget")}
    if n==1389&&pad!=0{t.Fatal("must not fragment oversize outer packet")}
    w,fill:=coder.seal(s.Inner,0,uint64(n*100+trial),pad)
    if len(w)+underlayOverhead>pathMTU{t.Fatal("MTU violation")}
    got,pn,padLen,e:=coder.open(w,0)
    if e!=nil||padLen!=pad||pn!=uint64(n*100+trial)||!bytes.Equal(got,s.Inner){
     t.Fatalf("decrypted original/padding mismatch n=%d pad=%d err=%v",n,pad,e)
    }
    if pad>0&&len(fill)!=pad{t.Fatal("random padding bytes absent")}
    w[len(w)-1]^=1
    if _,_,_,e=coder.open(w,0);e==nil{t.Fatal("AES tamper accepted")}
   }
  }
 }
}
func TestOrdinary1000PacketsHaveZeroPadding(t *testing.T){
 for i:=0;i<1000;i++{
  s:=boundaryTestSpec(false,i%2==0,40+(i%1200),0x18,6)
  if pad:=choosePadding(s);pad!=0{t.Fatalf("packet %d padded ordinary data %d",i,pad)}
 }
}
func TestFastNeverPadsAndRecover(t *testing.T){
 coder,e:=newCoder();if e!=nil{t.Fatal(e)}
 s:=boundaryTestSpec(false,true,1345,0x18,6)
 w,_:=coder.seal(s.Inner,1,2,0)
 got,pn,pad,e:=coder.open(w,1)
 if e!=nil||pn!=2||pad!=0||!bytes.Equal(got,s.Inner){t.Fatal("fast roundtrip failed")}
 s.Boundary=true
 if pad:=choosePadding(s);pad==0{t.Fatal("expected positive lifecycle pad")}
 p0,_:=coder.seal(s.Inner,0,4,choosePadding(s))
 p1,_:=coder.seal(s.Inner,0,5,choosePadding(s))
 h0:=sha256.Sum256(p0);h1:=sha256.Sum256(p1)
 if h0==h1{t.Fatal("boundary random ciphertext unexpectedly identical")}
}

func BenchmarkMixed99_AESBoundaryPad(b *testing.B){
 bench99(b,true)
}
func BenchmarkMixed99_NoPadding(b *testing.B){
 bench99(b,false)
}
func bench99(b *testing.B,withPad bool){
 coder,e:=newCoder();if e!=nil{b.Fatal(e)}
 fast:=boundaryTestSpec(false,true,1345,0x18,6)
 assertFast:=gate(fast,true,12000,11000)
 if !assertFast{b.Fatal("fast gate not operational")}
 edge:=boundaryTestSpec(true,false,40,0x02,6)
 b.SetBytes(int64(99*len(fast.Inner)+len(edge.Inner)))
 b.ReportAllocs();b.ResetTimer()
 for i:=0;i<b.N;i++{
  for k:=0;k<100;k++{
   spec:=fast;mode:=byte(1);pad:=0
   if k==0{
    spec=edge;mode=0
    if withPad{pad=choosePadding(spec)}
   }
   if mode==1&&!gate(spec,true,12000,11000){b.Fatal("fast gate failure")}
   w,_:=coder.seal(spec.Inner,mode,uint64(i*100+k+1),pad)
   p,_,gotPad,e:=coder.open(w,mode)
   if e!=nil||gotPad!=pad||len(p)!=len(spec.Inner){b.Fatal("roundtrip fail")}
  }
 }
}
