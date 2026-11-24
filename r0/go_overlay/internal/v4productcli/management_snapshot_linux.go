//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
 "context"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "net"
 "net/netip"
 "os"
 "path/filepath"
 "sort"
 "strings"
 "time"

 "github.com/lly8666/wobuzhidao/internal/realityfront"
)

type managedClient struct {
 Account string `json:"account"`
 Device string `json:"device"`
 Session string `json:"session"`
 TunnelIP string `json:"tunnel_ip"`
 RemoteIP string `json:"remote_ip"`
 State string `json:"state"`
 Mode string `json:"mode"`
 Lanes uint8 `json:"lanes"`
 ConnectedSeconds int64 `json:"connected_seconds"`
 Cipher string `json:"cipher"`
 FEC string `json:"fec"`
 FECProfile int `json:"fec_profile"`
 ClientRecordLimit uint16 `json:"client_record_limit"`
 ServerRecordLimit uint16 `json:"server_record_limit"`
 RxRecords *uint64 `json:"rx_records,omitempty"`
 TxRecords *uint64 `json:"tx_records,omitempty"`
 FirstWireBytes *uint64 `json:"first_wire_bytes,omitempty"`
 GameCopied *uint64 `json:"game_kernel_copied,omitempty"`
 GameDelivered *uint64 `json:"game_first_delivered,omitempty"`
}
func managedClientFor(key realityfront.V4LinuxGameCohortID,ip [4]byte,lease string,at time.Time)managedClient{
 mode:="normal";if key.Lanes>1{mode=fmt.Sprintf("game%d",key.Lanes)}
 sec:=int64(0);if !at.IsZero(){sec=int64(time.Since(at)/time.Second)}
 return managedClient{Account:key.Principal,Device:hex.EncodeToString(key.TunnelID[:8]),Session:hex.EncodeToString(key.Epoch[:8]),TunnelIP:lease,RemoteIP:netip.AddrFrom4(ip).String(),State:"online",Mode:mode,Lanes:key.Lanes,ConnectedSeconds:sec,FEC:"",Cipher:"unknown"}
}
func(r *managedClient)applyIdentity(i realityfront.ManagementSessionIdentity){
 r.Account=i.Principal;r.TunnelIP=i.Lease;r.Session=hex.EncodeToString(i.Epoch[:8]);r.ClientRecordLimit=i.ClientRecordLimit;r.ServerRecordLimit=i.ServerRecordLimit
 switch i.Cipher{case realityfront.CipherChaCha:r.Cipher="chacha20-poly1305";case realityfront.CipherAES256:r.Cipher="aes-256-gcm";case realityfront.CipherAES128:r.Cipher="aes-128-gcm"}
}
type managementSnapshot struct {
 State string `json:"state"`
 ConfigRevision string `json:"config_revision"`
 Listen string `json:"listen"`
 ServerName string `json:"server_name"`
 ServerOuterLimit int `json:"server_outer_limit"`
 TunOSMTU int `json:"tun_os_mtu"`
 Clients []managedClient `json:"clients"`
}
func managedSnapshot(c config,tun string,rows []managedClient)managementSnapshot{
 sort.Slice(rows,func(i,j int)bool{if rows[i].Account==rows[j].Account{return rows[i].Device<rows[j].Device};return rows[i].Account<rows[j].Account})
 mtu:=0;if nic,e:=net.InterfaceByName(tun);e==nil{mtu=nic.MTU}
 return managementSnapshot{"ready",c.management.revision,net.JoinHostPort(c.localIP.String(),fmt.Sprint(c.localPort)),c.serverName,c.outerMTU,mtu,rows}
}
type serverManagement struct{
 path,revision string
 requests chan chan managementSnapshot
 listener net.Listener
 done chan struct{}
}
func managedRequests(m *serverManagement)<-chan chan managementSnapshot{if m==nil{return nil};return m.requests}
func(m *serverManagement)listen(ctx context.Context)error{
 if e:=os.MkdirAll(filepath.Dir(m.path),0755);e!=nil{return e}
 if e:=os.Remove(m.path);e!=nil&&!os.IsNotExist(e){return e}
 l,e:=net.Listen("unix",m.path);if e!=nil{return e}
 m.listener=l;m.done=make(chan struct{});m.requests=make(chan chan managementSnapshot)
 go func(){
  defer close(m.done)
  for{
   conn,e:=l.Accept();if e!=nil{return}
   _=conn.SetDeadline(time.Now().Add(3*time.Second))
   response:=make(chan managementSnapshot,1)
   select{case m.requests<-response:
    select{case s:=<-response:_=json.NewEncoder(conn).Encode(s);case <-ctx.Done():}
   case <-ctx.Done():}
   conn.Close()
  }
 }()
 return nil
}
func(m *serverManagement)close(){if m.listener!=nil{_ = m.listener.Close();<-m.done}}
func notifyManagedReady()error{
 path:=os.Getenv("NOTIFY_SOCKET");if path==""{return nil}
 if strings.HasPrefix(path,"@"){path="\x00"+path[1:]}
 conn,e:=net.DialUnix("unixgram",nil,&net.UnixAddr{Name:path,Net:"unixgram"});if e!=nil{return e}
 defer conn.Close()
 _,e=conn.Write([]byte("READY=1\nSTATUS=WBD native listener ready"));return e
}
func readManagedSnapshot(path string)(managementSnapshot,error){
 var s managementSnapshot
 conn,e:=net.DialTimeout("unix",path,3*time.Second);if e!=nil{return s,e};defer conn.Close()
 _=conn.SetDeadline(time.Now().Add(3*time.Second))
 e=json.NewDecoder(conn).Decode(&s);return s,e
}
