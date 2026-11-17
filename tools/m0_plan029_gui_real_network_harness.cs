// The original WBD WinForms button and non-mock ClientSession are the only
// owner of this CI client's Go/Rust signed Windows network process.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
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
  Need(b!=null,"real GUI button absent: "+text);b.PerformClick();
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
    "\"padding_npf_copied_bytes\":"+paddingBytes+"}");
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
