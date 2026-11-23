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
    private static List<String> withOuterMTU(int mtu){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,true,false,false,mtu);
    }
    private static List<String> withCipher(String cipher){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,true,false,false,1460,cipher);
    }
    private static List<String> withTunQueue(int packets){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",packets);
    }
    private static List<String> withPadding(String mode){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,mode);
    }
    private static List<String> withFec(String mode,int profile,String padding){
        return OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,
            padding,mode,profile);
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
        if(!one.contains("--android-tunnel-dns"))
            throw new AssertionError("real Android M4 tunnel UDP53 policy missing");
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
        value(one,"--record-cipher","chacha20-poly1305");
        value(withCipher("chacha20-poly1305"),"--record-cipher","chacha20-poly1305");
        value(withCipher("aes-128-gcm"),"--record-cipher","aes-128-gcm");
        value(withCipher("aes-256-gcm"),"--record-cipher","aes-256-gcm");
        rejected(()->withCipher("aes-192-gcm"));
        rejected(()->withCipher(""));
        rejected(()->withCipher(null));
        System.out.println("ANDROID_B9_REAL_AUTHENTICATED_AEAD_THREE_CIPHERS_GO_ARGV_HOST_PASS");
        value(withOuterMTU(1500),"--outer-mtu","1500");
        value(withOuterMTU(576),"--outer-mtu","576");
        rejected(()->withOuterMTU(575));
        rejected(()->withOuterMTU(1501));
        System.out.println("ANDROID_B8_ORIGINAL_GO_OUTER_MTU_APP_ARGV_HOST_PASS");
        value(one,"--outer-repair","off");
        value(one,"--tun-fq-maxrate-mbps","0");
        value(one,"--tun-txqlen-packets","500");
        value(one,"--startup-padding","off");
        value(withPadding("off"),"--startup-padding","off");
        value(withPadding("tls"),"--startup-padding","tls");
        value(withPadding("flows"),"--startup-padding","flows");
        rejected(()->withPadding("all"));
        rejected(()->withPadding(""));
        rejected(()->withPadding(null));
        System.out.println("ANDROID_B11B_ORIGINAL_GO_STARTUP_PADDING_PRODUCTION_ARGV_HOST_PASS");
        value(withFec("fec-fixed",0,"off"),"--mode","fec-fixed");
        value(withFec("fec-fixed",0,"off"),"--fec-profile","0");
        value(withFec("fec-fixed",6,"off"),"--fec-profile","6");
        absent(withFec("normal",1,"off"),"--fec-profile");
        value(withFec("fec-auto",1,"off"),"--mode","fec-auto");
        absent(withFec("fec-auto",1,"off"),"--fec-profile");
        rejected(()->withFec("fec-auto",1,"tls"));
        // B42 genuine Android App argv -> B41 original Go Game2/off.
        List<String> game2=OriginalGoCommandArgs.build("wlan0",43123456L,"192.0.2.10",
            "198.51.100.7",443,43900,"wbd.example.test","user-name",
            PASS,ROUTE,INSTALL,CN,new int[]{10123},false,null,null,
            false,false,false,false,1460,"chacha20-poly1305",500,
            "off","game2",1);
        value(game2,"--mode","game2");
        absent(game2,"--fec-profile");
        absent(game2,"--android-tunnel-dns");
        absent(game2,"--android-physical-dns");
        absent(game2,"--android-cn-dns-split");
        value(game2,"--android-route-uid","10123");
        if(!withFec("game2",1,"off").contains("--android-tunnel-dns"))
            throw new AssertionError("Game2 original tunnel DNS flag missing");
        rejected(()->withFec("game2",1,"tls"));
        System.out.println("ANDROID_B43_GAME2_TUNNEL_DNS_ARGV_HOST_PASS");
        System.out.println("ANDROID_B42_GAME2_ORIGINAL_GO_APP_ARGV_HOST_PASS");
        rejected(()->withFec("fec-fixed",7,"off"));
        rejected(()->withFec("fec-fixed",-1,"off"));
        rejected(()->withFec("fec-fixed",1,"tls"));
        System.out.println("ANDROID_B17_FIXED_EXPLICIT_NATIVE_GO_ARGV_HOST_PASS");
        System.out.println("ANDROID_B19_AUTO_EXPLICIT_NATIVE_GO_ARGV_HOST_PASS");
        value(withTunQueue(500),"--tun-txqlen-packets","500");
        value(withTunQueue(2048),"--tun-txqlen-packets","2048");
        rejected(()->withTunQueue(499));
        rejected(()->withTunQueue(2049));
        rejected(()->withTunQueue(0));
        System.out.println("ANDROID_B10_ORIGINAL_GO_OWNED_TUN_TXQLEN_REAL_ARGV_HOST_PASS");
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
        List<String> noDNS=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,false,false);
        absent(noDNS,"--android-tunnel-dns");
        absent(noDNS,"--android-physical-dns");
        value(noDNS,"--mode","normal");
        List<String> physicalDNS=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,false,true,true);
        if(!physicalDNS.contains("--android-physical-dns"))
            throw new AssertionError("actual physical DNS opt-in not forwarded");
        absent(physicalDNS,"--android-tunnel-dns");
        absent(physicalDNS,"--tls-verify-server");
        List<String> physicalAll=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            null,true,new int[]{10111,10112},null,false,false,true);
        if(!physicalAll.contains("--android-physical-dns"))
            throw new AssertionError("all ordinary App DNS option not forwarded");
        value(physicalAll,"--android-route-exclude-appids","10111,10112");
        List<String> split=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,false,true,true,true);
        if(!split.contains("--android-cn-dns-split"))
            throw new AssertionError("B5 original CN8503 split not enabled");
        absent(split,"--android-tunnel-dns");
        absent(split,"--android-physical-dns");
        absent(split,"--tls-verify-server");
        value(split,"--android-cn-geosite-file",CN);
        List<String> splitAll=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            null,true,new int[]{10111,10112},null,false,false,false,true);
        if(!splitAll.contains("--android-cn-dns-split"))
            throw new AssertionError("B5 ordinary all-app split not enabled");
        absent(splitAll,"--android-physical-dns");
        value(splitAll,"--android-route-exclude-appids","10111,10112");
        absent(one,"--android-cn-dns-split");
        absent(noDNS,"--android-cn-dns-split");
        System.out.println("ANDROID_B5_CN8503_SPLIT_SELECTED_ALL_APP_AND_LEGACY_GO_ARGV_HOST_PASS");
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
        System.out.println("ANDROID_B3_TUNNEL_DNS_ON_OFF_REAL_GO_ARGV_HOST_PASS");
        System.out.println("ANDROID_B4_REAL_PHYSICAL_DNS_SELECTED_ALL_APP_GO_ARGV_HOST_PASS");
        // B34: same original Go/Rust M4 owner; real physical DNS receives
        // a custom single upstream only when explicit physical/CN mode uses it.
        List<String> localPhysical=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,false,true,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","192.168.1.1");
        value(localPhysical,"--android-physical-dns-upstream-ipv4","192.168.1.1");
        absent(one,"--android-physical-dns-upstream-ipv4");
        rejected(()->OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,false,true,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","127.0.0.1"));
        System.out.println("ANDROID_B34_REAL_GO_CUSTOM_PHYSICAL_DNS_UPSTREAM_ARGV_PASS");
        // B35: the same physical IPv4 can serve ORIGINAL Go's cold peer
        // hostname lookup even when ordinary App DNS stays in the tunnel.
        List<String> customPeerBootstrap=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","lan.wbd.example",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","192.168.1.1");
        value(customPeerBootstrap,"--peer-host","lan.wbd.example");
        value(customPeerBootstrap,"--android-physical-dns-upstream-ipv4","192.168.1.1");
        List<String> unusedPhysical=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","192.168.1.1");
        absent(unusedPhysical,"--android-physical-dns-upstream-ipv4");
        System.out.println("ANDROID_B35_PEER_HOST_CUSTOM_PHYSICAL_DNS_COLD_ARGV_HOST_PASS");
        List<String> lowWake=OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","223.5.5.5",30);
        value(lowWake,"--android-native-health-seconds","30");
        value(one,"--android-native-health-seconds","15");
        rejected(()->OriginalGoCommandArgs.build(
            "wlan0",43123456L,"192.0.2.10","198.51.100.7",443,43900,
            "wbd.example.test","user-name",PASS,ROUTE,INSTALL,CN,
            new int[]{10123},false,null,null,
            false,true,false,false,1460,"chacha20-poly1305",500,"off",
            "normal",1,"","223.5.5.5",60));
        System.out.println("ANDROID_B37_ORIGINAL_RUST_HEALTH_15_30_REAL_GO_ARGV_HOST_PASS");
        System.out.println("ANDROID_ORIGINAL_APK_GO_CLI_ARGV_HOST_CONTRACT_PASS");
    }
}
