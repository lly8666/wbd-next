// 029B B4 only: ORIGINAL WinForms buttons and original signed Go/Rust
// Windows client, not a mock ClientSession or synthetic OS Applied receipt.
// One fresh cold generation at a time. The external original WSL2 supervisor
// removes its test-owned physical /32 ONLY after generation one owned Stop.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Wbd.Gui;

public static class Plan029BThreeRealGUI {
 static volatile bool ready,applied,inner;
 static void Need(bool ok,string message) {
  if(!ok)throw new IOException("PLAN029B B4 "+message);
 }
 static void Tick() {Application.DoEvents();Thread.Sleep(25);}
 static IEnumerable<Control> Children(Control c) {
  foreach(Control x in c.Controls) {
   yield return x;foreach(Control y in Children(x))yield return y;
  }
 }
 static void Click(MainForm f,string title) {
  var button=Children(f).OfType<Button>().FirstOrDefault(x=>x.Text==title);
  Need(button!=null&&button.Enabled,"real WinForms button unavailable "+title);
  button.PerformClick();
 }
 static string Status(MainForm f,string field) {
  var member=typeof(MainForm).GetField(field,
   BindingFlags.Instance|BindingFlags.NonPublic);
  Need(member!=null,"original GUI status field missing "+field);
  return ((Label)member.GetValue(f)).Text;
 }
 static void Lines(string line) {
  if(line=="WBD_WINDOWS_CLIENT_READY")ready=true;
  if(line=="WBD_WINDOWS_OS_APPLIED")applied=true;
  if(line!=null && line.StartsWith("WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 ") &&
      line.Contains("outer_config=1460") &&
      line.Contains("planned=1389") && line.Contains("applied=1389"))
   inner=true;
  if(line==null)return;
  if(line.IndexOf("password",StringComparison.OrdinalIgnoreCase)>=0 ||
     line.IndexOf("route-key",StringComparison.OrdinalIgnoreCase)>=0)return;
  Console.WriteLine(line);Console.Out.Flush();
 }
 static void WaitTask(Task work,int milliseconds,string reason) {
  var watch=Stopwatch.StartNew();
  while(!work.IsCompleted && watch.ElapsedMilliseconds<milliseconds)Tick();
  Need(work.IsCompleted,reason+" deadline");
  work.GetAwaiter().GetResult();
 }
 static Dictionary<string,object> Effective(PortableStore store,
  Profile profile,ClientSession client,int ordinal) {
  string path="data/plan029b-b4-effective-"+ordinal+".json";
  store.WriteAtomic(path,store.Json.Serialize(store.Effective(profile)));
  var task=client.ValidateAsync(store.InRoot(path));
  WaitTask(task,24000,"original Go check-config "+ordinal);
  return task.GetAwaiter().GetResult();
 }
 static void CheckEffective(Dictionary<string,object> actual,
  int ordinal) {
  bool cn=ordinal!=3,advanced=ordinal==1;
  Need(Convert.ToBoolean(actual["split-enable"])==cn &&
       Convert.ToBoolean(actual["cn-domain-direct"])==advanced &&
       Convert.ToString(actual["route-mode"])==(cn?"bypass-lan-cn":"all") &&
       Convert.ToString(actual["startup-padding"])=="off" &&
       Convert.ToInt32(actual["mtu"])==1460 &&
       Convert.ToInt32(actual["derived-inner-tun-mtu"])==1389,
    "actual original Go effective three-generation policy mismatch "+ordinal);
 }
 static void Connect(MainForm f,ClientSession client,int ordinal) {
  ready=false;applied=false;inner=false;
  Click(f,"保存配置");Tick();
  Click(f,"连接 / 切换");
  var watch=Stopwatch.StartNew();
  while(watch.ElapsedMilliseconds<88000) {
   Tick();
   if(ready&&applied&&inner&&client.Active &&
      Status(f,"state").Contains("系统 Applied") &&
      Status(f,"mtuStatus").Contains("1460B") &&
      Status(f,"mtuStatus").Contains("1389B"))break;
   if(!client.Active&&watch.ElapsedMilliseconds>14000)
    throw new IOException("original Go/Rust child exited before real Apply");
  }
  Need(ready&&applied&&inner&&client.Active &&
       Status(f,"state").Contains("系统 Applied"),
       "actual Wintun/Rust OS Applied absent generation "+ordinal);
  Console.WriteLine("PLAN029B_B4_REAL_GUI_GENERATION_APPLIED ordinal="+ordinal);
  Console.Out.Flush();
 }
 static void WaitGuestReady() {
  // This is only a test-owned prerequisite from an already bound original
  // Linux kernel DNS/TUN witness. It is NOT Windows/Rust product Ready.
  string path=Environment.GetEnvironmentVariable("WBD_PLAN029B_B4_GUEST_READY_PATH");
  string source=Environment.GetEnvironmentVariable("GITHUB_SHA");
  Need(!String.IsNullOrEmpty(path)&&!String.IsNullOrEmpty(source),
       "signed source-locked guest readiness fence missing");
  var clock=Stopwatch.StartNew();
  while(clock.ElapsedMilliseconds<35000) {
   Tick();
   if(File.Exists(path)&&File.ReadAllText(path).Trim()==source)return;
  }
  throw new IOException("original Linux kernel DNS/TUN witness never ready");
 }
 static string QueryA(int ordinal) {
  byte[] name=new byte[]{3,119,119,119,2,99,110,7,101,120,97,109,112,108,101,0};
  byte[] query=new byte[12+name.Length+4];
  query[0]=0x29;query[1]=(byte)(0x60+ordinal);
  query[2]=1;query[5]=1;
  Buffer.BlockCopy(name,0,query,12,name.Length);
  query[12+name.Length+1]=1;query[12+name.Length+3]=1;
  string server=ordinal==3?"10.66.0.1":"8.8.8.8";
  var remote=new IPEndPoint(IPAddress.Parse(server),53);
  using(var sock=new Socket(AddressFamily.InterNetwork,SocketType.Dgram,
     ProtocolType.Udp)) {
   sock.Bind(new IPEndPoint(IPAddress.Parse("10.66.0.2"),0));
   sock.ReceiveTimeout=1000;
   var watch=Stopwatch.StartNew();
   while(watch.ElapsedMilliseconds<15000) {
    Need(sock.SendTo(query,remote)==query.Length,"short real DNS request");
    var buffer=new byte[2048];EndPoint from=new IPEndPoint(IPAddress.Any,0);
    int n;
    try{n=sock.ReceiveFrom(buffer,ref from);}
    catch(SocketException x) {
     if(x.SocketErrorCode==SocketError.TimedOut)continue;
     throw;
    }
    var endpoint=(IPEndPoint)from;
    if(!endpoint.Address.Equals(remote.Address) || endpoint.Port!=53 ||
       n<16 || buffer[0]!=query[0] || buffer[1]!=query[1])continue;
    if((buffer[2]&128)==0||(buffer[3]&15)!=0||
       (buffer[6]==0&&buffer[7]==0)){
     // One bounded diagnostic only on the exact first genuine DNS ticket;
     // do not log query contents, credentials or per-packet data.
     Console.WriteLine("PLAN029B_B4_FIRST_DNS_REPLY_FAILURE ordinal="+ordinal+
        " rcode="+(buffer[3]&15)+
        " answer_count="+((buffer[6]<<8)|buffer[7])+
        " reply_len="+n+" lane="+(ordinal==3?"tunnel":"physical"));
     Console.Out.Flush();
     throw new IOException("PLAN029B B4 real A CNAME/TTL answer absent or negative");
    }
    string ip=new IPAddress(new byte[]{buffer[n-4],buffer[n-3],
                                       buffer[n-2],buffer[n-1]}).ToString();
    Need(ordinal==1?ip.StartsWith("198.18.",StringComparison.Ordinal):
         ip=="203.0.113.77",
         "advanced FakeIP vs ordinary/all real A mismatch "+ordinal+" "+ip);
    Console.WriteLine("PLAN029B_B4_REAL_DNS_A ordinal="+ordinal+
      " lane="+(ordinal==3?"tun":"physical")+
      " presentation="+(ordinal==1?"fake":"real"));
    Console.Out.Flush();
    return ip;
   }
  }
  throw new IOException("original Windows kernel DNS timeout phase "+ordinal);
 }
 static void Business(string ip,int ordinal,bool stale) {
  string token=stale?"P29B4-STALE-G"+ordinal:"P29B4-G"+ordinal;
  byte[] req=System.Text.Encoding.ASCII.GetBytes(token);
  byte[] answer=System.Text.Encoding.ASCII.GetBytes(token+"-ACK");
  using(var sock=new Socket(AddressFamily.InterNetwork,SocketType.Dgram,
     ProtocolType.Udp)) {
   sock.Bind(new IPEndPoint(IPAddress.Parse("10.66.0.2"),0));
   sock.ReceiveTimeout=stale?850:1100;
   var target=new IPEndPoint(IPAddress.Parse(ip),46119);
   var watch=Stopwatch.StartNew();
   while(watch.ElapsedMilliseconds<(stale?1000:15500)) {
    Need(sock.SendTo(req,target)==req.Length,"short original Wintun data send");
    var buf=new byte[128];EndPoint from=new IPEndPoint(IPAddress.Any,0);
    try{
     int n=sock.ReceiveFrom(buf,ref from);
     if(stale)throw new IOException("retired FakeIP produced actual reply");
     if(((IPEndPoint)from).Address.Equals(target.Address) &&
        n==answer.Length && buf.Take(n).SequenceEqual(answer)) {
      Console.WriteLine("PLAN029B_B4_REAL_KERNEL_UDP_ECHO ordinal="+ordinal);
      Console.Out.Flush();return;
     }
    }catch(SocketException ex){
     if(ex.SocketErrorCode==SocketError.TimedOut) {
      if(stale) {
       Console.WriteLine("PLAN029B_B4_STALE_FAKE_APP_ATTEMPT_NO_REPLY ordinal="+ordinal);
       Console.Out.Flush();return;
      }
      continue;
     }
     throw;
    }
   }
  }
  throw new IOException(stale?"retired FakeIP timeout check broken":
                       "real kernel business reply missing "+ordinal);
 }
 static string JournalHash(PortableStore store) {
  string path=store.InRoot("data/network-state.json.n4-fakeip-journal");
  Need(File.Exists(path),"advanced real FakeIP durable journal absent");
  using(var sha=SHA256.Create())
   return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path)));
 }
 static void Stop(MainForm form,ClientSession client,PortableStore store,
  int ordinal) {
  Click(form,"断开连接");
  var watch=Stopwatch.StartNew();
  while(watch.ElapsedMilliseconds<37000) {
   Tick();
   if(!client.Active&&Status(form,"state")=="未连接")break;
  }
  Need(!client.Active&&Status(form,"state")=="未连接",
       "real GUI Stop/child join missing generation "+ordinal);
  string wal=store.InRoot("data/network-state.json");
  foreach(string suffix in new[]{"",".n4-owned-wal",".n4-owned-wal.routes",
       ".routes",".plan029-defender-tcp"})
   Need(!File.Exists(wal+suffix),"owned WAL/Defender residue "+ordinal+" "+suffix);
  using(var flush=new Process()) {
   flush.StartInfo.FileName="ipconfig.exe";
   flush.StartInfo.Arguments="/flushdns";
   flush.StartInfo.CreateNoWindow=true;
   flush.StartInfo.UseShellExecute=false;
   Need(flush.Start(),"Windows DNS cache flush process did not start");
   Need(flush.WaitForExit(14000)&&flush.ExitCode==0,
        "Windows DNS cache flush failed after original Stop "+ordinal);
  }
  Console.WriteLine("PLAN029B_B4_REAL_GUI_OWNED_STOP_WAL_CLEAN ordinal="+ordinal);
  Console.Out.Flush();
 }
 static string ReadSupervisor(string required,int milliseconds) {
  var task=Task.Run(()=>Console.ReadLine());
  WaitTask(task,milliseconds,"external original owner command");
  Need(task.GetAwaiter().GetResult()==required,
       "external original owner command mismatch");
  return required;
 }
 [STAThread] public static int Main(string[] argv) {
  MainForm form=null;ClientSession client=null;
  try {
   Need(argv.Length==2,"portable root and profile seed required");
   Application.EnableVisualStyles();
   Application.SetCompatibleTextRenderingDefault(false);
   string root=Path.GetFullPath(argv[0]);
   string file=Path.GetFullPath(argv[1]);
   Need(file.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar)+
     Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),
     "foreign GUI seed");
   var store=new PortableStore(root);
   var seed=store.Json.Deserialize<Dictionary<string,object>>(
      PortableStore.ReadBounded(file));
   Need(seed!=null&&seed.ContainsKey("tls-ca-pem") &&
        Convert.ToBoolean(seed["split-enable"]) &&
        Convert.ToBoolean(seed["cn-domain-direct"]) &&
        Convert.ToString(seed["route-mode"])=="bypass-lan-cn",
        "actual original advanced CN profile absent");
   var profile=store.Book.Profiles[0];
   store.ImportValues(profile,seed);store.Save();
   client=new ClientSession(store);client.Line+=Lines;
   form=new MainForm(store,client,()=>Dependencies.Detect(store));
   form.Show();Tick();
   string firstFake=null,journal=null;
   for(int ordinal=1;ordinal<=3;ordinal++) {
    if(ordinal>1) {
     form.LoadEditor();
     form.SetEditor("cn-domain-direct",false);
     form.SetEditor("split-enable",ordinal==2);
     form.SetEditor("route-mode",ordinal==2?"bypass-lan-cn":"all");
     form.SaveEditor();
    }
    CheckEffective(Effective(store,profile,client,ordinal),ordinal);
    Connect(form,client,ordinal);
    if(ordinal==1)WaitGuestReady();
    string ip=QueryA(ordinal);
    if(ordinal==1)firstFake=ip;
    Business(ip,ordinal,false);
    if(ordinal>1)Business(firstFake,ordinal,true);
    if(ordinal==3) {
     form.Capture(store.InRoot("data/plan029b-b4-third-applied.png"));
     Console.WriteLine("PLAN029B_B4_THIRD_APPLIED");
     Console.Out.Flush();
     ReadSupervisor("stop",190000);
    }
    Stop(form,client,store,ordinal);
    if(ordinal==1)journal=JournalHash(store);
    else Need(JournalHash(store)==journal,
              "retired advanced FakeIP journal mutated by inactive generation");
    if(ordinal==1) {
     // The external signed supervisor releases ONLY its own /32 route
     // before allowing the ordinary generation to send the SAME real A.
     Console.WriteLine("PLAN029B_B4_PHASE1_STOP_ROUTE_RELEASE_REQUIRED");
     Console.Out.Flush();
     ReadSupervisor("continue-ordinary",30000);
    }
   }
   store.WriteAtomic("data/plan029b-b4-three-real-receipt.json",
     "{\"schema_version\":1,\"original_gui\":true,\"generations\":3,"+
     "\"real_applied\":3,\"owned_stop\":3,\"mtu\":1460,\"inner\":1389,"+
     "\"cn_dns_physical\":2,\"all_dns_tunnel\":1,"+
     "\"advanced_fakeip\":true,\"ordinary_real_a\":true,"+
     "\"all_real_a\":true,\"stale_fake_app_attempts\":2,"+
     "\"stale_fake_journal_unchanged\":true}");
   Console.WriteLine("PLAN029B_B4_THREE_REAL_GUI_GENERATIONS_AND_STOPS_COMPLETE");
   Console.Out.Flush();return 0;
  }catch(Exception ex) {
   Console.Error.WriteLine("PLAN029B_B4_FIRST_FAILURE "+
     ex.GetType().Name+" "+ex.Message);
   return 1;
  }finally {
   if(form!=null&&client!=null&&client.Active) {
    try{
     var stop=form.DisconnectAsync();
     var watch=Stopwatch.StartNew();
     while(!stop.IsCompleted&&watch.ElapsedMilliseconds<37000)Tick();
     if(stop.IsCompleted)stop.GetAwaiter().GetResult();
    }catch(Exception ex){
     Console.Error.WriteLine("PLAN029B_B4_OWNED_STOP_INCOMPLETE "+ex.GetType().Name);
    }
   }
   // Never synchronously Dispose a WinForms handle racing BeginInvoke;
   // the genuine ClientSession Stop above owns all network state.
  }
 }
}
