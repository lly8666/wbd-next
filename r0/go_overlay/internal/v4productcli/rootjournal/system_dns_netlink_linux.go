//go:build linux

package rootjournal

import (
 "encoding/binary"
 "fmt"
 "runtime"
 "strconv"
 "strings"
 "syscall"
)

// B93 real Android kernel accepted the exact rule selectors while its
// ip(8) parser rejected ipproto and its printer omitted ipproto/dport.
// This is the same cold owner and journal, not an additional routing policy.
func PlatformSystemDNSRuleIO()*SystemDNSRuleIO{
 if runtime.GOOS!="android"{return nil}
 return &SystemDNSRuleIO{Read:systemDNSNetlinkRead,Change:systemDNSNetlinkChange}
}
const (
 dnsFRAIIF=3
 dnsFRAPriority=6
 dnsFRAFwmark=10
 dnsFRASuppressIfgroup=13
 dnsFRASuppressPrefixlen=14
 dnsFRATable=15
 dnsFRAFwMask=16
 dnsFRAUID=20
 dnsFRAProtocol=21
 dnsFRAIPProto=22
 dnsFRADport=24
)
func dnsNLFamily(s string)(byte,uint32,error){
 switch s{case "-4":return syscall.AF_INET,19845,nil;case "-6":return syscall.AF_INET6,19846,nil}
 return 0,0,fmt.Errorf("invalid system DNS family")
}
func dnsNL32(v uint32)[]byte{b:=make([]byte,4);binary.NativeEndian.PutUint32(b,v);return b}
func dnsNLAttr(typ uint16,data []byte)[]byte{
 n:=4+len(data);b:=make([]byte,(n+3)&^3)
 binary.NativeEndian.PutUint16(b[:2],uint16(n))
 binary.NativeEndian.PutUint16(b[2:4],typ)
 copy(b[4:],data);return b
}
func dnsNLParse32(s string)(uint32,error){
 n,e:=strconv.ParseUint(s,0,32);return uint32(n),e
}
func systemDNSNetlinkPayload(row []string)([]byte,error){
 if len(row)!=17||row[1]!="rule"||(row[2]!="add"&&row[2]!="del")||
 row[3]!="pref"||row[5]!="iif"||row[6]!="lo"||row[7]!="fwmark"||
 row[9]!="uidrange"||row[11]!="ipproto"||row[13]!="dport"||row[14]!="53"||row[15]!="lookup"{
  return nil,fmt.Errorf("invalid system DNS rule shape")
 }
 family,table,e:=dnsNLFamily(row[0]);if e!=nil{return nil,e}
 pref,e:=dnsNLParse32(row[4]);if e!=nil||pref<systemDNSPref||pref>=systemDNSPref+2*AllMaxRules{return nil,fmt.Errorf("invalid DNS priority")}
 got,e:=dnsNLParse32(row[16]);if e!=nil||got!=table{return nil,fmt.Errorf("invalid DNS table")}
 mark:=strings.Split(row[8],"/");uids:=strings.Split(row[10],"-")
 if len(mark)!=2||len(uids)!=2{return nil,fmt.Errorf("invalid DNS rule range")}
 id,e:=dnsNLParse32(mark[0]);mask,f:=dnsNLParse32(mark[1])
 lo,g:=dnsNLParse32(uids[0]);hi,h:=dnsNLParse32(uids[1])
 if e!=nil||f!=nil||g!=nil||h!=nil||id==0||id>65535||mask!=65535||lo<10000||hi<lo||hi>1999999{return nil,fmt.Errorf("invalid DNS UID/netid")}
 var proto byte
 switch row[12]{case "udp":proto=17;case "tcp":proto=6;default:return nil,fmt.Errorf("invalid DNS protocol")}
 payload:=make([]byte,12)
 payload[0]=family;payload[7]=1 // FR_ACT_TO_TBL
 ports:=make([]byte,4)
 binary.NativeEndian.PutUint16(ports[:2],53);binary.NativeEndian.PutUint16(ports[2:],53)
 for _,a:=range []struct{t uint16;b []byte}{
  {dnsFRAIIF,[]byte{'l','o',0}},{dnsFRAPriority,dnsNL32(pref)},
  {dnsFRAFwmark,dnsNL32(id)},{dnsFRATable,dnsNL32(table)},{dnsFRAFwMask,dnsNL32(mask)},
  {dnsFRAUID,append(dnsNL32(lo),dnsNL32(hi)...)},{dnsFRAIPProto,[]byte{proto}},{dnsFRADport,ports},
 }{payload=append(payload,dnsNLAttr(a.t,a.b)...)}
 return payload,nil
}
func systemDNSNetlinkAttrs(b []byte)(map[uint16][]byte,error){
 a:=map[uint16][]byte{}
 for len(b)>0{
  if len(b)<4{return nil,fmt.Errorf("short DNS rule attribute")}
  n:=int(binary.NativeEndian.Uint16(b[:2]));step:=(n+3)&^3
  t:=binary.NativeEndian.Uint16(b[2:4])
  if n<4||step>len(b){return nil,fmt.Errorf("bad DNS rule attribute")}
  if _,ok:=a[t];ok{return nil,fmt.Errorf("duplicate DNS rule attribute")}
  a[t]=b[4:n];b=b[step:]
 }
 return a,nil
}
func systemDNSNetlinkRow(data []byte,family byte,table uint32)(string,error){
 if len(data)<12{return "",fmt.Errorf("short kernel rule")}
 if data[0]!=family{return "",nil}
 a,e:=systemDNSNetlinkAttrs(data[12:]);if e!=nil{return "",e}
 u32:=func(t uint16)uint32{if len(a[t])!=4{return 0};return binary.NativeEndian.Uint32(a[t])}
 pref:=u32(dnsFRAPriority);tbl:=uint32(data[4])
 if len(a[dnsFRATable])==4{tbl=u32(dnsFRATable)}
 if tbl!=table&&(pref<systemDNSPref||pref>=systemDNSPref+2*AllMaxRules){return "",nil}
 // No loss of selectors in a text printer: only canonicalize the exact
 // kernel fields the original owner knows, reject any foreign rule.
 if data[1]!=0||data[2]!=0||data[3]!=0||data[5]!=0||data[6]!=0||
 data[7]!=1||binary.NativeEndian.Uint32(data[8:12])!=0||tbl!=table||
 string(a[dnsFRAIIF])!="lo\x00"||len(a[dnsFRAUID])!=8||
 len(a[dnsFRAIPProto])!=1||len(a[dnsFRADport])!=4||len(a[dnsFRAPriority])!=4||
 len(a[dnsFRATable])!=4||len(a[dnsFRAFwmark])!=4||len(a[dnsFRAFwMask])!=4{
  return "",fmt.Errorf("foreign DNS netlink rule at priority %d",pref)
 }
 for t,v:=range a{
  switch t{case dnsFRAIIF,dnsFRAPriority,dnsFRAFwmark,dnsFRATable,dnsFRAFwMask,dnsFRAUID,dnsFRAIPProto,dnsFRADport:
  // The kernel dump emits disabled suppress_prefixlength (-1) even
  // when the original request did not carry a suppressor. This is not
  // a selector. An enabled suppressor must still never be owned.
  case dnsFRASuppressPrefixlen,dnsFRASuppressIfgroup:
   if len(v)!=4||binary.NativeEndian.Uint32(v)!=^uint32(0){return "",fmt.Errorf("foreign DNS suppressor %d: %x",t,v)}
  case dnsFRAProtocol:if len(v)!=1||v[0]!=0{return "",fmt.Errorf("foreign DNS rule origin %x",v)}
  default:return "",fmt.Errorf("foreign DNS selector %d length=%d",t,len(v))}
 }
 ports:=a[dnsFRADport]
 if binary.NativeEndian.Uint16(ports[:2])!=53||binary.NativeEndian.Uint16(ports[2:])!=53{return "",fmt.Errorf("foreign DNS port")}
 proto:=""
 switch a[dnsFRAIPProto][0]{case 17:proto="udp";case 6:proto="tcp";default:return "",fmt.Errorf("foreign DNS protocol")}
 u:=a[dnsFRAUID]
 return fmt.Sprintf("%d: from all fwmark 0x%x/0x%x iif lo uidrange %d-%d ipproto %s dport 53 lookup %d",
  pref,u32(dnsFRAFwmark),u32(dnsFRAFwMask),binary.NativeEndian.Uint32(u[:4]),binary.NativeEndian.Uint32(u[4:]),proto,tbl),nil
}
func systemDNSNetlinkRead(s string)(string,error){
 family,table,e:=dnsNLFamily(s);if e!=nil{return "",e}
 data,e:=syscall.NetlinkRIB(34,int(family));if e!=nil{return "",e}
 messages,e:=syscall.ParseNetlinkMessage(data);if e!=nil{return "",e}
 var rows []string
 for _,m:=range messages{
  if m.Header.Type!=32{continue}
  row,e:=systemDNSNetlinkRow(m.Data,family,table);if e!=nil{return "",e}
  if row!=""{rows=append(rows,row)}
 }
 return strings.Join(rows,"\n"),nil
}
func systemDNSNetlinkChange(rows [][]string)error{
 if len(rows)==0{return nil}
 fd,e:=syscall.Socket(syscall.AF_NETLINK,syscall.SOCK_RAW|syscall.SOCK_CLOEXEC,syscall.NETLINK_ROUTE);if e!=nil{return e}
 defer syscall.Close(fd)
 if e=syscall.Bind(fd,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return e}
 if e=syscall.SetsockoptTimeval(fd,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&syscall.Timeval{Sec:3});e!=nil{return e}
 for i,row:=range rows{
  payload,e:=systemDNSNetlinkPayload(row);if e!=nil{return e}
  typ,flags:=uint16(32),uint16(0x400|0x200|1|4)
  if row[2]=="del"{typ=33;flags=1|4}
  seq:=uint32(i+1);buf:=make([]byte,16+len(payload))
  binary.NativeEndian.PutUint32(buf[:4],uint32(len(buf)))
  binary.NativeEndian.PutUint16(buf[4:6],typ);binary.NativeEndian.PutUint16(buf[6:8],flags)
  binary.NativeEndian.PutUint32(buf[8:12],seq);copy(buf[16:],payload)
  if e=syscall.Sendto(fd,buf,0,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return e}
  reply:=make([]byte,8192);n,from,e:=syscall.Recvfrom(fd,reply,0);if e!=nil{return e}
  peer,ok:=from.(*syscall.SockaddrNetlink);if !ok||peer.Pid!=0{return fmt.Errorf("nonkernel DNS rule response")}
  msgs,e:=syscall.ParseNetlinkMessage(reply[:n]);if e!=nil{return e}
  ack:=false
  for _,m:=range msgs{
   if m.Header.Seq!=seq||m.Header.Type!=syscall.NLMSG_ERROR||len(m.Data)<4{continue}
   code:=int32(binary.NativeEndian.Uint32(m.Data[:4]))
   if code!=0{return fmt.Errorf("DNS rule %s %s: %w",row[2],row[4],syscall.Errno(-code))}
   ack=true
  }
  if !ack{return fmt.Errorf("missing kernel DNS rule ACK")}
 }
 return nil
}
