//go:build windows

package faketcp

// PLAN029: a single bounded, physical-Npcap UDP A lookup. Unlike a normal
// Winsock resolver, this never traverses the owned Wintun /1 routes or WFP's
// non-tunnel port-53 guard. It is only used for the configured SERVER host,
// not as a bypass for ordinary business DNS. There is no persistent worker.
import (
 "context"
 "crypto/rand"
 "encoding/binary"
 "errors"
 "fmt"
 "net/netip"
 "strings"
 "syscall"
 "time"
 "unsafe"

 "golang.org/x/net/dns/dnsmessage"
)

var ErrPhysicalDNS = errors.New("faketcp: physical server bootstrap DNS failed")

type PhysicalDNSConfig struct {
 Device string
 SourceMAC, NextHopMAC [6]byte
 Source4, Resolver4 netip.Addr
}

func (c PhysicalDNSConfig) valid() bool {
 return canonicalNpcapDevice(c.Device) &&
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

func physicalDNSReply(frame []byte,c PhysicalDNSConfig,port,id uint16,name dnsmessage.Name)([]netip.Addr,bool){
 ip,ok:=extractEthernetIPv4(frame)
 if !ok||len(ip)<28||ip[9]!=17||binary.BigEndian.Uint16(ip[6:8])&0x3fff!=0{return nil,false}
 ihl:=int(ip[0]&0x0f)*4
 if ihl<20||len(ip)<ihl+8||physicalDNSChecksumFold(physicalDNSChecksumSum(ip[:ihl]))!=0{return nil,false}
 dst,src:=c.Source4.As4(),c.Resolver4.As4()
 if string(ip[12:16])!=string(src[:])||string(ip[16:20])!=string(dst[:]){return nil,false}
 udp:=ip[ihl:]
 if binary.BigEndian.Uint16(udp[0:2])!=53||binary.BigEndian.Uint16(udp[2:4])!=port{return nil,false}
 used:=int(binary.BigEndian.Uint16(udp[4:6]))
 if used<8||used>len(udp){return nil,false}
 udp=udp[:used]
 if binary.BigEndian.Uint16(udp[6:8])!=0 && physicalDNSChecksumFold(physicalDNSPseudoSum(src[:],dst[:],udp))!=0{return nil,false}
 var p dnsmessage.Parser
 h,err:=p.Start(udp[8:])
 if err!=nil||!h.Response||h.ID!=id||h.Truncated{return nil,false}
 q,e:=p.Question()
 if e!=nil||q.Type!=dnsmessage.TypeA||q.Class!=dnsmessage.ClassINET||
  !strings.EqualFold(q.Name.String(),name.String()){return nil,false}
 if e=p.SkipAllQuestions();e!=nil{return nil,false}
 if h.RCode!=dnsmessage.RCodeSuccess{return nil,true}
 var out []netip.Addr
 for len(out)<8 {
  a,e:=p.Answer()
  if e==dnsmessage.ErrSectionDone{break}
  if e!=nil{return nil,false}
  if a.Header.Type!=dnsmessage.TypeA||a.Header.Class!=dnsmessage.ClassINET{continue}
  body,ok:=a.Body.(*dnsmessage.AResource)
  if !ok{continue}
  addr:=netip.AddrFrom4(body.A)
  if !addr.IsUnspecified()&&!addr.IsMulticast()&&!addr.IsLoopback() {
   duplicate:=false
   for _,v:=range out{if v==addr{duplicate=true;break}}
   if !duplicate{out=append(out,addr)}
  }
 }
 return out,true
}

// LookupPhysicalServerA performs ONE exact DNS query with a short deadline.
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

 dll,e:=loadNpcapDLL()
 if e!=nil{return nil,fmt.Errorf("%w: verified Npcap DLL: %v",ErrPhysicalDNS,e)}
 defer dll.Release()
 procs:=make(map[string]*syscall.Proc,10)
 for _,key:=range []string{"pcap_open_live","pcap_datalink","pcap_setmode","pcap_compile","pcap_setfilter","pcap_freecode","pcap_sendpacket","pcap_next_ex","pcap_close","pcap_geterr"}{
  p,err:=dll.FindProc(key);if err!=nil{return nil,fmt.Errorf("%w: Npcap export %s",ErrPhysicalDNS,key)}
  procs[key]=p
 }
 device,e:=syscall.BytePtrFromString(c.Device);if e!=nil{return nil,ErrPhysicalDNS}
 var errorBuffer [pcapErrbufSize]byte
 handle,_,_:=procs["pcap_open_live"].Call(
  uintptr(unsafe.Pointer(device)),2048,0,pcapReadTimeoutMS,uintptr(unsafe.Pointer(&errorBuffer[0])))
 if handle==0{return nil,fmt.Errorf("%w: Npcap open physical device: %s",ErrPhysicalDNS,cString(errorBuffer[:]))}
 defer procs["pcap_close"].Call(handle)
 if typ,_,_:=procs["pcap_datalink"].Call(handle);int32(typ)!=pcapDLTEthernet{
  return nil,fmt.Errorf("%w: physical device must be Ethernet",ErrPhysicalDNS)
 }
 if ret,_,_:=procs["pcap_setmode"].Call(handle,npcapModeSendToRxClear);int32(ret)!=0{
  return nil,fmt.Errorf("%w: Npcap receive policy: %s",ErrPhysicalDNS,pcapError(procs["pcap_geterr"],handle))
 }
 filter:=fmt.Sprintf("udp and src host %s and dst host %s and src port 53 and dst port %d and (ip[6:2] & 0x3fff = 0)",
  c.Resolver4,c.Source4,port)
 f,e:=syscall.BytePtrFromString(filter);if e!=nil{return nil,ErrPhysicalDNS}
 var program pcapBPFProgram
 if ret,_,_:=procs["pcap_compile"].Call(handle,uintptr(unsafe.Pointer(&program)),
  uintptr(unsafe.Pointer(f)),1,pcapNetmaskUnknown);int32(ret)!=0{
  return nil,fmt.Errorf("%w: Npcap DNS filter: %s",ErrPhysicalDNS,pcapError(procs["pcap_geterr"],handle))
 }
 defer procs["pcap_freecode"].Call(uintptr(unsafe.Pointer(&program)))
 if ret,_,_:=procs["pcap_setfilter"].Call(handle,uintptr(unsafe.Pointer(&program)));int32(ret)!=0{
  return nil,fmt.Errorf("%w: Npcap exact DNS filter: %s",ErrPhysicalDNS,pcapError(procs["pcap_geterr"],handle))
 }
 if ctx.Err()!=nil{return nil,ctx.Err()}
 if ret,_,_:=procs["pcap_sendpacket"].Call(handle,uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)));int32(ret)!=0{
  return nil,fmt.Errorf("%w: Npcap DNS TX: %s",ErrPhysicalDNS,pcapError(procs["pcap_geterr"],handle))
 }
 deadline:=time.Now().Add(1500*time.Millisecond)
 for time.Now().Before(deadline){
  if e:=ctx.Err();e!=nil{return nil,e}
  var header,packet uintptr
  ret,_,_:=procs["pcap_next_ex"].Call(handle,uintptr(unsafe.Pointer(&header)),uintptr(unsafe.Pointer(&packet)))
  if int32(ret)==0 {continue}
  if int32(ret)!=1{return nil,fmt.Errorf("%w: Npcap DNS RX code %d",ErrPhysicalDNS,int32(ret))}
  if header==0||packet==0{continue}
  h:=(*pcapHeader)(unsafe.Pointer(header))
  if h.Caplen<42||h.Caplen>2048||h.Caplen!=h.Len{continue}
  wire:=unsafe.Slice((*byte)(unsafe.Pointer(packet)),int(h.Caplen))
  ips,valid:=physicalDNSReply(wire,c,port,id,name)
  if !valid{continue}
  if len(ips)==0{return nil,fmt.Errorf("%w: no usable A answer",ErrPhysicalDNS)}
  return ips,nil
 }
 return nil,fmt.Errorf("%w: bounded physical A query timeout",ErrPhysicalDNS)
}
