//go:build windows && wbd_v4_embedded_go
package main

import "testing"

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
