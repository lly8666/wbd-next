package org.wbdnext.rootclient;

import java.util.List;

public final class OriginalGoCommandArgsTest {
    private static final String PASS="/data/user/0/org.wbdnext.rootclient/files/wbd-pass.secret";
    private static final String ROUTE="/data/user/0/org.wbdnext.rootclient/files/wbd-route.secret";
    private static final String INSTALL="/data/user/0/org.wbdnext.rootclient/files/wbd-installation-id";
    private static final String CN="/data/user/0/org.wbdnext.rootclient/no_backup/wbd-arm64-verified/wbd-cn-geosite.txt";
    private static final String CA="/data/user/0/org.wbdnext.rootclient/files/wbd-server-ca.pem";
    private static List<String> build(String peer,int[] uids,boolean allApps,int[] excluded,String ca){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            peer,443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,uids,allApps,excluded,ca);
    }
    private static void value(List<String> a,String flag,String expected){
        int i=a.indexOf(flag);
        if(i<0||i+1>=a.size()||!expected.equals(a.get(i+1)))
            throw new AssertionError("missing original Go flag/value "+flag);
    }
    private static void absent(List<String> a,String flag){
        if(a.contains(flag))throw new AssertionError("unexpected flag "+flag);
    }
    private static void rejected(Runnable callback){
        boolean blocked=false;
        try{callback.run();}catch(IllegalArgumentException expected){blocked=true;}
        if(!blocked)throw new AssertionError("invalid native argv accepted");
    }
    public static void main(String[] args){
        List<String> one=build("198.51.100.7",new int[]{10123},false,null,null);
        absent(one,"--tls-verify-server");
        value(one,"--mode","normal");
        if(!one.contains("--auto-ip"))throw new AssertionError("no protected /32");
        value(one,"--peer-ip","198.51.100.7");
        absent(one,"--peer-host");
        value(one,"--raw-interface","wlan0");
        value(one,"--android-network-handle","43123456");
        value(one,"--local-ip","192.0.2.10");
        value(one,"--peer-port","443");
        value(one,"--local-port","43900");
        value(one,"--tun-name","wbdv40");
        value(one,"--username","user-name");
        value(one,"--server-name","wbd.example.test");
        value(one,"--password-file",PASS);
        value(one,"--route-key-hex-file",ROUTE);
        value(one,"--installation-id-file",INSTALL);
        value(one,"--android-cn-geosite-file",CN);
        value(one,"--outer-mtu","1460");
        value(one,"--outer-repair","off");
        value(one,"--tun-fq-maxrate-mbps","0");
        value(one,"--tun-txqlen-packets","500");
        value(one,"--android-route-uid","10123");
        for(String f:new String[]{"--password","--route-key-hex","--tls-ca-pem",
            "--android-route-uids","--android-route-all-apps","--android-route-exclude-appids"})
            absent(one,f);
        List<String> host=build("server.example.test",new int[]{10123,110123},false,null,CA);
        value(host,"--peer-host","server.example.test");
        absent(host,"--peer-ip");
        value(host,"--android-route-uids","10123,110123");
        absent(host,"--tls-ca-pem");
        absent(host,"--tls-verify-server");
        List<String> strict=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","server.example.test",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,CA,true);
        if(!strict.contains("--tls-verify-server"))
            throw new AssertionError("strict TLS flag not sent");
        value(strict,"--tls-ca-pem",CA);
        List<String> all=build("203.0.113.10",null,true,new int[]{10111,10112},CA);
        if(!all.contains("--android-route-all-apps"))
            throw new AssertionError("no all-app route policy");
        value(all,"--android-route-exclude-appids","10111,10112");
        absent(all,"--tls-verify-server");
        absent(all,"--tls-ca-pem");
        absent(all,"--android-route-uids");
        absent(all,"--android-route-uid");
        rejected(()->build("198.51.100.7",null,false,null,null));
        rejected(()->build("198.51.100.7",new int[]{1000},false,null,null));
        rejected(()->build("198.51.100.7",new int[]{10123,10123},false,null,null));
        rejected(()->build("198.51.100.7",new int[]{10123},true,new int[]{10111,10112},null));
        rejected(()->build("198.51.100.7",null,true,new int[]{1000,10112},null));
        rejected(()->build("198.51.100.7",new int[]{10123},false,new int[]{10111,10112},null));
        rejected(()->build("198.51.100.7",null,true,null,null));
        rejected(()->build("198.51.100.7",new int[]{10123},false,null,
                          "not-an-absolute-path"));
        rejected(()->build("198.51.100.7",new int[]{10123},false,null,"/tmp/a\npath"));
        rejected(()->OriginalGoCommandArgs.build("wlan0",0,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null));
        // Validate exactly the production su -c POSIX quoting, including
        // a single quote, whitespace, dollar and shell command separators.
        String hostile="u' ; touch /tmp/wbd-should-never-exist; $(id) $HOME";
        try{
            Process p=new ProcessBuilder("sh","-c",
                "set -- "+OriginalGoCommandArgs.shellQuote(hostile)+
                "; printf '%s' \"$1\"").start();
            java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();
            byte[] buffer=new byte[128];
            int n;
            try(java.io.InputStream input=p.getInputStream()){
                while((n=input.read(buffer))!=-1)out.write(buffer,0,n);
            }
            if(p.waitFor()!=0||
               !hostile.equals(new String(out.toByteArray(),"UTF-8")))
                throw new AssertionError("production su shell quote changed argv");
        }catch(Exception unexpected){throw new AssertionError(unexpected);}
        rejected(()->OriginalGoCommandArgs.shellQuote(null));
        try{one.add("injected");throw new AssertionError("mutable production argv");}
        catch(UnsupportedOperationException expected){}
        System.out.println("ANDROID_A37_MAIN_TLS_DEFAULT_OFF_OPT_IN_HOST_PASS");
        System.out.println("ANDROID_ORIGINAL_APK_GO_CLI_ARGV_HOST_CONTRACT_PASS");
    }
}
