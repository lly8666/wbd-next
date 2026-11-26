//go:build windows

package faketcp

// PLAN029: one cold physical WinXDP UDP A lookup. A validated TC=1 response
// permits only TCP/53 on the SAME dns.direct endpoint, with explicit physical
// source/interface binding and a shared deadline. No system resolver, Wintun,
// cross-direction fallback or persistent worker. Server bootstrap only.
import (
 "bytes"
 "context"
 "crypto/rand"
 "encoding/binary"
 "errors"
 "fmt"
 "io"
 "math/bits"
 "net"
 "net/netip"
 "os"
 "path/filepath"
 "strings"
 "syscall"
 "time"

 "golang.org/x/net/dns/dnsmessage"
)

var ErrPhysicalDNS = errors.New("faketcp: physical server bootstrap DNS failed")

type PhysicalDNSConfig struct {
 Device string
 SourceMAC, NextHopMAC [6]byte
 Source4, Resolver4 netip.Addr
 // Actual cold-selected physical NIC, never the owned Wintun interface.
 // Required only for the TCP branch after a validated UDP TC=1.
 InterfaceIndex uint32
}

func (c PhysicalDNSConfig) valid() bool {
 return c.InterfaceIndex!=0 &&
  c.SourceMAC!=([6]byte{}) && c.NextHopMAC!=([6]byte{}) &&
  c.Source4.Is4() && !c.Source4.IsUnspecified() &&
  c.Resolver4.Is4() && !c.Resolver4.IsUnspecified() &&
  !c.Resolver4.IsMulticast() && c.Source4!=c.Resolver4
}

// Ones-complement checksums for the exact on-wire IPv4/UDP DNS frame.
func physicalDNSChecksumSum(b []byte) uint32 {
 var sum uint32
 for len(b)>1 {sum+=uint32(binary.BigEndian.Uint16(b[:2]));b=b[2:]}
 if len(b)>0 {sum+=uint32(b[0])<<8}
 return sum
}
func physicalDNSChecksumFold(sum uint32) uint16 {
 for sum>>16!=0 {sum=(sum&0xffff)+(sum>>16)}
 return ^uint16(sum)
}
func physicalDNSPseudoSum(source,dest []byte,udp []byte)uint32{
 sum:=physicalDNSChecksumSum(source)+physicalDNSChecksumSum(dest)
 sum+=17+uint32(len(udp))
 return sum+physicalDNSChecksumSum(udp)
}

func physicalDNSFrame(c PhysicalDNSConfig,sourcePort uint16,wire []byte,id uint16)([]byte,error){
 if !c.valid()||sourcePort<1024||len(wire)<12||len(wire)>1000 {return nil,ErrPhysicalDNS}
 total:=20+8+len(wire)
 frame:=make([]byte,14+total)
 copy(frame[0:6],c.NextHopMAC[:]);copy(frame[6:12],c.SourceMAC[:])
 binary.BigEndian.PutUint16(frame[12:14],0x0800)
 ip:=frame[14:34]
 ip[0]=0x45;binary.BigEndian.PutUint16(ip[2:4],uint16(total))
 binary.BigEndian.PutUint16(ip[4:6],id)
 binary.BigEndian.PutUint16(ip[6:8],0x4000)
 ip[8]=64;ip[9]=17
 s,d:=c.Source4.As4(),c.Resolver4.As4()
 copy(ip[12:16],s[:]);copy(ip[16:20],d[:])
 binary.BigEndian.PutUint16(ip[10:12],physicalDNSChecksumFold(physicalDNSChecksumSum(ip)))
 udp:=frame[34:42]
 binary.BigEndian.PutUint16(udp[0:2],sourcePort)
 binary.BigEndian.PutUint16(udp[2:4],53)
 binary.BigEndian.PutUint16(udp[4:6],uint16(8+len(wire)))
 copy(frame[42:],wire)
 check:=physicalDNSChecksumFold(physicalDNSPseudoSum(s[:],d[:],frame[34:]))
 if check==0 {check=0xffff}
 binary.BigEndian.PutUint16(udp[6:8],check)
 return frame,nil
}

func physicalDNSReplyState(frame []byte,c PhysicalDNSConfig,port,id uint16,name dnsmessage.Name)([]netip.Addr,bool,bool){
 ip,ok:=extractEthernetIPv4(frame)
 if !ok||len(ip)<28||ip[9]!=17||binary.BigEndian.Uint16(ip[6:8])&0x3fff!=0{return nil,false,false}
 ihl:=int(ip[0]&0x0f)*4
 if ihl<20||len(ip)<ihl+8||physicalDNSChecksumFold(physicalDNSChecksumSum(ip[:ihl]))!=0{return nil,false,false}
 dst,src:=c.Source4.As4(),c.Resolver4.As4()
 if string(ip[12:16])!=string(src[:])||string(ip[16:20])!=string(dst[:]){return nil,false,false}
 udp:=ip[ihl:]
 if binary.BigEndian.Uint16(udp[0:2])!=53||binary.BigEndian.Uint16(udp[2:4])!=port{return nil,false,false}
 used:=int(binary.BigEndian.Uint16(udp[4:6]))
 if used<8||used>len(udp){return nil,false,false}
 udp=udp[:used]
 if binary.BigEndian.Uint16(udp[6:8])!=0 && physicalDNSChecksumFold(physicalDNSPseudoSum(src[:],dst[:],udp))!=0{return nil,false,false}
 return physicalDNSAnswerPayload(udp[8:],id,name)
}
func physicalDNSAnswerPayload(wire []byte,id uint16,name dnsmessage.Name)([]netip.Addr,bool,bool){
 var p dnsmessage.Parser
 h,err:=p.Start(wire)
 if err!=nil||!h.Response||h.ID!=id{return nil,false,false}
 q,e:=p.Question()
 if e!=nil||q.Type!=dnsmessage.TypeA||q.Class!=dnsmessage.ClassINET||
  !strings.EqualFold(q.Name.String(),name.String()){return nil,false,false}
 if e=p.SkipAllQuestions();e!=nil{return nil,false,false}
 // A valid original UDP truncation authorizes precisely one same-endpoint
 // physical TCP attempt. Wrong question/source/ID never triggers a dial.
 if h.Truncated{return nil,false,true}
 if h.RCode!=dnsmessage.RCodeSuccess{return nil,true,false}
 // A records for unrelated owners are not valid answers to this query.
 // Follow only CNAME links rooted at the exact requested QNAME; a public
 // DNS resolver may return unrelated additional names. Bounded 16 RRs.
 var answers []dnsmessage.Resource
 for i:=0;i<=16;i++{
  a,e:=p.Answer()
  if e==dnsmessage.ErrSectionDone{break}
  if e!=nil||i==16{return nil,false,false}
  answers=append(answers,a)
 }
 allowed:=map[string]bool{strings.ToLower(name.String()):true}
 for depth:=0;depth<8;depth++{
  grown:=false
  for _,a:=range answers{
   if a.Header.Class!=dnsmessage.ClassINET||a.Header.Type!=dnsmessage.TypeCNAME||
      !allowed[strings.ToLower(a.Header.Name.String())]{continue}
   cname,ok:=a.Body.(*dnsmessage.CNAMEResource);if !ok{return nil,false,false}
   key:=strings.ToLower(cname.CNAME.String())
   if !allowed[key]{allowed[key]=true;grown=true}
  }
  if !grown{break}
 }
 var out []netip.Addr
 for _,a:=range answers{
  if len(out)>=8{break}
  if a.Header.Type!=dnsmessage.TypeA||a.Header.Class!=dnsmessage.ClassINET||
     !allowed[strings.ToLower(a.Header.Name.String())]{continue}
  body,ok:=a.Body.(*dnsmessage.AResource)
  if !ok{continue}
  addr:=netip.AddrFrom4(body.A)
  if addr.IsUnspecified()||addr.IsMulticast()||addr.IsLoopback(){continue}
  duplicate:=false
  for _,v:=range out{if v==addr{duplicate=true;break}}
  if !duplicate{out=append(out,addr)}
 }
 return out,true,false
}

func physicalDNSReply(frame []byte,c PhysicalDNSConfig,port,id uint16,name dnsmessage.Name)([]netip.Addr,bool){
 ips,ok,tc:=physicalDNSReplyState(frame,c,port,id,name)
 return ips,ok&&!tc
}

// TCP is used ONLY if the exact on-wire UDP tuple, question and ID matched
// a truncated answer. Never call net.LookupHost or let Windows choose an
// unbound interface under the Wintun /1 capture route.
func physicalBootstrapTCPSameEndpoint(ctx context.Context,c PhysicalDNSConfig,
 query []byte,id uint16,name dnsmessage.Name)([]netip.Addr,error){
 if ctx==nil||!c.valid()||c.InterfaceIndex==0||len(query)<12||len(query)>1000{
  return nil,ErrPhysicalDNS
 }
 tcpCtx,cancel:=context.WithTimeout(ctx,3500*time.Millisecond)
 defer cancel()
 src:=c.Source4.As4()
 dialer:=net.Dialer{
  LocalAddr:&net.TCPAddr{IP:net.IP(src[:])},
  Control:func(network,address string,raw syscall.RawConn)error{
   var sockErr error
   if err:=raw.Control(func(fd uintptr){
    // Winsock IP_UNICAST_IF=31 accepts the ifindex in network byte order.
    // Windows x64/ARM64 are little-endian. Unselected/foreign NICs fail.
    sockErr=syscall.SetsockoptInt(syscall.Handle(fd),syscall.IPPROTO_IP,
     31,int(bits.ReverseBytes32(c.InterfaceIndex)))
   });err!=nil{return err}
   return sockErr
  },
 }
 conn,err:=dialer.DialContext(tcpCtx,"tcp",net.JoinHostPort(c.Resolver4.String(),"53"))
 if err!=nil{return nil,fmt.Errorf("%w: same-endpoint physical TCP dial: %v",ErrPhysicalDNS,err)}
 defer conn.Close()
 if actual,ok:=conn.LocalAddr().(*net.TCPAddr);!ok||
  !actual.IP.Equal(net.IP(src[:])){
  return nil,fmt.Errorf("%w: physical TCP source changed",ErrPhysicalDNS)
 }
 if deadline,ok:=tcpCtx.Deadline();ok{
  if err=conn.SetDeadline(deadline);err!=nil{return nil,err}
 }
 length:=[]byte{byte(len(query)>>8),byte(len(query))}
 if _,err=io.Copy(conn,bytes.NewReader(append(length,query...)));err!=nil{
  return nil,fmt.Errorf("%w: physical TCP write: %v",ErrPhysicalDNS,err)
 }
 var prefix [2]byte
 if _,err=io.ReadFull(conn,prefix[:]);err!=nil{return nil,fmt.Errorf("%w: physical TCP length: %v",ErrPhysicalDNS,err)}
 n:=int(binary.BigEndian.Uint16(prefix[:]))
 if n<12||n>2048{return nil,ErrPhysicalDNS}
 response:=make([]byte,n)
 if _,err=io.ReadFull(conn,response);err!=nil{return nil,fmt.Errorf("%w: physical TCP response: %v",ErrPhysicalDNS,err)}
 var p dnsmessage.Parser
 h,e:=p.Start(response)
 if e!=nil||!h.Response||h.ID!=id||h.Truncated{return nil,ErrPhysicalDNS}
 q,e:=p.Question()
 if e!=nil||q.Type!=dnsmessage.TypeA||q.Class!=dnsmessage.ClassINET||
  !strings.EqualFold(q.Name.String(),name.String()){return nil,ErrPhysicalDNS}
 if e=p.SkipAllQuestions();e!=nil{return nil,ErrPhysicalDNS}
 // The same CNAME/A parser used for UDP validates the DNS payload.
 ips,ok,truncated:=physicalDNSAnswerPayload(response,id,name)
 if !ok||truncated||len(ips)==0{return nil,ErrPhysicalDNS}
 return ips,nil
}

// LookupPhysicalServerA starts with one exact physical UDP DNS query. A
// validated TC=1 may use the SAME physical endpoint over TCP under 5s total.
// It never calls GetAddrInfo, the system resolver, Wintun, or an unbound socket.
// The caller must first select and verify the ORIGINAL physical underlay.
func LookupPhysicalServerA(ctx context.Context,c PhysicalDNSConfig,host string)([]netip.Addr,error){
 if !c.valid()||ctx.Err()!=nil{return nil,ErrPhysicalDNS}
 if host==""||len(host)>253||strings.ContainsAny(host,"/\\:@ "){return nil,ErrPhysicalDNS}
 name,e:=dnsmessage.NewName(strings.TrimSuffix(host,".")+".")
 if e!=nil{return nil,ErrPhysicalDNS}
 var seed [4]byte
 if _,e=rand.Read(seed[:]);e!=nil{return nil,ErrPhysicalDNS}
 id:=binary.BigEndian.Uint16(seed[:2])
 port:=uint16(49152+binary.BigEndian.Uint16(seed[2:])%16384)
 query,e:=(&dnsmessage.Message{
  Header:dnsmessage.Header{ID:id,RecursionDesired:true},
  Questions:[]dnsmessage.Question{{Name:name,Type:dnsmessage.TypeA,Class:dnsmessage.ClassINET}},
 }).Pack()
 if e!=nil{return nil,e}
 frame,e:=physicalDNSFrame(c,port,query,id)
 if e!=nil{return nil,e}

 executable,exeErr:=os.Executable();if exeErr!=nil{return nil,exeErr}
 carrier,available,openErr:=openXdpPorts(filepath.Join(filepath.Dir(executable),"wbd_engine.dll"),c.InterfaceIndex,[]uint16{port},true)
 if openErr!=nil{return nil,openErr}
 if !available{return nil,fmt.Errorf("%w: WinXDP entry absent",ErrPhysicalDNS)}
 defer carrier.Close()
 if e=carrier.writeRaw(frame);e!=nil{return nil,e}
 deadline:=time.Now().Add(1500*time.Millisecond)
 var raw [2048]byte
 for time.Now().Before(deadline){
  if e=ctx.Err();e!=nil{return nil,e}
  n,readErr:=carrier.readRaw(raw[:]);if readErr!=nil{return nil,readErr}
  if n==0{continue}
  ips,valid,truncated:=physicalDNSReplyState(raw[:n],c,port,id,name)
  if truncated{_ = carrier.Close();return physicalBootstrapTCPSameEndpoint(ctx,c,query,id,name)}
  if !valid{continue}
  if len(ips)==0{return nil,fmt.Errorf("%w: no usable A answer",ErrPhysicalDNS)}
  return ips,nil
 }
 return nil,fmt.Errorf("%w: bounded physical A query timeout",ErrPhysicalDNS)
}
