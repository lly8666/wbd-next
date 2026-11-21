package org.wbdnext.rootclient;

public final class NetworkScopeGateTest {
    private static int assertions;
    private static void check(boolean ok,String name){
        assertions++;
        if(!ok)throw new AssertionError(name);
    }
    public static void main(String[] args){
        boolean rejected=false;
        try{new NetworkScopeGate(0);}catch(IllegalArgumentException e){rejected=true;}
        check(rejected,"reject zero handle");
        NetworkScopeGate g=new NetworkScopeGate(1234);
        check(g.selected(1234),"exact selected");
        check(!g.selected(5678),"unrelated handle");
        check(!g.lost(5678),"unrelated loss ignored");
        check(g.lost(1234),"selected loss");
        check(!g.changed(1234,true),"unchanged selected scope");
        check(g.changed(1234,false),"selected scope changed");
        check(!g.changed(5678,false),"unrelated scope change");
        check(!g.blocked(1234,false),"selected unblocked");
        check(g.blocked(1234,true),"selected blocked");
        check(!g.blocked(5678,true),"unrelated blocked");
        g.close();
        check(!g.lost(1234),"closed generation ignores lost");
        check(!g.changed(1234,false),"closed generation ignores changed");
        check(!g.blocked(1234,true),"closed generation ignores blocked");
        NetworkScopeGate next=new NetworkScopeGate(1234);
        check(next.selected(1234),"new generation with same handle works");
        check(next.changed(1234,false),"new generation reacts independently");
        System.out.println("ANDROID_NETWORK_CALLBACK_SCOPE_GATE_PASS assertions="+assertions);
    }
}
