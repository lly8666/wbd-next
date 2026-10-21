// PLAN020 test-only WinForms executable harness: no real WFP/route mutation.
// The compiled native WBD.exe is loaded for real MainForm event processing.
// This fake child process is NOT a product OS Applied qualification.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows.Forms;
using Wbd.Gui;

public static class M0Plan020GUIAuthorityHarness {
 sealed class Session : IClientSession {
  public event Action<string> Line;
  public bool Active { get; set; }
  public Task<Dictionary<string,object>> ValidateAsync(string _) {
   return Task.FromResult(new Dictionary<string,object>());
  }
  public Task StartAsync(string _) {Active=true;return Task.FromResult(0);}
  public Task StopAsync(){Active=false;return Task.FromResult(0);}
  public void Signal(string message){if(Line!=null)Line(message);}
  public void Dispose(){}
 }
 static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
 [STAThread]
 public static int Main(){
  try{
   Application.EnableVisualStyles();
   Application.SetCompatibleTextRenderingDefault(false);
   var root=AppDomain.CurrentDomain.BaseDirectory;
   var store=new PortableStore(root);
   var test=new Session{Active=true};
   using(var form=new MainForm(store,test,()=>new DependencyState{
      Admin=true,Npcap=true,Wintun=true,NpcapVersion="mocked-driver-for-ui-only"
   })){
    var flags=BindingFlags.NonPublic|BindingFlags.Instance;
    var idField=typeof(MainForm).GetField("connectedId",flags);
    var statusField=typeof(MainForm).GetField("state",flags);
    var drain=typeof(MainForm).GetMethod("Drain",flags);
    Require(idField!=null&&statusField!=null&&drain!=null,"native GUI fields not wired");
    var label=(Label)statusField.GetValue(form);
    idField.SetValue(form,store.Book.Profiles[0].Id);
    test.Signal("WBD_WINDOWS_CLIENT_READY");
    drain.Invoke(form,null);
    Require(label.Text.Contains("待验证")&&!label.Text.Contains("已连接"),
       "READY falsely promoted native Applied");
    test.Signal("WBD_WINDOWS_OS_APPLIED");
    drain.Invoke(form,null);
    Require(label.Text.Contains("已连接")&&label.Text.Contains("Applied"),
       "genuine explicit OS receipt channel not applied to UI");
    // Existing unrecovered route sidecar must make Stop fail without showing
    // disconnected, even when a child process returned successfully.
    var sidecar=store.InRoot("data/network-state.json.n4-owned-wal.routes");
    File.WriteAllText(sidecar,"intent-not-a-real-journal");
    bool denied=false;
    try {form.DisconnectAsync().GetAwaiter().GetResult();}
    catch(IOException){denied=true;}
    Require(denied&&!label.Text.Equals("未连接"),
       "WinForms falsely disconnected with owned WAL sidecar");
    File.Delete(sidecar);
    test.Active=true;
    form.DisconnectAsync().GetAwaiter().GetResult();
    Require(label.Text.Equals("未连接"),"WinForms successful empty-WAL disconnect incorrect");
   }
   Console.WriteLine("M0_PLAN020_REAL_COMPILED_WINFORMS_READY_NOT_APPLIED_AND_WAL_STOP_DENIAL_PASS");
   return 0;
  }catch(Exception error){
   Console.Error.WriteLine("M0_PLAN020_WINFORMS_GUI_TEST_FAIL "+error);
   return 1;
  }
 }
}
