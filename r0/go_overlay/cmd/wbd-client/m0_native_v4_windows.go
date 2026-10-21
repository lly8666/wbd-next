//go:build windows && wbd_v4_embedded_go
package main

// Real PUBLIC native Windows CLI protected FakeTCP/TLS original-Go Rust
// V4 admission. Explicit --native-v4-product opens a PLAN021 network
// test-channel trial after exact-source Actions validation, not automatic
// host activation or any fake Applied result.
import(
 "context"
 "crypto/rand"
 "encoding/binary"
 "errors"
 "fmt"
 "net/netip"
 "os"
 "os/signal"
 "path/filepath"
 "sync"
 "syscall"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
 "github.com/lly8666/wobuzhidao/internal/windowsownerlease"
 "golang.org/x/sys/windows"
)

func runM0NativeV4Windows(o m0NativeV4Options)error{
 if !o.ServerIP.Is4()||o.ServerPort==0||o.SourcePort==0||
  o.ServerName==""||len(o.RouteKey)<16||o.Username==""||o.Password==""||
  o.TunnelID==([16]byte{})||o.Installation==([16]byte{})||
  !o.Lease4.IsValid()||!o.Lease4.Addr().Is4()||o.Lease4.Bits()!=32||
  o.Lease4.Addr().IsUnspecified()||o.TunnelMTU<576||o.TunnelMTU>1500{
  return windowsclient.ErrN4NativeGuard
 }
 ctx,cancel:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
 defer cancel()
 if o.ControlStdin{go watchGUIControl(os.Stdin,cancel)}
 slot,err:=acquireGUIClientSlot()
 if err!=nil{return err}
 defer windows.CloseHandle(slot)
 underlay,err:=windowsclient.DiscoverPhysicalUnderlay(o.ServerIP,0)
 if err!=nil{return err}
 ncfg,err:=underlay.NpcapConfig(o.SourcePort,o.ServerPort,1,faketcp.PacketPersonaWindows11)
 if err!=nil{return err}
 endpoint,err:=faketcp.OpenNpcapEndpoint(ncfg)
 if err!=nil{return err}
 defer endpoint.Close()
 flow:=faketcp.ClientFlow{
  LocalIP:underlay.Source4.As4(),PeerIP:o.ServerIP.As4(),
  LocalPort:o.SourcePort,PeerPort:o.ServerPort,
 }
 var seed [4]byte
 if _,err=rand.Read(seed[:]);err!=nil{return err}
 assoc,err:=faketcp.NewClientAssociation(flow,binary.BigEndian.Uint32(seed[:]),time.Second,
  func(seg faketcp.Segment)error{
   _,e:=endpoint.WriteSegment(1,seg)
   return e
  })
 if err!=nil{return err}
 defer assoc.Close()
 failure:=make(chan error,2)
 nativeFrames:=make(chan faketcp.Segment,64)
 var readers sync.WaitGroup
 readers.Add(1)
 go func(){
  defer readers.Done()
  for{
   seg,_,e:=endpoint.ReadSegment(1)
   if e!=nil{
    select{case failure<-e:default:}
    return
   }
   if assoc.State()==faketcp.ClientAssociationDetached{
    // Verified original TLS hands the bounded real TCP frame to Rust M3.
    select{case nativeFrames<-seg:
    default:
     select{case failure<-windowsclient.ErrN4NativeGuard:default:}
     return
    }
    continue
   }
   if e=assoc.HandleSegment(seg,time.Now());e!=nil{
    select{case failure<-e:default:}
    return
   }
  }
 }()
 defer func(){ _=endpoint.Close();readers.Wait() }()
 if err=assoc.Start(time.Now());err!=nil{return err}
 ticker:=time.NewTicker(100*time.Millisecond)
 defer ticker.Stop()
 handshaked:=make(chan error,1)
 go func(){handshaked<-assoc.WaitEstablished(ctx)}()
 waitHandshake:
 for{
  select{
  case <-ctx.Done():return ctx.Err()
  case e:=<-failure:return fmt.Errorf("original V4 TCP bootstrap failed: %w",e)
  case e:=<-handshaked:
   if e!=nil{return e}
   break waitHandshake
  case <-ticker.C:
   if _,e:=assoc.EmitRetransmitDue(time.Now());e!=nil{return e}
  }
 }
 // Original pinned TLS handshake, protected credentials, exact
 // FakeTCP Detach and native Rust M1/M3 Commit: no synthetic cold key.
 policy,e:=realityfront.FixedPolicyForClient(1,0)
 if e!=nil{return e}
 auth:=realityfront.ClientAdmissionConfig{
  TLS:realityfront.ClientConfig{ServerName:o.ServerName,
    RouteKey:append([]byte(nil),o.RouteKey...),Timeout:15*time.Second},
  AutoLease:false,DesiredLanes:1,InstallationID:o.Installation[:],
  Username:o.Username,Password:o.Password,
  TunnelID:o.TunnelID[:],ClientLimit:1400,
  LaneID:1,Policy:policy,
 }
 dll:=filepath.Join(windowsExecutableDir(),"wbd_engine.dll")
 if !filepath.IsAbs(dll){return windowsclient.ErrN4NativeGuard}
 owner,session,e:=realityfront.V4WindowsEstablishOriginalClientOwner(ctx,dll,assoc,auth)
 if e!=nil{return fmt.Errorf("original credential TLS→native Rust V4 owner rejected: %w",e)}
 // After TLS+Rust, either the same native product service assumes
 // full ownership or we retire Rust FIRST; never return GUI Applied
 // because the Wintun alias/process exists.
 defer func(){
  stop,c:=context.WithTimeout(context.Background(),15*time.Second)
  defer c()
  _=owner.StopScopedOwner(stop)
 }()
 if session==nil||session.Epoch==[16]byte{}{
  return windowsclient.ErrN4NativeGuard
 }
 tun,e:=windowsclient.OpenTUN(o.AdapterAlias)
 if e!=nil{return e}
 defer tun.Close()
 // The sole typed product owns the exact Rust↔Wintun native hold,
 // instead of a separate pre-binding that could outlive OS WAL.
 physical,e:=underlay.PhysicalPath()
 if e!=nil{return e}
 plan,e:=windowsclient.BuildCompactNetworkPlan(windowsclient.Config{
  AdapterAlias:o.AdapterAlias,TunnelMTU:o.TunnelMTU,
  Lease4:o.Lease4,Server4:o.ServerIP,Physical:physical,
  DNSServers4:append([]netip.Addr(nil),o.DNSServers4...),
  Direct4:append([]netip.Prefix(nil),o.Direct4...),
  Bypass4:append([]netip.Prefix(nil),o.Bypass4...),
  StatePath:o.StatePath,
 })
 if e!=nil{return e}
 if plan.StatePath==""{return windowsclient.ErrN4NativeGuard}
 transport,e:=newM0NativeV4Peer(owner,endpoint,flow,nativeFrames)
 if e!=nil{return e}
 product,e:=windowsownerlease.PrepareOriginalTLSNativeProduct(
  ctx,owner,tun,plan,o.Installation,session.Epoch,transport)
 if e!=nil{return e}
 cleanup:=func()error{
  stop,c:=context.WithTimeout(context.Background(),60*time.Second)
  defer c()
  return product.Stop(stop)
 }
 // PLAN021 explicit user authorization: exact-source GitHub Actions
 // functional PASS admits opt-in --native-v4-product NETWORK TRIALS.
 // The old frozen N4NativeNetworkReady is an unconditional V3 product
 // barrier and cannot decide whether this V4 product's real per-session
 // original TLS/Rust/Wintun/WFP/route WAL owner is valid. Do not call it.
 // This is NOT an Applied grant: Apply/LiveReceipt/Stop remain the sole
 // native generation/OS/crypto authorities, and an unsupported WFP, /1
 // route, bad owner or failed packet remains a real error and retained WAL.
 receipt,e:=product.Apply(ctx)
 if e!=nil{return errors.Join(e,cleanup())}
 if !receipt.AllNativeOSApplied{return errors.Join(windowsclient.ErrN4NativeGuard,cleanup())}
 observed,e:=product.LiveReceipt(ctx)
 if e!=nil||!observed.AllNativeOSApplied{
  return errors.Join(e,windowsclient.ErrN4NativeGuard,cleanup())
 }
 fmt.Println("WBD_WINDOWS_NATIVE_APPLIED_V1 original_tls=1 rust_m3=1 signed_wintun=1 os_wal=1")
 // Native OS readback and original Rust M3 peer first+reverse proved.
 fmt.Println("WBD_WINDOWS_OS_APPLIED")
 fmt.Println("WBD_WINDOWS_CLIENT_READY")
 var runtimeErr error
 select{
 case <-ctx.Done():
 case runtimeErr=<-failure:
 case runtimeErr=<-transport.Errors():
 }
 stopErr:=cleanup()
 if stopErr!=nil{return errors.Join(runtimeErr,stopErr)}
 fmt.Println("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1")
 return runtimeErr
}
