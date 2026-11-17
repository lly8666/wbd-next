package org.wbdnext.rootclient;

public final class ServerAddressTest {
    private static void check(boolean ok,String why){
        if(!ok)throw new AssertionError(why);
    }
    public static void main(String[] args){
        check(ServerAddress.isIPv4Literal("192.168.1.2"),"literal");
        check(!ServerAddress.isDnsName("192.168.1.2"),"literal not DNS");
        check(ServerAddress.valid("edge.example.net"),"DNS bootstrap");
        check(ServerAddress.valid("xn--bcher-kva.example"),"ASCII IDNA");
        check(!ServerAddress.valid("256.2.3.4"),"invalid dotted numeric");
        check(!ServerAddress.valid("01.2.3.4"),"ambiguous dotted decimal");
        check(!ServerAddress.valid("foo..example"),"empty DNS label");
        check(!ServerAddress.valid("-bad.example"),"invalid label");
        check(!ServerAddress.valid("example.com/evil"),"shell unsafe name");
        check(!ServerAddress.valid("example.com "), "whitespace");
        check(!ServerAddress.valid("bad_name.example"),"DNS hostname only");
        System.out.println("ANDROID_ROOT_SERVER_IP_OR_PHYSICAL_DNS_HOST_GRAMMAR_PASS");
    }
}
