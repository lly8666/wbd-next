//go:build windows && wbd_v4_embedded_go
package realityfront

import (
 "testing"
 "time"
)

// S52 genuine Windows 2s ticker jitter: the old independent floor(8s)
// and floor(16s) could pair a true 8s mature cohort with 10s actual-k,
// creating >=25% artificial k overhang and freezing otherwise valid down.
func TestM0WindowsAutoAlignedMatureCohortPreservesTrueKWindow(t *testing.T){
 ms:=[]int64{0,2000,3900,6100,7900,10010,11900,14050,15900,18100,19900,22050}
 points:=make([]winAutoPoint,0,len(ms))
 for _,m:=range ms{
  // Real monotonic cumulative first-send and first-close counters with
  // constant 2/3 source per ms. No invented received/Ack to pass quality.
  n:=uint64(m*2/3)
  var quality V4WindowsAutoQuality
  quality.Revision=1
  quality.Counters[0],quality.Counters[1]=n,n
  quality.Counters[5],quality.Counters[6]=n,n
  quality.Counters[14]=n // actual k=1, so symbol count=block count
  points=append(points,winAutoPoint{at:time.Duration(m)*time.Millisecond,v:quality})
 }
 now:=points[len(points)-1].at
 fast,slow,hist,ok:=winAutoAlignedMatureCohorts(points,now)
 if !ok{t.Fatal("genuine 12 real observations cannot select paired cohorts")}
 if got,want:=slow.at,14050*time.Millisecond;got!=want{
  t.Fatalf("wrong 8s mature cohort start %v want %v",got,want)
 }
 if got,want:=hist.at,6100*time.Millisecond;got!=want{
  t.Fatalf("actual-k did not use matching real sample intervals: %v want %v",got,want)
 }
 raw:=points[len(points)-1].v.Counters
 f,okF:=winAutoWindow(raw,fast.v.Counters,0)
 s,okS:=winAutoWindow(raw,slow.v.Counters,5)
 n,okK:=winAutoDiff(hist.v.Counters[14],slow.v.Counters[14])
 if !okF||!okS||!okK{t.Fatal("real monotonic mature/actual-k data rejected")}
 snap:=FecV2Snapshot{Validity:FecV2Valid,At:now,SRTT:4*time.Millisecond,Fast:f,Slow:s}
 snap.ActualK[0]=n
 v,reason,_:=fecV2Quality(now,snap)
 if v!=FecV2Valid{t.Fatalf("equal real cohort with zero loss treated as %s: %s (slow=%d k=%d)",v,reason,s.FirstSent,n)}
 // Reconstruct the S52 buggy independent 16s floor (3.9s): it picks
 // ~10s actual-k against ~8s mature FIRST, and MUST still be UNKNOWN.
 wrong,okWrong:=winAutoDiff(points[2].v.Counters[14],slow.v.Counters[14])
 if !okWrong{t.Fatal("invalid synthetic historical counter")}
 snap.ActualK[0]=wrong
 if v,why,_:=fecV2Quality(now,snap);v!=FecV2Unknown||why!="actual-k observation incomplete"{
  t.Fatalf("mismatched real sampled cohorts got false acceptance %s %s",v,why)
 }
 if _,_,_,ok:=winAutoAlignedMatureCohorts(points[:5],points[4].at);ok{
  t.Fatal("insufficient genuine 16s historical cohort forged VALID")
 }
}
