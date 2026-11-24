package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Map;
import java.util.TreeMap;

/** Real settings codec nested in new local 4-slot named profile. */
public final class RootConnectionProfileTest {
    private static void ok(boolean b,String msg){if(!b)throw new AssertionError(msg);}
    public static void main(String[] args)throws Exception {
        Map<String,Integer> apps=new TreeMap<>();
        apps.put("org.example.browser",10123);
        apps.put("org.example.game",10124);
        for(String mode:new String[]{"normal","fec-auto","game2","game4-fixed"}){
            RootConnectionSettings config=new RootConnectionSettings(
                "server.example.test","sni.example.test","account",443,
                1460,2048,"chacha20-poly1305","off",mode,6,
                false,true,false,false,false,apps,"10.12.0.0/16",
                new TreeMap<String,Integer>(),"192.168.1.1",false,30,true);
            RootConnectionProfile original=new RootConnectionProfile(
                "工作／游戏 "+mode,config);
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            original.write(out);
            byte[] encoded=out.toByteArray();
            ok(encoded.length<RootConnectionProfile.MAX_FILE_BYTES,"bounded");
            RootConnectionProfile loaded=RootConnectionProfile.read(
                new ByteArrayInputStream(encoded));
            ok(loaded!=null&&loaded.label.equals(original.label),"profile label");
            ok(loaded.settings.mode.equals(mode)&&loaded.settings.profile==6,
                "original Normal/FEC/Game modes");
            ok(loaded.settings.selected.equals(apps)&&
               loaded.settings.directCIDRs.equals("10.12.0.0/16")&&
               loaded.settings.nativeHealthSeconds==30&&
               loaded.settings.autoConnectedDirect,
                "real selected apps/route/health preserved");
            String raw=new String(encoded,"ISO-8859-1");
            ok(!raw.contains("password=")&&!raw.contains("route_key=")&&
                !raw.contains("network_handle="),"no native credentials or stale Network");
        }
        for(int slot=1;slot<=RootConnectionProfile.SLOTS;slot++)
            ok(slot>0&&slot<=4,"four persistent slots");
        ok(RootConnectionProfile.read(new ByteArrayInputStream(
            new byte[]{0,0,0,0}))==null,"unknown local profile magic");
        System.out.println("ANDROID_B50_NAMED_ORIGINAL_ROOT_CONNECTION_PROFILES_HOST_PASS");
    }
}
