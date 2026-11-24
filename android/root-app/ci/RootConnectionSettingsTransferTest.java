package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;

/** Actual production SAF codec, host JVM; no Root/device I/O. */
public final class RootConnectionSettingsTransferTest {
    private static void check(boolean ok,String s){
        if(!ok)throw new AssertionError(s);
    }
    public static void main(String[] args)throws Exception{
        Map<String,Integer> apps=new TreeMap<>();
        for(int i=0;i<16;i++)apps.put("org.example.shared"+i,10123);
        RootConnectionSettings c=new RootConnectionSettings(
            "wbd.example.test","tls.example.test","acct",443,1460,500,
            "chacha20-poly1305","off","fec-auto",3,true,true,false,false,false,apps);
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        c.write(out);
        byte[] exported=out.toByteArray();
        RootConnectionSettings imported=RootConnectionSettingsTransfer.read(
            new ByteArrayInputStream(exported));
        check(imported!=null&&imported.selected.equals(apps),
            "SAF round trip 16 package identities");
        check(imported.peer.equals(c.peer)&&imported.sni.equals(c.sni)&&
            imported.mode.equals(c.mode)&&imported.tunnelDNS&&imported.verifyTLS,
            "SAF round trip same original Go cold parameters");
        String raw=new String(exported,StandardCharsets.ISO_8859_1);
        check(!raw.contains("password=")&&!raw.contains("route_key=")&&
            !raw.contains("ca_pem=")&&!raw.contains("network_handle="),
            "no password/key/CA/current network in export");
        check(RootConnectionSettingsTransfer.read(null)==null,"null");
        check(RootConnectionSettingsTransfer.read(
            new ByteArrayInputStream(new byte[0]))==null,"empty");
        check(RootConnectionSettingsTransfer.read(
            new ByteArrayInputStream(new byte[8193]))==null,"oversized");
        check(RootConnectionSettingsTransfer.read(
            new ByteArrayInputStream("version=2\n".getBytes(
                StandardCharsets.ISO_8859_1)))==null,"unknown version");
        check(RootConnectionSettingsTransfer.read(
            new ByteArrayInputStream("version=1\nselected_count=99\n".getBytes(
                StandardCharsets.ISO_8859_1)))==null,"bad preset");
        System.out.println("ANDROID_B26_SAF_NONSECRET_16_PACKAGE_PRESET_TRANSFER_HOST_PASS");
    }
}
