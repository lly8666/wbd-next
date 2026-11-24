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
    final String peer,sni,account,cipher,padding,mode,directCIDRs,physicalDNSUpstream,ipv6Gateway,ipv6DirectCIDRs,tunnelDNSUpstream,game4CopySchedule;
    final boolean cnIPDirect;
    final int port,outerMTU,tunQueue,profile,nativeHealthSeconds,recoveryMode,rotationMinutes;
    final boolean verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,physicalDNSFollowNetwork,autoConnectedDirect,appTcpDNS,tetherSharing,systemDNS,systemDNS6;
    final Map<String,Integer> selected,bypass;
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,
            mode,profile,verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,"");
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,
            mode,profile,verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,
            directCIDRs,new TreeMap<>());
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,
            directCIDRs,bypass,RootPhysicalDNSUpstream.DEFAULT);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,
            mode,profile,verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,
            directCIDRs,bypass,physicalDNSUpstream,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,15);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,0,0);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,systemDNS6,"");
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6,String ipv6Gateway) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,systemDNS6,ipv6Gateway,"");
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6,String ipv6Gateway,String ipv6DirectCIDRs) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,systemDNS6,ipv6Gateway,ipv6DirectCIDRs,RootPhysicalDNSUpstream.TUNNEL_DEFAULT);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6,String ipv6Gateway,String ipv6DirectCIDRs,String tunnelDNSUpstream) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,systemDNS6,ipv6Gateway,ipv6DirectCIDRs,tunnelDNSUpstream,"stagger-4-50-140");
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6,String ipv6Gateway,String ipv6DirectCIDRs,String tunnelDNSUpstream,String game4CopySchedule) {
        this(peer,sni,account,port,outerMTU,tunQueue,cipher,padding,mode,profile,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,allApps,selected,directCIDRs,
            bypass,physicalDNSUpstream,followSelectedNetworkDNS,healthSeconds,
            autoConnectedDirect,recoveryMode,rotationMinutes,appTcpDNS,tetherSharing,systemDNS,systemDNS6,ipv6Gateway,ipv6DirectCIDRs,tunnelDNSUpstream,game4CopySchedule,false);
    }
    RootConnectionSettings(String peer,String sni,String account,
        int port,int outerMTU,int tunQueue,String cipher,String padding,
        String mode,int profile,boolean verifyTLS,boolean tunnelDNS,
        boolean physicalDNS,boolean cnSplitDNS,boolean allApps,
        Map<String,Integer> selected,String directCIDRs,Map<String,Integer> bypass,
        String physicalDNSUpstream,boolean followSelectedNetworkDNS,int healthSeconds,
        boolean autoConnectedDirect,int recoveryMode,int rotationMinutes,boolean appTcpDNS,boolean tetherSharing,boolean systemDNS,boolean systemDNS6,String ipv6Gateway,String ipv6DirectCIDRs,String tunnelDNSUpstream,String game4CopySchedule,boolean cnIPDirect) {
        this.cnIPDirect=cnIPDirect;
        this.game4CopySchedule=game4CopySchedule(game4CopySchedule);
        this.tunnelDNSUpstream=RootPhysicalDNSUpstream.tunnel(tunnelDNSUpstream);
        this.ipv6Gateway=ipv6Gateway(ipv6Gateway);
        this.ipv6DirectCIDRs=ipv6DirectCIDRs(ipv6DirectCIDRs);
        this.systemDNS=systemDNS;
        this.systemDNS6=systemDNS6;
        this.tetherSharing=tetherSharing;
        this.appTcpDNS=appTcpDNS;
        this.recoveryMode=recoveryMode;
        this.rotationMinutes=rotationMinutes;
        this.autoConnectedDirect=autoConnectedDirect;
        this.nativeHealthSeconds=healthSeconds;
        this.physicalDNSFollowNetwork=followSelectedNetworkDNS;
        this.physicalDNSUpstream=RootPhysicalDNSUpstream.canonical(physicalDNSUpstream);
        if(bypass==null)throw new IllegalArgumentException("missing bypass map");
        this.bypass=new TreeMap<>(bypass);
        this.directCIDRs=RootDirectIPv4.canonicalCSV(directCIDRs);
        this.peer=peer;this.sni=sni;this.account=account;
        this.port=port;this.outerMTU=outerMTU;this.tunQueue=tunQueue;
        this.cipher=cipher;this.padding=padding;this.mode=mode;
        this.profile=profile;this.verifyTLS=verifyTLS;
        this.tunnelDNS=tunnelDNS;this.physicalDNS=physicalDNS;
        this.cnSplitDNS=cnSplitDNS;this.allApps=allApps;
        this.selected=new TreeMap<>(selected);
        if(!valid())throw new IllegalArgumentException("invalid connection settings");
    }
    static String game4CopySchedule(String value){
        if(value==null||value.isEmpty())return "stagger-4-50-140";
        if(!oneOf(value,"immediate","stagger-4-20-60","stagger-4-50-140"))throw new IllegalArgumentException("invalid Game4 schedule");
        return value;
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
            (nativeHealthSeconds!=15&&nativeHealthSeconds!=30)||
           recoveryMode<0||recoveryMode>2||
           (rotationMinutes!=0&&rotationMinutes!=5&&rotationMinutes!=15&&rotationMinutes!=30)||
           !oneOf(cipher,"chacha20-poly1305","aes-128-gcm","aes-256-gcm")||
           !oneOf(padding,"off","tls","flows")||
           !oneOf(mode,"normal","fec-fixed","fec-auto","game2","game4",
               "game2-fixed","game4-fixed")||
           (tunnelDNS?1:0)+(physicalDNS?1:0)+(cnSplitDNS?1:0)>1||
           selected.size()>SelectedAppGroup.MAX_PACKAGES||
           (allApps&&!selected.isEmpty())||
           (!allApps&&!bypass.isEmpty())||bypass.size()>6)return false;
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
        // Only genuinely installed package/UID pairs may be restored to a
        // selected all-app bypass after fresh PackageManager validation.
        // The same app ID is excluded in every existing Android user profile.
        for(Map.Entry<String,Integer> x:bypass.entrySet()){
            int uid=x.getValue()==null?-1:x.getValue();
            if(!InstalledAppTarget.validPackage(x.getKey())||
                uid<10000||uid>1999999||
                uid%AllAppUIDPolicy.PER_USER<AllAppUIDPolicy.FIRST_APP_ID||
                uid%AllAppUIDPolicy.PER_USER>AllAppUIDPolicy.LAST_APP_ID)
                return false;
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
        p.setProperty("direct_cidrs",directCIDRs);
        p.setProperty("physical_dns_upstream",physicalDNSUpstream);
        p.setProperty("tunnel_dns_upstream",tunnelDNSUpstream);
        p.setProperty("game4_copy_schedule",game4CopySchedule);
        p.setProperty("cn_ip_direct",Boolean.toString(cnIPDirect));
        p.setProperty("physical_dns_follow_network",Boolean.toString(physicalDNSFollowNetwork));
        p.setProperty("native_health_seconds",Integer.toString(nativeHealthSeconds));
        p.setProperty("direct_lan_auto",Boolean.toString(autoConnectedDirect));
        // Saved preferences authorize nothing until the user presses START.
        p.setProperty("cold_recovery_mode",Integer.toString(recoveryMode));
        p.setProperty("cold_rotation_minutes",Integer.toString(rotationMinutes));
        p.setProperty("app_tcp_dns",Boolean.toString(appTcpDNS));
        p.setProperty("tether_sharing",Boolean.toString(tetherSharing));
        p.setProperty("system_dns",Boolean.toString(systemDNS));
        p.setProperty("system_dns6",Boolean.toString(systemDNS6));
        p.setProperty("ipv6_gateway",ipv6Gateway);
        p.setProperty("ipv6_direct_cidrs",ipv6DirectCIDRs);
        p.setProperty("selected_count",Integer.toString(selected.size()));
        p.setProperty("bypass_count",Integer.toString(bypass.size()));
        int bypassNumber=0;
        for(Map.Entry<String,Integer> x:bypass.entrySet()){
            p.setProperty("bypass_"+bypassNumber+"_package",x.getKey());
            p.setProperty("bypass_"+bypassNumber+"_uid",Integer.toString(x.getValue()));
            bypassNumber++;
        }
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
            int bypassCount=Integer.parseInt(p.getProperty("bypass_count","0"));
            if(bypassCount<0||bypassCount>6)return null;
            Map<String,Integer> bypass=new TreeMap<>();
            for(int i=0;i<bypassCount;i++){
                String pkg=p.getProperty("bypass_"+i+"_package","");
                int uid=Integer.parseInt(p.getProperty("bypass_"+i+"_uid","-1"));
                if(bypass.put(pkg,uid)!=null)return null;
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
                flag(p,"all_apps"),selected,p.getProperty("direct_cidrs",""),
                bypass,p.getProperty("physical_dns_upstream",RootPhysicalDNSUpstream.DEFAULT),
                p.containsKey("physical_dns_follow_network")&&
                    flag(p,"physical_dns_follow_network"),
                Integer.parseInt(p.getProperty("native_health_seconds","15")),
                p.containsKey("direct_lan_auto")&&flag(p,"direct_lan_auto"),
                Integer.parseInt(p.getProperty("cold_recovery_mode","0")),
                Integer.parseInt(p.getProperty("cold_rotation_minutes","0")),
                p.containsKey("app_tcp_dns")&&flag(p,"app_tcp_dns"),
                p.containsKey("tether_sharing")&&flag(p,"tether_sharing"),
                p.containsKey("system_dns")&&flag(p,"system_dns"),
                p.containsKey("system_dns6")&&flag(p,"system_dns6"),p.getProperty("ipv6_gateway",""),p.getProperty("ipv6_direct_cidrs",""),p.getProperty("tunnel_dns_upstream",RootPhysicalDNSUpstream.TUNNEL_DEFAULT),p.getProperty("game4_copy_schedule","stagger-4-50-140"),p.containsKey("cn_ip_direct")&&flag(p,"cn_ip_direct"));
        }catch(IllegalArgumentException invalid){
            return null;
        }
    }
    // Numeric IPv6 only; Go owns canonical kernel prefix construction.
    static String ipv6DirectCIDRs(String raw){
        if(raw==null||raw.trim().isEmpty())return "";
        String[] entries=raw.trim().split(",",-1);
        if(entries.length>16)throw new IllegalArgumentException("最多16条IPv6直连CIDR");
        java.util.LinkedHashSet<String> prefixes=new java.util.LinkedHashSet<>();
        for(String item:entries){
            String[] pair=item.trim().split("/",-1);
            if(pair.length!=2||!pair[0].contains(":")||!pair[0].matches("[0-9a-fA-F:]+")||!pair[1].matches("[0-9]{1,3}"))
                throw new IllegalArgumentException("请输入IPv6 CIDR");
            int bits=Integer.parseInt(pair[1]);
            if(bits<1||bits>128)throw new IllegalArgumentException("IPv6 CIDR前缀长度须为1..128");
            try{
                if(!(java.net.InetAddress.getByName(pair[0]) instanceof java.net.Inet6Address))
                    throw new IllegalArgumentException("请输入IPv6 CIDR");
            }catch(java.net.UnknownHostException invalid){throw new IllegalArgumentException("请输入IPv6 CIDR",invalid);}
            prefixes.add(pair[0]+"/"+bits);
        }
        return String.join(",",prefixes);
    }
    static String ipv6Gateway(String raw){
        if(raw==null||raw.trim().isEmpty())return "";
        String ip=raw.trim();
        if(!ServerAddress.isIPv4Literal(ip))
            throw new IllegalArgumentException("IPv6兼容承载需要服务端私有TUN IPv4");
        String[] v=ip.split("\\.");
        int a=Integer.parseInt(v[0]),b=Integer.parseInt(v[1]);
        if(!(a==10||a==172&&b>=16&&b<=31||a==192&&b==168))
            throw new IllegalArgumentException("IPv6兼容承载需要服务端私有TUN IPv4");
        return ip;
    }
}
