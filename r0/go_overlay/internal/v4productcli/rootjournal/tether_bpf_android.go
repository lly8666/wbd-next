//go:build android && (arm64 || amd64)

package rootjournal

import(
 "encoding/binary"
 "errors"
 "fmt"
 "net"
 "os"
 "runtime"
 "strings"
 "sync"
 "syscall"
 "unsafe"
)

const tetherIngress=0xfffffff2
func tetherTC32(b []byte)uint32{if len(b)!=4{return 0};return binary.NativeEndian.Uint32(b)}
func tetherTCAttrs(b []byte)(map[uint16][]byte,error){
 a:=map[uint16][]byte{}
 for len(b)>0{
  if len(b)<4{return nil,fmt.Errorf("short tc attr")}
  n:=int(binary.NativeEndian.Uint16(b));step:=(n+3)&^3
  if n<4||step>len(b){return nil,fmt.Errorf("invalid tc attr")}
  a[binary.NativeEndian.Uint16(b[2:4])&0x3fff]=b[4:n];b=b[step:]
 }
 return a,nil
}
func tetherTCMsg(index int,handle,info uint32)[]byte{
 b:=make([]byte,20);binary.NativeEndian.PutUint32(b[4:],uint32(index))
 binary.NativeEndian.PutUint32(b[8:],handle);binary.NativeEndian.PutUint32(b[12:],tetherIngress)
 binary.NativeEndian.PutUint32(b[16:],info);return b
}
// Direct NETLINK_ROUTE avoids ROM-specific tc formatting and parser support.
func tetherTCRequest(typ,flags uint16,payload []byte)([][]byte,error){
 fd,e:=syscall.Socket(syscall.AF_NETLINK,syscall.SOCK_RAW|syscall.SOCK_CLOEXEC,syscall.NETLINK_ROUTE)
 if e!=nil{return nil,e};defer syscall.Close(fd)
 if e=syscall.Bind(fd,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return nil,e}
 if e=syscall.SetsockoptTimeval(fd,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&syscall.Timeval{Sec:3});e!=nil{return nil,e}
 req:=make([]byte,16+len(payload));binary.NativeEndian.PutUint32(req,uint32(len(req)))
 binary.NativeEndian.PutUint16(req[4:],typ);binary.NativeEndian.PutUint16(req[6:],flags|1)
 binary.NativeEndian.PutUint32(req[8:],1);copy(req[16:],payload)
 if e=syscall.Sendto(fd,req,0,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK});e!=nil{return nil,e}
 var out [][]byte;b:=make([]byte,65536)
 for{
  n,from,e:=syscall.Recvfrom(fd,b,0);if errors.Is(e,syscall.EINTR){continue};if e!=nil{return nil,e}
  nl,ok:=from.(*syscall.SockaddrNetlink);if !ok||nl.Pid!=0||n==len(b){return nil,fmt.Errorf("invalid tc netlink response")}
  msgs,e:=syscall.ParseNetlinkMessage(b[:n]);if e!=nil{return nil,e}
  for _,m:=range msgs{
   if m.Header.Seq!=1{continue}
   if m.Header.Flags&16!=0{return nil,fmt.Errorf("tc dump interrupted")}
   switch m.Header.Type{
   case syscall.NLMSG_ERROR:
    if len(m.Data)<4{return nil,fmt.Errorf("short tc ack")}
    rc:=int32(binary.NativeEndian.Uint32(m.Data));if rc<0{return nil,syscall.Errno(-rc)}
    if rc==0{return out,nil};return nil,fmt.Errorf("unexpected tc ack")
   case syscall.NLMSG_DONE:
    if len(m.Data)>=4{rc:=int32(binary.NativeEndian.Uint32(m.Data));if rc<0{return nil,syscall.Errno(-rc)}}
    return out,nil
   case 44:out=append(out,append([]byte(nil),m.Data...))
   }
  }
 }
}
func tetherTCRead(iface net.Interface)([]TetherBPFHook,error){
 rows,e:=tetherTCRequest(46,0x300,tetherTCMsg(iface.Index,0,0))
 if errors.Is(e,syscall.ENOENT)||errors.Is(e,syscall.ENODEV){return nil,nil}
 if e!=nil{return nil,e}
 var out []TetherBPFHook
 for _,row:=range rows{
  if len(row)<20{return nil,fmt.Errorf("short tc filter")}
  if int(tetherTC32(row[4:8]))!=iface.Index||tetherTC32(row[12:16])!=tetherIngress{continue}
  a,e:=tetherTCAttrs(row[20:]);if e!=nil{return nil,e}
  if strings.TrimRight(string(a[1]),"\x00")!="bpf"{continue}
  opts,e:=tetherTCAttrs(a[2]);if e!=nil{return nil,e}
  name:=strings.TrimRight(string(opts[7]),"\x00")
  pin,_,_:=tetherBPFName(name)
  if pin==""{
   if strings.Contains(name,"schedcls_tether_"){return nil,fmt.Errorf("unknown tether BPF name")}
   continue
  }
  flags:=tetherTC32(opts[9])
  if tetherTC32(opts[8])!=1||flags&^uint32(1|8|16)!=0||len(opts[1])!=0||len(opts[2])!=0||
   tetherTC32(opts[3])!=0||tetherTC32(a[11])!=0||tetherTC32(row[8:12])==0{
   return nil,fmt.Errorf("unsupported tether BPF classifier attributes")
  }
  h:=TetherBPFHook{Interface:iface.Name,Index:iface.Index,Handle:tetherTC32(row[8:12]),
   Info:tetherTC32(row[16:20]),ProgramID:tetherTC32(opts[11]),Flags:flags&^uint32(8),Name:name,Pin:pin}
  if !h.valid(){return nil,fmt.Errorf("invalid tether BPF classifier")}
  out=append(out,h)
 }
 return out,nil
}
func tetherBPFSyscall()uintptr{if runtime.GOARCH=="arm64"{return 280};return 321}
func tetherPinFD(pin string)(int,uint32,error){
 path:=append([]byte(pin),0)
 var pinned runtime.Pinner
 pinned.Pin(&path[0]);defer pinned.Unpin()
 attr:=struct{Path uint64;FD,Flags uint32}{Path:uint64(uintptr(unsafe.Pointer(&path[0])))}
 fd,_,errno:=syscall.Syscall(tetherBPFSyscall(),7,uintptr(unsafe.Pointer(&attr)),unsafe.Sizeof(attr))
 runtime.KeepAlive(path)
 if errno!=0{return -1,0,errno}
 info:=make([]byte,256)
 pinned.Pin(&info[0])
 req:=struct{FD,Length uint32;Info uint64}{uint32(fd),uint32(len(info)),uint64(uintptr(unsafe.Pointer(&info[0])))}
 _,_,errno=syscall.Syscall(tetherBPFSyscall(),15,uintptr(unsafe.Pointer(&req)),unsafe.Sizeof(req))
 runtime.KeepAlive(info)
 if errno!=0||tetherTC32(info[:4])!=3||tetherTC32(info[4:8])==0{
  syscall.Close(int(fd));if errno!=0{return -1,0,errno};return -1,0,fmt.Errorf("not original sched_cls BPF program")
 }
 return int(fd),tetherTC32(info[4:8]),nil
}
func tetherTCChange(h TetherBPFHook,add bool)error{
 if !h.valid(){return fmt.Errorf("invalid tether tc attachment")}
 b:=tetherTCMsg(h.Index,h.Handle,h.Info)
 b=append(b,dnsNLAttr(1,[]byte("bpf\x00"))...)
 typ,flags:=uint16(45),uint16(4)
 if add{
  fd,id,e:=tetherPinFD(h.Pin);if e!=nil{return e};defer syscall.Close(fd)
  if id!=h.ProgramID{return fmt.Errorf("pinned tether program ID changed")}
  opts:=dnsNLAttr(6,dnsNL32(uint32(fd)))
  opts=append(opts,dnsNLAttr(7,append([]byte(h.Name),0))...)
  opts=append(opts,dnsNLAttr(8,dnsNL32(1))...)
  if h.Flags!=0{opts=append(opts,dnsNLAttr(9,dnsNL32(h.Flags))...)}
  b=append(b,dnsNLAttr(2,opts)...)
  typ,flags=44,4|0x200|0x400
 }
 _,e:=tetherTCRequest(typ,flags,b);return e
}
func tetherXDPActive(indices map[int]bool)error{
 data,e:=syscall.NetlinkRIB(syscall.RTM_GETLINK,syscall.AF_UNSPEC);if e!=nil{return e}
 msgs,e:=syscall.ParseNetlinkMessage(data);if e!=nil{return e}
 for _,m:=range msgs{
  if m.Header.Type!=syscall.RTM_NEWLINK||len(m.Data)<16{continue}
  index:=int(tetherTC32(m.Data[4:8]));if !indices[index]{continue}
  a,e:=tetherTCAttrs(m.Data[16:]);if e!=nil{return e}
  if len(a[43])==0{continue}
  x,e:=tetherTCAttrs(a[43]);if e!=nil{return e}
  if len(x[2])!=1||x[2][0]!=0{return fmt.Errorf("XDP present or unreadable on tether interface")}
 }
 return nil
}
func androidTetherBPFIO(only map[string]bool)TetherBPFIO{
 return TetherBPFIO{
  Read:func()([]TetherBPFHook,error){
   interfaces,e:=net.Interfaces();if e!=nil{return nil,e}
   out:=[]TetherBPFHook{}
   for _,i:=range interfaces{
    if only!=nil&&!only[i.Name]{continue}
    if i.Flags&net.FlagLoopback!=0{continue}
    hooks,e:=tetherTCRead(i);if e!=nil{return nil,e}
    out=append(out,hooks...)
   }
   return out,nil
  },
  PinID:func(pin string)(uint32,error){fd,id,e:=tetherPinFD(pin);if e==nil{syscall.Close(fd)};return id,e},
  Change:tetherTCChange,
  Current:func(h TetherBPFHook)bool{i,e:=net.InterfaceByIndex(h.Index);return e==nil&&i.Name==h.Interface},
  BootID:func()(string,error){b,e:=os.ReadFile("/proc/sys/kernel/random/boot_id");return strings.TrimSpace(string(b)),e},
 }
}
func AndroidTetherBPFIO()TetherBPFIO{return androidTetherBPFIO(nil)}
func AndroidTetherBPFDownstreamIO(iface string)TetherBPFIO{return androidTetherBPFIO(map[string]bool{iface:true})}
// Restore legacy B117 journals as well, but inspect only their saved interfaces.
func RecoverAndroidTetherBPF(path string)error{
 record,found,e:=readTetherBPF(path);if e!=nil||!found{return e}
 scope:=map[string]bool{};for _,h:=range record.Hooks{scope[h.Interface]=true}
 return RecoverTetherBPF(androidTetherBPFIO(scope),path)
}

 // Listen for normal Android topology changes instead of adding a data-path
 // check or periodic full filter scan. Stop the session if tether offload
 // reattaches; Android remains the owner of its topology.
func WatchTetherBPFPause(k TetherBPFIO,path,selected string,onChange func())(func(),error){
 iface,e:=net.InterfaceByName(selected);if e!=nil{return nil,e}
 indices:=map[int]bool{iface.Index:true}
 fd,e:=syscall.Socket(syscall.AF_NETLINK,syscall.SOCK_RAW|syscall.SOCK_CLOEXEC|syscall.SOCK_NONBLOCK,syscall.NETLINK_ROUTE)
 if e!=nil{return nil,e}
 if e=syscall.Bind(fd,&syscall.SockaddrNetlink{Family:syscall.AF_NETLINK,Groups:9});e!=nil{syscall.Close(fd);return nil,e}
 f:=os.NewFile(uintptr(fd),"tether-bpf-events")
 if e=VerifyTetherBPFPause(k,path,selected);e!=nil{f.Close();return nil,e}
 stopping,done:=make(chan struct{}),make(chan struct{})
 var once sync.Once
 go func(){
  defer close(done)
  changed:=func(){select{case <-stopping:return;default:onChange()}}
  b:=make([]byte,65536)
  for{
   n,e:=f.Read(b);if e!=nil{changed();return}
   msgs,e:=syscall.ParseNetlinkMessage(b[:n]);if e!=nil{changed();return}
   for _,m:=range msgs{
    if m.Header.Type==syscall.RTM_DELLINK&&len(m.Data)>=16&&indices[int(tetherTC32(m.Data[4:8]))]{changed();return}
    if m.Header.Type!=44||len(m.Data)<20||!indices[int(tetherTC32(m.Data[4:8]))]||tetherTC32(m.Data[12:16])!=tetherIngress{continue}
    a,e:=tetherTCAttrs(m.Data[20:]);if e!=nil{changed();return}
    if strings.TrimRight(string(a[1]),"\x00")!="bpf"{continue}
    opts,e:=tetherTCAttrs(a[2]);if e!=nil{changed();return}
    _,upload,_:=tetherBPFName(strings.TrimRight(string(opts[7]),"\x00"));if upload{changed();return}
   }
  }
 }()
 return func(){once.Do(func(){close(stopping);f.Close();<-done})},nil
}
