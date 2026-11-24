package dnsnative

import (
 "fmt"
 "net"
 "net/netip"
)

// Inbound DNS destination family is independent of QTYPE and original
// IPv4 upstream transport. Never listen on an IPv6 wildcard address.
// Ordinary IPv6 App DNS and system DNS share the same local listener.
func(s *AppTCPDNS) IPv6Port()(int,error){
 if s.ctx.Err()!=nil{return 0,ErrInvalid}
 if s.ipv6TCP!=nil{return s.ipv6TCP.Addr().(*net.TCPAddr).Port,nil}
 return s.EnableIPv6()
}
func(s *AppTCPDNS) EnableIPv6() (int,error){
 if s.ctx.Err()!=nil||s.ipv6TCP!=nil{return 0,ErrInvalid}
 l,e:=net.Listen("tcp6","[::1]:0")
 if e!=nil{return 0,e}
 port:=l.Addr().(*net.TCPAddr).Port
 p,e:=net.ListenPacket("udp6",fmt.Sprintf("[::1]:%d",port))
 if e!=nil{l.Close();return 0,e}
 s.ipv6TCP,s.ipv6UDP=l,p
 s.wg.Add(2)
 // REDIRECT preserves the original source, which need not be ::1.
 go s.accept(l,netip.Prefix{})
 go s.serveUDP(p,netip.Prefix{})
 return port,nil
}
