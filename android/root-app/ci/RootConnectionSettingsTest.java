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
        RootConnectionSettings fixed=read(stored(sample(true,"fec-fixed")));
        check(fixed!=null&&fixed.allApps&&fixed.selected.isEmpty(),"all ordinary App scope");
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
        System.out.println("ANDROID_B22_LAST_CONNECTION_NO_BACKUP_PRESET_HOST_PASS");
    }
}
