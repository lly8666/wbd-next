package dnsnative

// B64: kernel TCP on both sides; only length-framed ordinary DNS is
// relayed. No TUN reads, user-space TCP/IP stack or ordinary DATA worker.
// The owner installs the exact App UID NAT rules after protected M4 READY.
import (
 "context"
 "encoding/binary"
 "errors"
 "io"
 "net"
 "net/netip"
 "sync"
 "time"
)

const maxAppTCP=64

type AppTCPDNS struct {
 listener net.Listener
 udp net.PacketConn
 downstreamTCP net.Listener
 downstreamUDP net.PacketConn
 ipv6TCP net.Listener
 ipv6UDP net.PacketConn
 resolver *Resolver
 allPhysical bool
 ctx context.Context
 cancel context.CancelFunc
 mu sync.Mutex
 clients map[net.Conn]struct{}
 wg sync.WaitGroup
}

// One original fixed DNS mode per cold generation. Physical and tunnel
// endpoints are literal, and every socket uses the supplied scoped dialer.
func StartAppTCPDNS(dial DialFunc, match CNMatch, split, allPhysical bool,
 physical string)(*AppTCPDNS,error){
 if split&&allPhysical{return nil,ErrInvalid}
 r,e:=New(dial,match,split)
 if e!=nil{return nil,e}
 r.direct=physical
 l,e:=net.Listen("tcp4","127.0.0.1:0")
 if e!=nil{return nil,e}
 ctx,cancel:=context.WithCancel(context.Background())
 s:=&AppTCPDNS{listener:l,resolver:r,allPhysical:allPhysical,
  ctx:ctx,cancel:cancel,clients:make(map[net.Conn]struct{})}
 s.wg.Add(1);go s.accept(l,netip.Prefix{})
 return s,nil
}
func (s *AppTCPDNS) Port()int{return s.listener.Addr().(*net.TCPAddr).Port}
func allowedDNSPeer(addr net.Addr,scope netip.Prefix)bool{
 if !scope.IsValid(){return true}
 var ip net.IP
 switch a:=addr.(type){case *net.TCPAddr:ip=a.IP;case *net.UDPAddr:ip=a.IP;default:return false}
 peer,ok:=netip.AddrFromSlice(ip)
 return ok&&scope.Contains(peer.Unmap())
}
func (s *AppTCPDNS) accept(l net.Listener,scope netip.Prefix){
 defer s.wg.Done()
 for{
  c,e:=l.Accept()
  if e!=nil{return}
  if !allowedDNSPeer(c.RemoteAddr(),scope){c.Close();continue}
  s.mu.Lock()
  if s.ctx.Err()!=nil||len(s.clients)>=maxAppTCP{
   s.mu.Unlock();c.Close();continue
  }
  s.clients[c]=struct{}{}
  s.wg.Add(1);s.mu.Unlock()
  go s.serve(c)
 }
}
func (s *AppTCPDNS) serve(c net.Conn){
 defer s.wg.Done()
 defer func(){c.Close();s.mu.Lock();delete(s.clients,c);s.mu.Unlock()}()
 for s.ctx.Err()==nil{
  // A persistent client TCP stream may carry multiple sequential queries.
  // Kernel TCP handles segmentation/retransmission, not the Go DNS owner.
  if c.SetDeadline(time.Now().Add(30*time.Second))!=nil{return}
  var size [2]byte
  if _,e:=io.ReadFull(c,size[:]);e!=nil{return}
  n:=int(binary.BigEndian.Uint16(size[:]))
  if n<17||n>MaxQuery{return}
  query:=make([]byte,n)
  if _,e:=io.ReadFull(c,query);e!=nil{return}
  q,e:=parseQuery(query);if e!=nil{return}
  path,endpoint:=s.resolver.decide(q.name,s.allPhysical)
  ctx,cancel:=context.WithTimeout(s.ctx,3*time.Second)
  reply,e:=s.resolver.tcp(ctx,path,endpoint,query)
  cancel()
  if e!=nil{return}
  truncated,e:=validateReply(query,reply,q)
  if e!=nil||truncated{return}
  binary.BigEndian.PutUint16(size[:],uint16(len(reply)))
  if c.SetWriteDeadline(time.Now().Add(3*time.Second))!=nil{return}
  frame:=append(size[:],reply...)
  for len(frame)>0{
   n,e=c.Write(frame);if e!=nil||n==0{return};frame=frame[n:]
  }
 }
}
func (s *AppTCPDNS) Close()error{
 s.cancel()
 e:=s.listener.Close()
 if s.udp!=nil{e=errors.Join(e,s.udp.Close())}
 if s.downstreamTCP!=nil{e=errors.Join(e,s.downstreamTCP.Close())}
 if s.downstreamUDP!=nil{e=errors.Join(e,s.downstreamUDP.Close())}
 if s.ipv6TCP!=nil{e=errors.Join(e,s.ipv6TCP.Close())}
 if s.ipv6UDP!=nil{e=errors.Join(e,s.ipv6UDP.Close())}
 s.mu.Lock()
 for c:=range s.clients{c.Close()}
 s.mu.Unlock()
 s.wg.Wait()
 if e!=nil&&!errors.Is(e,net.ErrClosed){return e}
 return nil
}
