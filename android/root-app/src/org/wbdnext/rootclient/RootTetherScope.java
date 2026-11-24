package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Build;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.net.Inet4Address;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Executor;

// Public API 36 tethering callback, reflected only to keep the existing
// SDK35 build fallback. No hidden API, root command or tethering mutation.
final class RootTetherScope implements AutoCloseable {
    interface Listener { void changed(List<RootTetherScope> scopes); }
    final String iface,subnet;
    final int index;
    private Object manager,callback;
    private Method unregister;
    private RootTetherScope(String iface,String subnet,int index){
        this.iface=iface;this.subnet=subnet;this.index=index;
    }
    static RootTetherScope read(String iface){
        try{
            if(iface==null||!iface.matches("[A-Za-z0-9_.-]{1,15}"))return null;
            NetworkInterface n=NetworkInterface.getByName(iface);
            if(n==null||!n.isUp()||n.isLoopback()||n.getIndex()<=0)return null;
            RootTetherScope found=null;
            for(InterfaceAddress address:n.getInterfaceAddresses()){
                if(!(address.getAddress() instanceof Inet4Address)||!address.getAddress().isSiteLocalAddress())continue;
                int bits=address.getNetworkPrefixLength();
                if(bits<8||bits>30)continue;
                if(found!=null)return null;
                found=new RootTetherScope(iface,RootDirectIPv4.connectedSubnet(address.getAddress().getHostAddress(),bits),n.getIndex());
            }
            return found;
        }catch(Exception e){return null;}
    }
    boolean same(RootTetherScope other){
        return other!=null&&iface.equals(other.iface)&&subnet.equals(other.subnet)&&index==other.index;
    }
    @Override public String toString(){return iface+" · "+subnet;}
    static RootTetherScope watch(Context c,Listener listener)throws Exception{
        if(Build.VERSION.SDK_INT<36)throw new IllegalStateException("热点共享需要 Android 16 公共 tethering API");
        Class<?> type=Class.forName("android.net.TetheringManager");
        Class<?> cb=Class.forName("android.net.TetheringManager$TetheringEventCallback");
        Class<?> downstream=Class.forName("android.net.TetheringInterface");
        Method name=downstream.getMethod("getInterface");
        RootTetherScope handle=new RootTetherScope("","",0);
        handle.manager=c.getSystemService(type);
        if(handle.manager==null)throw new IllegalStateException("TetheringManager unavailable");
        handle.unregister=type.getMethod("unregisterTetheringEventCallback",cb);
        handle.callback=Proxy.newProxyInstance(cb.getClassLoader(),new Class<?>[]{cb},(proxy,method,args)->{
            switch(method.getName()){
                case "hashCode":return System.identityHashCode(proxy);
                case "equals":return proxy==args[0];
                case "toString":return "WBD tether callback";
                case "onTetheredInterfacesChanged":
                    if(handle.callback==null)return null;
                    List<RootTetherScope> result=new ArrayList<>();
                    if(args!=null&&args.length==1&&args[0] instanceof Set){
                        for(Object item:(Set<?>)args[0]){
                            RootTetherScope scope=read((String)name.invoke(item));
                            if(scope!=null)result.add(scope);
                        }
                    }
                    Collections.sort(result,(x,y)->x.iface.compareTo(y.iface));
                    listener.changed(result);
                    return null;
                default:return null;
            }
        });
        try{type.getMethod("registerTetheringEventCallback",Executor.class,cb)
            .invoke(handle.manager,c.getMainExecutor(),handle.callback);}
        catch(Exception e){handle.close();throw e;}
        return handle;
    }
    @Override public void close(){
        Object old=callback;callback=null;
        if(old!=null&&manager!=null&&unregister!=null)
            try{unregister.invoke(manager,old);}catch(Exception ignored){}
    }
}
