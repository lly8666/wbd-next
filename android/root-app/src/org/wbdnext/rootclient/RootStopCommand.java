package org.wbdnext.rootclient;

// Cold-only, source-testable POSIX stop script for exactly one rooted owner.
// No PID/name wildcard, no broad routing, no shell data-plane loop.
final class RootStopCommand {
    private RootStopCommand(){}
    static String build(String token){
        if(token==null||!token.matches("[0-9a-f]{32}"))
            throw new IllegalArgumentException("invalid exact root generation");
        return "set -eu; p='/data/local/tmp/wbd-next-root'; n=0; "+
            "while [ \"$n\" -lt 60 ]; do "+
            "if [ -r \"$p/owner.pid\" ]; then "+
            "read pid expected generation < \"$p/owner.pid\"; "+
            "if [ \"$generation\" = '"+token+"' ]; then "+
            "case \"$pid\" in ''|*[!0-9]*) exit 51;; esac; "+
            "if [ -r \"/proc/$pid/stat\" ]; then "+
            "set -- $(cat \"/proc/$pid/stat\"); "+
            "if [ \"${22}\" = \"$expected\" ]; then "+
            "actual=$(readlink \"/proc/$pid/exe\"); "+
            "if [ \"$actual\" = \"$p/wbd-v4-client-arm64\" ]; then "+
            "kill -TERM \"$pid\"; exit 0; "+
            "fi; fi; fi; fi; fi; "+
            "n=$((n+1)); sleep 0.2; "+
            "done; exit 55";
    }
}
