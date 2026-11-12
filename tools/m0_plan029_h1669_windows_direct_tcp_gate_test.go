//go:build windows
package windowsclient

// PLAN029 minimal SIGNED Windows TCP capability gate. No old WFP guard,
// no Defender rule edits, no mock Wintun, no assumed full Direct/Tunnel PASS.
import (
 "context"
 "crypto/rand"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net"
 "net/netip"
 "os"
 "path/filepath"
 "syscall"
 "testing"
 "time"
 "unsafe"
)

func p029Sum(b []byte)uint16{
 var s uint32
 for len(b)>1{s+=uint32(binary.BigEndian.Uint16(b[:2]));b=b[2:]}
 if len(b)>0{s+=uint32(b[0])<<8}
 for s>>16!=0{s=(s&0xffff)+(s>>16)}
 return ^uint16(s)
}
func p029TCP4(src,dst [4]byte,sport,dport uint16,seq,ack uint32,flags byte,payload []byte)[]byte{
 plen:=20+20+len(payload)
 b:=make([]byte,plen)
 b[0]=0x45;b[8]=64;b[9]=6
 binary.BigEndian.PutUint16(b[2:4],uint16(plen))
 binary.BigEndian.PutUint16(b[6:8],0x4000)
 copy(b[12:16],src[:]);copy(b[16:20],dst[:])
 binary.BigEndian.PutUint16(b[10:12],p029Sum(b[:20]))
 tcp:=b[20:]
 binary.BigEndian.PutUint16(tcp[0:2],sport)
 binary.BigEndian.PutUint16(tcp[2:4],dport)
 binary.BigEndian.PutUint32(tcp[4:8],seq)
 binary.BigEndian.PutUint32(tcp[8:12],ack)
 tcp[12]=0x50;tcp[13]=flags
 binary.BigEndian.PutUint16(tcp[14:16],65535)
 copy(tcp[20:],payload)
 pseudo:=make([]byte,12+len(tcp))
 copy(pseudo[0:4],src[:]);copy(pseudo[4:8],dst[:])
 pseudo[9]=6;binary.BigEndian.PutUint16(pseudo[10:12],uint16(len(tcp)))
 copy(pseudo[12:],tcp)
 check:=p029Sum(pseudo);if check==0{check=0xffff}
 binary.BigEndian.PutUint16(tcp[16:18],check)
 return b
}
func p029AwaitTCP(ctx context.Context,ring *N4OriginalKernelPacketLease,src,dst [4]byte,sport,dport uint16,flags byte,payload []byte)(uint32,error){
 var b [65535]byte
 end:=time.Now().Add(6*time.Second)
 for time.Now().Before(end){
  if e:=ctx.Err();e!=nil{return 0,e}
  n,e:=ring.n4ReceiveReadyIPv4(ctx,b[:])
  if errors.Is(e,ErrN4NativeNoPacket){time.Sleep(10*time.Millisecond);continue}
  if e!=nil{return 0,e}
  if n<40||b[0]>>4!=4||b[9]!=6||b[0]&0x0f!=5{continue}
  if string(b[12:16])!=string(src[:])||string(b[16:20])!=string(dst[:]){continue}
  tcp:=b[20:n]
  if binary.BigEndian.Uint16(tcp[0:2])!=sport||binary.BigEndian.Uint16(tcp[2:4])!=dport{continue}
  if tcp[13]&flags!=flags{continue}
  ihl:=int(tcp[12]>>4)*4
  if ihl<20||ihl>len(tcp){continue}
  if len(payload)>0&&(len(tcp)<ihl+len(payload)||string(tcp[ihl:ihl+len(payload)])!=string(payload)){continue}
  return binary.BigEndian.Uint32(tcp[4:8]),nil
 }
 return 0,fmt.Errorf("real signed Windows TCP kernel response absent within 6s; no WFP/firewall bypass attempted")
}

func TestPlan029RealSignedWintunKernelTCPListenerFeasibility(t *testing.T){
 if os.Getenv("WBD_PLAN029_DIRECT_TCP_GATE")!="1"||os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("real Windows signed Wintun only")
 }
 receipt:=map[string]any{
  "source_sha":os.Getenv("GITHUB_SHA"),"result":"FAIL_UNFINISHED",
  "driver":"REAL_SIGNED_WINTUN","wfp_guard":"NOT_CREATED",
  "system_firewall_change":"NONE","tcp_real_kernel":"NOT_QUALIFIED",
  "physical_socket_egress":"NOT_RUN","full_direct_owner":"NOT_RUN",
  "tls_original":"NOT_RUN","fallback_tcp_stack":"NOT_CHOSEN"}
 defer func(){
  path:=os.Getenv("WBD_PLAN029_TCP_GATE_RECEIPT")
  if path==""{t.Error("receipt path missing");return}
  b,e:=json.MarshalIndent(receipt,"","  ");if e!=nil{t.Error(e);return}
  if e=os.MkdirAll(filepath.Dir(path),0700);e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Error(e)}
 }()
 if receipt["source_sha"]==""{t.Fatal("SOURCE SHA missing")}
 ctx,cancel:=context.WithTimeout(context.Background(),45*time.Second);defer cancel()
 var seed [8]byte;if _,e:=rand.Read(seed[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-TCP-"+hex.EncodeToString(seed[:]))
 if e!=nil{receipt["result"]="NOT_RUN_REAL_DRIVER_UNAVAILABLE";t.Fatalf("real signed Wintun OpenTUN failed: %v",e)}
 t.Cleanup(func(){if e:=tun.Close();e!=nil{t.Errorf("owned Wintun close: %v",e)}})
 now,e:=tun.NativeIdentity(ctx)
 if e!=nil||!now.CreatedByProcess||now.Index==0||now.LUID==0{t.Fatalf("real native Wintun identity %+v %v",now,e)}
 local:=netip.MustParseAddr("198.18.88.77")
 remote:=netip.MustParseAddr("198.18.88.88")
 lease:=N4NativeLeaseIntent{InterfaceIndex:now.Index,Prefix:netip.PrefixFrom(local,32)}
 existing,found,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
 if e!=nil||found{t.Fatalf("test-only source4 is already owned or unknown: found=%v row=%v error=%v",found,existing,e)}
 row,e:=n4NativeLeaseRow(lease);if e!=nil{t.Fatal(e)}
 if e=n4CreateUnicast.Find();e!=nil{t.Fatal(e)}
 code,_,_:=n4CreateUnicast.Call(uintptr(unsafe.Pointer(&row)))
 if code!=0{t.Fatalf("real Windows IP Helper /32 create rc=%d",code)}
 t.Cleanup(func(){
  cleanup,stop:=context.WithTimeout(context.Background(),10*time.Second);defer stop()
  observed,present,e:=(N4WindowsLeaseReader{}).Lookup(cleanup,lease)
  if e!=nil||!present||N4NativeLeaseDADGate(observed,lease)!=nil{
   t.Errorf("refuse unsafe test lease delete; inspect owned address manually found=%v err=%v",present,e);return
  }
  if e=n4DeleteUnicast.Find();e!=nil{t.Errorf("IP Helper delete procedure: %v",e);return}
  rc,_,_:=n4DeleteUnicast.Call(uintptr(unsafe.Pointer(&observed)))
  if rc!=0{t.Errorf("owned test /32 remove rc=%d",rc)}
 })
 for {
  current,present,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
  if e!=nil{t.Fatal(e)}
  if present&&N4NativeLeaseDADGate(current,lease)==nil{break}
  if ctx.Err()!=nil{t.Fatal("actual owned Wintun address DAD never Preferred")}
  time.Sleep(100*time.Millisecond)
 }
 route:=NativeRouteKey{Prefix:netip.PrefixFrom(remote,32),Interface:now.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7}
 backend:=N4WindowsRouteBackend{}
 present,_,e:=backend.Lookup(ctx,route)
 if e!=nil||present{t.Fatalf("test-only remote /32 conflict: %v %v",present,e)}
 if e=backend.CreateIfAbsent(ctx,route);e!=nil{t.Fatalf("real exact route create: %v",e)}
 t.Cleanup(func(){cleanup,done:=context.WithTimeout(context.Background(),10*time.Second);defer done();if e:=backend.RemoveOwned(cleanup,route);e!=nil{t.Errorf("test exact /32 restore: %v",e)}})
 present,exact,e:=backend.Lookup(ctx,route)
 if e!=nil||!present||!exact{t.Fatalf("readback of owned exact reverse route failed %v %v %v",present,exact,e)}
 server,e:=net.ListenTCP("tcp4",&net.TCPAddr{IP:net.IP(local.AsSlice()),Port:0})
 if e!=nil{t.Fatalf("real Windows TCP kernel could not bind owned Wintun address: %v",e)}
 t.Cleanup(func(){server.Close()})
 port:=uint16(server.Addr().(*net.TCPAddr).Port)
 var installation,generation [16]byte
 if _,e=rand.Read(installation[:]);e!=nil{t.Fatal(e)}
 if _,e=rand.Read(generation[:]);e!=nil{t.Fatal(e)}
 guid,e:=n4NativeInterfaceGUID(now.Index);if e!=nil{t.Fatal(e)}
 id:=N4UnifiedIdentity{Installation:installation,Generation:generation,WintunLUID:now.LUID,
  WintunIndex:now.Index,WintunGUID:guid.String(),AdapterAlias:tun.Name()}
 pin,e:=n4ProbeOriginalWintunPnP(ctx,id);if e!=nil{t.Fatal(e)}
 id.PnPInstanceSHA256=pin.InstanceSHA256
 ring,e:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
 if e!=nil{t.Fatalf("real owned signed native ring: %v",e)}
 t.Cleanup(func(){cl,done:=context.WithTimeout(context.Background(),10*time.Second);defer done();if e:=ring.Stop(cl);e!=nil{t.Errorf("owned ring Stop: %v",e)}})
 s,d:=remote.As4(),local.As4()
 const sport uint16=46131
 const clientSeq uint32=0x23011000
 send:=func(seq,ack uint32,flags byte,payload []byte){
  pkt:=p029TCP4(s,d,sport,port,seq,ack,flags,payload)
  n,e:=tun.WritePacket(pkt)
  if e!=nil||n!=len(pkt){t.Fatalf("real WintunSendPacket TCP copy n=%d expected=%d error=%v",n,len(pkt),e)}
 }
 send(clientSeq,0,0x02,nil)
 serverSeq,e:=p029AwaitTCP(ctx,ring,d,s,port,sport,0x12,nil)
 if e!=nil{receipt["result"]="FAIL_SIGNED_WINTUN_KERNEL_TCP_SYNACK_ABSENT";t.Fatal(e)}
 send(clientSeq+1,serverSeq+1,0x10,nil)
 server.SetDeadline(time.Now().Add(7*time.Second))
 conn,e:=server.AcceptTCP()
 if e!=nil{t.Fatalf("real Windows kernel TCP listener did not accept injected three-way handshake: %v",e)}
 defer conn.Close()
 if e=conn.SetDeadline(time.Now().Add(7*time.Second));e!=nil{t.Fatal(e)}
 payload:=[]byte("plan029-genuine-kernel-tcp-payload")
 send(clientSeq+1,serverSeq+1,0x18,payload)
 read:=make([]byte,len(payload))
 if _,e=io.ReadFull(conn,read);e!=nil||string(read)!=string(payload){
  t.Fatalf("real Windows TCP socket did not receive Wintun-injected data: %v %q",e,read)
 }
 reply:=[]byte("windows-kernel-reverse-tcp")
 if _,e=conn.Write(reply);e!=nil{t.Fatal(e)}
 if _,e=p029AwaitTCP(ctx,ring,d,s,port,sport,0x10,reply);e!=nil{
  t.Fatalf("real reverse Windows kernel socket-to-Wintun packet absent: %v",e)
 }
 send(clientSeq+1+uint32(len(payload)),serverSeq+1+uint32(len(reply)),0x11,nil)
 conn.SetReadDeadline(time.Now().Add(6*time.Second))
 var one [1]byte
 if _,e=conn.Read(one[:]);!errors.Is(e,io.EOF){t.Fatalf("Windows TCP FIN/EOF not delivered: %v",e)}
 receipt["result"]="PASS_SCOPED_REAL_SIGNED_WINTUN_TCP_SYN_ACK_DATA_FIN_OS_ROUTE_NO_WFP"
 receipt["tcp_real_kernel"]="SYNACK_ACCEPT_DATA_REVERSE_FIN"
 receipt["windows_interface_index"]=now.Index
 receipt["owned_route_count"]=1
 t.Log("PLAN029_H1669_REAL_SIGNED_WINTUN_WINDOWS_TCP_KERNEL_INGRESS_AND_REVERSE_PASS_NO_DIRECT_EGRESS")
 var _ syscall.Errno // keep native return type evident
}
