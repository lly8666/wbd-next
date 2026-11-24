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
 RemotePort uint16 `json:"remote_port"`
 State string `json:"state"`
 Mode string `json:"mode"`
 Lanes uint8 `json:"lanes"`
 ConnectedSeconds int64 `json:"connected_seconds"`
 Cipher string `json:"cipher"`
 FEC string `json:"fec"`
 FECProfile int `json:"fec_profile"`
 ClientOuterSetting *uint32 `json:"client_outer_setting"`
 C2SEffectiveOuter *uint32 `json:"c2s_effective_outer"`
 S2CEffectiveOuter *uint32 `json:"s2c_effective_outer"`
 NegotiatedInnerCap *uint32 `json:"negotiated_inner_cap"`
 ClientOSInnerMTU *uint32 `json:"client_os_inner_mtu"`
 BusinessRxBytes *uint64 `json:"business_rx_bytes"`
 BusinessTxBytes *uint64 `json:"business_tx_bytes"`
 LastBusinessUnix *int64 `json:"last_business_unix"`
 RTTUs *uint64 `json:"rtt_us"`
 LossPercent *float64 `json:"loss_percent"`
 QualitySampleAgeSeconds *uint64 `json:"quality_sample_age_seconds"`
 ClientRecordLimit uint16 `json:"client_record_limit"`
 ServerRecordLimit uint16 `json:"server_record_limit"`
 RxRecords *uint64 `json:"rx_records,omitempty"`
 TxRecords *uint64 `json:"tx_records,omitempty"`
 FirstWireBytes *uint64 `json:"first_wire_bytes,omitempty"`
 GameCopied *uint64 `json:"game_kernel_copied,omitempty"`
 GameDelivered *uint64 `json:"game_first_delivered,omitempty"`
 RxRecordsPerSecond *float64 `json:"rx_records_per_second,omitempty"`
 TxRecordsPerSecond *float64 `json:"tx_records_per_second,omitempty"`
 GameCopiedPerSecond *float64 `json:"game_copied_per_second,omitempty"`
 GameDeliveredPerSecond *float64 `json:"game_delivered_per_second,omitempty"`
}
func managedClientFor(key realityfront.V4LinuxGameCohortID,ip [4]byte,lease string,at time.Time)managedClient{
 mode:="normal";if key.Lanes>1{mode=fmt.Sprintf("game%d",key.Lanes)}
 sec:=int64(0);if !at.IsZero(){sec=int64(time.Since(at)/time.Second)}
 return managedClient{Account:key.Principal,Device:hex.EncodeToString(key.TunnelID[:8]),Session:hex.EncodeToString(key.Epoch[:8]),TunnelIP:lease,RemoteIP:netip.AddrFrom4(ip).String(),State:"online",Mode:mode,Lanes:key.Lanes,ConnectedSeconds:sec,FEC:"",Cipher:"unknown"}
}
func(r *managedClient)applyIdentity(i realityfront.ManagementSessionIdentity){
 r.Account=i.Principal;r.TunnelIP=i.Lease;r.Session=hex.EncodeToString(i.Epoch[:8]);if r.Lanes==1{r.Session=hex.EncodeToString(i.Incarnation[:8])};r.ClientRecordLimit=i.ClientRecordLimit;r.ServerRecordLimit=i.ServerRecordLimit
 // Normal/off has no FEC owner to query; the authenticated policy is
 // the existing cold source for this mode. Runtime FEC readback still
 // supplies the other modes.
 if i.NormalFECOff{r.FEC="off"}
 switch i.Cipher{case realityfront.CipherChaCha:r.Cipher="chacha20-poly1305";case realityfront.CipherAES256:r.Cipher="aes-256-gcm";case realityfront.CipherAES128:r.Cipher="aes-128-gcm"}
}
// Reuse the negotiated wire-record cap and the sole Rust budget ABI.
 // This is an inner upper bound, not remote OS MTU or inferred user setting.
func(r *managedClient) applyNegotiatedBudget(){
 if r.ClientRecordLimit==0||r.ServerRecordLimit==0||r.FEC==""{return}
 mode:=uint32(0)
 if r.Lanes>1{mode=2}
 if r.FEC!="off"{mode++}
 if b,e:=realityfront.V4DeriveColdMTUBudget(realityfront.V4ColdMTUBudgetInput{
  ConfiguredOuterIPMTU:1500,PeerAdvertisedMSS:1460,
  AgreedRecordWireCap:uint32(min(r.ClientRecordLimit,r.ServerRecordLimit)),
  IPv4HeaderBytes:20,TCPDataHeaderBytes:20,Mode:mode,
 });e==nil{r.NegotiatedInnerCap=&b.SingleInnerIPCap}
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
 for i:=range rows{rows[i].applyNegotiatedBudget()}
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
