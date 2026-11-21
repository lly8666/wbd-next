package org.wbdnext.rootclient;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Map;
import java.util.Properties;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * B22: settings for the next manual original-Go START.
 * Never contains password, RouteKey, CA PEM, raw log, physical Network
 * handle or an already-authorized UID route. A restored app is selected
 * only after its package AND current installed UID still match.
 */
final class RootConnectionSettings {
    final String peer,sni,account,cipher,padding,mode;
    final int port,outerMTU,tunQueue,profile;
    final boolean verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps;
    final Map<String,Integer> selected;
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected) {
        this.peer=peer;this.sni=sni;this.account=account;
        this.port=port;this.outerMTU=outerMTU;this.tunQueue=tunQueue;
        this.cipher=cipher;this.padding=padding;this.mode=mode;
        this.profile=profile;this.verifyTLS=verifyTLS;
        this.tunnelDNS=tunnelDNS;this.physicalDNS=physicalDNS;
        this.cnSplitDNS=cnSplitDNS;this.allApps=allApps;
        this.selected=new TreeMap<>(selected);
        if(!valid())throw new IllegalArgumentException("invalid connection settings");
    }
    private static boolean oneOf(String value,String... options){
        if(value==null)return false;
        for(String x:options)if(x.equals(value))return true;
        return false;
    }
    private boolean valid(){
        if(!ServerAddress.valid(peer)||sni==null||sni.isEmpty()||sni.length()>253||
           account==null||account.isEmpty()||account.length()>128||
           port<1||port>65535||outerMTU<576||outerMTU>1500||
           (tunQueue!=500&&tunQueue!=2048)||profile<0||profile>6||
           !oneOf(cipher,"chacha20-poly1305","aes-128-gcm","aes-256-gcm")||
           !oneOf(padding,"off","tls","flows")||
           !oneOf(mode,"normal","fec-fixed","fec-auto")||
           (!"normal".equals(mode)&&!"off".equals(padding))||
           (tunnelDNS?1:0)+(physicalDNS?1:0)+(cnSplitDNS?1:0)>1||
           selected.size()>SelectedAppGroup.MAX_PACKAGES||
           (allApps&&!selected.isEmpty()))return false;
        // The route actually supports up to 16 package names sharing no
        // more than 8 distinct UIDs. The B22 preset incorrectly capped
        // PACKAGE count at 8, so a valid 9..16 package selection vanished
        // on Activity restart. Match the original selected-App contract.
        TreeSet<Integer> uids=new TreeSet<>();
        for(Map.Entry<String,Integer> x:selected.entrySet()){
            int uid=x.getValue()==null?-1:x.getValue();
            if(!InstalledAppTarget.validPackage(x.getKey())||
               uid<10000||uid>1999999)return false;
            uids.add(uid);
            if(uids.size()>SelectedAppGroup.MAX_UIDS)return false;
        }
        return true;
    }
    void write(OutputStream out)throws IOException{
        Properties p=new Properties();
        p.setProperty("version","1");
        p.setProperty("peer",peer);
        p.setProperty("sni",sni);
        p.setProperty("account",account);
        p.setProperty("port",Integer.toString(port));
        p.setProperty("outer_mtu",Integer.toString(outerMTU));
        p.setProperty("tun_queue",Integer.toString(tunQueue));
        p.setProperty("cipher",cipher);
        p.setProperty("padding",padding);
        p.setProperty("fec_mode",mode);
        p.setProperty("fec_profile",Integer.toString(profile));
        p.setProperty("tls_verify",Boolean.toString(verifyTLS));
        p.setProperty("tunnel_dns",Boolean.toString(tunnelDNS));
        p.setProperty("physical_dns",Boolean.toString(physicalDNS));
        p.setProperty("cn_split_dns",Boolean.toString(cnSplitDNS));
        p.setProperty("all_apps",Boolean.toString(allApps));
        p.setProperty("selected_count",Integer.toString(selected.size()));
        int i=0;
        for(Map.Entry<String,Integer> x:selected.entrySet()){
            p.setProperty("selected_"+i+"_package",x.getKey());
            p.setProperty("selected_"+i+"_uid",Integer.toString(x.getValue()));
            i++;
        }
        p.store(out,"WBD Root connection UI only; no secrets");
    }
    private static boolean flag(Properties p,String key){
        String s=p.getProperty(key,"");
        if("true".equals(s))return true;
        if("false".equals(s))return false;
        throw new IllegalArgumentException("invalid setting flag");
    }
    static RootConnectionSettings read(InputStream in)throws IOException{
        Properties p=new Properties();
        p.load(in);
        if(!"1".equals(p.getProperty("version")))return null;
        try{
            int count=Integer.parseInt(p.getProperty("selected_count","-1"));
            if(count<0||count>SelectedAppGroup.MAX_PACKAGES)return null;
            Map<String,Integer> selected=new TreeMap<>();
            for(int i=0;i<count;i++){
                String pkg=p.getProperty("selected_"+i+"_package","");
                int uid=Integer.parseInt(p.getProperty("selected_"+i+"_uid","-1"));
                if(selected.put(pkg,uid)!=null)return null;
            }
            return new RootConnectionSettings(
                p.getProperty("peer",""),p.getProperty("sni",""),
                p.getProperty("account",""),
                Integer.parseInt(p.getProperty("port","-1")),
                Integer.parseInt(p.getProperty("outer_mtu","-1")),
                Integer.parseInt(p.getProperty("tun_queue","-1")),
                p.getProperty("cipher",""),p.getProperty("padding",""),
                p.getProperty("fec_mode",""),
                Integer.parseInt(p.getProperty("fec_profile","-1")),
                flag(p,"tls_verify"),flag(p,"tunnel_dns"),
                flag(p,"physical_dns"),flag(p,"cn_split_dns"),
                flag(p,"all_apps"),selected);
        }catch(IllegalArgumentException invalid){
            return null;
        }
    }
}
