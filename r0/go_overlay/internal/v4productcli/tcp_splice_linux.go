//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

/*
#cgo LDFLAGS: -lwbd_engine
#include <stdlib.h>
void *wbd_linux_tcp_splice_start(int listener, const char *cc);
int wbd_linux_tcp_splice_stop(void *owner);
*/
import "C"
import (
    "context"
    "errors"
    "fmt"
    "log"
    "net"
    "os/exec"
    "strconv"
    "syscall"
    "unsafe"
)

type ownedTCPSplice struct{
    native unsafe.Pointer
    undo [][]string
}
func spliceCommand(args ...string) error {
    out,e:=exec.Command(args[0],args[1:]...).CombinedOutput()
    if e!=nil{return fmt.Errorf("%v: %w: %s",args,e,out)}
    return nil
}
func (p *ownedTCPSplice) add(do,undo []string)error{
    if e:=spliceCommand(do...);e!=nil{return e}
    p.undo=append(p.undo,undo);return nil
}
func (p *ownedTCPSplice) Close()error{
    var e error
    for i:=len(p.undo)-1;i>=0;i--{e=errors.Join(e,spliceCommand(p.undo[i]...))}
    p.undo=nil
    if p.native!=nil{
        if C.wbd_linux_tcp_splice_stop(p.native)!=0{e=errors.Join(e,fmt.Errorf("TCP splice owner stop failed"))}
        p.native=nil
    }
    log.Printf("WBD_TCP_SPLICE_STOP error=%v",e)
    return e
}
// One process-owned listener, one native owner. Only forwarded TUN TCP;
// local service, UDP, raw carrier and all outbound sockets retain old routing.
func startOwnedTCPSplice(c config)(*ownedTCPSplice,error){
    lc:=net.ListenConfig{Control:func(network,address string,raw syscall.RawConn)error{
        var e error
        if er:=raw.Control(func(fd uintptr){
            e=syscall.SetsockoptInt(int(fd),syscall.IPPROTO_IP,19,1) // IP_TRANSPARENT
            if e==nil{e=syscall.SetsockoptString(int(fd),syscall.IPPROTO_TCP,syscall.TCP_CONGESTION,c.tcpProxyCC)}
        });er!=nil{return er};return e
    }}
    l,e:=lc.Listen(context.Background(),"tcp4","0.0.0.0:"+strconv.Itoa(c.tcpProxyPort))
    if e!=nil{return nil,e}
    f,e:=l.(*net.TCPListener).File();l.Close()
    if e!=nil{return nil,e};defer f.Close()
    cc:=C.CString(c.tcpProxyCC);defer C.free(unsafe.Pointer(cc))
    native:=C.wbd_linux_tcp_splice_start(C.int(f.Fd()),cc)
    if native==nil{return nil,fmt.Errorf("TCP splice native start failed")}
    p:=&ownedTCPSplice{native:native}
    fail:=func(e error)(*ownedTCPSplice,error){return nil,errors.Join(e,p.Close())}
    // Reserved per-instance route table / mark from configured listener port.
    // Explicit route table and rule owner, no global TCP sysctl mutation.
    table:=strconv.Itoa(100000+c.tcpProxyPort)
    mark:=fmt.Sprintf("0x%x",0x57420000|c.tcpProxyPort)
    priority:=strconv.Itoa(100000+c.tcpProxyPort)
    route:=[]string{"local","0.0.0.0/0","dev","lo","table",table}
    if e=p.add(append([]string{"ip","-4","route","add"},route...),append([]string{"ip","-4","route","del"},route...));e!=nil{return fail(e)}
    rule:=[]string{"pref",priority,"iif",c.tunName,"fwmark",mark,"lookup",table}
    // Priority must precede main (32766), use port-derived lower priority.
    rule[1]=strconv.Itoa(10000+c.tcpProxyPort%10000)
    if e=p.add(append([]string{"ip","-4","rule","add"},rule...),append([]string{"ip","-4","rule","del"},rule...));e!=nil{return fail(e)}
    match:=[]string{"-i",c.tunName,"-p","tcp","-m","addrtype","!","--dst-type","LOCAL","-j","TPROXY","--on-port",strconv.Itoa(c.tcpProxyPort),"--on-ip","127.0.0.1","--tproxy-mark",mark+"/0xffffffff"}
    if e=p.add(append([]string{"iptables","-w","3","-t","mangle","-I","PREROUTING","1"},match...),append([]string{"iptables","-w","3","-t","mangle","-D","PREROUTING"},match...));e!=nil{return fail(e)}
    log.Printf("WBD_TCP_SPLICE_READY tun=%s port=%d cc=%s",c.tunName,c.tcpProxyPort,c.tcpProxyCC)
    return p,nil
}
