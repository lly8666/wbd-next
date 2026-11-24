//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
 "bufio"
 "crypto/sha256"
 "crypto/tls"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "strings"
 "time"
)

const managedConfigPath="/etc/wbd-next/server.json"
const managedState="/var/lib/wbd-next"
const managedOpt="/opt/wbd-next"
const managedSocket="/run/wbd-next/clients.sock"
const managedUnit="/etc/systemd/system/wbd-next.service"

type managedUser struct{Username string `json:"username"`;Password string `json:"password"`}
type managedServerConfig struct{
 Listen string `json:"listen"`
 ServerName string `json:"server-name"`
 RouteKeyFile string `json:"route-key-hex-file"`
 TLSCert string `json:"tls-cert,omitempty"`
 TLSKey string `json:"tls-key,omitempty"`
 Users []managedUser `json:"users"`
 RawInterface string `json:"raw-interface,omitempty"`
 TunIPv4 string `json:"tun-ipv4,omitempty"`
 LeasePool string `json:"lease-pool,omitempty"`
 Decoy string `json:"decoy,omitempty"`
 PublicAddress string `json:"public-address,omitempty"`
}
func defaultManagedConfig()managedServerConfig{
 return managedServerConfig{Listen:"0.0.0.0:443",ServerName:"www.cisco.com",RouteKeyFile:managedState+"/route-key.hex",TLSCert:managedState+"/server.crt",TLSKey:managedState+"/server.key"}
}
func loadManagedConfig(path string)(managedServerConfig,[]byte,error){
 c:=defaultManagedConfig();b,e:=os.ReadFile(path);if e!=nil{return c,nil,e}
 e=json.Unmarshal(b,&c);return c,b,e
}
func writeManagedFile(path string,b []byte,mode os.FileMode)error{
 if e:=os.MkdirAll(filepath.Dir(path),0755);e!=nil{return e}
 f,e:=os.CreateTemp(filepath.Dir(path),".wbd-next-");if e!=nil{return e};defer os.Remove(f.Name())
 if e=f.Chmod(mode);e==nil{_,e=f.Write(b)};e=errors.Join(e,f.Close());if e!=nil{return e}
 return os.Rename(f.Name(),path)
}
func commandOutput(name string,args ...string)([]byte,error){
 b,e:=exec.Command(name,args...).CombinedOutput();if e!=nil{return b,fmt.Errorf("%s: %w: %s",name,e,strings.TrimSpace(string(b)))};return b,nil
}
func managedMaterial(c managedServerConfig)error{
 for _,p:=range []string{c.RouteKeyFile,c.TLSCert,c.TLSKey}{if e:=os.MkdirAll(filepath.Dir(p),0700);e!=nil{return e}}
 if _,e:=os.Stat(c.RouteKeyFile);os.IsNotExist(e){if e=initServerRouteKeyFile(c.RouteKeyFile);e!=nil{return e}}else if e!=nil{return e}
 _,ce:=os.Stat(c.TLSCert);_,ke:=os.Stat(c.TLSKey)
 if os.IsNotExist(ce)&&os.IsNotExist(ke){
  _,e:=commandOutput("openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","36525","-subj","/CN="+c.ServerName,"-addext","subjectAltName=DNS:"+c.ServerName,"-keyout",c.TLSKey,"-out",c.TLSCert)
  if e!=nil{return e};return os.Chmod(c.TLSKey,0600)
 }
 return errors.Join(ce,ke)
}
func defaultUnderlay()(string,error){
 b,e:=commandOutput("ip","-j","-4","route","show","default");if e!=nil{return "",e}
 var routes []struct{Dev string `json:"dev"`}
 if e=json.Unmarshal(b,&routes);e!=nil{return "",e};if len(routes)==0||routes[0].Dev==""{return "",fmt.Errorf("无默认IPv4路由，请配置 raw-interface")}
 return routes[0].Dev,nil
}
// Convert the JSON management surface into the EXISTING server parser.
// Roster lives only in a private temporary file, never in process argv.
func managedArgs(c managedServerConfig)([]string,func(),error){
 noop:=func(){}
 host,port,e:=net.SplitHostPort(c.Listen);if e!=nil{return nil,noop,e}
 iface:=c.RawInterface;if iface==""{iface,e=defaultUnderlay();if e!=nil{return nil,noop,e}}
 users:=make(map[string]string,len(c.Users))
 for _,u:=range c.Users{if _,ok:=users[u.Username];ok{return nil,noop,fmt.Errorf("重复账号: %s",u.Username)};users[u.Username]=u.Password}
 roster,e:=json.Marshal(users);if e!=nil{return nil,noop,e}
 tmp,e:=os.MkdirTemp("","wbd-next-roster-");if e!=nil{return nil,noop,e}
 clean:=func(){_ = os.RemoveAll(tmp)}
 path:=filepath.Join(tmp,"users.json")
 if e=os.WriteFile(path,roster,0600);e!=nil{clean();return nil,noop,e}
 args:=[]string{"--mode","shared","--raw-interface",iface,"--local-ip",host,"--local-port",port,"--server-name",c.ServerName,"--route-key-hex-file",c.RouteKeyFile,"--tls-cert",c.TLSCert,"--tls-key",c.TLSKey,"--users-file",path}
 if c.TunIPv4!=""{args=append(args,"--tun-ipv4",c.TunIPv4)}
 if c.LeasePool!=""{args=append(args,"--lease-pool",c.LeasePool)}
 if c.Decoy!=""{args=append(args,"--decoy",c.Decoy)}
 return args,clean,nil
}
func checkManagedConfig(c managedServerConfig)error{
 args,clean,e:=managedArgs(c);if e!=nil{return e};defer clean()
 cfg,e:=parse("server",args);if e!=nil{return e}
 if _,e=net.InterfaceByName(cfg.rawInterface);e!=nil{return e}
 _,e=tls.LoadX509KeyPair(cfg.tlsCert,cfg.tlsKey);return e
}
func saveManagedConfig(path string,c managedServerConfig)error{
 if e:=managedMaterial(c);e!=nil{return e}
 if e:=checkManagedConfig(c);e!=nil{return e}
 b,e:=json.MarshalIndent(c,"","  ");if e!=nil{return e}
 return writeManagedFile(path,append(b,'\n'),0600)
}
func serveManaged(path,socket string)error{
 c,b,e:=loadManagedConfig(path);if e!=nil{return e}
 args,clean,e:=managedArgs(c);if e!=nil{return e};defer clean()
 hash:=sha256.Sum256(b)
 return runManagedProduct("server",args,&serverManagement{path:socket,revision:hex.EncodeToString(hash[:])})
}
// The raw carrier must suppress the local kernel's RST for its owned
// listener. This is ordinary host integration, not a change to wire format.
func prepareManagedNetwork(c config)(func()error,error){
 rule:=[]string{"OUTPUT","-o",c.rawInterface,"-s",c.localIP.String(),"-p","tcp","--sport",strconv.Itoa(int(c.localPort)),"--tcp-flags","RST","RST","-m","comment","--comment","wbd-next-managed","-j","DROP"}
 original,e:=os.ReadFile("/proc/sys/net/ipv4/ip_forward");if e!=nil{return nil,e}
 if _,e=linuxMasqueradeCommand(append([]string{"-I"},rule...)...);e!=nil{return nil,e}
 cleanup:=func()error{
  _,err:=linuxMasqueradeCommand(append([]string{"-D"},rule...)...)
  if strings.TrimSpace(string(original))!="1" {
   if current,x:=os.ReadFile("/proc/sys/net/ipv4/ip_forward");x==nil&&strings.TrimSpace(string(current))=="1"{err=errors.Join(err,os.WriteFile("/proc/sys/net/ipv4/ip_forward",original,0644))}
  }
  return err
 }
 if strings.TrimSpace(string(original))!="1"{if e=os.WriteFile("/proc/sys/net/ipv4/ip_forward",[]byte("1\n"),0644);e!=nil{return nil,errors.Join(e,cleanup())}}
 return cleanup,nil
}
const managedHelp=`WBD Next 服务端管理
  wbd-next                   中文菜单（终端）
  wbd-next install           安装并开机启动（当前完整包）
  wbd-next config [--file PATH]  修改配置 / 导入配置，保存后重启生效
  wbd-next config check [--config PATH]
  wbd-next config export USER [--output PATH]  导出连接资料
  wbd-next status [--json]
  wbd-next clients [--json] [--watch]
  wbd-next start | stop | restart | logs
  wbd-next uninstall [--yes]
  wbd-next serve --config PATH  前台原生 Go TLS/Rust 服务
`
func terminalInput()bool{s,e:=os.Stdin.Stat();return e==nil&&s.Mode()&os.ModeCharDevice!=0}
func prompt(r *bufio.Reader,label,def string)(string,error){
 fmt.Printf("%s [%s]: ",label,def);v,e:=r.ReadString('\n');if e!=nil{return "",e};v=strings.TrimSpace(v);if v==""{v=def};return v,nil
}
func passwordPrompt(r *bufio.Reader)(string,error){
 fmt.Print("密码（不回显）: ")
 off:=exec.Command("stty","-echo");off.Stdin=os.Stdin;if e:=off.Run();e!=nil{return "",e}
 defer func(){on:=exec.Command("stty","echo");on.Stdin=os.Stdin;_ = on.Run();fmt.Println()}()
 v,e:=r.ReadString('\n');return strings.TrimRight(v,"\r\n"),e
}
func editManagedConfig(r *bufio.Reader)error{
 c,_,e:=loadManagedConfig(managedConfigPath);if os.IsNotExist(e){c=defaultManagedConfig()}else if e!=nil{return e}
 if c.Listen,e=prompt(r,"监听",c.Listen);e!=nil{return e}
 if c.ServerName,e=prompt(r,"借站域名",c.ServerName);e!=nil{return e}
 if c.PublicAddress,e=prompt(r,"客户端连接地址（公网IP或域名）",c.PublicAddress);e!=nil{return e}
 if c.RawInterface,e=prompt(r,"网卡（留空自动）",c.RawInterface);e!=nil{return e}
 fmt.Print("现有账号: ");for _,u:=range c.Users{fmt.Printf("%s ",u.Username)};fmt.Println()
 action,e:=prompt(r,"账号操作 add/replace/delete/keep","keep");if e!=nil{return e}
 if action!="keep"||len(c.Users)==0{
  name,e:=prompt(r,"账号","user1");if e!=nil{return e}
  if action=="delete"{for i,u:=range c.Users{if u.Username==name{c.Users=append(c.Users[:i],c.Users[i+1:]...);break}}}else{
   pass,e:=passwordPrompt(r);if e!=nil{return e}
   found:=false;for i,u:=range c.Users{if u.Username==name{c.Users[i].Password=pass;found=true}}
   if !found{c.Users=append(c.Users,managedUser{name,pass})}
  }
 }
 if e=saveManagedConfig(managedConfigPath,c);e!=nil{return e}
 fmt.Println("配置已保存；重启服务生效。客户端连接资料如有变化请重新导出。");return nil
}
func argValue(args []string,key,def string)string{for i:=0;i+1<len(args);i++{if args[i]==key{return args[i+1]}};return def}
func hasArg(args []string,key string)bool{for _,v:=range args{if v==key{return true}};return false}
func systemctl(args ...string)error{b,e:=commandOutput("systemctl",args...);if e==nil&&len(b)>0{fmt.Print(string(b))};return e}
func getUnitState()string{
 b,_:=exec.Command("systemctl","is-active","wbd-next.service").Output();return strings.TrimSpace(string(b))
}
func showManagedStatus(asJSON bool)error{
 unit:=getUnitState();c,b,e:=loadManagedConfig(managedConfigPath)
 v:=map[string]any{"service":unit,"installed":!os.IsNotExist(e)}
 if e==nil{sum:=sha256.Sum256(b);v["listen"]=c.Listen;v["server_name"]=c.ServerName;v["disk_revision"]=hex.EncodeToString(sum[:])}
 if s,e:=readManagedSnapshot(managedSocket);e==nil{v["running_revision"]=s.ConfigRevision;v["online_devices"]=len(s.Clients);v["native_ready"]=true}else{v["native_ready"]=false}
 if asJSON{return json.NewEncoder(os.Stdout).Encode(v)}
 fmt.Printf("WBD Next 服务端：%s；监听 %s；借站域名 %s\n",unit,c.Listen,c.ServerName)
 if n,ok:=v["online_devices"];ok{fmt.Printf("在线设备：%v\n",n)}
 if v["disk_revision"]!=nil&&v["running_revision"]!=nil&&v["disk_revision"]!=v["running_revision"]{fmt.Println("磁盘配置已变化，需重启服务。")}
 return nil
}
func showManagedClients(args []string)error{
 for{
  s,e:=readManagedSnapshot(managedSocket);if e!=nil{return fmt.Errorf("读取运行中的服务失败: %w",e)}
  if hasArg(args,"--json"){if e=json.NewEncoder(os.Stdout).Encode(s);e!=nil{return e}}else{
   fmt.Printf("在线设备 %d；服务端外层上限 %d；TUN OS MTU %d\n",len(s.Clients),s.ServerOuterLimit,s.TunOSMTU)
   for _,r:=range s.Clients{fmt.Printf("%s/%s  %s  %s  %s %d lane  %s  FEC=%s/%d  %ds\n",r.Account,r.Device,r.TunnelIP,r.RemoteIP,r.Mode,r.Lanes,r.Cipher,r.FEC,r.FECProfile,r.ConnectedSeconds)}
  }
  if !hasArg(args,"--watch"){return nil};time.Sleep(2*time.Second)
 }
}
func exportManagedClient(args []string)error{
 if len(args)<1{return fmt.Errorf("指定账号")}
 c,_,e:=loadManagedConfig(managedConfigPath);if e!=nil{return e}
 if c.PublicAddress==""{return fmt.Errorf("请配置 public-address")}
 var u managedUser;for _,v:=range c.Users{if v.Username==args[0]{u=v;break}}
 if u.Username==""{return fmt.Errorf("账号不存在")}
 _,port,e:=net.SplitHostPort(c.Listen);if e!=nil{return e}
 key,e:=readPrivateArgFile(c.RouteKeyFile);if e!=nil{return e}
 pem,e:=os.ReadFile(c.TLSCert);if e!=nil{return e}
 data:=map[string]any{"address":c.PublicAddress,"port":port,"server-name":c.ServerName,"route-key-hex":key,"username":u.Username,"password":u.Password,"tls-verify-server":true,"tls-ca-pem-content":string(pem)}
 b,e:=json.MarshalIndent(data,"","  ");if e!=nil{return e}
 path:=argValue(args,"--output",u.Username+"-wbd-connection.json")
 if e=writeManagedFile(path,append(b,'\n'),0600);e!=nil{return e};fmt.Println("连接资料已导出:",path);return nil
}
const unitContent=`[Unit]
Description=WBD Next native server
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/wbd-next serve --config /etc/wbd-next/server.json
Restart=on-failure
RestartSec=3
TimeoutStartSec=30
TimeoutStopSec=30
RuntimeDirectory=wbd-next

[Install]
WantedBy=multi-user.target
`
func copyManagedFile(src,dst string,mode os.FileMode)error{
 b,e:=os.ReadFile(src);if e!=nil{return e};return writeManagedFile(dst,b,mode)
}
func installManaged(r *bufio.Reader,args []string)error{
 exe,e:=os.Executable();if e!=nil{return e};dir:=filepath.Dir(exe)
 if dir!=managedOpt{
  if _,e=commandOutput("sh","-c","cd \"$1\" && sha256sum -c SHA256SUMS","wbd-next",dir);e!=nil{return e}
  if e=os.MkdirAll(managedOpt,0755);e!=nil{return e}
  for _,f:=range []string{"wbd-v4-server","libwbd_engine.so","manifest.json","SHA256SUMS","wbd-next"}{mode:=os.FileMode(0644);if f=="wbd-v4-server"||f=="wbd-next"{mode=0755};if e=copyManagedFile(filepath.Join(dir,f),filepath.Join(managedOpt,f),mode);e!=nil{return e}}
 }
 if _,e=os.Stat(managedConfigPath);os.IsNotExist(e){
  if path:=argValue(args,"--config","");path!=""{c,_,x:=loadManagedConfig(path);if x!=nil{return x};if x=saveManagedConfig(managedConfigPath,c);x!=nil{return x}}else if terminalInput(){if e=editManagedConfig(r);e!=nil{return e}}else{return fmt.Errorf("首次安装需要 --config PATH 或终端配置")}
 }else if e!=nil{return e}
 c,_,e:=loadManagedConfig(managedConfigPath);if e!=nil{return e};if e=checkManagedConfig(c);e!=nil{return e}
 if e=writeManagedFile(managedUnit,[]byte(unitContent),0644);e!=nil{return e}
 if e=copyManagedFile(managedOpt+"/wbd-next","/usr/local/bin/wbd-next",0755);e!=nil{return e}
 if e=systemctl("daemon-reload");e!=nil{return e}
 if e=systemctl("enable","--now","wbd-next.service");e!=nil{return e}
 return showManagedStatus(false)
}
func uninstallManaged(r *bufio.Reader,args []string)error{
 if !hasArg(args,"--yes"){v,e:=prompt(r,"完整卸载并删除本程序配置/证书？输入 yes","no");if e!=nil{return e};if v!="yes"{return nil}}
 if e:=systemctl("disable","--now","wbd-next.service");e!=nil{return e}
 if getUnitState()=="active"{return fmt.Errorf("服务尚未停止")}
 // Stop above waits for the original Rust owners and Go NAT/TUN cleanup.
 for _,p:=range []string{managedUnit,"/usr/local/bin/wbd-next"}{if e:=os.Remove(p);e!=nil&&!os.IsNotExist(e){return e}}
 if e:=systemctl("daemon-reload");e!=nil{return e}
 for _,p:=range []string{managedOpt,"/etc/wbd-next","/run/wbd-next","/var/log/wbd-next",managedState}{if e:=os.RemoveAll(p);e!=nil{return e}}
 fmt.Println("已卸载 WBD Next");return nil
}
func manageCommand(r *bufio.Reader,args []string)error{
 switch args[0]{
 case "help","--help","-h":fmt.Print(managedHelp);return nil
 case "serve":return serveManaged(argValue(args,"--config",managedConfigPath),argValue(args,"--socket",managedSocket))
 case "install":return installManaged(r,args[1:])
 case "config":
  if len(args)>1&&args[1]=="check"{c,_,e:=loadManagedConfig(argValue(args,"--config",managedConfigPath));if e!=nil{return e};if e=checkManagedConfig(c);e!=nil{return e};fmt.Println("配置有效");return nil}
  if len(args)>1&&args[1]=="export"{return exportManagedClient(args[2:])}
  if path:=argValue(args,"--file","");path!=""{c,_,e:=loadManagedConfig(path);if e!=nil{return e};return saveManagedConfig(managedConfigPath,c)}
  if !terminalInput(){return fmt.Errorf("config 需要终端或 --file PATH")};return editManagedConfig(r)
 case "status":return showManagedStatus(hasArg(args,"--json"))
 case "clients":return showManagedClients(args[1:])
 case "start","stop","restart":return systemctl(args[0],"wbd-next.service")
 case "logs":cmd:=exec.Command("journalctl","-u","wbd-next.service","-n","80","--no-pager");cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr;return cmd.Run()
 case "uninstall":return uninstallManaged(r,args[1:])
 default:return fmt.Errorf("未知命令: %s",args[0])
 }
}
func ManageServer(args []string)error{
 r:=bufio.NewReader(os.Stdin)
 if len(args)>0{return manageCommand(r,args)}
 if !terminalInput(){fmt.Print(managedHelp);return nil}
 commands:=map[string]string{"1":"install","2":"config","3":"clients","4":"start","5":"stop","6":"restart","7":"status","8":"uninstall"}
 for{
  _=showManagedStatus(false)
  fmt.Println("1 安装并开机启动   2 修改配置\n3 查看客户端信息   4 启动服务\n5 停止服务         6 重启服务\n7 状态与最近日志   8 完整卸载\n0 退出")
  v,e:=prompt(r,"请选择","0");if errors.Is(e,io.EOF){return nil};if e!=nil{return e};if v=="0"{return nil}
  if cmd,ok:=commands[v];ok{if e=manageCommand(r,[]string{cmd});e!=nil{fmt.Println(e)};if v=="7"{_ = manageCommand(r,[]string{"logs"})}}
 }
}
