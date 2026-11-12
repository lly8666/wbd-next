// PLAN028 Windows VM: actual compiled original WinForms controls. Test-only
// session must never claim signed OS Apply. Native GUI-initiated OS test separate.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Wbd.Gui;

public static class M0Plan028GUIButtonsVMHarness {
 [DllImport("user32.dll", CharSet=CharSet.Unicode)]
 static extern IntPtr FindWindow(string klass,string title);
 [DllImport("user32.dll")]
 static extern bool PostMessage(IntPtr h,uint msg,IntPtr w,IntPtr l);
 sealed class S : IClientSession {
  public event Action<string> Line;
  public bool Active {get;private set;}
  public int Starts,Stops,Checks;
  public string LastConfig="";
  public Task<Dictionary<string,object>> ValidateAsync(string config) {
   Checks++; LastConfig=File.ReadAllText(config);
   return Task.FromResult(new Dictionary<string,object>());
  }
  public Task StartAsync(string config) {
   Starts++;Active=true; LastConfig=File.ReadAllText(config);
   if(Line!=null)Line("WBD_WINDOWS_CLIENT_READY");
   return Task.FromResult(0);
  }
  public Task StopAsync(){Stops++;Active=false;return Task.FromResult(0);}
  public void Signal(string line){if(Line!=null)Line(line);}
  public void Dispose(){}
 }
 static void Need(bool value,string label) {
  if(!value)throw new Exception(label);
  Console.WriteLine("H1638_GUI_VM_CONTROL_PASS "+label);
 }
 static IEnumerable<Control> Walk(Control root) {
  yield return root;
  foreach(Control child in root.Controls)foreach(Control x in Walk(child))yield return x;
 }
 static Button FindButton(Form f,string text) {
  var buttons=Walk(f).OfType<Button>().Where(b=>b.Text==text).ToList();
  Need(buttons.Count>=1,"button_exists_"+text);
  return buttons[0];
 }
 static void Click(Form form,string text){
  var btn=FindButton(form,text);
  TabPage page=btn.Parent as TabPage;
  for(Control x=btn.Parent;x!=null;x=x.Parent) if(x is TabPage){page=(TabPage)x;break;}
  if(page!=null && page.Parent is TabControl)((TabControl)page.Parent).SelectedTab=page;
  Application.DoEvents();
  Need(btn.Enabled,"button_enabled_"+text);
  btn.PerformClick(); Application.DoEvents();
 }
 static void Until(Func<bool> ok,string message,int milliseconds=10000) {
  var limit=DateTime.UtcNow.AddMilliseconds(milliseconds);
  while(!ok()&&DateTime.UtcNow<limit){Application.DoEvents();Thread.Sleep(15);}
  Need(ok(),message);
 }
 static bool Modal(Form f,string title,int button,string label,Action action) {
  bool seen=false;
  using(var tm=new System.Windows.Forms.Timer{Interval=80}){
   tm.Tick+=(s,e)=>{
    IntPtr h=FindWindow("#32770",title);
    if(h!=IntPtr.Zero){seen=true;PostMessage(h,0x0111,(IntPtr)button,IntPtr.Zero);tm.Stop();}
   };
   tm.Start();action();tm.Stop();Application.DoEvents();
  }
  Need(seen,label);return seen;
 }
 static Label State(MainForm f){
  return (Label)typeof(MainForm).GetField("state",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(f);
 }
 static void Drain(MainForm f){
  typeof(MainForm).GetMethod("Drain",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(f,null);
 }
 [STAThread]public static int Main(string[] args){
  try{
   Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
   string root=Path.GetFullPath(args[0]);
   var book=new PortableStore(root);
   Need(Convert.ToString(book.Fields.First(x=>x.Key=="mtu").Default)=="1460","outer1460_GUI_assembled_default");
   Need(Convert.ToString(book.Fields.First(x=>x.Key=="record-cipher").Default)=="chacha20-poly1305","default_Chacha");
   Need(Convert.ToString(book.Fields.First(x=>x.Key=="lease4").Default)=="","default_autoIP");
   Need(Convert.ToString(book.Fields.First(x=>x.Key=="fec.mode").Default)=="off","FEC2_default_Off");
   Need(book.Fields.Any(x=>x.Key=="outer-repair"),"outer_repair_selector_exists");
   var p=book.Book.Profiles[0];
   book.Book.DriverNoticeAccepted=true;book.Save();
   var fake=new S();
   using(var form=new MainForm(book,fake,()=>new DependencyState{Admin=true,Npcap=true,Wintun=true,NpcapVersion="VM-UI-Fake-Not-OS"})){
    form.Show();Application.DoEvents();
    string[] names={"连接 / 切换","断开连接","保存配置","校验配置",
     "新增","复制","删除","导入 JSON","导出 JSON","导入中国 IP 表",
     "手动更新 IP 表","使用内置 IP 表","Npcap 官方下载","重新检测",
     "打开程序文件夹","恢复残留网络状态","只读检查网络状态",
     "原生系统预检（只读）"};
    foreach(string name in names)FindButton(form,name);
    Need(Walk(form).OfType<TabPage>().Count()>=6,"all_six_gui_pages");
    var allEditors=(Dictionary<string,Control>)typeof(MainForm).GetField("editors",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form);
    foreach(string old in new[]{"fec-mode","fec-parity","fec-min-parity","fec-start-parity"})
      Need(!allEditors.ContainsKey(old),"no_legacy_visible_FEC_"+old);
    var tabs=Walk(form).OfType<TabControl>().Single();
    tabs.SelectedTab=tabs.TabPages.Cast<TabPage>().Single(t=>t.Text=="传输");
    Application.DoEvents();
    form.SetEditor("lanes","1");
    form.SetEditor("fec.mode","off");
    Application.DoEvents();
    Need(!allEditors["fec.profile"].Visible && !allEditors["fec.auto_policy"].Visible,"FEC_Off_compact_only_mode");
    form.SetEditor("fec.mode","fixed");Application.DoEvents();
    Need(allEditors["fec.profile"].Visible && !allEditors["fec.auto_policy"].Visible,"FEC_Fixed_shows_only_seven_grades");
    var grades=(ComboBox)allEditors["fec.profile"];
    Need(grades.Items.Count==7,"FEC_Fixed_seven_real_Rust_ratios");
    form.SetEditor("fec.profile","maximum");
    Click(form,"保存配置");
    Need(Convert.ToString(p.Values["fec.profile"])=="maximum" &&
      Convert.ToString(book.Effective(p)["fec-mode"])=="fixed" &&
      Convert.ToInt32(book.Effective(p)["fec-parity"])==4,"FEC_Normal_maximum_maps_correct_internal_carrier");
    form.SetEditor("fec.mode","auto");Application.DoEvents();
    Need(!allEditors["fec.profile"].Visible && allEditors["fec.auto_policy"].Visible &&
      allEditors["fec.auto_start_profile"].Visible,"FEC_Normal_Auto_only_relevant_controls");
    form.SetEditor("lanes","4");Application.DoEvents();
    var hint=(Label)typeof(MainForm).GetField("fecGuidance",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form);
    Need(hint.Text.Contains("不支持自动") && !allEditors["fec.auto_start_profile"].Visible &&
      Convert.ToString(((Choice)((ComboBox)allEditors["fec.mode"]).SelectedItem).Value)=="auto","Game_auto_warns_instead_of_silent_downgrade");
    form.SetEditor("fec.mode","off");form.SetEditor("lanes","1");Application.DoEvents();
    Need(!allEditors["fec.profile"].Visible,"FEC_Off_keeps_default");
    form.SetEditor("mtu","1460");
    form.SetEditor("outer-repair","off");
    form.SetEditor("record-cipher","aes-128-gcm");
    Click(form,"保存配置");
    Need(Convert.ToString(p.Values["outer-repair"])=="off","outer_repair_UI_saved_explicit");
    Need(Convert.ToString(p.Values["record-cipher"])=="aes-128-gcm","AES128_UI_saved");
    Click(form,"校验配置");Until(()=>fake.Checks>=1,"validate_button_fires");
    Click(form,"连接 / 切换");Until(()=>fake.Starts==1,"connect_button_fires");
    Drain(form);
    Need(State(form).Text.Contains("待验证"),"READY_not_OS_Applied");
    fake.Signal("WBD_WINDOWS_OS_APPLIED");Drain(form);
    Need(State(form).Text.Contains("已连接"),"Applied_only_from_explicit_OS_receipt");
    Click(form,"断开连接");Until(()=>!fake.Active,"disconnect_button_fires");
    Need(State(form).Text=="未连接","Stop_status_disconnected");
    int n=book.Book.Profiles.Count;
    Click(form,"新增");Need(book.Book.Profiles.Count==n+1,"new_profile_button");
    Click(form,"复制");Need(book.Book.Profiles.Count==n+2,"duplicate_profile_button");
    Modal(form,"删除服务器",1,"delete_confirmation_dialog",()=>Click(form,"删除"));
    Need(book.Book.Profiles.Count==n+1,"delete_profile_button_commit");
    var pwd=(TextBox)((Dictionary<string,Control>)typeof(MainForm).GetField("editors",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form))["password"];
    var reveal=Walk(form).OfType<CheckBox>().Single(x=>x.Text=="显示密钥 / 密码");
    Need(pwd.UseSystemPasswordChar,"password_hidden_before_click");
    reveal.Checked=true;Need(!pwd.UseSystemPasswordChar,"reveal_secret_checked");
    reveal.Checked=false;Need(pwd.UseSystemPasswordChar,"reveal_secret_unchecked");
    Modal(form,"导出配置",1,"export_confirmation_dialog",()=>Click(form,"导出 JSON"));
    Need(Directory.GetFiles(book.InRoot("data/exports"),"server-*.json").Length>0,"export_button_real_file");
    Click(form,"使用内置 IP 表");
    Need(Convert.ToString(book.Book.Profiles.First(x=>x.Id==book.Book.SelectedId).Values["china-ip-file"])=="","embedded_IP_button_clears_path");
    Click(form,"重新检测");
    Click(form,"恢复残留网络状态");Application.DoEvents();
    Need(!File.Exists(book.InRoot("data/network-state.json")),"recover_no_WAL_no_OS_change");
    var tray=(NotifyIcon)typeof(MainForm).GetField("tray",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form);
    Need(tray.ContextMenuStrip.Items.Count==3,"tray_three_menu_actions");
    tray.ContextMenuStrip.Items[0].PerformClick();
    Need(form.Visible,"tray_show_window");
    tray.ContextMenuStrip.Items[1].PerformClick();
    Until(()=>State(form).Text=="未连接","tray_disconnect");
    Need(Dependencies.Download.StartsWith("https://npcap.com/"),"npcap_download_only_official_destination_no_browser");
    Need(FindButton(form,"打开程序文件夹")!=null,"open_folder_button_present_external_OS_test_not_run");
    Need(FindButton(form,"导入 JSON")!=null&&FindButton(form,"导入中国 IP 表")!=null,"file_picker_buttons_present");
    Need(FindButton(form,"只读检查网络状态")!=null&&FindButton(form,"原生系统预检（只读）")!=null,"native_readonly_buttons_present");
    form.Capture(book.InRoot("gui-buttons-vm.png"));
   }
   var reopened=new PortableStore(root);
   Need(reopened.Book.Profiles.Count>=2,"profiles_reopen_persist");
   Console.WriteLine("H1638_GUI_VM_BUTTONS_AND_EFFECTIVE_SOURCE_SCOPED_PASS_NOT_SIGNED_DRIVER");
   return 0;
  }catch(Exception e){Console.Error.WriteLine("H1638_GUI_VM_BUTTONS_FAIL "+e);return 1;}
 }
}
