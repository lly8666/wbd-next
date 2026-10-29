//go:build windows && wbd_v4_embedded_go
package main

import "errors"

// Native V4 records are independently protected by Rust AEAD/PN. This
// fixed-capacity TCP serial interval ledger only controls the *cumulative*
// carrier ACK. A later genuine record may be delivered before a missing one;
// its bytes do NOT advance the cumulative ACK across that hole.
// The ledger tracks only packets actually copied to the current Wintun ring.
// It is not a replacement for Rust generation/replay authentication.
const m0V4RxAheadMax = 128 * 1024
const m0V4RxRecordMax = 2048
const m0V4RxSlots = 256
var errM0V4RxWindow = errors.New("native V4 TCP sequence outside bounded verified receipt window")
type m0V4RxWindow struct {
 cumulative uint32
 // Independent progress is trusted only after Rust M3 AEAD+unique-PN,
 // and after all DATA has actually reached the owned Wintun sink.
 // Never feed this to the TCP cumulative ACK / Rust M2 receipt.
 authenticatedHigh uint32
 // The cumulative TCP receipt ledger is permanently detached once genuine
 // M3 progress outruns it. Later 32-bit serial aliases cannot forge an ACK.
 independentOnly bool
 received map[uint32]uint32
}
func newM0V4RxWindow(start uint32)*m0V4RxWindow{
 return &m0V4RxWindow{cumulative:start,authenticatedHigh:start,received:make(map[uint32]uint32,m0V4RxSlots)}
}
// Check returns false for old/duplicate/overlapping ciphertext: never
// feed that record into the native Rust owner twice, and never mistake a
// ciphertext TCP retransmission for a new logical AEAD packet.
func(w *m0V4RxWindow) Check(seq uint32,n int)(bool,error){
 if w==nil||n<=0||n>m0V4RxRecordMax{return false,errM0V4RxWindow}
 ahead:=int32(seq-w.cumulative)
 if w.independentOnly{return false,errM0V4RxWindow}
 if ahead<0{
  // A cumulative hole may be >2^31 behind verified independent traffic.
  // Distinguish by M3-authenticated proximity, never the stale ACK anchor.
  if w.authenticatedHigh!=w.cumulative && w.IndependentAEADCandidate(seq,n){
   return false,errM0V4RxWindow
  }
  return false,nil
 }
 if ahead>m0V4RxAheadMax||uint32(ahead)+uint32(n)>m0V4RxAheadMax{
  return false,errM0V4RxWindow
 }
 // A saturated map MUST still admit the exact missing head, because its
 // immediate contiguous drain retires prior verified rows. At most one
 // transient entry beyond the 256-slot ledger is reachable here.
 if len(w.received)>=m0V4RxSlots && seq!=w.cumulative{
  return false,errM0V4RxWindow
 }
 a,b:=uint32(ahead),uint32(ahead)+uint32(n)
 for first,size:=range w.received{
  from:=uint32(first-w.cumulative)
  if a<from+size&&from<b{return false,nil}
 }
 return true,nil
}
func(w *m0V4RxWindow) Copied(seq uint32,n int)(uint32,error){
 ok,err:=w.Check(seq,n)
 if err!=nil||!ok{return w.cumulative,errM0V4RxWindow}
 w.received[seq]=uint32(n)
 for {
  size,exists:=w.received[w.cumulative]
  if !exists{break}
  delete(w.received,w.cumulative)
  w.cumulative+=size // serial arithmetic, handles 32-bit wrap.
 }
 // Copied is called ONLY after real original Rust M3 authentication and
 // a successful owned Wintun copy. A contiguous progress is also genuine
 // authenticated evidence: keep its high watermark at least as fresh as
 // the cumulative ACK. Otherwise a previously copied stale retransmit
 // could be misclassified as fatal out-of-window (not a normal duplicate).
 if int32(w.cumulative-w.authenticatedHigh)>0{
  w.authenticatedHigh=w.cumulative
 }
 return w.cumulative,nil
}
func(w *m0V4RxWindow) Ack()uint32{return w.cumulative}
func(w *m0V4RxWindow) Pending()int{return len(w.received)}

// A far-ahead or saturated presentation-ACK ledger may not hold more
// intervals. Only the SAME original TLS-bound Rust M3 unique AEAD/PN
// can deliver this bounded candidate independently; the TCP cumulative
// ACK NEVER advances, and no new Go receipt-map slot is allocated.
const m0V4IndependentAEADLookahead = 4 * 1024 * 1024
func(w *m0V4RxWindow) IndependentAEADCandidate(seq uint32,n int)bool{
 if w==nil||n<51||n>m0V4RxRecordMax{return false}
 ahead:=int32(seq-w.cumulative)
 if !w.independentOnly && ahead>=0 &&
    uint64(ahead)+uint64(n)<=m0V4IndependentAEADLookahead{return true}
 // A lost control carrier can keep the *presentation* ACK at one old hole
 // forever: Rust M2 never fabricates ACK for it. Past 4MiB, only proximity
 // to previously M3-authenticated unique ciphertext opens the bounded
 // window for another try by that SAME Rust opener. This is NOT an ACK.
 if w.authenticatedHigh==w.cumulative && ahead<0{return false}
 near:=int64(int32(seq-w.authenticatedHigh))
 return near>=-m0V4IndependentAEADLookahead &&
        near+int64(n)<=m0V4IndependentAEADLookahead
}
// Call only AFTER authentic M3 open and complete owned Wintun business copy,
// or successful authentic kind1 control handling. No untrusted TCP field,
// rejected AEAD or duplicate record may advance this serial high-water.
func(w *m0V4RxWindow) NoteAuthenticated(seq uint32,n int){
 if w==nil||n<51||n>m0V4RxRecordMax{return}
 end:=seq+uint32(n)
 if int32(end-w.authenticatedHigh)>0{
  if w.independentOnly || int32(seq-w.cumulative)<0 ||
     uint32(seq-w.cumulative)+uint32(n)>m0V4RxAheadMax {
   w.independentOnly=true
  }
  w.authenticatedHigh=end
 }
}
