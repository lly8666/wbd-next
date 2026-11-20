package org.wbdnext.rootclient;

// Only the original Go ELF may recover WBD-owned kernel state.
// POSIX command never flushes global iptables, main routes, DNS or VPN.
final class RootRecoveryCommand {
    private RootRecoveryCommand(){}
    static String build(String binary,String signedGo,String signedRust){
        if(!"wbd-v4-client-arm64".equals(binary)&&
           !"wbd-v4-client-amd64".equals(binary))
            throw new IllegalArgumentException("unsupported signed client ABI");
        for(String path:new String[]{signedGo,signedRust}){
            if(path==null||path.length()<2||path.length()>512||
               path.charAt(0)!='/'||path.indexOf('\n')>=0||
               path.indexOf('\r')>=0||path.indexOf('\0')>=0)
                throw new IllegalArgumentException("invalid trusted APK asset");
        }
        String bin=OriginalGoCommandArgs.shellQuote(binary);
        String go=OriginalGoCommandArgs.shellQuote(signedGo);
        String rust=OriginalGoCommandArgs.shellQuote(signedRust);
        StringBuilder s=new StringBuilder("set -eu; umask 077; ");
        s.append("test \"$(id -u)\" = 0; ");
        s.append("p='/data/local/tmp/wbd-next-root'; ");
        s.append("test -d \"$p\" && test ! -L \"$p\"; ");
        s.append("test \"$(stat -c '%u:%a' \"$p\")\" = '0:700'; ");
        s.append("if [ -e \"$p/owner.pid\" ]; then ");
        s.append("test -f \"$p/owner.pid\" && test ! -L \"$p/owner.pid\"; ");
        s.append("test \"$(stat -c '%u:%a:%h' \"$p/owner.pid\")\" = '0:600:1'; ");
        s.append("read pid expected generation < \"$p/owner.pid\"; ");
        s.append("case \"$pid\" in ''|*[!0-9]*) exit 71;; esac; ");
        s.append("case \"$expected\" in ''|*[!0-9]*) exit 72;; esac; ");
        s.append("case \"$generation\" in ''|*[!0-9a-f]*) exit 73;; esac; ");
        s.append("test \"$generation\" != '' && test \"$(printf %s \"$generation\" | wc -c)\" -eq 32; ");
        s.append("if [ -r \"/proc/$pid/stat\" ]; then ");
        s.append("set -- $(cat \"/proc/$pid/stat\"); ");
        s.append("if [ \"$22\" = \"$expected\" ]; then ");
        s.append("actual=$(readlink \"/proc/$pid/exe\"); ");
        s.append("test \"$actual\" = \"$p/\"").append(bin).append("; ");
        s.append("kill -TERM \"$pid\"; n=0; ");
        s.append("while [ \"$n\" -lt 100 ]; do ");
        s.append("if [ ! -r \"/proc/$pid/stat\" ]; then break; fi; ");
        s.append("set -- $(cat \"/proc/$pid/stat\"); ");
        s.append("if [ \"$22\" != \"$expected\" ]; then break; fi; ");
        s.append("n=$((n+1)); sleep 0.2; done; ");
        s.append("if [ -r \"/proc/$pid/stat\" ]; then ");
        s.append("set -- $(cat \"/proc/$pid/stat\"); ");
        s.append("test \"$22\" != \"$expected\" || exit 74; fi; ");
        s.append("fi; fi; fi; ");
        s.append("cp ").append(go).append(" \"$p/.recover-client.tmp\"; ");
        s.append("cp ").append(rust).append(" \"$p/.recover-engine.tmp\"; ");
        s.append("chmod 700 \"$p/.recover-client.tmp\"; ");
        s.append("chmod 600 \"$p/.recover-engine.tmp\"; ");
        s.append("mv -f \"$p/.recover-client.tmp\" \"$p/\"").append(bin).append("; ");
        s.append("mv -f \"$p/.recover-engine.tmp\" \"$p/libwbd_engine.so\"; ");
        s.append("LD_LIBRARY_PATH=\"$p\"; export LD_LIBRARY_PATH; ");
        s.append("\"$p/\"").append(bin).append(" --android-recover-owned-root; ");
        s.append("if [ -e \"$p/owner.pid\" ]; then rm \"$p/owner.pid\"; fi; ");
        s.append("echo WBD_PUBLIC_ROOT_RESTORE_COMPLETE");
        return s.toString();
    }
}
