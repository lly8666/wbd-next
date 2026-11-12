// PLAN029 Windows 2025 compiled WinForms + REAL current original Go
// --check-config; no mock network, no driver Apply, no fake TLS PASS.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Windows.Forms;
using Wbd.Gui;

public static class M0Plan029GUIAddressMTUVMHarness {
 static void Need(bool ok,string name){
  if(!ok)throw new Exception(name);
  Console.WriteLine("PLAN029_H1663_REAL_GUI_CLI_CONFIG_PASS "+name);
 }
 static Dictionary<string,object> Check(PortableStore store,Profile profile,string file,ClientSession cli){
  store.WriteAtomic(file,store.Json.Serialize(store.Effective(profile)));
  return cli.ValidateAsync(store.InRoot(file)).GetAwaiter().GetResult();
 }
 static void Correct(Dictionary<string,object> actual,string key,string want){
  Need(actual.ContainsKey(key)&&Convert.ToString(actual[key])==want,key+"_CLI_effective_"+want);
 }
 [STAThread]public static int Main(string[] args){
  try{
   Application.EnableVisualStyles();
   Application.SetCompatibleTextRenderingDefault(false);
   string root=Path.GetFullPath(args[0]);
   var store=new PortableStore(root);
   var p=store.Book.Profiles[0];
   p.Values["server-ip"]="edge.example.test";
   p.Values["server-name"]="borrow.example.org";
   p.Values["account"]="test-account";
   p.Values["username"]="tester";
   p.Values["password"]="not-real-secret";
   p.Values["route-key-hex"]=new string('a',64);
   p.Values["tunnel-id"]="00112233445566778899aabbccddeeff";
   p.Values["installation-id"]="11112222333344445555666677778888";
   p.Values["lease4"]="10.66.0.7/32";
   p.Values["mtu"]=1460;
   p.Values["fec.mode"]="off";
   p.Values["lanes"]=1;
   store.Save();

   Need(store.Fields.Single(f=>f.Key=="server-ip").Label.Contains("域名"),"address_visible_DNS_label");
   Need(store.Fields.Single(f=>f.Key=="mtu").Label=="外层 MTU（字节，上限）","one_editable_outer_MTU_label");
   Need(Convert.ToInt32(store.Fields.Single(f=>f.Key=="mtu").Default)==1460,"outer_default1460_not1500");
   Need(!store.Fields.Any(f=>f.Key=="derived-inner-tun-mtu"||f.Key=="inner-mtu"),"no_editable_inner_MTU");

   using(var cli=new ClientSession(store))
   using(var form=new MainForm(store,cli,()=>Dependencies.Detect(store))){
    form.Show();Application.DoEvents();
    var readOnly=(Label)typeof(MainForm).GetField("mtuStatus",
      System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(form);
    Need(readOnly.Text.Contains("未知")&&readOnly.Text.Contains("未验证"),
      "effective_outer_auto_inner_OS_receipts_start_unknown");
    form.LoadEditor();
    form.SetEditor("server-ip","EDGE.Example.Test.");
    form.SetEditor("server-name","borrow.example.org");
    form.SetEditor("mtu","1460");
    form.SaveEditor();
    Correct(Check(store,p,"data/h1663-normal.json",cli),"server-ip","EDGE.Example.Test.");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"server-name","borrow.example.org");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"mtu","1460");
    var n=Check(store,p,"data/h1663-normal.json",cli);
    int inner=Convert.ToInt32(n["derived-inner-tun-mtu"]);
    Need(inner>0&&inner<1460,"native_Rust_inner_derived_only_no_GUI_rewrite");
    Need(Convert.ToInt32(p.Values["mtu"])==1460,"outer_kept_after_native_inner_read");

    form.SetEditor("lanes","4");
    form.SetEditor("fec.mode","off");
    form.SaveEditor();
    var game=Check(store,p,"data/h1663-game4.json",cli);
    Correct(game,"server-ip","EDGE.Example.Test.");
    Correct(game,"mtu","1460");
    Need(Convert.ToInt32(p.Values["mtu"])==1460,"mode_switch_never_rewrites_outer");
    Need(Convert.ToInt32(game["derived-inner-tun-mtu"])>0,"game4_native_inner_derived");
    form.SetEditor("mtu","1500");
    form.SaveEditor();
    var explicitMax=Check(store,p,"data/h1663-explicit1500.json",cli);
    Correct(explicitMax,"mtu","1500");
    Need(Convert.ToInt32(p.Values["mtu"])==1500,"1500_explicit_only");
    form.SetEditor("mtu","1460");
    form.SetEditor("lanes","1");
    form.SaveEditor();

    var invalid=new Dictionary<string,object>(store.Effective(p));
    invalid["derived-inner-tun-mtu"]=1000;
    bool denied=false;
    try{store.ImportValues(p,invalid);}catch(InvalidDataException){denied=true;}
    Need(denied,"derived_inner_cannot_import_into_GUI_profile");
    Need(Convert.ToInt32(p.Values["mtu"])==1460,"bad_inner_import_not_mutate_outer");
    form.Capture(store.InRoot("h1663-domain-mtu-winforms.png"));
   }
   var reopen=new PortableStore(root);
   var saved=reopen.Book.Profiles.Single(x=>x.Id==p.Id);
   Need(Convert.ToInt32(saved.Values["mtu"])==1460,"reopen_retains_outer1460");
   Need(Convert.ToString(saved.Values["server-ip"])=="EDGE.Example.Test.","reopen_retains_server_domain");
   Need(Convert.ToString(saved.Values["server-name"])=="borrow.example.org","reopen_preserves_separate_verified_TLS_SNI");
   Need(!File.Exists(store.InRoot("data/network-state.json")),"no_fake_OS_Applied_or_WAL");
   Console.WriteLine("PLAN029_H1663_WINFORMS_REAL_CLI_EFFECTIVE_BUILD_SCOPED_PASS_NO_DRIVER_NETWORK");
   return 0;
  }catch(Exception err){
   Console.Error.WriteLine("PLAN029_H1663_WINFORMS_REAL_CLI_CONFIG_FAIL "+err);
   return 1;
  }
 }
}
