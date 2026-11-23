package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;

/** Exact production non-secret UI preset codec, host JVM, no Android/Root. */
public final class RootConnectionSettingsTest {
    private static void check(boolean ok,String why){
        if(!ok)throw new AssertionError(why);
    }
    private static byte[] stored(RootConnectionSettings v)throws Exception{
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        v.write(b);
        return b.toByteArray();
    }
    private static RootConnectionSettings read(byte[] b)throws Exception{
        return RootConnectionSettings.read(new ByteArrayInputStream(b));
    }
    private static RootConnectionSettings sample(boolean allApps,String mode){
        Map<String,Integer> selected=new TreeMap<>();
        if(!allApps){
            selected.put("org.example.browser",10123);
            selected.put("org.example.ping",10124);
        }
        return new RootConnectionSettings("wbd.example.test","tls.example.test",
            "example_user",443,1460,2048,"aes-128-gcm","off",mode,6,
            true,false,false,true,allApps,selected);
    }
    public static void main(String[] args)throws Exception{
        RootConnectionSettings a=sample(false,"fec-auto");
        byte[] bytes=stored(a);
        RootConnectionSettings b=read(bytes);
        check(b!=null,"round trip");
        check(b.peer.equals("wbd.example.test")&&
            b.sni.equals("tls.example.test")&&
            b.account.equals("example_user")&&
            b.port==443&&b.outerMTU==1460&&b.tunQueue==2048,
            "host/port/MTU/queue");
        check(b.mode.equals("fec-auto")&&b.profile==6&&b.cnSplitDNS&&
            b.verifyTLS&&!b.tunnelDNS&&
            !b.allApps&&b.selected.size()==2&&
            b.selected.get("org.example.browser")==10123,"mode, DNS and exact installed app identity");
        // B42 original Game2/off preset, no new serialization format.
        RootConnectionSettings game=new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","game2",1,
            false,false,false,false,true,new TreeMap<String,Integer>());
        RootConnectionSettings gameRestored=read(stored(game));
        check(gameRestored!=null&&"game2".equals(gameRestored.mode)&&
            !gameRestored.tunnelDNS&&!gameRestored.physicalDNS&&
            !gameRestored.cnSplitDNS,"Game2/off original preset round trip");
        boolean gameDNSRejected=false;
        try{new RootConnectionSettings("wbd.example.test","tls.example.test",
            "example_user",443,1460,500,"chacha20-poly1305","off","game2",1,
            false,true,false,false,true,new TreeMap<String,Integer>());}
        catch(IllegalArgumentException expected){gameDNSRejected=true;}
        check(gameDNSRejected,"Game2 App DNS currently has no original M4 owner");
        System.out.println("ANDROID_B42_GAME2_OFF_ORIGINAL_PRESET_HOST_PASS");
        RootConnectionSettings fixed=read(stored(sample(true,"fec-fixed")));
        check(fixed!=null&&fixed.allApps&&fixed.selected.isEmpty(),"all ordinary App scope");
        // B25: 16 packages may legally share one original native UID.
        // Previously the settings file silently truncated/rejected them.
        Map<String,Integer> shared=new TreeMap<>();
        for(int i=0;i<16;i++)shared.put("org.example.same"+i,10123);
        RootConnectionSettings sixteen=new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","normal",1,
            false,true,false,false,false,shared);
        RootConnectionSettings restored=read(stored(sixteen));
        check(restored!=null&&restored.selected.equals(shared),
            "round-trip all 16 packages sharing one original route UID");
        Map<String,Integer> tooManyUids=new TreeMap<>();
        for(int i=0;i<9;i++)tooManyUids.put("org.example.diff"+i,11010+i);
        boolean rejected=false;
        try{new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","normal",1,
            false,true,false,false,false,tooManyUids);}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"nine different UIDs are not a valid selected route");
        shared.put("org.example.more17",10123);
        rejected=false;
        try{new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","normal",1,
            false,true,false,false,false,shared);}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"more than sixteen packages cannot be saved");
        String raw=new String(bytes,StandardCharsets.ISO_8859_1);
        check(!raw.contains("password=")&&!raw.contains("route_key=")&&
            !raw.contains("ca_pem=")&&!raw.contains("network_handle="),
            "never save secret/CA or stale physical handle");
        check(read("version=2\npeer=wbd.example.test\n".getBytes(
            StandardCharsets.ISO_8859_1))==null,"unsupported settings version");
        check(read("version=1\nselected_count=999999\n".getBytes(
            StandardCharsets.ISO_8859_1))==null,"bad selected app count");
        try{
            new RootConnectionSettings("bad host","tls.example.test","acct",443,
                1460,500,"chacha20-poly1305","off","normal",1,
                false,true,false,false,true,new TreeMap<>());
            throw new AssertionError("invalid server accepted");
        }catch(IllegalArgumentException expected){}
        try{
            new RootConnectionSettings("198.51.100.7","tls.example.test","acct",443,
                1460,500,"chacha20-poly1305","flows","fec-auto",1,
                false,true,false,false,true,new TreeMap<>());
            throw new AssertionError("Auto startup padding accepted");
        }catch(IllegalArgumentException expected){}
        // B33: same user-selected real IPv4 direct prefixes survive SAF and
        // private local settings in the exact original Root App codec.
        RootConnectionSettings direct=new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","normal",1,
            false,true,false,false,true,new TreeMap<>(),
            "192.168.7.0/24,10.9.0.0/16");
        RootConnectionSettings directRestored=read(stored(direct));
        check(directRestored!=null&&
            directRestored.directCIDRs.equals("10.9.0.0/16,192.168.7.0/24"),
            "B33 direct IPv4 CIDRs lost through original settings codec");
        // B34: extra all-app bypass packages and physical DNS upstream are
        // nonsecret cold UI settings, never a restored UID route or Network.
        Map<String,Integer> bypass=new TreeMap<>();
        bypass.put("org.example.localgame",10333);
        bypass.put("org.example.lanclient",110444);
        RootConnectionSettings withBypass=new RootConnectionSettings(
            "wbd.example.test","tls.example.test","example_user",443,
            1460,500,"chacha20-poly1305","off","normal",1,
            false,false,true,false,true,new TreeMap<>(),
            "192.168.7.0/24",bypass,"192.168.1.1");
        RootConnectionSettings bypassRestored=read(stored(withBypass));
        check(bypassRestored!=null&&bypassRestored.bypass.equals(bypass)&&
            bypassRestored.physicalDNSUpstream.equals("192.168.1.1")&&
            bypassRestored.directCIDRs.equals("192.168.7.0/24"),
            "real all-app bypass/physical DNS/IPv4 direct preset lost");
        check(b.directCIDRs.isEmpty()&&
            b.physicalDNSUpstream.equals("223.5.5.5")&&b.bypass.isEmpty(),
            "older presets without new keys must restore original defaults");
        RootConnectionSettings follow=new RootConnectionSettings(
            "lan.example.test","tls.example.test","acct",443,1460,500,
            "chacha20-poly1305","off","normal",1,false,false,true,false,true,
            new TreeMap<>(),"",new TreeMap<>(),"192.168.1.1",true);
        RootConnectionSettings afterFollow=read(stored(follow));
        check(afterFollow!=null&&afterFollow.physicalDNSFollowNetwork&&
            afterFollow.physicalDNSUpstream.equals("192.168.1.1"),
            "B36 follow selected Network DNS lost through local/SAF settings");
        check(!b.physicalDNSFollowNetwork&&!bypassRestored.physicalDNSFollowNetwork,
            "B22/B34 old settings cannot implicitly enable Network DNS");
        RootConnectionSettings lowWake=new RootConnectionSettings(
            "lan.example.test","tls.example.test","acct",443,1460,500,
            "chacha20-poly1305","off","normal",1,false,false,true,false,true,
            new TreeMap<>(),"",new TreeMap<>(),"192.168.1.1",true,30);
        RootConnectionSettings lowWakeRestored=read(stored(lowWake));
        check(lowWakeRestored!=null&&lowWakeRestored.nativeHealthSeconds==30,
            "B37 original native Health setting not saved");
        check(b.nativeHealthSeconds==15&&bypassRestored.nativeHealthSeconds==15,
            "old presets must use original 15-second Health default");
        boolean healthInvalid=false;
        try{new RootConnectionSettings(
            "lan.example.test","tls.example.test","acct",443,1460,500,
            "chacha20-poly1305","off","normal",1,false,false,true,false,true,
            new TreeMap<>(),"",new TreeMap<>(),"192.168.1.1",true,60);}
        catch(IllegalArgumentException expected){healthInvalid=true;}
        check(healthInvalid,"unsupported native Health setting persisted");
        RootConnectionSettings onLink=new RootConnectionSettings(
            "lan.example.test","tls.example.test","acct",443,1460,500,
            "chacha20-poly1305","off","normal",1,false,false,true,false,true,
            new TreeMap<>(),"192.168.1.0/24",new TreeMap<>(),
            "192.168.1.1",false,15,true);
        RootConnectionSettings onLinkRestored=read(stored(onLink));
        check(onLinkRestored!=null&&onLinkRestored.autoConnectedDirect,
            "B38 live selected Network subnet auto-direct option not persisted");
        check(!b.autoConnectedDirect&&!lowWakeRestored.autoConnectedDirect,
            "old preset must never silently opt into LAN direct");
        System.out.println("ANDROID_B38_SELECTED_NETWORK_LOCAL_CIDR_PRESET_HOST_PASS");
        System.out.println("ANDROID_B37_ORIGINAL_NATIVE_HEALTH_PRESET_HOST_PASS");
        System.out.println("ANDROID_B36_SELECTED_NETWORK_DNS_PRESET_HOST_PASS");
        System.out.println("ANDROID_B34_ALL_APP_BYPASS_AND_PHYSICAL_DNS_PRESET_HOST_PASS");
        System.out.println("ANDROID_B33_DIRECT_CIDRS_ROOT_PRESET_CODEC_HOST_PASS");
        System.out.println("ANDROID_B22_LAST_CONNECTION_NO_BACKUP_PRESET_HOST_PASS");
        System.out.println("ANDROID_B25_PRESET_SELECTED_16_PACKAGES_8_UNIQUE_UIDS_HOST_PASS");
    }
}
