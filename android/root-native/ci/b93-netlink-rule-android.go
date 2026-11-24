//go:build android && cgo && wbd_v4_embedded_go && wbd_android_specialty_test

// CI-only independent kernel capability probe. No product fallback: compare
// the actual Android rtnetlink support to the original ip(8) parser. A
// lookup in an empty, dedicated table has no routing effect.
package v4productcli

import (
 "bytes"
 "encoding/binary"
 "errors"
 "fmt"
 "strconv"
 "strings"
 "syscall"

 "github.com/lly8666/wobuzhidao/internal/v4productcli/dnsnative"
)
const b93ProbePref=9099
const b93ProbeTable=19845
func b93U32(v uint32)[]byte{b:=make([]byte,4);binary.NativeEndian.PutUint32(b,v);return b}
func b93Attr(typ uint16,data []byte)[]byte{
 n:=4+len(data);b:=make([]byte,(n+3)&^3)
 binary.NativeEndian.PutUint16(b[:2],uint16(n))
 binary.NativeEndian.PutUint16(b[2:4],typ)
 copy(b[4:],data);return b
}
func b93RulePayload(uid,netid uint32)[]byte{
 p:=make([]byte,12)
 p[0]=syscall.AF_INET;p[7]=1 // fib_rule_hdr: FR_ACT_TO_TBL
 uids:=append(b93U32(uid),b93U32(uid)...)
 ports:=make([]byte,4)
 binary.NativeEndian.PutUint16(ports[:2],53)
 binary.NativeEndian.PutUint16(ports[2:],53)
 for _,a:=range []struct{typ uint16;data []byte}{
  {3,[]byte{'l','o',0}},{6,b93U32(b93ProbePref)},{10,b93U32(netid)},
  {15,b93U32(b93ProbeTable)},{16,b93U32(65535)},{20,uids},{22,[]byte{17}},{24,ports},
 }{p=append(p,b93Attr(a.typ,a.data)...)}
 return p
}
func b93RuleRequest(typ uint16,flags uint16,payload []byte)error{
 fd,e:=syscall.Socket(syscall.AF_NETLINK,syscall.SOCK_RAW|syscall.SOCK_CLOEXEC,syscall.NETLINK_ROUTE);if e!=nil{return e}
 defer syscall.Close(fd)
 if e=syscall.Bind(fd,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return e}
 if e=syscall.SetsockoptTimeval(fd,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&syscall.Timeval{Sec:3});e!=nil{return e}
 buf:=make([]byte,16+len(payload))
 binary.NativeEndian.PutUint32(buf[:4],uint32(len(buf)))
 binary.NativeEndian.PutUint16(buf[4:6],typ)
 binary.NativeEndian.PutUint16(buf[6:8],flags|1|4) // REQUEST, ACK
 binary.NativeEndian.PutUint32(buf[8:12],1)
 copy(buf[16:],payload)
 if e=syscall.Sendto(fd,buf,0,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return e}
 reply:=make([]byte,8192)
 n,_,e:=syscall.Recvfrom(fd,reply,0);if e!=nil{return e}
 msgs,e:=syscall.ParseNetlinkMessage(reply[:n]);if e!=nil{return e}
 for _,m:=range msgs{
  if m.Header.Seq!=1||m.Header.Type!=syscall.NLMSG_ERROR||len(m.Data)<4{continue}
  code:=int32(binary.NativeEndian.Uint32(m.Data[:4]))
  if code==0{return nil};return syscall.Errno(-code)
 }
 return fmt.Errorf("no kernel rule ACK")
}
func b93DumpRule(uid,netid uint32)(found,exact bool,err error){
 raw,e:=syscall.NetlinkRIB(34,syscall.AF_INET);if e!=nil{return false,false,e} // RTM_GETRULE
 msgs,e:=syscall.ParseNetlinkMessage(raw);if e!=nil{return false,false,e}
 expected:=b93RulePayload(uid,netid)
 attrs:=func(b []byte)(map[uint16][]byte,error){
  out:=map[uint16][]byte{}
  for len(b)>=4{
   n:=int(binary.NativeEndian.Uint16(b[:2]));step:=(n+3)&^3
   if n<4||step>len(b){return nil,fmt.Errorf("bad rule attr")}
   out[binary.NativeEndian.Uint16(b[2:4])&0x3fff]=b[4:n];b=b[step:]
  }
  return out,nil
 }
 want,e:=attrs(expected[12:]);if e!=nil{return false,false,e}
 for _,m:=range msgs{
  if m.Header.Type!=32||len(m.Data)<12||m.Data[0]!=syscall.AF_INET{continue}
  have,e:=attrs(m.Data[12:]);if e!=nil{return false,false,e}
  if !bytes.Equal(have[6],want[6]){continue}
  if found{return true,false,fmt.Errorf("duplicate probe priority")}
  found=true;exact=m.Data[7]==1
  for k,v:=range want{if !bytes.Equal(have[k],v){exact=false}}
 }
 return found,exact,nil
}
func b93ProbeDNSRule(scope dnsnative.PhysicalScope,uid int)(ret error){
 netid:=uint32(scope.NetworkHandle>>32)
 if netid==0||netid>65535{return fmt.Errorf("invalid selected netid")}
 // Only proceed if the dedicated table and exact probe priority are empty.
 routes,e:=b90IP("-4","route","show","table","all");if e!=nil{return e}
 for _,line:=range strings.Split(routes,"\n"){
  if strings.Contains(" "+line+" "," table "+strconv.Itoa(b93ProbeTable)+" "){return fmt.Errorf("probe table occupied")}
 }
 found,_,e:=b93DumpRule(uint32(uid),netid)
 if e!=nil{fmt.Println("B93_DNS_NETLINK_DUMP_BLOCKED",e);return nil}
 if found{return fmt.Errorf("probe priority occupied")}
 payload:=b93RulePayload(uint32(uid),netid)
 e=b93RuleRequest(32,0x400|0x200,payload) // CREATE|EXCL
 if e!=nil{
  fmt.Println("B93_DNS_NETLINK_ADD_REJECTED",e)
  f,exact,dumpErr:=b93DumpRule(uint32(uid),netid)
  if dumpErr!=nil{return errors.Join(e,dumpErr)}
  if !f{return nil}
  if !exact{return fmt.Errorf("probe ACK failed and foreign rule found")}
  if d:=b93RuleRequest(33,0,payload);d!=nil{return errors.Join(e,d)}
  f,_,dumpErr=b93DumpRule(uint32(uid),netid)
  if dumpErr!=nil||f{return errors.Join(e,dumpErr,fmt.Errorf("probe cleanup unproven"))}
  return nil
 }
 defer func(){
  // Exact delete of only this fresh probe rule, never a broad flush.
  d:=b93RuleRequest(33,0,payload)
  f,_,r:=b93DumpRule(uint32(uid),netid)
  ret=errors.Join(ret,d,r)
  if f{ret=errors.Join(ret,fmt.Errorf("probe rule still present"))}
  if ret==nil{fmt.Println("B93_DNS_NETLINK_PROBE_CLEAN_PASS")}
 }()
 f,exact,e:=b93DumpRule(uint32(uid),netid)
 if e!=nil{return e}
 if !f||!exact{return fmt.Errorf("probe rule exact binary readback failed")}
 fmt.Println("B93_DNS_NETLINK_EXACT_SELECTORS_PASS")
 out,e:=b90IP("-4","rule","show")
 if e!=nil{return e}
 for _,line:=range strings.Split(out,"\n"){
  if strings.HasPrefix(strings.TrimSpace(line),strconv.Itoa(b93ProbePref)+":"){
   fmt.Println("B93_DNS_IP_PRINT",strings.TrimSpace(line))
  }
 }
 return nil
}
