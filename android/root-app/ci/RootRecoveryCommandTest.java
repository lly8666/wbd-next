package org.wbdnext.rootclient;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
public final class RootRecoveryCommandTest{
    public static void main(String[] args)throws Exception{
        for(String binary:new String[]{"wbd-v4-client-arm64","wbd-v4-client-amd64"}){
            String command=RootRecoveryCommand.build(binary,"/data/user/0/app/verifiedGo","/data/user/0/app/verifiedRust");
            for(String marker:new String[]{"--android-recover-owned-root","owner.pid",
                "/proc/$pid/stat","/proc/$pid/exe","kill -TERM","LD_LIBRARY_PATH",
                "WBD_PUBLIC_ROOT_RESTORE_COMPLETE"}){
                if(!command.contains(marker))throw new AssertionError("Restore marker missing: "+marker);
            }
            for(String forbidden:new String[]{"pkill","killall","iptables -F","ip route flush","ip rule flush"}){
                if(command.contains(forbidden))throw new AssertionError("unsafe global mutation");
            }
            Process p=new ProcessBuilder("sh","-n").start();
            p.getOutputStream().write(command.getBytes(StandardCharsets.UTF_8));
            p.getOutputStream().close();
            if(!p.waitFor(5,TimeUnit.SECONDS)||p.exitValue()!=0)
                throw new AssertionError("Restore POSIX syntax");
        }
        for(String name:new String[]{"sh","wbd-v4-client-arm64;exit",""}){
            boolean refused=false;
            try{RootRecoveryCommand.build(name,"/tmp/go","/tmp/rust");}
            catch(IllegalArgumentException expected){refused=true;}
            if(!refused)throw new AssertionError("arbitrary binary accepted");
        }
        for(String path:new String[]{"relative","/tmp/bad\nexit","/tmp/a\0b"}){
            boolean refused=false;
            try{RootRecoveryCommand.build("wbd-v4-client-arm64",path,"/tmp/rust");}
            catch(IllegalArgumentException expected){refused=true;}
            if(!refused)throw new AssertionError("unsafe path accepted");
        }
        System.out.println("ANDROID_A36_EXACT_RESTORE_SHELL_POSIX_HOST_PASS");
    }
}
