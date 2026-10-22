//go:build windows && wbd_v4_embedded_go
package main

import (
 "testing"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)

func TestM0PLAN025WindowsNativeV4OutOfOrderFirstAndRealCumulativeACK(t *testing.T){
 w:=newM0V4RxWindow(1000)
 if ok,e:=w.Check(1200,100);!ok||e!=nil{t.Fatalf("ahead check=%v %v",ok,e)}
 if ack,e:=w.Copied(1200,100);e!=nil||ack!=1000{
  t.Fatalf("hole falsely ACKed: %d %v",ack,e)
 }
 if ok,e:=w.Check(1200,100);ok||e!=nil{t.Fatalf("duplicate should drop not close: %v %v",ok,e)}
 if ok,e:=w.Check(1220,80);ok||e!=nil{t.Fatalf("overlapping window admitted: %v %v",ok,e)}
 if ack,e:=w.Copied(1000,200);e!=nil||ack!=1300{
  t.Fatalf("real contiguous ACK after first arrives: %d %v",ack,e)
 }
 if ack,e:=w.Copied(1300,200);e!=nil||ack!=1500{
  t.Fatalf("in order wrong: %d %v",ack,e)
 }
 if ok,e:=w.Check(1000,100);ok||e!=nil{t.Fatalf("stale replay incorrectly admitted")}
 if ok,e:=w.Check(1500+m0V4RxAheadMax,40);ok||e==nil{
  t.Fatal("unbounded future seq accepted")
 }
}
func TestM0PLAN025WindowsNativeV4SerialWrapAndOutOfOrderNoFalseACK(t *testing.T){
 w:=newM0V4RxWindow(^uint32(0)-99)
 if ack,e:=w.Copied(100,100);e!=nil||ack!=^uint32(0)-99{
  t.Fatalf("future wrapped TCP record falsely ACKed %d err %v",ack,e)
 }
 if ack,e:=w.Copied(^uint32(0)-99,200);e!=nil||ack!=200{
  t.Fatalf("actual missing record did not advance wrapped cumulative ACK %d err %v",ack,e)
 }
 if w.Pending()!=0{t.Fatalf("unreleased verified receipt map %d",w.Pending())}
}

func TestM0PLAN026WindowsNativeV4ParallelModeDoesNotDowngradeAndStalledCarrierFails(t *testing.T){
 flow:=faketcp.ClientFlow{
  LocalIP:[4]byte{10,25,0,2},PeerIP:[4]byte{10,25,0,1},
  LocalPort:41001,PeerPort:443,
 }
 owner:=&realityfront.V4WindowsAuthenticatedClientOwner{}
 ep:=&faketcp.NpcapEndpoint{}
 inbound:=make(chan faketcp.Segment,1)
 for _,mode:=range []m0WindowsV4Mode{m0WinModeGame2,m0WinModeGame4,"unknown"}{
  if got,e:=newM0NativeV4PeerForMode(owner,ep,flow,inbound,mode);
   e==nil||got!=nil{t.Fatalf("unsupported Game group silently downgraded to one-lane Normal mode=%s",mode)}
 }
 for _,mode:=range []m0WindowsV4Mode{m0WinModeNormal,m0WinModeFixed,m0WinModeAuto}{
  p,e:=newM0NativeV4PeerForMode(owner,ep,flow,inbound,mode)
  if e!=nil||p==nil||p.mode!=mode||p.blockID!=1{
   t.Fatalf("original TLS peer mode selection incorrect %s error %v",mode,e)
  }
  p.pending=append(p.pending,m0NativeV4Outbound{
   seq:500,wire:[]byte{1,2,3},sentAt:time.Now().Add(-5*time.Second),
   lastSent:time.Now().Add(-2*time.Second),retries:8,
  })
  // This path must never pretend a stalled TCP FrozenRecord was ACKed:
  // the exact maximum retry exhaustion is an explicit bounded failure.
  if tx,err:=p.retryOne(time.Now());tx||err==nil{
   t.Fatalf("stalled original carrier silently accepted mode=%s",mode)
  }
  snap:=p.Stats()
  if snap.Mode!=mode||snap.TxPackets!=0||snap.RxFirstDelivered!=0{
   t.Fatalf("not a zero-delivery public performance receipt: %+v",snap)
  }
 }
}

func TestM0PLAN024WindowsM2IndependentAuthenticatedAheadDoesNotForgeTCPACK(t *testing.T){
 w:=newM0V4RxWindow(1000)
 far:=uint32(1000+m0V4RxAheadMax+2048)
 if w.IndependentAEADCandidate(far,120)!=true{
  t.Fatal("bounded independent M3 authenticated out-of-order candidate denied")
 }
 if _,err:=w.Check(far,120);err==nil{
  t.Fatal("too-far packet falsely added to 128KiB cumulative ACK ledger")
 }
 if w.Ack()!=1000||w.Pending()!=0{
  t.Fatalf("presentation ACK falsely advanced: ack=%d pending=%d",w.Ack(),w.Pending())
 }
 if w.IndependentAEADCandidate(uint32(1000+m0V4IndependentAEADLookahead),120){
  t.Fatal("unbounded untrusted serial candidate admitted")
 }
 if w.IndependentAEADCandidate(uint32(999),120){
  t.Fatal("stale untrusted original before current cumulative ACK admitted")
 }
 if w.IndependentAEADCandidate(far,3000){
  t.Fatal("oversize record bypassed kernel/AEAD limit")
 }
}
