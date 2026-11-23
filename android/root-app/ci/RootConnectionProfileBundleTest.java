package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;

/** Host-execute the actual four-slot SAF codec, no fake Root or packets. */
public final class RootConnectionProfileBundleTest {
    private static void ok(boolean value,String why){
        if(!value)throw new AssertionError(why);
    }
    public static void main(String[] args)throws Exception {
        RootConnectionProfile[] slots=
            new RootConnectionProfile[RootConnectionProfile.SLOTS];
        String[] modes={"normal","fec-fixed","game2", "game4-fixed"};
        for(int i=0;i<slots.length;i++){
            if(i==2)continue; // empty slot survives roundtrip
            Map<String,Integer> apps=new TreeMap<>();
            apps.put("org.example.app"+i,10001+i);
            RootConnectionSettings settings=new RootConnectionSettings(
                "server"+i+".example.test","sni.example.test","account",
                443+i,1460,500,"aes-128-gcm","off",modes[i],i,
                false,true,false,false,false,apps,"10.42.0.0/16",
                new TreeMap<String,Integer>(),"192.168.1.1",false,30,true);
            slots[i]=new RootConnectionProfile("配置"+i,settings);
        }
        ByteArrayOutputStream raw=new ByteArrayOutputStream();
        RootConnectionProfileBundle.write(raw,slots);
        byte[] encoded=raw.toByteArray();
        ok(encoded.length<RootConnectionProfileBundle.MAX_BYTES,"bounded");
        RootConnectionProfile[] restored=RootConnectionProfileBundle.read(
            new ByteArrayInputStream(encoded));
        ok(restored!=null&&restored.length==4,"all four slots");
        for(int i=0;i<restored.length;i++){
            if(i==2){ok(restored[i]==null,"empty slot");continue;}
            ok(restored[i]!=null&&restored[i].label.equals("配置"+i),
                "name restored");
            ok(restored[i].settings.mode.equals(modes[i])&&
                restored[i].settings.port==443+i&&
                restored[i].settings.nativeHealthSeconds==30&&
                restored[i].settings.selected.equals(slots[i].settings.selected),
                "real Go/Rust cold settings and app UIDs restored");
        }
        String content=new String(encoded,StandardCharsets.ISO_8859_1);
        ok(!content.contains("password=")&&
           !content.contains("route_key=")&&
           !content.contains("ca_pem=")&&
           !content.contains("network_handle="),"no secret/current Network exported");
        byte[] wrong=encoded.clone();
        wrong[0]=0;
        ok(RootConnectionProfileBundle.read(new ByteArrayInputStream(wrong))==null,
            "wrong bundle version");
        byte[] tail=new byte[encoded.length+1];
        System.arraycopy(encoded,0,tail,0,encoded.length);
        ok(RootConnectionProfileBundle.read(new ByteArrayInputStream(tail))==null,
            "no trailing profile");
        byte[] over=new byte[RootConnectionProfileBundle.MAX_BYTES+1];
        ok(RootConnectionProfileBundle.read(new ByteArrayInputStream(over))==null,
            "invalid large import");
        ok(RootConnectionProfileBundle.read(new ByteArrayInputStream(
            new byte[0]))==null,"empty import");
        System.out.println("ANDROID_B53_FOUR_NAMED_ORIGINAL_PROFILE_SAF_TRANSFER_HOST_PASS");
    }
}
