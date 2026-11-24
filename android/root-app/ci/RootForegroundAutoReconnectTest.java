package org.wbdnext.rootclient;
public final class RootForegroundAutoReconnectTest {
    private static void ok(boolean v,String why){if(!v)throw new AssertionError(why);}
    public static void main(String[] args){
        RootForegroundAutoReconnect p=new RootForegroundAutoReconnect();
        ok(!p.complete(true,true,true),"no unarmed restart");
        p.arm();p.onNetworkStop(false);
        ok(p.armed()&&!p.pending(),"other stops unchanged");
        p.onNetworkStop(true);
        ok(p.pending()&&!p.armed(),"selected Network event");
        ok(!p.complete(false,true,true)&&p.pending(),"wait for Go/Rust owner");
        ok(!p.complete(true,false,true)&&!p.pending(),"missing joined Stop");
        p.arm();p.onNetworkStop(true);
        ok(!p.complete(true,true,false)&&!p.pending(),"no physical target");
        p.arm();p.onNetworkStop(true);
        ok(p.complete(true,true,true),"old Stop and new physical target");
        ok(!p.complete(true,true,true),"only once");
        p.arm();p.onNetworkStop(true);p.cancel();
        ok(!p.pending()&&!p.complete(true,true,true),"manual Stop/pause cancels");
        System.out.println("ANDROID_B60_FOREGROUND_AUTOMATIC_COLD_NETWORK_HOST_PASS");
    }
}
