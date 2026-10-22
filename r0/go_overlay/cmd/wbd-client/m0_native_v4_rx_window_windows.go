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
 received map[uint32]uint32
}
func newM0V4RxWindow(start uint32)*m0V4RxWindow{
 return &m0V4RxWindow{cumulative:start,received:make(map[uint32]uint32,m0V4RxSlots)}
}
// Check returns false for old/duplicate/overlapping ciphertext: never
// feed that record into the native Rust owner twice, and never mistake a
// ciphertext TCP retransmission for a new logical AEAD packet.
func(w *m0V4RxWindow) Check(seq uint32,n int)(bool,error){
 if w==nil||n<=0||n>m0V4RxRecordMax{return false,errM0V4RxWindow}
 ahead:=int32(seq-w.cumulative)
 if ahead<0{return false,nil}
 if ahead>m0V4RxAheadMax||uint32(ahead)+uint32(n)>m0V4RxAheadMax{
  return false,errM0V4RxWindow
 }
 if len(w.received)>=m0V4RxSlots{return false,errM0V4RxWindow}
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
 return w.cumulative,nil
}
func(w *m0V4RxWindow) Ack()uint32{return w.cumulative}
func(w *m0V4RxWindow) Pending()int{return len(w.received)}
