//go:build windows && wbd_v4_embedded_go
package main

// Genuine per-lane original-Go FakeTCP credential/TLS bootstrap, then
// the proven Linux shared Rust GameAdapter and one native OS/WAL owner.
import(
 "context"
 "crypto/rand"
 "encoding/binary"
 "errors"
 "fmt"
 "path/filepath"
 "sync"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
)
func runM0NativeV4WindowsGame(
 ctx context.Context,o m0NativeV4Options,localIP [4]byte,
 open func(uint16,uint16)(*faketcp.NpcapEndpoint,error),
 makePlan func()(windowsclient.NetworkPlan,error),
)error{
 count:=2;if o.Mode==m0WinModeGame4{count=4}
 assocs:=make([]*faketcp.ClientAssociation,0,count)
 endpoints:=make([]*faketcp.NpcapEndpoint,0,count)
 lanes:=make([]m0GameLane,0,count)
 inbound:=make(chan m0GameInbound,256)
 failed:=make(chan error,count+1)
 var readers sync.WaitGroup
 defer func(){
  for _,ep:=range endpoints{_ = ep.Close()}
  readers.Wait()
  for _,assoc:=range assocs{assoc.Close()}
 }()
 for i:=0;i<count;i++{
  src,dst:=int(o.SourcePort)+i,int(o.ServerPort)+i
  if src>65535||dst>65535{return windowsclient.ErrN4NativeGuard}
  ep,err:=open(uint16(src),uint16(dst))
  if err!=nil{return err}
  endpoints=append(endpoints,ep)
  flow:=faketcp.ClientFlow{
   LocalIP:localIP,PeerIP:o.ServerIP.As4(),
   LocalPort:uint16(src),PeerPort:uint16(dst),
  }
  var seed [4]byte
  if _,err=rand.Read(seed[:]);err!=nil{return err}
  assoc,err:=faketcp.NewClientAssociation(flow,binary.BigEndian.Uint32(seed[:]),
   time.Second,func(seg faketcp.Segment)error{
    _,e:=ep.WriteSegment(1,seg);return e
   })
  if err!=nil{return err}
  assocs=append(assocs,assoc)
  lanes=append(lanes,m0GameLane{endpoint:ep,flow:flow})
  readers.Add(1)
  go func(index int,endpoint *faketcp.NpcapEndpoint,a *faketcp.ClientAssociation){
   defer readers.Done()
   for{
    seg,_,err:=endpoint.ReadSegment(1)
    if err!=nil{
     if ctx.Err()==nil{select{case failed<-err:default:}}
     return
    }
    if a.State()==faketcp.ClientAssociationDetached{
     select{case inbound<-m0GameInbound{lane:index,segment:seg}:
     case <-ctx.Done():return}
    }else if err=a.HandleSegment(seg,time.Now());err!=nil{
     if ctx.Err()==nil{select{case failed<-err:default:}}
     return
    }
   }
  }(i,ep,assoc)
  if err=assoc.Start(time.Now());err!=nil{return err}
  // Same original FakeTCP SYN timer as the proven one-lane Windows
  // bootstrap, separately per Game lane. No invented TCP/FEC owner.
  established,cancel:=context.WithTimeout(ctx,20*time.Second)
  handshaked:=make(chan error,1)
  go func(a *faketcp.ClientAssociation){handshaked<-a.WaitEstablished(established)}(assoc)
  tick:=time.NewTicker(100*time.Millisecond)
 waitLane:
  for{
   select{
   case <-established.Done():
    err=established.Err();break waitLane
   case err=<-handshaked:
    break waitLane
   case err=<-failed:
    break waitLane
   case <-tick.C:
    _,err=assoc.EmitRetransmitDue(time.Now())
    if err!=nil{break waitLane}
   }
  }
  tick.Stop()
  cancel()
  if err!=nil{return fmt.Errorf("original Game%d lane%d TCP: %w",count,i+1,err)}
 }
 policy,err:=realityfront.FixedPolicyForClient(count,4)
 if err!=nil{return err}
 cfg:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{
   ServerName:o.ServerName,RouteKey:append([]byte(nil),o.RouteKey...),Timeout:15*time.Second,
  },
  AutoLease:false,DesiredLanes:uint8(count),
  InstallationID:o.Installation[:],Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:1400,Policy:policy,
 }
 fecMode:=uint8(0)
 if o.FEC2Mode=="fixed"{
  profile,e:=m0WindowsV4Profile(o.FEC2Profile)
  if e!=nil{return e}
  fecMode=uint8(profile)+1 // Linux GameFec=profile+1, TLS protected
 }
 group,err:=realityfront.V4WindowsEstablishOriginalGameClientGroup(
  ctx,filepath.Join(windowsExecutableDir(),"wbd_engine.dll"),assocs,cfg,fecMode)
 if err!=nil{return err}
 tun,err:=windowsclient.OpenTUN(o.AdapterAlias)
 if err!=nil{return err}
 defer tun.Close()
 plan,err:=makePlan()
 if err!=nil{return err}
 packet:=&m0NativeV4GamePeer{
  group:group,first:group.FirstOriginalOwner(),tun:tun,fec:fecMode!=0,
  lanes:lanes,inbound:inbound,stop:make(chan struct{}),done:make(chan struct{}),
  errors:make(chan error,1),
 }
 product,err:=windowsownerlease.PrepareOriginalTLSNativeGameProduct(
  ctx,group,tun,plan,o.Installation,group.Epoch(),packet)
 if err!=nil{return err}
 stop:=func()error{
  done,cancel:=context.WithTimeout(context.Background(),60*time.Second)
  defer cancel()
  return product.Stop(done)
 }
 receipt,err:=product.Apply(ctx)
 if err!=nil{return errors.Join(err,stop())}
 if !receipt.AllNativeOSApplied{return errors.Join(windowsclient.ErrN4NativeGuard,stop())}
 live,err:=product.LiveReceipt(ctx)
 if err!=nil||!live.AllNativeOSApplied{
  return errors.Join(err,windowsclient.ErrN4NativeGuard,stop())
 }
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=%d fec=%d tls=1 rust=1 native_os_wal=1\n",count,fecMode)
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 ticker:=time.NewTicker(time.Second);defer ticker.Stop()
 var runtimeErr error
outer:
 for{
  select{
  case <-ctx.Done():break outer
  case runtimeErr=<-packet.Errors():break outer
  case runtimeErr=<-failed:break outer
  case <-ticker.C:fmt.Println("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+packet.Stats())
  }
 }
 stopErr:=stop()
 if stopErr!=nil{return errors.Join(runtimeErr,stopErr)}
 fmt.Printf("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes=%d wal_restored=1 rust_stopped=1\n",count)
 return runtimeErr
}
