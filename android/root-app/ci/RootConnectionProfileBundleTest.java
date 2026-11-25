package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;

/** Host-execute the actual ten-slot SAF codec, no fake Root or packets. */
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
                443+i,1460-i,500,"aes-128-gcm","off",modes[i%modes.length],i%7,
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
        ok(restored!=null&&restored.length==10,"all ten slots");
        for(int i=0;i<restored.length;i++){
            if(i==2){ok(restored[i]==null,"empty slot");continue;}
            ok(restored[i]!=null&&restored[i].label.equals("配置"+i),
                "name restored");
            ok(restored[i].settings.mode.equals(modes[i%modes.length])&&
                restored[i].settings.port==443+i&&restored[i].settings.outerMTU==1460-i&&
                restored[i].settings.nativeHealthSeconds==30&&
                restored[i].settings.selected.equals(slots[i].settings.selected),
                "real Go/Rust cold settings and app UIDs restored");
        }
        // Original four-slot v1 file is still readable and does not
        // describe or overwrite the six newly added slots.
        ByteArrayOutputStream legacyRaw=new ByteArrayOutputStream();
        java.io.DataOutputStream legacy=new java.io.DataOutputStream(legacyRaw);
        legacy.writeInt(0x57425042);legacy.writeInt(4);
        for(int i=0;i<4;i++){
            if(slots[i]==null){legacy.writeInt(0);continue;}
            ByteArrayOutputStream one=new ByteArrayOutputStream();
            slots[i].write(one);legacy.writeInt(one.size());one.writeTo(legacy);
        }
        RootConnectionProfile[] old=RootConnectionProfileBundle.read(new ByteArrayInputStream(legacyRaw.toByteArray()));
        ok(old!=null&&old.length==4&&old[0].label.equals(slots[0].label)&&old[2]==null,"old four-slot backup");
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
        RootConnectionProfileBundle.Entry[] full=new RootConnectionProfileBundle.Entry[10];
        for(int i=0;i<full.length;i++)if(slots[i]!=null)
            full[i]=new RootConnectionProfileBundle.Entry(slots[i],"密码"+i+"-example","RouteKey"+i,
                i==0?new String(new char[100000]).replace('\0','a'):"-----BEGIN CERTIFICATE-----\nfixture"+i+"\n-----END CERTIFICATE-----");
        ByteArrayOutputStream whole=new ByteArrayOutputStream();
        RootConnectionProfileBundle.writeComplete(whole,full);
        RootConnectionProfileBundle.Entry[] loaded=RootConnectionProfileBundle.readComplete(new ByteArrayInputStream(whole.toByteArray()));
        ok(loaded!=null&&loaded.length==10&&loaded[2]==null,"full slot roundtrip");
        for(int i=0;i<full.length;i++)if(full[i]!=null){
            ok(loaded[i].password.equals(full[i].password)&&loaded[i].routeKey.equals(full[i].routeKey)&&
                loaded[i].ca.equals(full[i].ca),"complete credentials and large CA restored");
            ByteArrayOutputStream expected=new ByteArrayOutputStream(),actual=new ByteArrayOutputStream();
            full[i].profile.write(expected);loaded[i].profile.write(actual);
            ok(java.util.Arrays.equals(expected.toByteArray(),actual.toByteArray()),"all serialized settings equal");
        }
        RootConnectionProfileBundle.Entry[] legacyFull=RootConnectionProfileBundle.readComplete(new ByteArrayInputStream(legacyRaw.toByteArray()));
        ok(legacyFull.length==4&&legacyFull[0].password.isEmpty()&&legacyFull[2]==null,"legacy migration");
        byte[] truncated=java.util.Arrays.copyOf(whole.toByteArray(),whole.size()-1);
        ok(RootConnectionProfileBundle.readComplete(new ByteArrayInputStream(truncated))==null,"truncated full backup");
        System.out.println("ANDROID_B124_COMPLETE_SERVER_BACKUP_ALL_FIELDS_ROUNDTRIP_PASS");
        System.out.println("ANDROID_B53_FOUR_NAMED_ORIGINAL_PROFILE_SAF_TRANSFER_HOST_PASS");
    }
}
