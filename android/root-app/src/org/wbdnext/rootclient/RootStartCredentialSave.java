package org.wbdnext.rootclient;

// Small production seam: local encrypted "remember me" is convenient, but
// MUST NEVER gate a real native Go/Rust connection. AndroidKeyStore may be
// unavailable or locked. Tests execute this exact class on a Host JVM.
final class RootStartCredentialSave {
    private RootStartCredentialSave(){}
    interface Action { void run() throws Exception; }
    static boolean attempt(Action action) {
        if(action==null)return false;
        try{
            action.run();
            return true;
        }catch(Exception unavailable){
            return false;
        }
    }
}
