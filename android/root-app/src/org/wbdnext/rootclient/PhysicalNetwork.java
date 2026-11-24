package org.wbdnext.rootclient;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.IpPrefix;
import android.os.Build;
import java.net.Inet6Address;
import java.net.InterfaceAddress;
import android.net.Network;
import android.net.NetworkCapabilities;
import java.net.Inet4Address;
import java.net.NetworkInterface;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

// Only real ConnectivityManager Network instances: NEVER infer a netId
// from an interface name, use VpnService, or select the default after loss.
// Stateless and cold-only; native Bionic independently binds its RAW FD.
final class PhysicalNetwork {
    final long handle;
    final String interfaceName;
    final int ifindex;
    final int mtu;
    final String address;
    final String parentInterface,nat64Prefix;
    final boolean clat;
    final boolean hasInternetCapability;
    final boolean validatedByAndroid;
    private PhysicalNetwork(long handle,String name,int index,int mtu,String addr,
                            boolean internetCapability,boolean validated){
        this(handle,name,index,mtu,addr,internetCapability,validated,name,"");
    }
    private PhysicalNetwork(long handle,String name,int index,int mtu,String addr,
                            boolean internetCapability,boolean validated,
                            String parent,String nat64Prefix){
        this.handle=handle;this.interfaceName=name;
        this.ifindex=index;this.mtu=mtu;this.address=addr;
        this.parentInterface=parent;this.nat64Prefix=nat64Prefix;
        this.clat=!name.equals(parent);
        this.hasInternetCapability=internetCapability;
        this.validatedByAndroid=validated;
    }
    String title(){
        return interfaceName+"  "+address+"  MTU "+mtu+
            "  Network "+Long.toUnsignedString(handle)+
            (clat?"  [464XLAT · "+parentInterface+" · "+nat64Prefix+"]":"")+
            (hasInternetCapability
                ?(validatedByAndroid?"":"  [公网未验证：可连接局域网WBD]")
                :"  [仅本地链路：Android未声明Internet]");
    }
    boolean same(PhysicalNetwork other){
        return other!=null&&handle==other.handle&&
            interfaceName.equals(other.interfaceName)&&
            ifindex==other.ifindex&&mtu==other.mtu&&
            address.equals(other.address)&&parentInterface.equals(other.parentInterface)&&
            nat64Prefix.equals(other.nat64Prefix);
    }
    // B27: no INTERNET requirement. Many user-controlled WiFi/Ethernet
    // LAN links reach a nearby WBD server without Internet validation.
    // The SAME cold selection and Service callback policy is used; the
    // original kernel IPv4/interface/MTU check is still mandatory.
    static boolean physicalUnderlay(NetworkCapabilities caps){
        return caps!=null&&PhysicalUnderlayPolicy.accepts(
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN));
    }
    static List<PhysicalNetwork> available(Context context){
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null)return Collections.emptyList();
        ArrayList<PhysicalNetwork> out=new ArrayList<>();
        for(Network network:cm.getAllNetworks()){
            try{
                NetworkCapabilities caps=cm.getNetworkCapabilities(network);
                if(!physicalUnderlay(caps)){
                    continue;
                }
                LinkProperties link=cm.getLinkProperties(network);
                if(link==null||link.getInterfaceName()==null)continue;
                String name=link.getInterfaceName();
                NetworkInterface iface=NetworkInterface.getByName(name);
                if(iface==null||iface.getIndex()<=0||!iface.isUp())continue;
                int mtu=iface.getMTU();
                if(mtu<576||mtu>65535)continue;
                String addr=null;
                for(LinkAddress a:link.getLinkAddresses()){
                    if(a.getAddress() instanceof Inet4Address){
                        String ip=a.getAddress().getHostAddress();
                        if(!a.getAddress().isAnyLocalAddress()&&
                           !a.getAddress().isLoopbackAddress()&&
                           !a.getAddress().isLinkLocalAddress()){
                            // The Network handle and actual kernel interface
                            // MUST agree on this source IP before FakeTCP SYN.
                            java.util.Enumeration<java.net.InetAddress> owned=
                                iface.getInetAddresses();
                            while(owned.hasMoreElements()){
                                if(ip.equals(owned.nextElement().getHostAddress())){
                                    addr=ip;break;
                                }
                            }
                            if(addr!=null)break;
                        }
                    }
                }
                long handle=network.getNetworkHandle();
                if(handle==0)continue;
                if(addr==null){
                    PhysicalNetwork translated=existingClat(handle,link,caps);
                    if(translated!=null)out.add(translated);
                    continue;
                }
                out.add(new PhysicalNetwork(handle,name,iface.getIndex(),mtu,addr,
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET),
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)));
            }catch(Exception ignored){
                // A disappearing Network is never a candidate.
            }
        }
        return out;
    }
    // Android 11+ exposes the selected Network's NAT64 prefix publicly.
    // AOSP ClatCoordinator creates v4-<parent>, assigns an RFC7335 /32
    // and sets the translated MTU. Never create/reconfigure CLAT here.
    private static PhysicalNetwork existingClat(long handle,LinkProperties link,
                                                NetworkCapabilities caps){
        if(Build.VERSION.SDK_INT<30||link==null||caps==null)return null;
        try{
            String parent=link.getInterfaceName();
            String name=PhysicalUnderlayPolicy.clatInterface(parent);
            IpPrefix prefix=link.getNat64Prefix();
            if(name==null||prefix==null||!(prefix.getAddress() instanceof Inet6Address))return null;
            NetworkInterface parentNIC=NetworkInterface.getByName(parent);
            if(parentNIC==null||!parentNIC.isUp())return null;
            boolean nativeIPv4=false,globalIPv6=false;
            for(LinkAddress address:link.getLinkAddresses()){
                java.net.InetAddress ip=address.getAddress();
                if(ip instanceof Inet4Address&&!ip.isAnyLocalAddress()&&!ip.isLoopbackAddress()&&!ip.isLinkLocalAddress())
                    nativeIPv4=true;
                if(ip instanceof Inet6Address&&!ip.isAnyLocalAddress()&&!ip.isLoopbackAddress()&&
                   !ip.isLinkLocalAddress()&&!ip.isMulticastAddress()){
                    java.util.Enumeration<java.net.InetAddress> local=parentNIC.getInetAddresses();
                    while(local.hasMoreElements())if(ip.equals(local.nextElement())){globalIPv6=true;break;}
                }
            }
            NetworkInterface translated=NetworkInterface.getByName(name);
            if(translated==null||!translated.isUp()||translated.getIndex()<=0||
               translated.getMTU()<576||translated.getMTU()>65535)return null;
            String chosen=null;
            for(InterfaceAddress address:translated.getInterfaceAddresses()){
                if(!(address.getAddress() instanceof Inet4Address))continue;
                String candidate=address.getAddress().getHostAddress();
                if(!PhysicalUnderlayPolicy.useClat(nativeIPv4,globalIPv6,prefix.getPrefixLength(),
                    parent,name,candidate,address.getNetworkPrefixLength()))continue;
                if(chosen!=null)return null;
                chosen=candidate;
            }
            if(chosen==null)return null;
            return new PhysicalNetwork(handle,name,translated.getIndex(),translated.getMTU(),chosen,
                caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET),
                caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED),parent,prefix.toString());
        }catch(Exception ignored){return null;}
    }
    private boolean matchesClat(LinkProperties link){
        if(Build.VERSION.SDK_INT<30||link==null||!parentInterface.equals(link.getInterfaceName()))return false;
        try{
            IpPrefix prefix=link.getNat64Prefix();
            if(prefix==null||!nat64Prefix.equals(prefix.toString()))return false;
            NetworkInterface parent=NetworkInterface.getByName(parentInterface);
            NetworkInterface translated=NetworkInterface.getByName(interfaceName);
            if(parent==null||!parent.isUp()||translated==null||!translated.isUp()||
               translated.getIndex()!=ifindex||translated.getMTU()!=mtu)return false;
            boolean nativeIPv4=false,globalIPv6=false;
            for(LinkAddress a:link.getLinkAddresses()){
                java.net.InetAddress ip=a.getAddress();
                if(ip instanceof Inet4Address&&!ip.isAnyLocalAddress()&&!ip.isLoopbackAddress()&&!ip.isLinkLocalAddress())nativeIPv4=true;
                if(ip instanceof Inet6Address&&!ip.isAnyLocalAddress()&&!ip.isLoopbackAddress()&&!ip.isLinkLocalAddress()&&!ip.isMulticastAddress()){
                    java.util.Enumeration<java.net.InetAddress> local=parent.getInetAddresses();
                    while(local.hasMoreElements())if(ip.equals(local.nextElement())){globalIPv6=true;break;}
                }
            }
            for(InterfaceAddress a:translated.getInterfaceAddresses()){
                if(address.equals(a.getAddress().getHostAddress())&&
                   PhysicalUnderlayPolicy.useClat(nativeIPv4,globalIPv6,prefix.getPrefixLength(),
                       parentInterface,interfaceName,address,a.getNetworkPrefixLength()))return true;
            }
            return false;
        }catch(Exception e){return false;}
    }
    /**
     * B28: one pre-Root, off-UI resolution of a WBD server hostname.
     * For a non-VALIDATED local LAN, use Android's DNS bound to the EXACT
     * selected Network rather than original-Go's fixed public 223.5.5.5
     * bootstrap, which may be unreachable. This only obtains peer IPv4;
     * original Go still emits the real SYN and standard TLS/Admission.
     * It does NOT capture any ordinary Android app/netd DNS traffic.
     */
    // B36: only this actual ConnectivityManager.Network LinkProperties,
    // never the OS process-default resolver or a guessed interface DNS.
    // B38: read one selected physical IPv4 LinkAddress prefix, on demand
    // at START only. No default Network, global route or packet callback.
    static String selectedConnectedIPv4Subnet(Context context,PhysicalNetwork chosen){
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null||chosen==null)
            throw new IllegalArgumentException("没有选定的实体Network");
        for(Network network:cm.getAllNetworks()){
            if(network.getNetworkHandle()!=chosen.handle)continue;
            LinkProperties link=cm.getLinkProperties(network);
            if(!chosen.matchesLinkProperties(link))
                throw new IllegalArgumentException("实体Network子网已改变");
            // A CLAT /32 represents the translator itself, not an on-link
            // IPv4 LAN. Do not synthesize a direct route for 192.0.0.x.
            if(chosen.clat)return "";
            for(LinkAddress address:link.getLinkAddresses()){
                if(address.getAddress() instanceof Inet4Address&&
                   chosen.address.equals(address.getAddress().getHostAddress()))
                    return RootDirectIPv4.connectedSubnet(chosen.address,
                        address.getPrefixLength());
            }
            throw new IllegalArgumentException("选定Network没有可信IPv4本地前缀");
        }
        throw new IllegalArgumentException("选定Network已断开");
    }
    static String selectedDNSIPv4(Context context,PhysicalNetwork chosen){
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null||chosen==null)
            throw new IllegalArgumentException("没有所选Android Network");
        for(Network network:cm.getAllNetworks()){
            if(network.getNetworkHandle()!=chosen.handle)continue;
            LinkProperties link=cm.getLinkProperties(network);
            if(!chosen.matchesLinkProperties(link))
                throw new IllegalArgumentException("读取DNS时选中Network已变化");
            return RootPhysicalDNSUpstream.firstSelectedIPv4(link.getDnsServers());
        }
        throw new IllegalArgumentException("所选Network已断开");
    }
    static String coldPeerIPv4(Context context,PhysicalNetwork selected,
                               String peer)throws UnknownHostException{
        if(selected==null||!ServerAddress.valid(peer))
            throw new UnknownHostException("invalid original peer identity");
        if(ServerAddress.isIPv4Literal(peer)||selected.validatedByAndroid)
            return peer;
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null)throw new UnknownHostException("Android ConnectivityManager unavailable");
        for(Network network:cm.getAllNetworks()){
            if(network.getNetworkHandle()!=selected.handle)continue;
            // Preserve the original-Go physical 223.5.5.5 hostname
            // bootstrap when this optional scoped LAN DNS has no answer.
            // Only a confirmed local A record changes the cold peer to
            // --peer-ip; never use the default Android Network resolver.
            String ip=null;
            try{
                ip=PhysicalPeerIPv4Choice.select(network.getAllByName(peer));
            }catch(UnknownHostException unresolved){
                // Original Go still owns its existing public DNS fallback.
            }
            if(exact(context,selected.handle,selected.interfaceName,
                     selected.ifindex,selected.mtu,selected.address)==null)
                throw new UnknownHostException("physical LAN Network changed during DNS bootstrap");
            return ip==null?peer:ip;
        }
        throw new UnknownHostException("selected LAN Network no longer exists");
    }
    // Consume the callback's own LinkProperties, never synchronously
    // requery ConnectivityManager inside its asynchronous callback.
    boolean matchesLinkProperties(LinkProperties link){
        if(clat)return matchesClat(link);
        if(link==null||!interfaceName.equals(link.getInterfaceName()))return false;
        try{
            NetworkInterface iface=NetworkInterface.getByName(interfaceName);
            if(iface==null||!iface.isUp()||iface.getIndex()!=ifindex||
                iface.getMTU()!=mtu)return false;
            boolean linkAddress=false,kernelAddress=false;
            for(LinkAddress a:link.getLinkAddresses()){
                if(a.getAddress() instanceof Inet4Address &&
                    address.equals(a.getAddress().getHostAddress())){
                    linkAddress=true;break;
                }
            }
            java.util.Enumeration<java.net.InetAddress> addrs=iface.getInetAddresses();
            while(addrs.hasMoreElements()){
                if(address.equals(addrs.nextElement().getHostAddress())){
                    kernelAddress=true;break;
                }
            }
            return linkAddress&&kernelAddress;
        }catch(Exception ignored){return false;}
    }
    // B62 cold choice after prior original owner Stop; outside callbacks.
    static PhysicalNetwork recoveryTarget(Context context,long excluded){
        ConnectivityManager cm=context.getSystemService(ConnectivityManager.class);
        if(cm==null)return null;
        Network active=cm.getActiveNetwork();
        List<PhysicalNetwork> choices=available(context);
        long[] handles=new long[choices.size()];
        boolean[] validated=new boolean[choices.size()];
        for(int i=0;i<choices.size();i++){
            handles[i]=choices.get(i).handle;
            validated[i]=choices.get(i).validatedByAndroid;
        }
        int selected=RootColdRotation.recoveryIndex(active==null?0:active.getNetworkHandle(),
            excluded,handles,validated);
        return selected<0?null:choices.get(selected);
    }
    static PhysicalNetwork exact(Context ctx,long handle,String iface,
                                 int ifindex,int mtu,String address){
        for(PhysicalNetwork n:available(ctx)){
            if(n.handle==handle&&n.interfaceName.equals(iface)&&
               n.ifindex==ifindex&&n.mtu==mtu&&n.address.equals(address)){
                return n;
            }
        }
        return null;
    }
}
