package org.wbdnext.rootclient;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

// Host JVM builds the production exact Stop script and asks a real POSIX
// shell to parse it. java/Android compilation cannot catch a missing fi.
public final class RootStopCommandTest {
    private static int assertions;
    private static void check(boolean ok,String title){
        assertions++;
        if(!ok)throw new AssertionError(title);
    }
    public static void main(String[] args)throws Exception{
        String token="0123456789abcdef0123456789abcdef";
        String command=RootStopCommand.build(token);
        check(command.contains("'"+token+"'"),"root generation matched exactly");
        check(command.contains("owner.pid"),"owner file verified");
        check(command.contains("/proc/$pid/stat"),"kernel starttime checked");
        check(command.contains("/proc/$pid/exe"),"actual executable checked");
        check(command.contains("kill -TERM"),"only SIGTERM");
        check(!command.contains("pkill")&&!command.contains("killall"),
            "no wildcard process termination");
        check(command.contains("-lt 60"),"bounded stop startup wait");
        Process sh=new ProcessBuilder("sh","-n").start();
        sh.getOutputStream().write(command.getBytes(StandardCharsets.UTF_8));
        sh.getOutputStream().close();
        check(sh.waitFor(3,TimeUnit.SECONDS)&&sh.exitValue()==0,
            "generated production Stop script passes sh -n");
        for(String invalid:new String[]{"","invalid","0123456789ABCDEF0123456789ABCDEF"}){
            boolean rejected=false;
            try{RootStopCommand.build(invalid);}
            catch(IllegalArgumentException expected){rejected=true;}
            check(rejected,"invalid generation refused");
        }
        String x86=RootStopCommand.build(token,"wbd-v4-client-amd64");
        check(x86.contains("$p/wbd-v4-client-amd64"),"CI x86 exact native image");
        Process x86sh=new ProcessBuilder("sh","-n").start();
        x86sh.getOutputStream().write(x86.getBytes(StandardCharsets.UTF_8));
        x86sh.getOutputStream().close();
        check(x86sh.waitFor(3,TimeUnit.SECONDS)&&x86sh.exitValue()==0,
            "same POSIX Stop script supports x86 native ELF");
        boolean refused=false;
        try{RootStopCommand.build(token,"wbd-v4-client-arm");}
        catch(IllegalArgumentException expected){refused=true;}
        check(refused,"arbitrary executable path refused");
        System.out.println("ANDROID_ROOT_EXACT_STOP_POSIX_SYNTAX_PASS assertions="+assertions);
    }
}
