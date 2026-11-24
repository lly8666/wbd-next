package dnsnative

import (
 "fmt"
 "net"
 "net/netip"
)

// EnableDownstream runs only during cold startup, before publication.
// A distinct listener address prevents a hotspot client from reaching the
// app-only localhost listener. Both entrances share the same resolver.
func(s *AppTCPDNS) EnableDownstream(gateway netip.Addr,subnet netip.Prefix)(int,error){
 if s.ctx.Err()!=nil||s.downstreamTCP!=nil||!gateway.Is4()||
    !subnet.IsValid()||!subnet.Addr().Is4()||subnet!=subnet.Masked()||!subnet.Contains(gateway){
  return 0,ErrInvalid
 }
 l,e:=net.Listen("tcp4",net.JoinHostPort(gateway.String(),"0"))
 if e!=nil{return 0,e}
 port:=l.Addr().(*net.TCPAddr).Port
 p,e:=net.ListenPacket("udp4",fmt.Sprintf("%s:%d",gateway,port))
 if e!=nil{l.Close();return 0,e}
 s.downstreamTCP,s.downstreamUDP=l,p
 s.wg.Add(2)
 go s.accept(l,subnet)
 go s.serveUDP(p,subnet)
 return port,nil
}

// B74: existing downstream IPv6 prefix/address, same original resolver.
func(s *AppTCPDNS) EnableDownstream6(gateway netip.Addr,subnet netip.Prefix)(int,error){
 if s.ctx.Err()!=nil||!gateway.Is6()||gateway.Is4In6()||
    !subnet.IsValid()||subnet!=subnet.Masked()||!subnet.Contains(gateway){return 0,ErrInvalid}
 l,e:=net.Listen("tcp6",net.JoinHostPort(gateway.String(),"0"))
 if e!=nil{return 0,e}
 port:=l.Addr().(*net.TCPAddr).Port
 p,e:=net.ListenPacket("udp6",net.JoinHostPort(gateway.String(),fmt.Sprint(port)))
 if e!=nil{l.Close();return 0,e}
 s.downstream6TCP=append(s.downstream6TCP,l)
 s.downstream6UDP=append(s.downstream6UDP,p)
 s.wg.Add(2)
 go s.accept(l,subnet)
 go s.serveUDP(p,subnet)
 return port,nil
}
