//go:build windows && wbd_v4_embedded_go
package main

import (
 "context"
 "os"
 "strings"
 "testing"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
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
  if e!=nil||p==nil||p.mode!=mode||len(p.pending)!=0{
   t.Fatalf("original TLS peer selection must not pre-create legacy Go FEC source blocks %s error %v",mode,e)
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

func TestM0PLAN024WindowsBoundedPresentationACKLedgerFullMissingHeadReleases(t *testing.T){
 w:=newM0V4RxWindow(2000)
 for i:=1;i<=m0V4RxSlots;i++{
  seq:=uint32(2000+i*100)
  if ack,e:=w.Copied(seq,100);e!=nil||ack!=2000{
   t.Fatalf("future slot %d falsely ACKed: %d %v",i,ack,e)
  }
 }
 if w.Pending()!=m0V4RxSlots{t.Fatalf("expected full bounded bitmap, got %d",w.Pending())}
 if w.IndependentAEADCandidate(2000+100*uint32(m0V4RxSlots+1),120)!=true{
  t.Fatal("authentic independent candidate blocked by full ACK presentation map")
 }
 if ack,e:=w.Copied(2000,100);e!=nil||
   ack!=uint32(2000+100*(m0V4RxSlots+1)){
  t.Fatalf("late actual gap head failed to retire contiguous 256 rows: %d %v",ack,e)
 }
 if w.Pending()!=0 {t.Fatalf("late gap ACK did not drain bounded ledger %d",w.Pending())}
}


func TestM0PLAN024AuthenticatedHighWaterFreshBeyondFourMiBOldCarrierHole(t *testing.T){
 // One old lost presentation-only carrier byte may never be ACKed.
 // Future valid independent M3 records must still be offered without
 // inventing a TCP ACK or allocating a 4MiB Go receipt map.
 const base=uint32(10000)
 w:=newM0V4RxWindow(base)
 first:=base+m0V4RxAheadMax+2048
 // A raw/untrusted jump cannot self-advance the authenticated high-water.
 if w.IndependentAEADCandidate(first+2*m0V4IndependentAEADLookahead,1024){
  t.Fatal("unauthenticated far carrier bypassed M3 proximity bound")
 }
 for i:=0;i<6000;i++{
  seq:=first+uint32(i)*1024
  if !w.IndependentAEADCandidate(seq,1024){
   t.Fatalf("fresh seq blocked behind old cumulative ACK after %d valid records",i)
  }
  // This callback represents the sole M3-verified+Wintun-accepted path;
  // production calls it only after actual Rust verification.
  w.NoteAuthenticated(seq,1024)
 }
 if w.Ack()!=base||w.Pending()!=0{
  t.Fatalf("old carrier gap forged ACK or grew map ack=%d pending=%d",w.Ack(),w.Pending())
 }
 if w.IndependentAEADCandidate(first+uint32(6000*1024)+m0V4IndependentAEADLookahead,1024){
  t.Fatal("far unauthenticated packet admitted outside moving M3 bound")
 }
 if w.IndependentAEADCandidate(first+uint32(6000*1024),3000){
  t.Fatal("oversize packet admitted after genuine M3 progress")
 }
}
func TestM0PLAN024AuthenticatedHighWaterGapSpanningTCP32Wrap(t *testing.T){
 start:=^uint32(0)-uint32(m0V4RxAheadMax/2)
 w:=newM0V4RxWindow(start)
 first:=start+uint32(m0V4RxAheadMax+2048)
 for i:=0;i<5000;i++{
  seq:=first+uint32(i)*1024
  if !w.IndependentAEADCandidate(seq,1024){
   t.Fatalf("real wrap candidate blocked after %d authenticated ahead",i)
  }
  w.NoteAuthenticated(seq,1024)
 }
 if w.Ack()!=start||w.Pending()!=0{
  t.Fatal("authenticated independent wrap forged original carrier ACK")
 }
}

// This test lives in the embedded native test compilation, never the
// ordinary Windows legacy build without the source-locked Rust bridge.
func TestM0WindowsAutoOriginalControlRequestAndOwnedStop(t *testing.T){
 r,w,err:=os.Pipe();if err!=nil{t.Fatal(err)}
 defer r.Close();defer w.Close()
 ctx,cancel:=context.WithCancel(context.Background())
 defer cancel()
 requests:=make(chan realityfront.FecV2Profile,2)
 go watchM0NativeV4AutoControl(ctx,r,cancel,requests)
 if _,err=w.WriteString("fec.profile=light\n");err!=nil{t.Fatal(err)}
 select{
 case p:=<-requests:
  if p!=realityfront.FecV2Light{t.Fatalf("unexpected Auto profile %d",p)}
 case <-time.After(time.Second):t.Fatal("real Auto control ignored profile change")
 }
 if _,err=w.WriteString("stop\n");err!=nil{t.Fatal(err)}
 select{
 case <-ctx.Done():
 case <-time.After(time.Second):t.Fatal("Auto stdin stop failed to cancel native owner")
 }
}

func TestM0RemediationHalfAndFullWrapUnauthenticatedNeverForgesCarrierACK(t *testing.T){
 w:=newM0V4RxWindow(1000)
 first:=uint32(1000+m0V4RxAheadMax+2048)
 w.NoteAuthenticated(first,100) // only callable after real Rust AEAD+Wintun copy
 if !w.independentOnly{t.Fatal("did not detach after actual far-ahead verified record")}
 for _,high:=range []uint32{0x7ffffffe,0x80000080,0xfffffff0,0x000000a0}{
  // Simulated already-authenticated Rust high watermark at exact boundary.
  w.authenticatedHigh=high
  seq:=high+32
  if ok,e:=w.Check(seq,100);ok||e==nil{t.Fatalf("presentation accepted %08x",seq)}
  if !w.IndependentAEADCandidate(seq,100){t.Fatalf("verified-near candidate refused %08x",seq)}
  w.NoteAuthenticated(seq,100)
  if w.Ack()!=1000||w.Pending()!=0{t.Fatal("hole crossed by invented carrier ACK")}
  if w.IndependentAEADCandidate(seq+m0V4IndependentAEADLookahead+1024,100){
   t.Fatal("untrusted 4MiB+ jump accepted")
  }
 }
}

func TestM0RemediationGameSingleLaneNativeFailureIsIsolated(t *testing.T){
 p:=&m0NativeV4GamePeer{lanes:make([]m0GameLane,4)}
 if e:=p.retireLane(0,context.DeadlineExceeded);e!=nil{
  t.Fatalf("first bad lane killed healthy group: %v",e)
 }
 if !p.lanes[0].failed||p.lanes[1].failed||p.laneFailed!=1{
  t.Fatal("failed native lane contaminated independent siblings")
 }
 for _,i:=range []int{1,2}{
  if e:=p.retireLane(i,context.DeadlineExceeded);e!=nil{
   t.Fatalf("single failing lane killed remaining sibling: %v",e)
  }
 }
 if e:=p.retireLane(3,context.DeadlineExceeded);e==nil{
  t.Fatal("all dead native lanes falsely reported healthy group")
 }
 if p.laneFailed!=4{t.Fatalf("lane failure count=%d",p.laneFailed)}
}

func TestM0RemediationTXSequenceBoundedAuditNoWireDisclosure(t *testing.T){
 p:=&m0NativeV4Peer{auditStarted:time.Now()}
 for i:=0;i<70;i++{p.noteTX("source",uint32(i),uint32(i),uint64(i),128,"NPF_COPIED")}
 if p.auditCursor!=70{t.Fatalf("audit cursor=%d",p.auditCursor)}
 trace:=p.txTrace()
 if !strings.Contains(trace,"pn=69")||strings.Contains(trace,"pn=0 "){
  t.Fatalf("bounded most-recent audit incorrect: %s",trace)
 }
 if strings.Contains(trace,"Payload:")||strings.Contains(trace,"key="){
  t.Fatal("diagnostic contains sensitive wire")
 }
}

func TestM0RemediationBatchNativeFirstsendFailedOwnerCannotReplay(t *testing.T){
 p:=&m0NativeV4Peer{}
 p.m2ResultsCount=2
 p.m2Results[0]=realityfront.V4WindowsM2FirstsendResult{
  PN:9,Seq:100,WireLen:123,Outcome:1}
 p.m2Results[1]=realityfront.V4WindowsM2FirstsendResult{
  PN:10,Seq:223,WireLen:121,Outcome:2}
 // No authenticated device is configured. This MUST fail closed,
 // discard the entire pending Go-owned metadata array, and never retry
 // possibly already consumed original Rust NPF completion receipts.
 if err:=p.flushOriginalFirstsend(context.Background());err==nil{
  t.Fatal("unbound M4 original device reported native NPF copy")
 }
 if p.m2ResultsCount!=0{
  t.Fatal("partially returned batch must be fenced, not resubmitted")
 }
 for _,row:=range p.m2Results[:2]{
  if row!=(realityfront.V4WindowsM2FirstsendResult{}){
   t.Fatal("bounded completed metadata buffer leaked across Stop")
  }
 }
 if err:=p.flushOriginalFirstsend(context.Background());err!=nil{
  t.Fatal("already fenced failed packet must never be submitted twice",err)
 }
}

func TestM0RemediationGameNativeEffectiveMTUShrinkGrowWithoutOwnerReset(t *testing.T){
 p:=&m0NativeV4GamePeer{lanes:make([]m0GameLane,4)}
 for _,value:=range []int{1399,1179,1299,1399}{
  if err:=p.applyNativeGamePayloadMTU(value);err!=nil{
   t.Fatalf("legitimate Game MTU change %d: %v",value,err)
  }
  if p.maxIPv4!=value||len(p.scratch)!=value{
   t.Fatalf("Wintun ring copy capacity stale after MTU update %d",value)
  }
 }
 if p.mtuUpdates!=4{t.Fatal("lost effective native budget updates")}
 for _,bad:=range []int{0,19,1536,4096}{
  if err:=p.applyNativeGamePayloadMTU(bad);err==nil{
   t.Fatalf("unsupported native outer record size accepted %d",bad)
  }
  if p.maxIPv4!=1399||len(p.scratch)!=1399{
   t.Fatal("invalid MTU changed live protected Wintun capacity")
  }
 }
 if err:=p.refreshNativeGameMTU(context.Background());err==nil{
  t.Fatal("nil authenticated Rust Game group must not assert MTU readback")
 }
}

func TestM0RemediationNativeSourceBatchAlwaysRequiresRealM4Owner(t *testing.T){
 var p m0NativeV4Peer
 if _,err:=p.transmitReadySourceBatch(context.Background(),4);err==nil{
  t.Fatal("cold Go owner cannot stage original Rust source batch")
 }
 if _,err:=p.transmitReadySourceBatch(context.Background(),0);err==nil{
  t.Fatal("zero-capacity stage admitted")
 }
}

func TestM0RemediationOriginalGoSourceBatchObservabilityIsNotFakeGoodput(t *testing.T){
 p:=&m0NativeV4Peer{}
 p.sourceBatchCounts[1]=2
 p.sourceBatchCounts[4]=3
 p.maxM2CompletionBatch=4
 p.sourceBatchStageFailures=1
 got:=p.Stats()
 if got.SourceBatchCounts[1]!=2||got.SourceBatchCounts[4]!=3||
  got.MaxM2CompletionBatch!=4||got.SourceBatchStageFailures!=1{
  t.Fatal("bounded batch observability missing exact source owner counters")
 }
 if got.GoHeapAllocBytes!=0||got.GoNumGC!=0{
  t.Fatal("generic Stats must not fake a Go runtime sample")
 }
}

func TestM0WindowsNativeRingWaitObserverCanceledNoOrphanWake(t *testing.T){
 ctx,cancel:=context.WithCancel(context.Background())
 cancel()
 ready:=make(chan error)
 done:=make(chan struct{})
 go func(){
  m0V4ObserveRingReady(ctx,&windowsclient.N4OriginalKernelPacketLease{},ready)
  close(done)
 }()
 select{
 case <-done:
 case <-time.After(time.Second):
  t.Fatal("event waiter failed to join owned cancel")
 }
 select{
 case <-ready:t.Fatal("canceled owner emitted fake real Wintun wake")
 default:
 }
}

func TestM0PLAN025WindowsNativeSourceInvalidIPv4DoesNotPoisonBatch(t *testing.T){
 good:=make([]byte,120);good[0]=0x45
 v6:=append([]byte(nil),good...);v6[0]=0x60
 shortIHL:=append([]byte(nil),good...);shortIHL[0]=0x44
 tooLongIHL:=make([]byte,20);tooLongIHL[0]=0x4f
 for _,tc:=range []struct{name string;packet []byte;want bool}{
  {"trueIPv4",good,true},
  {"IPv6-on-Wintun",v6,false},
  {"IPv4-too-short",good[:19],false},
  {"bad-ihl",shortIHL,false},
  {"ihl-exceeds-packet",tooLongIHL,false},
  {"too-large",make([]byte,2049),false},
 }{
  t.Run(tc.name,func(t *testing.T){
   if got:=m0ValidNativeIPv4Source(tc.packet);got!=tc.want{
    t.Fatalf("unexpected pre-seal IP source decision: got %v want %v",got,tc.want)
   }
  })
 }
}
