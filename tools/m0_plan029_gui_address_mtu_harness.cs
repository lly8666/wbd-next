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
   p.Values["dns.direct"]="223.5.5.5";
   p.Values["dns.tunnel"]="1.1.1.1";
   store.Save();

   Need(store.Fields.Single(f=>f.Key=="server-ip").Label.Contains("域名"),"address_visible_DNS_label");
   Need(store.Fields.Single(f=>f.Key=="mtu").Label=="外层 MTU（字节，上限）","one_editable_outer_MTU_label");
   Need(Convert.ToInt32(store.Fields.Single(f=>f.Key=="mtu").Default)==1460,"outer_default1460_not1500");
   Need(!store.Fields.Any(f=>f.Key=="derived-inner-tun-mtu"||f.Key=="inner-mtu"),"no_editable_inner_MTU");
   Need(store.Fields.Single(f=>f.Key=="dns.direct").Section=="网络","one_visible_direct_DNS");
   Need(store.Fields.Single(f=>f.Key=="dns.tunnel").Section=="网络","one_visible_tunnel_DNS");
   Need(store.Fields.Single(f=>f.Key=="direct-flow-hard").Section=="网络","Direct_quota_field_visible");
   Need(store.Fields.Single(f=>f.Key=="route-mode").Section=="网络","CN_route_mode_visible");
   Need(store.Fields.Single(f=>f.Key=="split-enable").Section=="网络" &&
     store.Fields.Single(f=>f.Key=="split-enable").Kind=="Bool",
     "H1835_actual_GUI_CN_split_toggle_source");
   Need(store.Fields.Single(f=>f.Key=="cn-rules-file").Section=="网络",
     "H1835_actual_GUI_CN_domain_rule_source");
   Need(!Convert.ToBoolean(store.Fields.Single(f=>f.Key=="split-enable").Default),
     "H1835_split_off_by_default");
   Need(store.Fields.Single(f=>f.Key=="route-mode").Label.Contains("域名"),"CN_route_mode_label_shows_domain_union");
   Need(store.Fields.Single(f=>f.Key=="route-mode").Hint.Contains("QNAME"),"CN_route_mode_hint_explicit_single_dns_direction");
   Need(Convert.ToInt32(store.Fields.Single(f=>f.Key=="direct-flow-hard").Default)==16384,"Direct_quota_default");
   Need(store.Fields.Single(f=>f.Key=="dns4").Managed,"retired_legacy_dns4_not_editable");
   Need(!store.Effective(p).ContainsKey("dns4"),"new_profile_has_no_legacy_dns4");

   using(var cli=new ClientSession(store))
   using(var form=new MainForm(store,cli,()=>Dependencies.Detect(store))){
    form.Show();Application.DoEvents();
    // Actual original-Go read-only v2 preflight: no old WFP guard literal,
    // no driver Apply and never a false Ready promotion.
    var preflight=form.ReadNativeProductPreflightAsync();
    var clock=System.Diagnostics.Stopwatch.StartNew();
    while(!preflight.IsCompleted && clock.ElapsedMilliseconds<23000){
      Application.DoEvents();
      System.Threading.Thread.Sleep(25);
    }
    Need(preflight.IsCompleted,"v2_native_readonly_preflight_returns_bounded");
    Need(preflight.GetAwaiter().GetResult()=="absent","gui_v2_preflight_live_go_cli_readback_absent");
    Need(!File.Exists(store.InRoot("data/network-state.json")) &&
         !File.Exists(store.InRoot("data/network-state.json.n4-owned-wal")),
         "preflight_never_makes_network_state");

    var readOnly=(Label)typeof(MainForm).GetField("mtuStatus",
      System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(form);
    Need(readOnly.Text.Contains("未知")&&readOnly.Text.Contains("未验证"),
      "effective_outer_auto_inner_OS_receipts_start_unknown");
    form.LoadEditor();
    form.SetEditor("server-ip","EDGE.Example.Test.");
    form.SetEditor("server-name","borrow.example.org");
    form.SetEditor("mtu","1460");
    form.SetEditor("dns.direct","223.5.5.5");
    form.SetEditor("dns.tunnel","1.1.1.1");
    form.SetEditor("route-mode","bypass-lan-cn");
    var editors=(Dictionary<string,Control>)typeof(MainForm).GetField(
      "editors",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(form);
    Need(((ComboBox)editors["route-mode"]).SelectedItem.ToString().Contains("域名"),
      "CN_visible_dropdown_option_IP_domain_union");
    form.SetEditor("direct-flow-hard","2");
    store.WriteAtomic("data/h1835-cn-domains.txt","cn.example\n=exact.cn\n");
    form.SetEditor("split-enable",true);
    form.SetEditor("cn-rules-file","data/h1835-cn-domains.txt");
    form.SaveEditor();
    Correct(Check(store,p,"data/h1663-normal.json",cli),"server-ip","EDGE.Example.Test.");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"server-name","borrow.example.org");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"mtu","1460");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"dns.direct","223.5.5.5");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"dns.tunnel","1.1.1.1");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"route-mode","bypass-lan-cn");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"direct-flow-hard","2");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"split-enable","true");
    Correct(Check(store,p,"data/h1663-normal.json",cli),"cn-rules-file",
      store.InRoot("data/h1835-cn-domains.txt"));
    Need(Convert.ToBoolean(p.Values["split-enable"]) &&
      Convert.ToString(p.Values["cn-rules-file"])=="data/h1835-cn-domains.txt",
      "H1835_real_assembled_GUI_saved_cn_effective_portable");
    // A real Go parser must reject missing CN domain rules with explicit
    // split enabled. GUI cannot silently fall back to the old tunnel path.
    form.SetEditor("cn-rules-file","");
    form.SaveEditor();
    bool missingCnDenied=false;
    try{Check(store,p,"data/h1837-missing-cn.json",cli);}
    catch(Exception){missingCnDenied=true;}
    Need(missingCnDenied,"H1837_real_Go_CLI_missing_CN_snapshot_fails_closed");
    form.SetEditor("cn-rules-file","data/h1835-cn-domains.txt");
    form.SaveEditor();
    Correct(Check(store,p,"data/h1663-normal.json",cli),"dns4","");
    var n=Check(store,p,"data/h1663-normal.json",cli);
    int inner=Convert.ToInt32(n["derived-inner-tun-mtu"]);
    Need(inner>0&&inner<1460,"native_Rust_inner_derived_only_no_GUI_rewrite");
    Need(Convert.ToInt32(p.Values["mtu"])==1460,"outer_kept_after_native_inner_read");
    form.SetEditor("direct-flow-hard","16385");form.SaveEditor();
    bool invalidCapRejected=false;
    try{Check(store,p,"data/h1663-bad-direct-cap.json",cli);}catch(Exception){invalidCapRejected=true;}
    Need(invalidCapRejected,"invalid_quota_rejected_by_real_Go_cli");
    form.SetEditor("direct-flow-hard","2");form.SaveEditor();

    // Validate explicit cold mode switch through the same real Go CLI,
    // without ever turning saved config into a fabricated OS Applied.
    form.SetEditor("route-mode","all");form.SaveEditor();
    Correct(Check(store,p,"data/h1811-all.json",cli),"route-mode","all");
    form.SetEditor("lanes","4");
    form.SetEditor("fec.mode","off");
    form.SaveEditor();
    bool rejectedGameSplit=false;
    try{Check(store,p,"data/h1835-game4-split-invalid.json",cli);}
    catch(Exception){rejectedGameSplit=true;}
    Need(rejectedGameSplit,"H1835_real_Go_CLI_rejects_unwired_Game4_CN_before_OS");
    form.SetEditor("split-enable",false);form.SaveEditor();
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
    form.SetEditor("route-mode","bypass-lan-cn");
    form.SetEditor("split-enable",true);
    form.SetEditor("direct-flow-hard","16384");
    form.SaveEditor();

    var invalid=new Dictionary<string,object>(store.Effective(p));
    invalid["derived-inner-tun-mtu"]=1000;
    bool denied=false;
    try{store.ImportValues(p,invalid);}catch(InvalidDataException){denied=true;}
    Need(denied,"derived_inner_cannot_import_into_GUI_profile");
    Need(Convert.ToInt32(p.Values["mtu"])==1460,"bad_inner_import_not_mutate_outer");
    form.Capture(store.InRoot("h1663-domain-mtu-winforms.png"));
   }
   var legacy=new Dictionary<string,object>(store.Effective(p));
   legacy.Remove("dns.tunnel");
   legacy["dns4"]="9.9.9.9,8.8.8.8";
   store.ImportValues(p,legacy);
   store.Save();
   Need(Convert.ToString(p.Values["dns.tunnel"])=="9.9.9.9","legacy_first_migrates_to_single_tunnel_DNS");
   Need(!p.Values.ContainsKey("dns4"),"legacy_backup_never_persisted");
   using(var cli2=new ClientSession(store)){
     var migrated=Check(store,p,"data/h1663-migrated.json",cli2);
     Correct(migrated,"dns.direct","223.5.5.5");
     Correct(migrated,"dns.tunnel","9.9.9.9");
     Correct(migrated,"dns4","");
   }
   var conflict=new Dictionary<string,object>(store.Effective(p));
   conflict["dns4"]="8.8.8.8";
   bool rejected=false;
   try{store.ImportValues(p,conflict);}catch(InvalidDataException){rejected=true;}
   Need(rejected,"old_dns4_conflict_rejected");
   var reopen=new PortableStore(root);
   var saved=reopen.Book.Profiles.Single(x=>x.Id==p.Id);
   Need(Convert.ToInt32(saved.Values["mtu"])==1460,"reopen_retains_outer1460");
   Need(Convert.ToString(saved.Values["server-ip"])=="EDGE.Example.Test.","reopen_retains_server_domain");
   Need(Convert.ToString(saved.Values["server-name"])=="borrow.example.org","reopen_preserves_separate_verified_TLS_SNI");
   Need(Convert.ToString(saved.Values["dns.direct"])=="223.5.5.5","reopen_single_direct_DNS");
   Need(Convert.ToString(saved.Values["route-mode"])=="bypass-lan-cn","reopen_saved_CN_IP_DOMAIN_union_mode_cold_only");
   // ImportValues intentionally copies absolute exported CN source into
   // its own portable data/cn-rules-<profile> snapshot. Importing cannot
   // preserve the former relative filename; it MUST preserve the content
   // and the enabled setting while the read-only Go CLI accepts the new
   // exact owned path, without touching the network.
   string importedCN="data/cn-rules-"+p.Id+".txt";
   Need(Convert.ToBoolean(saved.Values["split-enable"]) &&
     Convert.ToString(saved.Values["cn-rules-file"])==importedCN &&
     File.ReadAllText(reopen.InRoot(importedCN)).Contains("cn.example"),
     "H1838_reopened_CN_split_import_uses_owned_copied_source");
   using(var importedCLI=new ClientSession(reopen)){
     var imported=Check(reopen,saved,"data/h1838-imported-effective.json",importedCLI);
     Correct(imported,"split-enable","true");
     Correct(imported,"cn-rules-file",reopen.InRoot(importedCN));
   }
   Need(Convert.ToInt32(saved.Values["direct-flow-hard"])==16384,"reopen_Direct_quota_default");
   Need(Convert.ToString(saved.Values["dns.tunnel"])=="9.9.9.9","reopen_migrated_single_tunnel_DNS");
   Need(!saved.Values.ContainsKey("dns4"),"reopen_never_restores_backup_DNS");
   Need(!File.Exists(store.InRoot("data/network-state.json")),"no_fake_OS_Applied_or_WAL");
   Console.WriteLine("PLAN029_H1663_WINFORMS_REAL_CLI_EFFECTIVE_BUILD_SCOPED_PASS_NO_DRIVER_NETWORK");
   return 0;
  }catch(Exception err){
   Console.Error.WriteLine("PLAN029_H1663_WINFORMS_REAL_CLI_CONFIG_FAIL "+err);
   return 1;
  }
 }
}
