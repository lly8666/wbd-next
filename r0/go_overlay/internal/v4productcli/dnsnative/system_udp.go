package dnsnative

import (
 "context"
 "encoding/binary"
 "fmt"
 "net"
 "net/netip"
 "time"
)

// B66 uses the same cold DNS owner, same upstream policy and same TCP
// listener port. The Android kernel supplies the inverse NAT; this does
// not read or manufacture TUN IP packets.
func(s *AppTCPDNS) EnableUDP()error{
 if s.udp!=nil{return fmt.Errorf("UDP DNS already running")}
 p,e:=net.ListenPacket("udp4",fmt.Sprintf("127.0.0.1:%d",s.Port()))
 if e!=nil{return e}
 s.udp=p
 s.wg.Add(1)
 go s.serveUDP(p,netip.Prefix{})
 return nil
}
func udpReplyLimit(query []byte,q question)int{
 if binary.BigEndian.Uint16(query[10:12])==1{
  limit:=int(binary.BigEndian.Uint16(query[q.end+3:q.end+5]))
  if limit<512{return 512}
  if limit>MaxQuery{return MaxQuery}
  return limit
 }
 return 512
}
func udpQuestionReply(query []byte,q question,flags uint16)[]byte{
 out:=append([]byte(nil),query[:q.end]...)
 binary.BigEndian.PutUint16(out[2:4],flags)
 // qdcount=1, no partial RRs; preserve exact original ID and question.
 for i:=6;i<12;i++{out[i]=0}
 return out
}
func(s *AppTCPDNS) serveUDP(p net.PacketConn,scope netip.Prefix){
 defer s.wg.Done()
 slots:=make(chan struct{},maxAppTCP)
 var scratch [MaxQuery+1]byte
 for{
  n,peer,e:=p.ReadFrom(scratch[:])
  if e!=nil{return}
  if n>MaxQuery||s.ctx.Err()!=nil||!allowedDNSPeer(peer,scope){continue}
  q,e:=parseQuery(scratch[:n]);if e!=nil{continue}
  select{case slots<-struct{}{}:default:continue}
  query:=append([]byte(nil),scratch[:n]...)
  s.wg.Add(1)
  go func(){
   defer s.wg.Done();defer func(){<-slots}()
   ctx,cancel:=context.WithTimeout(s.ctx,3*time.Second);defer cancel()
   reply,e:=s.resolver.Resolve(ctx,query,s.allPhysical)
   if s.ctx.Err()!=nil{return}
   if e!=nil{
    flags:=uint16(0x8082)|(binary.BigEndian.Uint16(query[2:4])&0x0110)
    reply=udpQuestionReply(query,q,flags)
   }else if len(reply)>udpReplyLimit(query,q){
    // A full TCP upstream answer may not fit the client's UDP budget.
    // Return TC; the same local TCP owner handles its retry.
    flags:=binary.BigEndian.Uint16(reply[2:4])|0x0200
    reply=udpQuestionReply(query,q,flags)
   }
   _,_=p.WriteTo(reply,peer)
  }()
 }
}
