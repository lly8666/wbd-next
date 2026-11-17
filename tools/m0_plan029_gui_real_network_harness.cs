// The original WBD WinForms button and non-mock ClientSession are the only
// owner of this CI client's Go/Rust signed Windows network process.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Wbd.Gui;
public static class Plan029GuiReal {
 static volatile bool ready,applied,inner,paddingNpf;
 static volatile int paddingRecords,paddingBytes;
 static void Need(bool yes,string text){if(!yes)throw new IOException(text);}
 static void Tick(){Application.DoEvents();Thread.Sleep(25);}
 static IEnumerable<Control> Children(Control c){
  foreach(Control x in c.Controls){yield return x;foreach(var y in Children(x))yield return y;}
 }
 static void Click(MainForm f,string text){
  var b=Children(f).OfType<Button>().FirstOrDefault(x=>x.Text==text);
  Need(b!=null,"real GUI button absent: "+text);
  Need(b.Enabled,"real GUI button disabled at click: "+text);
  b.PerformClick();
 }
 static bool ButtonReady(MainForm f,string text){
  var b=Children(f).OfType<Button>().FirstOrDefault(x=>x.Text==text);
  Need(b!=null,"real GUI button absent: "+text);
  return b.Enabled;
 }
 static string Label(MainForm f,string field){
  var obj=typeof(MainForm).GetField(field,
   BindingFlags.NonPublic|BindingFlags.Instance);
  Need(obj!=null,"real GUI read-only field absent");
  return ((Label)obj.GetValue(f)).Text;
 }
 static void Lines(string raw){
  if(raw==null)return;
  if(raw=="WBD_WINDOWS_CLIENT_READY")ready=true;
  if(raw=="WBD_WINDOWS_OS_APPLIED")applied=true;
  if(raw.StartsWith("WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 ") &&
    raw.Contains("outer_config=1460") && raw.Contains("planned=1389") &&
    raw.Contains("applied=1389"))inner=true;
  var match=Regex.Match(raw,@"^WBD_PLAN029_M1_STARTUP_PADDING_NPF_RECEIPT mode=flows copied_records=(\d+) copied_bytes=(\d+) source=original_Rust_M1_authenticated_NPF_accepted$");
  if(match.Success){
   int records,bytes;
   if(int.TryParse(match.Groups[1].Value,out records) &&
      int.TryParse(match.Groups[2].Value,out bytes)){
    paddingRecords=records;paddingBytes=bytes;paddingNpf=true;
   }
  }
  if(raw.IndexOf("password",StringComparison.OrdinalIgnoreCase)>=0 ||
     raw.IndexOf("route-key",StringComparison.OrdinalIgnoreCase)>=0)return;
  Console.WriteLine(raw);Console.Out.Flush();
 }
 static string QueryRealCnDns(int ordinal){
  // One real Windows kernel UDP socket, bound to the current Wintun lease.
  // A different transaction and source socket are used for every phase.
  byte[] name=new byte[]{3,119,119,119,2,99,110,7,101,120,97,109,112,108,101,0};
  byte[] query=new byte[12+name.Length+4];
  query[0]=0x29;query[1]=(byte)(0x60+ordinal);
  query[2]=1;query[5]=1; // RD=1, QDCOUNT=1
  Buffer.BlockCopy(name,0,query,12,name.Length);
  query[12+name.Length+1]=1;query[12+name.Length+3]=1;
  using(var sock=new Socket(AddressFamily.InterNetwork,SocketType.Dgram,ProtocolType.Udp)){
   sock.Bind(new IPEndPoint(IPAddress.Parse("10.66.0.2"),0));
   sock.ReceiveTimeout=1200;
   var target=new IPEndPoint(IPAddress.Parse("8.8.8.8"),53);
   var watch=Stopwatch.StartNew();
   while(watch.ElapsedMilliseconds<17000){
    sock.SendTo(query,target);
    byte[] packet=new byte[2048];
    EndPoint remote=new IPEndPoint(IPAddress.Any,0);
    int count=0;
    try{count=sock.ReceiveFrom(packet,ref remote);}
    catch(SocketException ex){
     if(ex.SocketErrorCode==SocketError.TimedOut)continue;
     throw;
    }
    var origin=(IPEndPoint)remote;
    if(origin.Port!=53 || !origin.Address.Equals(target.Address) ||
       count<16 || packet[0]!=query[0] || packet[1]!=query[1])continue;
    if((packet[2]&128)==0 || (packet[3]&15)!=0 ||
        (packet[6]==0 && packet[7]==0)){
     Console.WriteLine("PLAN029_H2063_TTL_APP_NEGATIVE phase="+ordinal+
      " rcode="+(packet[3]&15)+" answers="+
      ((packet[6]<<8)|packet[7])+" response_len="+count+
      " txid="+query[0].ToString("x2")+query[1].ToString("x2"));
     Console.Out.Flush();
     throw new IOException("actual CN DNS returned negative/empty response");
    }
    var a=new IPAddress(new byte[]{packet[count-4],packet[count-3],
       packet[count-2],packet[count-1]});
    string fake=a.ToString();
    Need(fake.StartsWith("198.18.",StringComparison.Ordinal),
      "actual CN DNS did not present a selective FakeIP");
    Console.WriteLine("PLAN029_H2063_TTL_APP_REPLY phase="+ordinal+
      " fake4="+fake+" txid="+query[0].ToString("x2")+query[1].ToString("x2"));
    Console.Out.Flush();
    return fake;
   }
  }
  throw new IOException("real CN DNS reply after TTL/reconnect missing");
 }
 [STAThread]public static int Main(string[] argv){
  MainForm form=null;ClientSession client=null;
  try{
   Need(argv.Length==2,"expected protected portable root and seed file");
   Application.EnableVisualStyles();
   Application.SetCompatibleTextRenderingDefault(false);
   string dir=Path.GetFullPath(argv[0]);
   string file=Path.GetFullPath(argv[1]);
   Need(file.StartsWith(dir.TrimEnd(Path.DirectorySeparatorChar)+
    Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"foreign seed");
   var store=new PortableStore(dir);
   var seed=store.Json.Deserialize<Dictionary<string,object>>(
     PortableStore.ReadBounded(file));
   Need(seed!=null && seed.ContainsKey("split-enable") &&
    seed.ContainsKey("tls-ca-pem"),"missing GUI source fields");
   bool flows=Environment.GetEnvironmentVariable(
    "WBD_PLAN029_GUI_PADDING_EFFECTIVE_SCENE")=="1";
   bool normalReconnect=Environment.GetEnvironmentVariable(
    "WBD_PLAN029_GUI_NORMAL_RECONNECT_SCENE")=="1";
   Need(!(flows && normalReconnect),"normal reconnect must not join padding flows scene");
   bool dnsTtl=Environment.GetEnvironmentVariable("WBD_PLAN029_DNS_TTL_RESTART_SCENE")=="1";
   Need(!dnsTtl || normalReconnect,"TTL/restart must use a real two-generation GUI");
   string expectedPadding=flows?"flows":"off";
   Need(seed.ContainsKey("startup-padding") &&
    Convert.ToString(seed["startup-padding"])==expectedPadding,
    "true user GUI cold padding choice not loaded");
   var profile=store.Book.Profiles[0];
   store.ImportValues(profile,seed);store.Save();
   Need(Convert.ToInt32(store.Fields.Single(x=>x.Key=="mtu").Default)==1460 &&
    Convert.ToInt32(profile.Values["mtu"])==1460,"GUI default outer MTU not 1460");
   client=new ClientSession(store);
   client.Line+=Lines;
   form=new MainForm(store,client,()=>Dependencies.Detect(store));
   form.Show();Tick();
   store.WriteAtomic("data/plan029-effective.json",
    store.Json.Serialize(store.Effective(profile)));
   var validate=client.ValidateAsync(store.InRoot("data/plan029-effective.json"));
   var clock=Stopwatch.StartNew();
   while(!validate.IsCompleted && clock.ElapsedMilliseconds<23000)Tick();
   Need(validate.IsCompleted,"Go/Rust config readback timeout");
   var effective=validate.GetAwaiter().GetResult();
   Need(Convert.ToInt32(effective["mtu"])==1460 &&
    Convert.ToInt32(effective["derived-inner-tun-mtu"])==1389 &&
    Convert.ToBoolean(effective["split-enable"]) &&
    Convert.ToBoolean(effective["cn-domain-direct"]) &&
    Convert.ToString(effective["route-mode"])=="bypass-lan-cn" &&
    effective.ContainsKey("startup-padding") &&
    Convert.ToString(effective["startup-padding"])==expectedPadding,
    "Go/Rust owner effective not matching GUI config");
   Console.WriteLine("PLAN029_REAL_GUI_GO_RUST_CONFIG_OUTER1460_INNER1389_PASS");
   Click(form,"保存配置");Tick();
   Click(form,"连接 / 切换");
   clock.Restart();
   while(clock.ElapsedMilliseconds<90000){
    Tick();
    if(ready && applied && inner && Label(form,"state").Contains("系统 Applied") &&
      Label(form,"mtuStatus").Contains("1460B") &&
      Label(form,"mtuStatus").Contains("1389B"))break;
    if(!client.Active && clock.ElapsedMilliseconds>12000)
     throw new IOException("real GUI child exited before Ready");
   }
   Need(ready && applied && inner &&
    Label(form,"state").Contains("系统 Applied") &&
    Label(form,"mtuStatus").Contains("1460B") &&
    Label(form,"mtuStatus").Contains("1389B"),
    "GUI true OS Applied/MTU readback/Go Rust owner incomplete");
   if(dnsTtl){
    QueryRealCnDns(1);
    var ttlWait=Stopwatch.StartNew();
    while(ttlWait.ElapsedMilliseconds<2800)Tick();
    QueryRealCnDns(2);
   }
   if(normalReconnect){
    // Normal user-disconnect then user-connect only. No power cut,
    // forced process kill, new service, injected network fault or timer.
    Click(form,"断开连接");
    clock.Restart();
    while(clock.ElapsedMilliseconds<34000){
     Tick();
     if(!client.Active && Label(form,"state")=="未连接" &&
        ButtonReady(form,"连接 / 切换"))break;
    }
    Need(!client.Active && Label(form,"state")=="未连接" &&
       ButtonReady(form,"连接 / 切换"),
      "first original GUI Stop or disabled connect button did not finish");
    string firstWal=store.InRoot("data/network-state.json");
    foreach(var suffix in new[]{"",".n4-owned-wal",".n4-owned-wal.routes",
      ".routes",".plan029-defender-tcp"})
     Need(!File.Exists(firstWal+suffix),"first GUI Stop owned residue "+suffix);
    Console.WriteLine("PLAN029_H2061_NORMAL_GUI_FIRST_DISCONNECT_WAL_ABSENT_PASS");
    Console.Out.Flush();
    ready=false;applied=false;inner=false;
    Click(form,"连接 / 切换");
    Console.WriteLine("PLAN029_H2064_SECOND_REAL_GUI_ENABLED_BUTTON_CLICKED");
    Console.Out.Flush();
    clock.Restart();
    while(clock.ElapsedMilliseconds<60000){
     Tick();
     if(ready && applied && inner && client.Active &&
       Label(form,"state").Contains("系统 Applied") &&
       Label(form,"mtuStatus").Contains("1460B") &&
       Label(form,"mtuStatus").Contains("1389B"))break;
     if(!client.Active && clock.ElapsedMilliseconds>12000)
      throw new IOException("second original GUI child ended before Ready");
    }
    Need(ready && applied && inner && client.Active &&
     Label(form,"state").Contains("系统 Applied") &&
     Label(form,"mtuStatus").Contains("1460B") &&
     Label(form,"mtuStatus").Contains("1389B"),
     "second normal GUI original Go/Rust OS Applied missing");
    Console.WriteLine("PLAN029_H2061_NORMAL_GUI_RECONNECT_SECOND_APPLIED");
    Console.Out.Flush();
    if(dnsTtl)QueryRealCnDns(3);
   }
   form.Capture(store.InRoot("data/plan029-gui-applied.png"));
   Console.WriteLine("PLAN029_REAL_GUI_WINFORMS_BUTTON_CONNECT_APPLIED_PASS");Console.Out.Flush();
   // Existing independent Windows and Linux kernel apps run while this
   // original GUI process remains owner; the external test alone requests Stop.
   Task<string> stop=Task.Run(()=>Console.ReadLine());
   clock.Restart();
   while(!stop.IsCompleted && clock.ElapsedMilliseconds<210000){
    Tick();
    Need(client.Active,"GUI child died before external owned Stop");
   }
   Need(stop.IsCompleted && stop.GetAwaiter().GetResult()=="stop",
    "supervisor Stop was not received exactly");
   Click(form,"断开连接");
   clock.Restart();
   while(clock.ElapsedMilliseconds<36000){
    Tick();
    if(!client.Active && Label(form,"state")=="未连接")break;
   }
   Need(!client.Active && Label(form,"state")=="未连接",
    "original WinForms Disconnect never completed");
   if(flows)Need(paddingNpf && paddingRecords>0 && paddingBytes>0,
    "original GUI selected flows but Rust M1/Npcap copied no actual padded record");
   string wal=store.InRoot("data/network-state.json");
   foreach(var suffix in new[]{"",".n4-owned-wal",".n4-owned-wal.routes",
      ".routes",".plan029-defender-tcp"})
    Need(!File.Exists(wal+suffix),"owned cleanup residue "+suffix);
   // The real ClientSession.StopAsync additionally rejects missing native
   // Rust Stop receipt, nonzero Go child exit and leftover generation WAL.
   store.WriteAtomic("data/plan029-gui-real-receipt.json",
    "{\"schema_version\":1,\"original_buttons\":true,\"source_locked_go_rust\":true,"+
    "\"outer\":1460,\"inner_os_applied\":1389,\"real_native_ready\":true,"+
    "\"owned_stop\":true,\"business\":\"EXTERNALLY_CHECKED\","+
    "\"startup_padding_mode\":\""+expectedPadding+"\","+
    "\"padding_npf_copied_records\":"+paddingRecords+","+
    "\"padding_npf_copied_bytes\":"+paddingBytes+","+
    "\"normal_reconnect_completed\":"+(normalReconnect?"true":"false")+","+
    "\"dns_ttl_restart_completed\":"+(dnsTtl?"true":"false")+"}");
   Console.WriteLine("PLAN029_REAL_GUI_WINFORMS_BUTTON_STOP_WAL_ABSENT_PASS");Console.Out.Flush();
   return 0;
  }catch(Exception e){
   Console.Error.WriteLine("PLAN029_REAL_GUI_FIRST_FAILURE "+e.GetType().Name+" "+e.Message);
   return 1;
  }finally{
   if(form!=null){
    try{
     if(client!=null && client.Active){
      var stopping=form.DisconnectAsync();var clock=Stopwatch.StartNew();
      while(!stopping.IsCompleted && clock.ElapsedMilliseconds<37000)Tick();
      if(stopping.IsCompleted)stopping.GetAwaiter().GetResult();
     }
    }catch(Exception e){
     Console.Error.WriteLine("PLAN029_REAL_GUI_OWNED_STOP_INCOMPLETE "+e.GetType().Name);
    }
    // H2054: original WinForms Control.BeginInvoke may still be creating\n    // a status Label handle while an STA test main is returning. A second\n    // synchronous Form.Dispose() here races CreateHandle and converts a\n    // genuinely completed Rust/WAL Stop into an unhandled GUI exit(1).\n    // The original ClientSession Disconnect above already owned the\n    // complete product network cleanup; the harness is a short-lived STA\n    // process, and its WinForms handle belongs to normal process teardown.\n    // Never manufacture Stop or swallow a child failure to fix this race.
   }
  }
 }
}
