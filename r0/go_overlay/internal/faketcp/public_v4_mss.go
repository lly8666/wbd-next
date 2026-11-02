package faketcp
import ("fmt";"sync/atomic")
// One current public V4 MSS, installed from Rust using the real physical
// egress and configured outer IP limit BEFORE the first SYN/SYN-ACK.
// There is NO silent DefaultMSS=1360 fallback and NO protocol version flag.
// The original owner stops the old generation before updating; individual
// associations capture a frozen MSS for retransmitted handshakes.
var publicV4MSS atomic.Uint32
func SetPublicV4AdvertisedMSS(mss uint16)error{
 if mss<536||mss>1460{return fmt.Errorf("V4 MSS %d outside 536..1460",mss)}
 publicV4MSS.Store(uint32(mss));return nil
}
func PublicV4AdvertisedMSS()uint16{
 n:=publicV4MSS.Load()
 if n==0{panic("Rust local V4 SYN MSS not installed before handshake")}
 return uint16(n)
}
